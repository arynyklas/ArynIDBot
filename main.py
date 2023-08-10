from aiogram import Router, Bot, Dispatcher, types, enums, F, filters, exceptions

from logging import LoggerAdapter
from asyncio import sleep, create_task, run as asyncio_run

from db import User, init_db
from basic_data import TEXTS
from config import config

import utils

from typing import Union


logger: LoggerAdapter = utils.get_logger(
    name = config.db.name
)


router: Router = Router()


inline_markup: types.InlineKeyboardMarkup = types.InlineKeyboardMarkup(
    inline_keyboard = [
        [
            types.InlineKeyboardButton(
                text = TEXTS.inline.markup,
                callback_data = "null"
            )
        ]
    ]
)


RATING_TEXT: str

CAN_STARTUP: bool = False


@router.inline_query()
async def inline_query_handler(inline_query: types.InlineQuery) -> None:
    await inline_query.answer(
        results = [
            types.InlineQueryResultArticle(
                id = str(inline_query.id),
                title = TEXTS.inline.title,
                input_message_content = types.InputTextMessageContent(
                    message_text = TEXTS.inline.processing
                ),
                reply_markup = inline_markup
            )
        ],
        cache_time = config.inline_cache_time
    )


async def update_user_score(user_id: int, score: int) -> None:
    user: Union[User, None] = await User.find_one(
        User.user_id == user_id
    )

    if not user:
        user = User(
            user_id = user_id
        )

    if not user.score or (user.score and score > user.score):
        user.score = score
        await user.save()


@router.chosen_inline_result()
async def chosen_inline_result_handler(chosen_inline: types.ChosenInlineResult) -> None:
    dc_id: int
    message_id: int
    chat_id: int

    inline_message_id: str = chosen_inline.inline_message_id

    try:
        dc_id, message_id, chat_id, _ = utils.resolve_inline_message_id(
            inline_message_id = inline_message_id
        )

    except:
        logger.exception(
            msg = "resolving error (1)",
            inline_message_id = inline_message_id
        )

        await chosen_inline.bot.edit_message_text(
            text = TEXTS.inline.process_error.format(
                inline_message_id = inline_message_id
            ),
            inline_message_id = inline_message_id
        )

        return

    try:
        is_chat: bool

        is_chat, chat_id = utils.parse_chat_id(
            chat_id = chat_id
        )

        text: str

        if is_chat:
            text = TEXTS.inline.processed_url.format(
                dc_id = dc_id,
                chat_id = chat_id,
                message_id = "{:,}".format(message_id),
                raw_message_id = message_id
            )

        else:
            text = TEXTS.inline.processed.format(
                dc_id = dc_id,
                user_id = chat_id,
                message_id = "{:,}".format(message_id)
            )

        await chosen_inline.bot.edit_message_text(
            text = text,
            inline_message_id = inline_message_id
        )

    except:
        logger.exception(
            msg = "resolving error (2)",
            inline_message_id = inline_message_id
        )

        await chosen_inline.bot.edit_message_text(
            text = TEXTS.inline.process_error.format(
                inline_message_id = inline_message_id
            ),
            inline_message_id = inline_message_id
        )

        return

    if not is_chat:
        await update_user_score(
            user_id = chosen_inline.from_user.id,
            score = message_id
        )


@router.callback_query()
async def callback_query_handler(callback_query: types.CallbackQuery) -> None:
    await callback_query.answer()


@router.message(F.chat.type == enums.ChatType.PRIVATE, filters.Command("start"))
async def start_command_handler(message: types.Message) -> None:
    await message.answer(
        text = TEXTS.start.format(
            user_id = message.chat.id,
            rating_text = RATING_TEXT
        )
    )


@router.message(filters.Command("top"))
async def top_command_handler(message: types.Message) -> None:
    await message.answer(
        text = RATING_TEXT
    )


@router.message(filters.Command("id"))
async def id_command_handler(message: types.Message) -> None:
    text: str

    if message.chat.id == message.from_user.id:
        text = TEXTS.id.pm.format(
            user_id = message.from_user.id
        )

    else:
        text = TEXTS.id.not_pm.format(
            chat_type = message.chat.type,
            chat_id = message.chat.id
        )

    await message.answer(
        text = text
    )


