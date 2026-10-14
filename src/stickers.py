"""Owners of sticker and custom emoji sets, read from the documents themselves."""

from telethon.tl import types


def decode_set_id(set_id: int) -> tuple[int, int]:
    """Returns `(owner user ID, owner's set increment ID)`.

    Ported from SPOwnerBot, where @madrik1337 fixed the owner ID decoding
    (https://github.com/arynyklas/SPOwnerBot/pull/1).
    """

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
