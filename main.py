from aiogram import Bot, Dispatcher, types, exceptions, executor

from filters import IsGroupJoin
from utils import resolve_inline_message_id, get_logger

from logging import LoggerAdapter

from config import BOT_TOKEN, BOT_NAME, TEXTS

from typing import List


logger: LoggerAdapter = get_logger(
    name = BOT_NAME
)


bot: Bot = Bot(
    token = BOT_TOKEN,
    parse_mode = types.ParseMode.HTML
)

dp: Dispatcher = Dispatcher(
    bot = bot
)


dp.filters_factory.bind(
    callback = IsGroupJoin,
    event_handlers = [
        dp.my_chat_member_handlers
    ]
)


inline_markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup()

inline_markup.add(
    types.InlineKeyboardButton(
        text = TEXTS["inline"]["markup"],
        callback_data = "0"
    )
)


@dp.inline_handler()
async def inline_handler(inline_query: types.InlineQuery) -> None:
    await inline_query.answer(
        results = [
            types.InlineQueryResultArticle(
                id = str(inline_query.id),
                title = TEXTS["inline"]["title"],
                input_message_content = types.InputTextMessageContent(
                    message_text = TEXTS["inline"]["processing"]
                ),
                reply_markup = inline_markup
            )
        ],
        cache_time = 31
    )


@dp.chosen_inline_handler()
async def chosen_inline_handler(chosen_inline: types.ChosenInlineResult) -> None:
    dc_id: int
    message_id: int
    pid: int
    access_hash: int

    inline_message_id: str = chosen_inline.inline_message_id

    try:
        dc_id, message_id, pid, access_hash = resolve_inline_message_id(
            inline_message_id = inline_message_id
        )

    except:
        logger.error(
            msg = "resolving error",
            inline_message_id = inline_message_id
        )

        await bot.edit_message_text(
            text = TEXTS["inline"]["process_error"].format(
                inline_message_id = inline_message_id
            ),
            inline_message_id = inline_message_id
        )

        return

    try:
        await bot.edit_message_text(
            text = TEXTS["inline"]["processed"].format(
                dc_id = dc_id,
                user_id = pid,
                message_id = "{:,}".format(message_id)
            ),
            inline_message_id = inline_message_id
        )

    except:
        logger.error(
            msg = "resolving error (2)",
            inline_message_id = inline_message_id
        )

        await bot.edit_message_text(
            text = TEXTS["inline"]["process_error"].format(
                inline_message_id = inline_message_id
            ),
            inline_message_id = inline_message_id
        )


@dp.callback_query_handler()
async def callback_query_handler(callback_query: types.CallbackQuery) -> None:
    await callback_query.answer()


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands=["start"])
async def start_command_handler(message: types.Message):
    await message.answer(
        text = TEXTS["start"].format(
            user_id = message.chat.id
        )
    )


@dp.message_handler(commands=["id"])
async def id_command_handler(message: types.Message):
    text: str

    if message.chat.id == message.from_user.id:
        text = TEXTS["id"]["pm"].format(
            user_id = message.from_user.id
        )

    else:
        text = TEXTS["id"]["not_pm"].format(
            chat_type = message.chat.type,
            chat_id = message.chat.id
        )

    await message.answer(
        text = text
    )


@dp.message_handler(commands="help")
async def help_command_handler(message: types.Message):
    await message.answer(
        text = TEXTS["help"]
    )


@dp.message_handler(lambda message: message.forward_from_chat, content_types=types.ContentTypes.ANY)
async def forwarded_message_handler(message: types.Message):
    text: str = TEXTS["id"]["chat_forwarded"].format(
        chat_id = message.forward_from_chat.id
    )

    if message.sticker:
        text += TEXTS["id"]["sticker"].format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@dp.message_handler(lambda message: message.forward_from, content_types=types.ContentTypes.ANY)
async def get_user_id_no_privacy(message: types.Message):
    text: str

    if message.forward_from.is_bot:
        text = TEXTS["id"]["hide"]["bot"].format(
            user_id = message.forward_from.id
        )

    else:
        text = TEXTS["id"]["not_hide"]["user"].format(
            user_id = message.from_user.id
        )

    if message.sticker:
        text += TEXTS["id"]["sticker"].format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@dp.message_handler(lambda message: message.forward_sender_name, content_types=types.ContentTypes.ANY)
async def get_user_id_with_privacy(message: types.Message):
    text: str = TEXTS["id"]["hide"]

    if message.sticker:
        text += TEXTS["id"]["sticker"].format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@dp.my_chat_member_handler(is_group_join=True)
async def new_chat(update: types.ChatMemberUpdated):
    await update.bot.send_message(
        chat_id = update.chat.id,
        text = TEXTS["id"]["join"].format(
            chat_type = update.chat.type,
            chat_id = update.chat.id
        )
    )


@dp.message_handler(content_types=["migrate_to_chat_id"])
async def group_upgrade_to(message: types.Message):
    await bot.send_message(
        chat_id = message.migrate_to_chat_id,
        text = TEXTS["id"]["migrated"].format(
            chat_id = message.chat.id,
            migrated_chat_id = message.migrate_to_chat_id
        )
    )


@dp.message_handler(chat_type=types.ChatType.PRIVATE, content_types=types.ContentTypes.ANY)
async def private_chat(message: types.Message):
    text: str = TEXTS["id"]["pm"].format(
        user_id = message.chat.id
    )

    if message.sticker:
        text += TEXTS["id"]["sticker"].format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@dp.errors_handler(exception=exceptions.TelegramAPIError)
async def errors_handler(update: types.Update, exception: exceptions.TelegramAPIError):
    return True


@dp.errors_handler(exception=Exception)
async def errors_handler(update: types.Update, exception: exceptions.TelegramAPIError):
    logger.exception(
        msg = "error occured: {update}".format(
            update = update.as_json()
        )
    )

    return True


async def on_startup(dp: Dispatcher):
    bot_commands: List[types.BotCommand] = [
        types.BotCommand(
            command = "/id",
            description = "Tell your ID or group's ID"
        ),
        types.BotCommand(
            command = "/help",
            description = "Help"
        )
    ]

    await bot.set_my_commands(
        commands = bot_commands
    )


if __name__ == "__main__":
    executor.start_polling(
        dispatcher = dp,
        skip_updates = False,
        on_startup = on_startup
    )
