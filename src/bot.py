"""Update handlers of the bot."""

import asyncio
from collections.abc import Callable, Coroutine
import functools
import html
from logging import Logger
import math
import re
from typing import Any, cast

from telethon import Button, TelegramClient, errors, events, utils
from telethon.tl import functions, types
from telethon.tl.custom import Message

from src import constants, texts
from src.cache import LruCache
from src.client import AUTH_ERRORS, revive_dead_file_senders
from src.config import Config
from src.describe import forward_origin, media_location
from src.inline import inline_message_location
from src.limiter import RateLimiter
from src.rating import Rating
from src.stickers import decode_set_id, sticker_set_id
from src.voice import opus_vendor, voice_platform

# `/name` or `/name@bot`, followed by whitespace or the end of the text.
_COMMAND = re.compile(r"/(?P<name>\w+)(?:@(?P<bot>\w+))?(?=\s|$)")
_GROUP_COMMANDS = frozenset({"id", "help", "top"})

type _Handler = Callable[[Any], Coroutine[Any, Any, None]]


def _chat_type(peer: types.TypePeer) -> str:
    return "group" if isinstance(peer, types.PeerChat) else "supergroup"


class IdBot:
    def __init__(
        self,
        client: TelegramClient,
        cfg: Config,
        rating: Rating | None,
        logger: Logger,
    ) -> None:
        self._client = client
        self._me_id = 0
        self._username = ""
        self._ready = asyncio.Event()
        self._cfg = cfg
        self._rating = rating
        self._logger = logger
        self._users = RateLimiter(cfg.limits.user_burst, cfg.limits.user_interval)
        self._chats = RateLimiter(cfg.limits.chat_burst, cfg.limits.chat_interval)
        self._inline_queries = RateLimiter(
            cfg.limits.inline_burst, cfg.limits.inline_interval
        )
        self._probes = asyncio.Semaphore(cfg.limits.voice_probes)
        self._vendors: LruCache[int, str] = LruCache(constants.CACHE_SIZE)
        self._emoji_sets: LruCache[int, int] = LruCache(constants.CACHE_SIZE)
        self._inline_buttons = [
            Button.inline(texts.INLINE_BUTTON, texts.INLINE_BUTTON_DATA)
        ]
        self.fatal = asyncio.Event()
        """Set once a handler found the bot's authorization gone."""

    def register(self) -> None:
        """Add the handlers. Call before the client connects: Telethon dispatches
        the updates missed while the bot was down as soon as it does. They wait
        for `activate`."""
        add = self._client.add_event_handler

        add(self._guard(self._on_message), events.NewMessage(incoming=True))
        add(self._guard(self._on_album), events.Album(func=lambda e: e.is_private))
        add(
            self._guard(self._on_service),
            events.Raw((types.UpdateNewMessage, types.UpdateNewChannelMessage)),
        )
        add(self._guard(self._on_inline_query), events.InlineQuery())
        add(self._guard(self._on_inline_send), events.Raw(types.UpdateBotInlineSend))
        add(self._guard(self._on_callback), events.CallbackQuery())

    def activate(self, me: types.User) -> None:
        """Let the handlers run, now that the bot knows who it is."""
        self._me_id = me.id
        self._username = (me.username or "").casefold()
        self._ready.set()

    def _guard(self, handler: _Handler) -> _Handler:
        name = getattr(handler, "__name__", repr(handler))

        @functools.wraps(handler)
        async def guarded(event: Any) -> None:  # noqa: ANN401
            try:
                await self._ready.wait()
                await handler(event)

            except AUTH_ERRORS as ex:
                self._logger.critical("Authorization lost in %s (%s)", name, ex)
                self.fatal.set()

            except errors.RPCError as ex:  # FloodWaitError, UserIsBlockedError, ...
                self._logger.warning("%s: %s", name, ex)

            except Exception:
                self._logger.exception("%s crashed", name)

        return guarded

    async def _admit(self, user_id: int, message: Message) -> bool:
        """Spend one request of `user_id`; the first refusal tells them when to retry."""
        verdict = self._users.hit(user_id)

        if verdict.warn:
            await message.reply(
                texts.SLOW_DOWN.format(seconds=math.ceil(verdict.retry_after))
            )

        if not verdict.allowed:
            self._logger.debug("User %d is over budget", user_id)

        return verdict.allowed

    def _command(self, text: str | None) -> str | None:
        match = _COMMAND.match(text or "")

        if match is None:
            return None

        if match["bot"] is not None and match["bot"].casefold() != self._username:
            return None  # addressed to another bot

        return match["name"].casefold()

    async def _on_message(self, event: events.NewMessage.Event) -> None:
        message = cast("Message", event.message)

        if event.is_private:
            await self._on_private_message(message)

        elif event.is_group:
            await self._on_group_message(message)

    async def _on_private_message(self, message: Message) -> None:
        if message.grouped_id is not None:
            return  # an album gets one answer, from `_on_album`

        user_id = cast("int", message.sender_id)

        if not await self._admit(user_id, message):
            return

        command = self._command(message.message)

        if command == "start":
            rating = await self._rating_text()
            await message.respond(texts.START.format(user_id=user_id, rating=rating))

        elif command == "help":
            await message.respond(texts.HELP, link_preview=False)

        elif command == "top":
            await message.respond(await self._rating_text())

        else:
            await message.reply(await self._describe(message), link_preview=False)

    async def _on_group_message(self, message: Message) -> None:
        command = self._command(message.message)

        if command not in _GROUP_COMMANDS:
            return

        chat_id = cast("int", message.chat_id)
        sender_id = cast("int | None", message.sender_id) or chat_id

        # Silent when over budget: a notice would be one more group message.
        if (
            not self._users.hit(sender_id).allowed
            or not self._chats.hit(chat_id).allowed
        ):
            return

        if command == "id":
            text = texts.CHAT_ID.format(
                chat_type=_chat_type(message.peer_id), chat_id=chat_id
            )

        elif command == "help":
            text = texts.HELP

        else:
            text = await self._rating_text()

        await message.respond(text, link_preview=False)

    async def _on_album(self, event: events.Album.Event) -> None:
        messages = cast("list[Message]", event.messages)
        first = messages[0]

        if not await self._admit(cast("int", first.sender_id), first):
            return

        lines = [self._origin(first)]
        dc_ids = [
            location[1]
            for message in messages
            if (location := media_location(message.media)) is not None
        ]

        if dc_ids:
            codes = ", ".join(f"<code>{dc_id}</code>" for dc_id in dc_ids)
            lines.append(texts.ALBUM_DC.format(dc_ids=codes))

        await first.reply("\n".join(lines), link_preview=False)

    async def _on_service(
        self, update: types.UpdateNewMessage | types.UpdateNewChannelMessage
    ) -> None:
        message = update.message

        if not isinstance(message, types.MessageService):
            return

        action = message.action
        chat_id = utils.get_peer_id(message.peer_id)

        if (
            isinstance(
                action, types.MessageActionChatAddUser | types.MessageActionChatCreate
            )
            and self._me_id in action.users
        ):
            text = texts.CHAT_ID.format(
                chat_type=_chat_type(message.peer_id), chat_id=chat_id
            )

        elif isinstance(action, types.MessageActionChannelMigrateFrom):
            old_chat_id = utils.get_peer_id(types.PeerChat(action.chat_id))
            text = texts.MIGRATED.format(chat_id=old_chat_id, migrated_chat_id=chat_id)

        else:
            return

        if self._chats.hit(chat_id).allowed:
            await self._client.send_message(message.peer_id, text)

    async def _on_inline_query(self, event: events.InlineQuery.Event) -> None:
        # A budget of its own: clients send a query per keystroke, and each new
        # query text reaches the bot. Over budget the query gets no answer, so
        # the client shows no results; there is nothing to notify.
        if not self._inline_queries.hit(cast("int", event.sender_id)).allowed:
            return

        await event.answer(
            [
                event.builder.article(
                    texts.INLINE_TITLE,
                    text=texts.INLINE_PROCESSING,
                    buttons=self._inline_buttons,
                )
            ],
            cache_time=self._cfg.inline.cache_time,
        )

    async def _on_inline_send(self, update: types.UpdateBotInlineSend) -> None:
        # `msg_id` comes only with a reply markup, hence the button.
        if update.msg_id is None or not self._users.hit(update.user_id).allowed:
            return

        dc_id, owner_id, message_id = inline_message_location(update.msg_id)

        if owner_id < 0:
            channel_id = -owner_id
            text = texts.INLINE_CHAT.format(
                dc_id=dc_id,
                chat_id=utils.get_peer_id(types.PeerChannel(channel_id)),
                message_id=f"{message_id:,}",
                channel_id=channel_id,
                raw_message_id=message_id,
            )

        else:
            text = texts.INLINE_USER.format(
                dc_id=dc_id, user_id=owner_id, message_id=f"{message_id:,}"
            )

        # `edit_message` documents inline message ids; its type hint omits them.
        inline_id = cast("Any", update.msg_id)
        await self._client.edit_message(inline_id, text, link_preview=False)

        # Channel message IDs count per channel, not per user.
        if owner_id > 0 and self._rating is not None:
            await self._rating.record(update.user_id, message_id)

    async def _on_callback(self, event: events.CallbackQuery.Event) -> None:
        if self._users.hit(cast("int", event.sender_id)).allowed:
            await event.answer()

    def _origin(self, message: Message) -> str:
        header = message.fwd_from

        if header is None:
            return texts.YOUR_ID.format(user_id=message.sender_id)

        forward = message.forward
        entity = None if forward is None else forward.sender or forward.chat

        return forward_origin(header, entity)

    async def _describe(self, message: Message) -> str:
        lines = [self._origin(message)]
        media = message.media

        if isinstance(media, types.MessageMediaDocument) and isinstance(
            media.document, types.Document
        ):
            document = media.document
            set_id = sticker_set_id(document)

            if set_id is not None:
                owner_id, set_number = decode_set_id(set_id)
                lines.append(
                    texts.STICKER_OWNER.format(owner_id=owner_id, set_number=set_number)
                )

            if message.voice is not None:
                lines.append(await self._voice_platform(document))

        lines += await self._emoji_owners(message)

        location = media_location(media)

        if location is not None:
            kind, dc_id = location
            lines.append(texts.FILE_DC.format(kind=kind, dc_id=dc_id))

        return "\n".join(lines)

    async def _voice_platform(self, document: types.Document) -> str:
        vendor = self._vendors.get(document.id)

        if vendor is None:
            try:
                async with asyncio.timeout(self._cfg.limits.voice_probe_timeout):
                    async with self._probes:
                        head = await self._download_head(document)

            # TimeoutError and ConnectionError are OSErrors; Telethon raises a
            # ValueError for a file served from a CDN, which bots cannot reach.
            except (OSError, ValueError, errors.RPCError) as ex:
                self._logger.warning("Voice %d not probed: %r", document.id, ex)

                return texts.VOICE_UNREADABLE

            vendor = opus_vendor(head)

            if vendor is None:
                return texts.VOICE_UNREADABLE

            self._vendors.put(document.id, vendor)

        shown = html.escape(vendor[: constants.VOICE_VENDOR_MAX_LENGTH])
        platform = voice_platform(vendor)

        if platform is None:
            return texts.VOICE_UNKNOWN.format(vendor=shown)

        return texts.VOICE_PLATFORM.format(platform=platform, vendor=shown)

    async def _download_head(self, document: types.Document) -> bytes:
        """The first block of the file: one `upload.getFile`, on the file's own DC."""
        revive_dead_file_senders(self._client, self._logger)

        async with self._client.iter_download(
            document, request_size=constants.VOICE_HEAD_SIZE, limit=1
        ) as stream:
            async for chunk in stream:
                return cast("bytes", chunk)

        return b""

    async def _emoji_owners(self, message: Message) -> list[str]:
        document_ids = list(
            dict.fromkeys(
                entity.document_id
                for entity in message.entities or ()
                if isinstance(entity, types.MessageEntityCustomEmoji)
            )
        )[: constants.MAX_CUSTOM_EMOJIS]
        unknown = [
            doc_id for doc_id in document_ids if self._emoji_sets.get(doc_id) is None
        ]

        if unknown:
            try:
                documents = await self._client(
                    functions.messages.GetCustomEmojiDocumentsRequest(
                        document_id=unknown
                    )
                )

            except errors.RPCError as ex:
                self._logger.warning("Custom emoji not resolved: %s", ex)
                documents = []

            for document in documents:
                set_id = sticker_set_id(document)

                if set_id is not None:
                    self._emoji_sets.put(document.id, set_id)

        set_ids = dict.fromkeys(
            set_id
            for doc_id in document_ids
            if (set_id := self._emoji_sets.get(doc_id)) is not None
        )

        return [
            texts.EMOJI_OWNER.format(owner_id=owner_id, set_number=set_number)
            for owner_id, set_number in map(decode_set_id, set_ids)
        ]

    async def _rating_text(self) -> str:
        top = None if self._rating is None else await self._rating.top()

        if top is None:
            return texts.RATING_UNAVAILABLE

        records = "\n".join(
            texts.RATING_RECORD.format(place=place, user_id=user_id, score=f"{score:,}")
            for place, (user_id, score) in enumerate(top, start=1)
        )

        return texts.RATING.format(records=records)
