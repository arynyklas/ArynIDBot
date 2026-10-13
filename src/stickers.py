"""Sticker set owners and Bot API file ids, read from the documents themselves."""

import base64
import struct

from telethon.tl import types
from telethon.tl.tlobject import TLObject

# tdlib's persistent file id: `FileType::Sticker`, the flag telling that a file
# reference follows the DC, and the version bytes appended after the encoding.
# Sub-version 61 is what the Bot API stamped on sticker file ids in October 2026.
_STICKER_FILE_TYPE = 8
_FILE_REFERENCE_FLAG = 1 << 25
_PERSISTENT_ID_SUBVERSION = 61
_PERSISTENT_ID_VERSION = 4
# tdlib's `zero_encode` caps one run of zero bytes at this many.
_MAX_ZERO_RUN = 250


def decode_set_id(set_id: int) -> tuple[int, int]:
    """Returns `(owner user ID, owner's set increment ID)`."""

    # set id = (owner & 0x7FFFFFFF) << 32 | ~((owner >> 31) << 22 | set_increment_id)
    #
    # The high word carries only the low 31 bits of the owner's id; the complement of
    # the low word splits into a 10-bit band (owner >> 31) and a 22-bit per-owner set
    # counter, so the band is read arithmetically instead of matching markers.
    #
    # A set whose owner's id fit in 31 bits predates the band field: its low word is a
    # plain small counter, so its top byte is zero. A modern id cannot look like that -
    # bands 0-3 put 0xFF in that byte, bands 4-7 0xFE, and it reaches zero only at
    # band 1020.
    high_word = set_id >> 32
    low_word = set_id & 0xFFFFFFFF

    if low_word >> 24 == 0:
        return high_word, low_word

    return high_word + (((~low_word & 0xFFFFFFFF) >> 22) << 31), ~low_word & 0x3FFFFF


def sticker_set_id(document: types.TypeDocument | None) -> int | None:
    """Set ID carried by a sticker or custom emoji document; no GetStickerSet round trip."""
    if not isinstance(document, types.Document):
        return None

    for attribute in document.attributes:
        if isinstance(
            attribute,
            types.DocumentAttributeSticker | types.DocumentAttributeCustomEmoji,
        ) and isinstance(attribute.stickerset, types.InputStickerSetID):
            return attribute.stickerset.id

    return None


def _zero_encode(data: bytes) -> bytes:
    """tdlib's `zero_encode`: each run of zero bytes becomes a zero and the run length."""
    out = bytearray()
    index = 0

    while index < len(data):
        byte = data[index]
        out.append(byte)
        index += 1

        if byte == 0:
            run = 1

            while run < _MAX_ZERO_RUN and index < len(data) and data[index] == 0:
                run += 1
                index += 1

            out.append(run)

    return bytes(out)


def sticker_file_id(document: types.Document) -> str:
    """The Bot API `file_id` of a sticker document, as tdlib would encode it."""
    file_type = _STICKER_FILE_TYPE
    reference = b""

    if document.file_reference:
        file_type |= _FILE_REFERENCE_FLAG
        reference = TLObject.serialize_bytes(document.file_reference)

    location = b"".join(
        (
            struct.pack("<ii", file_type, document.dc_id),
            reference,
            struct.pack("<qq", document.id, document.access_hash),
        )
    )
    encoded = _zero_encode(location) + bytes(
        (_PERSISTENT_ID_SUBVERSION, _PERSISTENT_ID_VERSION)
    )

    return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")
