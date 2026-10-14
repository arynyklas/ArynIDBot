"""Bot replies (HTML)."""

START = "Your ID is <code>{user_id}</code>\n\n{rating}\n\nHelp: /help"
HELP = (
    "Use this bot to get IDs of different entities across Telegram:\n"
    "• Forward a message from a channel to get the channel's ID;\n"
    "• Forward a message from a user to get their ID (unless they hide it);\n"
    "• Send a sticker or custom emoji to get its pack owner's ID;\n"
    "• Send a voice message to see which app recorded it;\n"
    "• Send a photo, video or file to see which DC stores it;\n"
    "• Add the bot to a group to get the group's ID "
    "(it will even tell you when you migrate from group to supergroup);\n"
    "• Use inline mode to send your DC, ID and message ID to any chat."
)
SLOW_DOWN = "Too many requests, try again in {seconds} s."

YOUR_ID = "Your Telegram ID is <code>{user_id}</code>"
CHAT_ID = "This {chat_type} chat ID is <code>{chat_id}</code>"
MIGRATED = (
    "Group upgraded to supergroup.\n"
    "Old ID: <code>{chat_id}</code>\n"
    "New ID: <code>{migrated_chat_id}</code>"
)

FORWARDED_USER = "This user's ID is <code>{user_id}</code>"
FORWARDED_BOT = "This bot's ID is <code>{user_id}</code>"
FORWARDED_CHANNEL = "This channel's ID is <code>{chat_id}</code>"
FORWARDED_GROUP = "This group's ID is <code>{chat_id}</code>"
FORWARDED_POST = "Its message ID there is <code>{message_id}</code>"
FORWARDED_HIDDEN = (
    "This user decided to <b>hide</b> their ID.\n\n"
    "Learn more about this feature "
    '<a href="https://telegram.org/blog/unsend-privacy-emoji#anonymous-forwarding">here</a>.'
)

STICKER_OWNER = (
    "This sticker pack's owner ID is <code>{owner_id}</code> (their pack #{set_number})"
)
EMOJI_OWNER = (
    "This custom emoji pack's owner ID is <code>{owner_id}</code> "
    "(their pack #{set_number})"
)
VOICE_PLATFORM = "This voice message was recorded in {platform} (<code>{vendor}</code>)"
VOICE_UNKNOWN = (
    "This voice message was recorded by an unknown app (<code>{vendor}</code>)"
)
VOICE_UNREADABLE = "Couldn't tell which app recorded this voice message"
FILE_DC = "This {kind} is stored on DC <code>{dc_id}</code>"
ALBUM_DC = "These files are stored on DC {dc_ids}"

RATING = "Users' rating by message id:\n{records}"
RATING_RECORD = "<i>{place}</i>. <code>{user_id}</code> — <i>{score}</i>"
RATING_UNAVAILABLE = "The rating is unavailable right now."

INLINE_TITLE = "Show DC/user/message ID"
INLINE_PROCESSING = "Processing..."
# INVISIBLE SEPARATOR: the button only exists to make Telegram report the
# message's inline id, which needs a reply markup.
INLINE_BUTTON = "\u2063"
INLINE_BUTTON_DATA = b"null"
INLINE_USER = (
    "DC ID: <code>{dc_id}</code>\n"
    "User ID: <code>{user_id}</code>\n"
    "Message ID: <code>{message_id}</code>"
)
INLINE_CHAT = (
    "DC ID: <code>{dc_id}</code>\n"
    "Chat ID: <code>{chat_id}</code>\n"
    "Message ID: <code>{message_id}</code> "
    '(<a href="https://t.me/c/{channel_id}/{raw_message_id}">link</a>)'
)
