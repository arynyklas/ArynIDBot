import pytest
from telethon.tl import types

from src.photo import _HEADERS, large_size, photo_platform

_BLOCK = 4096


@pytest.mark.parametrize(
    ("prefix", "platform"), _HEADERS, ids=[platform for _, platform in _HEADERS]
)
def test_every_header_in_the_table_can_match(prefix, platform):
    """The first match wins, so an earlier header must never be a prefix of a later one."""
    assert photo_platform(prefix + bytes(_BLOCK - len(prefix))) == platform


@pytest.mark.parametrize(
    "head",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"\x89PNG\r\n\x1a\n" + bytes(64), id="png"),
        pytest.param(
            b"\xff\xd8\xff\xe1\x00\x16Exif\x00\x00" + bytes(64), id="exif-first"
        ),
        pytest.param(
            bytes.fromhex("FFD8FFE000104A46494600010100000100010000FFDB004300040303"),
            id="libjpeg-defaults-at-quality-87",
        ),
        pytest.param(
            bytes.fromhex(
                "FFD8FFE000104A46494600010101004800480000"
                "FFE202284943435F50524F46494C4500010100000218"
            )
            + b"lcms",
            id="icc-profile-of-another-cmm",
        ),
        pytest.param(
            bytes.fromhex("FFD8FFE000104A46494600010101004800480000"),
            id="cut-before-the-next-segment",
        ),
    ],
)
def test_other_headers_match_nothing(head):
    assert photo_platform(head) is None


def _plain(kind: str, side: int) -> types.PhotoSize:
    return types.PhotoSize(type=kind, w=side, h=side * 3 // 4, size=side * 10)


def _progressive(kind: str, side: int) -> types.PhotoSizeProgressive:
    return types.PhotoSizeProgressive(
        type=kind, w=side, h=side * 3 // 4, sizes=[side, side * 10]
    )


_STRIPPED = types.PhotoStrippedSize(type="i", bytes=b"\x01\x28\x1e")


@pytest.mark.parametrize(
    ("sizes", "opened"),
    [
        pytest.param(
            [_STRIPPED, _plain("m", 320), _plain("x", 800), _progressive("y", 1280)],
            "y",
            id="progressive",
        ),
        pytest.param(
            [_progressive("y", 1280), _progressive("w", 2560)],
            "w",
            id="biggest-progressive",
        ),
        pytest.param(
            [_plain("w", 2560), _progressive("y", 1280)],
            "y",
            id="progressive-over-a-bigger-plain-size",
        ),
        pytest.param(
            [_plain("x", 800), _plain("w", 2560), _plain("y", 1280)],
            "y",
            id="y-before-w",
        ),
        pytest.param(
            [_plain("m", 320), _plain("x", 800), _STRIPPED],
            "x",
            id="stripped-size-listed-last",
        ),
    ],
)
def test_the_size_telegram_desktop_opens_is_chosen(sizes, opened):
    size = large_size(sizes)

    assert size is not None
    assert size.type == opened


@pytest.mark.parametrize(
    "sizes",
    [
        pytest.param([], id="no-sizes"),
        pytest.param(
            [_STRIPPED, types.PhotoPathSize(type="j", bytes=b"")], id="previews-only"
        ),
        pytest.param([types.PhotoSizeEmpty(type="y")], id="empty-size"),
    ],
)
def test_a_photo_without_a_viewable_size_has_none(sizes):
    assert large_size(sizes) is None
