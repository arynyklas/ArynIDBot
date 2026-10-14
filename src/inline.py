"""Where an inline message lives, read from the id Telegram hands the bot."""

from telethon.tl import types


def inline_message_location(
    msg_id: types.TypeInputBotInlineMessageID,
) -> tuple[int, int, int]:
    """`(dc_id, owner_id, message_id)` of an inline message.

    The owner is the box holding the message: a user for a private chat or a
    basic group, minus the channel ID for a channel or a supergroup.
    """
    if isinstance(msg_id, types.InputBotInlineMessageID64):
        return msg_id.dc_id, msg_id.owner_id, msg_id.id

    # The 32-bit layout packs both into `id`: the owner in the high word
    # (signed), the message in the low one.
    return msg_id.dc_id, msg_id.id >> 32, msg_id.id & 0xFFFFFFFF
