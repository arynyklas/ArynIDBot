from dataclasses import replace
import logging
from pathlib import Path
from typing import Any, cast

import pytest
from telethon.tl import types

from src.bot import IdBot
from src.config import Config

EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.example.yaml"


@pytest.fixture
def bot() -> IdBot:
    cfg = Config.load(EXAMPLE_CONFIG_PATH)
    me = types.User(id=1, bot=True, username="ArynIDBot")

    return IdBot(
        cast("Any", None),
        me,
        replace(cfg, database=replace(cfg.database, url=None)),
        None,
        logging.getLogger("tests"),
    )


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
