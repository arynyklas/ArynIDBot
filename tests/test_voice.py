import struct

import pytest

from src.voice import opus_vendor, voice_platform

_OPUS_HEAD = b"OpusHead" + bytes([1, 1]) + struct.pack("<HIhB", 312, 48000, 0, 0)


def _page(payload: bytes, sequence: int) -> bytes:
    lacing = [255] * (len(payload) // 255) + [len(payload) % 255]
    header = b"OggS" + struct.pack("<BBqIIIB", 0, 0, 0, 1, sequence, 0, len(lacing))

    return header + bytes(lacing) + payload


def _opus_tags(vendor: bytes, *, declared: int | None = None) -> bytes:
    length = len(vendor) if declared is None else declared

    return b"OpusTags" + struct.pack("<I", length) + vendor + struct.pack("<I", 0)


def _ogg_opus(vendor: bytes, *, declared: int | None = None) -> bytes:
    audio = _page(b"\xfc" * 600, 2)

    return (
        _page(_OPUS_HEAD, 0) + _page(_opus_tags(vendor, declared=declared), 1) + audio
    )


@pytest.mark.parametrize(
    "vendor", ["libopus 1.5.1", "Lavf60.16.101", "tweb", "x" * 300]
)
def test_the_vendor_string_is_read_from_the_comment_header(vendor):
    assert opus_vendor(_ogg_opus(vendor.encode())) == vendor


def test_the_first_block_of_a_file_is_enough():
    head = (_ogg_opus(b"telegram-web-a") + b"\x00" * 8192)[:4096]

    assert opus_vendor(head) == "telegram-web-a"


def test_bytes_that_are_not_utf8_are_replaced():
    assert opus_vendor(_ogg_opus(b"lib\xffopus")) == "lib\ufffdopus"


@pytest.mark.parametrize(
    "head",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"ID3\x04" + b"\x00" * 100, id="mp3"),
        pytest.param(
            _page(b"\x01vorbis" + b"\x00" * 23, 0) + _page(b"\x03vorbis", 1),
            id="ogg-vorbis",
        ),
        pytest.param(_page(_OPUS_HEAD, 0), id="no-second-page"),
        pytest.param(_ogg_opus(b"libopus 1.5.1")[:70], id="cut-inside-the-vendor"),
        pytest.param(_ogg_opus(b"tweb", declared=4000), id="vendor-longer-than-page"),
    ],
)
def test_anything_else_has_no_vendor(head):
    assert opus_vendor(head) is None


@pytest.mark.parametrize(
    ("vendor", "platform"),
    [
        ("libopus 1.5.1", "Telegram for iOS"),
        ("libopus unknown-fixed", "Telegram for Android"),
        ("Lavf60.16.101", "Telegram Desktop"),
        ("Lavf61.7.100", "Telegram Desktop"),
        ("libopus 1.3.1-fixed", "Telegram for macOS"),
        ("libopus unknown", "Telegram X"),
        ("tweb", "Telegram Web K"),
        ("telegram-web-a", "Telegram Web A"),
    ],
)
def test_known_encoders_name_their_app(vendor, platform):
    assert voice_platform(vendor) == platform


@pytest.mark.parametrize("vendor", ["libopus 1.4", "libopus 1.5.1 ", "", "lavf60"])
def test_other_encoders_name_no_app(vendor):
    assert voice_platform(vendor) is None
