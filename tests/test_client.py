import logging

import pytest
from telethon import TelegramClient
from telethon.client.telegrambaseclient import _ExportState
from telethon.sessions import MemorySession
from telethon.tl import types

from src.client import revive_dead_file_senders

FILE_DC = 4


class FakeExportedSender:
    """The part of `MTProtoSender` that `_borrow_exported_sender` touches."""

    def __init__(self, *, connected: bool) -> None:
        self.dc_id = FILE_DC
        self.connected = connected
        self.connections: list[object] = []

    def is_connected(self) -> bool:
        return self.connected

    async def connect(self, connection: object) -> bool:
        self.connections.append(connection)
        self.connected = True

        return True


@pytest.fixture
def logger() -> logging.Logger:
    instance = logging.getLogger("tests.client")
    instance.addHandler(logging.NullHandler())
    instance.propagate = False

    return instance


def _client_with(
    sender: FakeExportedSender, monkeypatch: pytest.MonkeyPatch
) -> tuple[TelegramClient, _ExportState]:
    client = TelegramClient(MemorySession(), 1, "0" * 32, receive_updates=False)
    # A download that failed never returned its borrow: `_n` stays 1, so
    # Telethon's idle cleanup never resets `_connected` for this sender.
    state = _ExportState()
    state.add_borrow()
    client._borrowed_senders[FILE_DC] = (state, sender)

    async def get_dc(dc_id: int) -> types.DcOption:
        return types.DcOption(id=dc_id, ip_address="127.0.0.1", port=443)

    monkeypatch.setattr(client, "_get_dc", get_dc)

    return client, state


async def test_a_dead_file_sender_is_reconnected_by_telethons_own_borrow(
    logger, monkeypatch
):
    """Telethon hands a cached per-DC sender out without checking that it is
    connected, so one that gave up made every later voice probe on its DC fail.

    This drives the real `_borrow_exported_sender`, so a Telethon upgrade that
    changes the contract the fix relies on fails here.
    """
    sender = FakeExportedSender(connected=False)
    client, state = _client_with(sender, monkeypatch)

    revive_dead_file_senders(client, logger)

    assert state.need_connect() is True

    borrowed = await client._borrow_exported_sender(FILE_DC)

    assert borrowed is sender
    assert len(sender.connections) == 1
    assert sender.is_connected() is True


async def test_a_sender_telethon_is_still_retrying_is_left_alone(logger, monkeypatch):
    sender = FakeExportedSender(connected=True)
    client, state = _client_with(sender, monkeypatch)

    revive_dead_file_senders(client, logger)

    assert state.need_connect() is False

    await client._borrow_exported_sender(FILE_DC)

    assert sender.connections == []
