import pytest
from telethon.tl import types

from src.inline import inline_message_location


@pytest.mark.parametrize("owner_id", [5631021872, -1001234567])
def test_the_64_bit_layout_is_read_field_by_field(owner_id):
    msg_id = types.InputBotInlineMessageID64(
        dc_id=4, owner_id=owner_id, id=987654, access_hash=-1
    )

    assert inline_message_location(msg_id) == (4, owner_id, 987654)


@pytest.mark.parametrize("owner_id", [794823214, -1234567890], ids=["user", "channel"])
def test_the_32_bit_layout_splits_its_id(owner_id):
    """The owner is the high word, signed; the message ID the low word."""
    msg_id = types.InputBotInlineMessageID(
        dc_id=2, id=(owner_id << 32) | 2_000_000_000, access_hash=-1
    )

    assert inline_message_location(msg_id) == (2, owner_id, 2_000_000_000)
