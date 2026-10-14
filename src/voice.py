"""Which app recorded a voice message, told by the encoder named in its Ogg Opus header.

Every Telegram app encodes voice messages itself, and the vendor string of the
OpusTags header (RFC 7845 section 5.2) differs between them; the table comes
from https://t.me/chekist42/503.
"""

import struct

_OGG_CAPTURE = b"OggS"
_OGG_HEADER_SIZE = 27  # fixed part of an Ogg page header, before the lacing values
_OGG_SEGMENTS_OFFSET = 26
_OPUS_HEAD = b"OpusHead"
_OPUS_TAGS = b"OpusTags"
_VENDOR_LENGTH = struct.Struct("<I")

_PLATFORMS = {
    "libopus 1.5.1": "Telegram for iOS",
    "libopus unknown-fixed": "Telegram for Android",
    "libopus 1.3.1-fixed": "Telegram for macOS",
    "libopus unknown": "Telegram X",
    "tweb": "Telegram Web K",
    "telegram-web-a": "Telegram Web A",
}
# Telegram Desktop records through FFmpeg, whose libavformat stamps its own
# version (`Lavf60.16.101`), which moves with every FFmpeg update.
_DESKTOP_VENDOR_PREFIX = "Lavf"
_DESKTOP = "Telegram Desktop"


def _page(data: bytes, offset: int) -> tuple[bytes, int] | None:
    """Payload of the Ogg page at `offset` (cut short with `data`), and where the next page starts."""
    lacing = offset + _OGG_HEADER_SIZE

    if len(data) < lacing or data[offset : offset + 4] != _OGG_CAPTURE:
        return None

    end_of_lacing = lacing + data[offset + _OGG_SEGMENTS_OFFSET]

    if len(data) < end_of_lacing:
        return None

    end = end_of_lacing + sum(data[lacing:end_of_lacing])

    return data[end_of_lacing:end], end


def opus_vendor(head: bytes) -> str | None:
    """Encoder vendor string of the Ogg Opus file starting with `head`.

    `None` when `head` is not the start of an Ogg Opus file, or ends before the
    vendor string does. RFC 7845 puts the ID header alone on the first page and
    starts the comment header on the second, so two pages suffice.
    """
    first = _page(head, 0)

    if first is None or not first[0].startswith(_OPUS_HEAD):
        return None

    second = _page(head, first[1])

    if second is None:
        return None

    tags = second[0]
    start = len(_OPUS_TAGS) + _VENDOR_LENGTH.size

    if not tags.startswith(_OPUS_TAGS) or len(tags) < start:
        return None

    (length,) = _VENDOR_LENGTH.unpack_from(tags, len(_OPUS_TAGS))
    vendor = tags[start : start + length]

    if len(vendor) != length:
        return None

    return vendor.decode("utf-8", errors="replace")


def voice_platform(vendor: str) -> str | None:
    """The app known to write `vendor`, if any."""
    if vendor.startswith(_DESKTOP_VENDOR_PREFIX):
        return _DESKTOP

    return _PLATFORMS.get(vendor)
