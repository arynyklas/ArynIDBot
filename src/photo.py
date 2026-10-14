"""Which platform uploaded a photo, told by the header of the JPEG it encoded.

Telegram keeps the JPEG header that the uploading app wrote (JFIF density, ICC
profile, quantization tables) in a photo's large size, and apps write it
differently. The table of headers and the choice of size follow materialgram's
media viewer:
https://github.com/kukuruzka165/materialgram/blob/main/Telegram/SourceFiles/media/view/media_view_overlay_widget.cpp
It also relabels profile photos, which the bot never shows.
"""

from collections.abc import Sequence

from telethon.tl import types

# (header prefix, platform) in materialgram's order; the first match wins. Its
# labels: "Desktop" is Telegram Desktop, a bare "macOS" is Telegram for macOS,
# and ", 2" or ", 3" is another header seen from the same platform.
_HEADERS = tuple(
    (bytes.fromhex(prefix), platform)
    for prefix, platform in (
        ("FFD8FFE000104A46494600010100000100010000FFDB004300090607", "iOS"),
        (
            "FFD8FFE000104A46494600010101004800480000FFE201D84943435F50524F46494C45",
            "Android",
        ),
        ("FFD8FFE000104A464946000101010078", "Desktop Windows"),
        ("FFD8FFE000104A464946000101010060", "Desktop Windows, 2"),
        ("FFD8FFE000104A46494600010101004800480000FFE201DB", "Desktop Windows, 3"),
        (
            "FFD8FFE000104A46494600010101004800480000FFDB00",
            "Desktop Linux, Unigram, Generic",
        ),
        (
            "FFD8FFE000104A46494600010101004800480000FFE202284943435F50524F46494C450001010000021800000000",
            "Android, old",
        ),
        ("FFD8FFE000104A4649460001010101", "Desktop macOS"),
        ("FFD8FFE000104A46494600010101009000900000FFE201DB", "Desktop macOS, 2"),
        ("FFD8FFE000104A46494600010100000100010000FFDB004300090606", "macOS"),
        ("FFD8FFE000104A46494600010100000100010000FFDB004300080606", "macOS, 2"),
        ("FFD8FFE000104A46494600010101009000900000FFDB004300", "macOS, 3"),
        (
            "FFD8FFE000104A46494600010101004800480000FFE201F04943435F50524F46494C45",
            "Desktop Linux",
        ),
        (
            "FFD8FFE000104A46494600010101004800480000FFE202284943435F50524F46494C45000101000002186170706C",
            "iOS, Share menu",
        ),
        (
            "FFD8FFE000104A46494600010101004800480000FFE202184943435F50524F46494C45",
            "Android, 2",
        ),
        (
            "FFD8FFE000104A46494600010101004800480000FFE202404943435F50524F46494C45",
            "Android, 3",
        ),
        ("FFD8FFE000104A46494600010100004800480000FFC000110801", "iOS, 2"),
    )
)

# Without a progressive size, Telegram Desktop opens the first size whose type
# comes earliest here (`LargeLevels` in its data_session.cpp).
_LARGE_LEVELS = "ydxcwmbsa"


def _progressive_area(size: types.TypePhotoSize) -> int:
    return size.w * size.h if isinstance(size, types.PhotoSizeProgressive) else 0


def _level(size: types.TypePhotoSize) -> int:
    """Rank of the size's type in `_LARGE_LEVELS`; past its end if not there."""
    if isinstance(size, types.PhotoSizeEmpty) or not size.type:
        return len(_LARGE_LEVELS)

    index = _LARGE_LEVELS.find(size.type[0])

    return len(_LARGE_LEVELS) if index < 0 else index


def large_size(sizes: Sequence[types.TypePhotoSize]) -> types.TypePhotoSize | None:
    """The size of a photo that Telegram Desktop opens in its media viewer.

    The biggest progressive size if there is one, else the size ranked first by
    `_LARGE_LEVELS`; `None` when no size qualifies.
    """
    if not sizes:
        return None

    biggest = max(sizes, key=_progressive_area)

    if isinstance(biggest, types.PhotoSizeProgressive):
        return biggest

    best = min(sizes, key=_level)

    return None if _level(best) == len(_LARGE_LEVELS) else best


def photo_platform(head: bytes) -> str | None:
    """The platform whose JPEG header the file starting with `head` has, if known."""
    for prefix, platform in _HEADERS:
        if head.startswith(prefix):
            return platform

    return None
