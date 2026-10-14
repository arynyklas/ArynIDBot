import asyncio
from dataclasses import replace
import logging
from pathlib import Path
from typing import Any, cast

import pytest
from telethon.tl import types

from src.bot import IdBot
from src.config import Config

EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.example.yaml"


def _unactivated_bot() -> IdBot:
    cfg = Config.load(EXAMPLE_CONFIG_PATH)

    return IdBot(
        cast("Any", None),
        replace(cfg, database=replace(cfg.database, url=None)),
        None,
        logging.getLogger("tests"),
    )


_ME = types.User(id=1, bot=True, username="ArynIDBot")


@pytest.fixture
def bot() -> IdBot:
    bot = _unactivated_bot()
    bot.activate(_ME)

    return bot


async def test_an_update_dispatched_before_activation_is_handled_after_it():
    """Telethon dispatches the updates missed while the bot was down as soon as
    it connects, before the bot knows its own username."""
    bot = _unactivated_bot()
    seen: list[str | None] = []

    async def handler(event: str) -> None:
        seen.append(bot._command(event))

    task = asyncio.create_task(bot._guard(handler)("/id@ArynIDBot"))
    await asyncio.sleep(0)

    assert seen == []

    bot.activate(_ME)
    await task

    assert seen == ["id"]


@pytest.mark.parametrize(
    ("text", "command"),
    [
        ("/start", "start"),
        ("/start payload", "start"),
        ("/top@ArynIDBot", "top"),
        ("/ID@arynidbot please", "id"),
        ("/help\nmore", "help"),
    ],
)
def test_commands_for_this_bot_are_recognized(bot, text, command):
    assert bot._command(text) == command


@pytest.mark.parametrize(
    "text",
    ["/id@OtherBot", "/start-now", "hello /start", "", None, "/"],
)
def test_other_texts_are_not_commands(bot, text):
    assert bot._command(text) is None