@router.message(filters.Command("help"))
async def help_command_handler(message: types.Message) -> None:
    await message.answer(
        text = TEXTS.help
    )


@router.message(F.forward_from_chat.is_not(None), F.chat.type == enums.ContentType.ANY)
async def forwarded_message_handler(message: types.Message) -> None:
    text: str = TEXTS.id.chat_forwarded.format(
        chat_id = message.forward_from_chat.id
    )

    if message.sticker:
        text += TEXTS.id.sticker.format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@router.message(F.forward_from.is_not(None), F.chat.type == enums.ContentType.ANY)
async def get_user_id_no_privacy(message: types.Message) -> None:
    text: str

    if message.forward_from.is_bot:
        text = TEXTS.id.hide.not_.bot.format(
            user_id = message.forward_from.id
        )

    else:
        text = TEXTS.id.hide.not_.user.format(
            user_id = message.from_user.id
        )

    if message.sticker:
        text += TEXTS.id.sticker.format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@router.message(F.forward_sender_name.is_not(None), F.chat.type == enums.ContentType.ANY)
async def get_user_id_with_privacy(message: types.Message) -> None:
    text: str = TEXTS.id.hide

    if message.sticker:
        text += TEXTS.id.sticker.format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@router.my_chat_member(
    F.old_chat_member.status.in_([enums.ChatMemberStatus.KICKED, enums.ChatMemberStatus.LEFT]),
    F.new_chat_member.status.in_([enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.ADMINISTRATOR]),
    F.chat.typw.in_([enums.ChatType.GROUP, enums.ChatType.SUPERGROUP])
)
async def my_chat_member_handler(update: types.ChatMemberUpdated) -> None:
    await update.bot.send_message(
        chat_id = update.chat.id,
        text = TEXTS.id.join.format(
            chat_type = update.chat.type,
            chat_id = update.chat.id
        )
    )


@router.message(F.content_type == enums.ContentType.MIGRATE_TO_CHAT_ID)
async def migrate_to_chat_id_handler(message: types.Message) -> None:
    await message.bot.send_message(
        chat_id = message.migrate_to_chat_id,
        text = TEXTS.id.migrated.format(
            chat_id = message.chat.id,
            migrated_chat_id = message.migrate_to_chat_id
        )
    )


@router.message(F.chat.type == enums.ChatType.PRIVATE, F.content_type == enums.ContentType.ANY)
async def message_private_chat_handler(message: types.Message) -> None:
    text: str = TEXTS.id.pm.format(
        user_id = message.chat.id
    )

    if message.sticker:
        text += TEXTS.id.sticker.format(
            sticker_file_id = message.sticker.file_id
        )

    await message.reply(
        text = text
    )


@router.error(exceptions.TelegramAPIError)
async def telegram_errors_handler(event: types.ErrorEvent) -> None:
    pass


@router.error()
async def all_errors_handler(event: types.ErrorEvent) -> None:
    logger.exception(
        msg = "error occured: {update}".format(
            update = event.update.model_dump_json()
        )
    )


async def rating_updater() -> None:
    global RATING_TEXT, CAN_STARTUP

    while True:
        start_time: int = utils.get_timestamp()

        RATING_TEXT = TEXTS.rating.default.format(
            rating_records = "\n".join([
                TEXTS.rating.record.format(
                    user_id = user.user_id,
                    score = user.score
                )
                for user in await User.find_all().sort([
                    (User.score, -1)
                ]).to_list()
            ])
        )

        if not CAN_STARTUP:
            CAN_STARTUP = True

        sleep_time: int = config.rating_update_seconds - (utils.get_timestamp() - start_time)

        if sleep_time > 0:
            await sleep(sleep_time)


@router.startup()
async def startup_handler() -> None:
    await init_db(
        db_uri = config.db.url,
        db_name = config.db.name
    )

    create_task(
        coro = rating_updater()
    )

    while not CAN_STARTUP:
        await sleep(1)


async def main() -> None:
    dp: Dispatcher = Dispatcher()

    dp.include_router(
        router = router
    )

    bot: Bot = Bot(
        token = config.bot_token,
        parse_mode = enums.ParseMode.HTML
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio_run(main())
