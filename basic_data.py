class TEXTS:
    start: str = "Your ID is <code>{user_id}</code>\n\n{rating_text}\n\nHelp: /help"
    help: str = "Use this bot to get ID for different entities across Telegram:\n• Forward message from channel to get channel ID;\n• Forward message from user to get their ID (unless they restrict from doing so);\n• Send a sticker to get its file_id (currently you can use the sticker's file_id with any bot);\n• Add bot to group to get its ID (it will even tell you when you migrate from group to supergroup);\n• Use inline mode to send your Telegram ID to any chat."

    class id:
        pm: str = "Your Telegram ID is <code>{user_id}</code>"
        not_pm: str = "This {chat_type} chat ID is <code>{chat_id}</code>"
        chat_forwarded: str = "This channel's ID is <code>{chat_id}</code>"
        sticker: str = "\nAlso this sticker's ID is <code>{sticker_file_id}</code>"

        class hide:
            default: str = "This user decided to <b>hide</b> their ID.\n\nLearn more about this feature <a href=\"https://telegram.org/blog/unsend-privacy-emoji#anonymous-forwarding\">here</a>."

            class not_:
                bot: str = "This bot's ID is <code>{user_id}</code>"
                user: str = "This user's ID is <code>{user_id}</code>"

        join: str = "This {chat_type} chat ID is <code>{chat_id}</code>"
        migrated: str = "Group upgraded to supergroup.\nOld ID: <code>{chat_id}</code>\nNew ID: <code>{migrated_chat_id}</code>"

    class inline:
        title: str = "Show DC/user/message ID"
        processing: str = "Processing..."
        process_error: str = "Error with your request - {inline_message_id}"
        markup: str = "⁣"
        processed: str = "DC ID: <code>{dc_id}</code>\nUser ID: <code>{user_id}</code>\nMessage ID: <code>{message_id}</code>"
        processed_url: str = "DC ID: <code>{dc_id}</code>\nChat ID: <code>{chat_id}</code>\nMessage ID: <code>{message_id}</code> (<a href=\"https://t.me/c/{chat_id}/{raw_message_id}\">link</a>)"

    class rating:
        default: str = "Users' rating by message id:\n{rating_records}"
        record: str = "<code>{user_id}</code> — <i>{score}</i>"
