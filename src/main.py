"""ArynIDBot: IDs of Telegram users, chats, messages, media DCs, sticker pack owners and voice apps."""

import argparse
import asyncio
from collections.abc import Coroutine
from logging import Logger
from pathlib import Path
import signal
import sys
from typing import Any, cast

from dature.errors import DatureConfigError, DatureErrorGroup, EnvVarExpandError
from ruamel.yaml.constructor import DuplicateKeyError
from telethon import TelegramClient, errors
from telethon.errors import common
from telethon.tl import types

from src import constants
from src.bot import IdBot
from src.client import AUTH_ERRORS, build_client
from src.config import Config
from src.logger import get_logger
from src.rating import Rating

_EXIT_OK = 0
_EXIT_CONFIG = 1
_EXIT_UNAUTHORIZED = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m src.main", description=__doc__)

    parser.add_argument(
        "--config",
        type=Path,
        default=constants.DEFAULT_CONFIG_PATH,
        help="path to the YAML config file",
    )

    return parser


def _install_signal_handlers(stop: asyncio.Event, logger: Logger) -> None:
    loop = asyncio.get_running_loop()

    def _handle(*_: object) -> None:
        logger.info("Shutdown signal received")
        loop.call_soon_threadsafe(stop.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle)

        except NotImplementedError:  # Windows
            signal.signal(sig, _handle)


def _consume_result(future: asyncio.Future[None]) -> None:
    if not future.cancelled():
        future.exception()


async def _serve(client: TelegramClient, bot: IdBot, logger: Logger) -> int:
    """Handle updates until a shutdown signal, a lost authorization or a lost connection."""
    stop = asyncio.Event()

    _install_signal_handlers(stop, logger)

    # Telethon resolves this once its sender gives up reconnecting; the bot
    # then exits for systemd to start it afresh.
    disconnected = client.disconnected
    disconnected.add_done_callback(_consume_result)
    waiters = [
        asyncio.create_task(stop.wait(), name="stop"),
        asyncio.create_task(bot.fatal.wait(), name="fatal"),
    ]

    try:
        await asyncio.wait(
            [*waiters, disconnected], return_when=asyncio.FIRST_COMPLETED
        )

    finally:
        for waiter in waiters:
            waiter.cancel()

    if bot.fatal.is_set():
        return _EXIT_UNAUTHORIZED

    if stop.is_set():
        return _EXIT_OK

    reason = disconnected.exception()

    if isinstance(reason, common.AuthKeyNotFound):
        logger.critical("Telegram no longer knows this session's auth key")

        return _EXIT_UNAUTHORIZED

    logger.error("Connection lost (%r), exiting", reason)

    return _EXIT_CONFIG


async def _run(cfg: Config, logger: Logger) -> int:
    client = build_client(cfg.bot, logger)
    url = cfg.database.url
    rating = None if url is None else Rating(url, cfg.database, cfg.rating, logger)

    try:
        # `start()` returns a coroutine when awaited from async code; the stub says otherwise.
        await cast(
            "Coroutine[Any, Any, TelegramClient]", client.start(bot_token=cfg.bot.token)
        )

        me = cast("types.User", await client.get_me())

        if str(me.id) != cfg.bot.token.partition(":")[0]:
            logger.critical(
                "%s belongs to account %d, not to bot.token; delete it to log in anew",
                cfg.bot.session_path,
                me.id,
            )

            return _EXIT_CONFIG

        if rating is None:
            logger.info("database.url is not set, the rating is off")

        else:
            await rating.create_indexes()

        bot = IdBot(client, me, cfg, rating, logger)
        bot.register()

        logger.info("Started as @%s (%d)", me.username, me.id)

        return await _serve(client, bot, logger)

    except AUTH_ERRORS as ex:
        logger.critical("Bot authorization failed (%s); check bot.token", ex)

        return _EXIT_UNAUTHORIZED

    except (errors.RPCError, OSError) as ex:  # FloodWaitError, ConnectionError
        logger.critical("Startup failed: %s", ex)

        return _EXIT_CONFIG

    finally:
        await client.disconnect()

        if rating is not None:
            await rating.close()


def _report_config_error(path: Path, ex: DatureErrorGroup) -> int:
    """Print why `path` did not load; never prints a config value."""
    if any(isinstance(error, FileNotFoundError) for error in ex.exceptions):
        print(f"Config file not found: {path}", file=sys.stderr)

        return _EXIT_CONFIG

    print(f"Invalid config {path}:", file=sys.stderr)

    for error in ex.exceptions:
        if isinstance(error, DuplicateKeyError):
            mark = error.problem_mark
            print(
                f"  duplicate key at line {mark.line + 1}, column {mark.column + 1}",
                file=sys.stderr,
            )

        else:
            print(error, file=sys.stderr)

    # dature shows at most 7 errors and adds a note on how many it left out.
    for note in getattr(ex, "__notes__", ()):
        print(note, file=sys.stderr)

    return _EXIT_CONFIG


async def main() -> int:
    args = _build_parser().parse_args()

    try:
        cfg = Config.load(args.config)

    except (DatureConfigError, EnvVarExpandError) as ex:
        return _report_config_error(args.config, ex)

    logger = get_logger(constants.LOGGER_NAME, cfg.logging)

    try:
        return await _run(cfg, logger)

    except Exception:
        logger.critical("Startup failed", exc_info=True)

        return _EXIT_CONFIG


def _entrypoint() -> int:
    try:
        return asyncio.run(main())

    except KeyboardInterrupt:
        # Until the signal handlers are installed, `asyncio.run` turns Ctrl+C into
        # a cancellation of `main` and re-raises it here after every `finally`
        # has disconnected, so this is a clean stop.
        return _EXIT_OK


if __name__ == "__main__":
    raise SystemExit(_entrypoint())
