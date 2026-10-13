import pytest
from telethon.tl import types

from src.stickers import decode_set_id, sticker_set_id


def _modern_set_id(owner_id: int, set_number: int) -> int:
    """Telegram's layout: low 31 bits of the owner high, band and counter complemented low."""
    low = ~(((owner_id >> 31) << 22) | set_number) & 0xFFFFFFFF

    return ((owner_id & 0x7FFFFFFF) << 32) | low


@pytest.mark.parametrize(
    "owner_id",
    [
        pytest.param(794823214, id="band-0"),
        pytest.param(2**31, id="band-1-first"),
        pytest.param(5631021872, id="band-2"),
        pytest.param(7_999_999_999, id="band-3"),
        pytest.param(8_589_934_592, id="band-4-top-byte-fe"),
        pytest.param(1019 * 2**31 + 12345, id="band-1019-last-modern"),
    ],
)
@pytest.mark.parametrize("set_number", [1, 31, 0x3FFFFF])
def test_owner_and_set_number_come_back_in_every_band(owner_id, set_number):
    assert decode_set_id(_modern_set_id(owner_id, set_number)) == (
        owner_id,
        set_number,
    )


def test_a_set_from_before_the_band_field_reads_as_owner_and_counter():
    """Its low word is a plain small counter, so its top byte is zero."""
    assert decode_set_id((123456789 << 32) | 7) == (123456789, 7)


def _document(*attributes: types.TypeDocumentAttribute) -> types.Document:
    return types.Document(
        id=1,
        access_hash=2,
        file_reference=b"\x01",
        date=None,
        mime_type="image/webp",
        size=1,
        dc_id=2,
        attributes=list(attributes),
    )


@pytest.mark.parametrize(
    "attribute",
    [
        types.DocumentAttributeSticker(
            alt="🙂", stickerset=types.InputStickerSetID(id=42, access_hash=1)
        ),
        types.DocumentAttributeCustomEmoji(
            alt="🙂", stickerset=types.InputStickerSetID(id=42, access_hash=1)
        ),
    ],
    ids=["sticker", "custom-emoji"],
)
def test_the_set_id_is_read_off_the_document(attribute):
    assert sticker_set_id(_document(attribute)) == 42


@pytest.mark.parametrize(
    "document",
    [
        _document(
            types.DocumentAttributeSticker(
                alt="🙂", stickerset=types.InputStickerSetEmpty()
            )
        ),
        _document(types.DocumentAttributeFilename(file_name="a.webp")),
        types.DocumentEmpty(id=1),
        None,
    ],
    ids=["no-set", "not-a-sticker", "empty-document", "none"],
)
def test_documents_without_a_set_id_have_none(document):
    assert sticker_set_id(document) is None
