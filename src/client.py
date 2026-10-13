"""Telethon client of the bot account."""

from logging import Logger

from telethon import TelegramClient, errors
from telethon.errors import common

from src import constants
from src.config import BotConfig

# The bot account can no longer be used: its token was revoked or is wrong, or
# Telegram forgot the session. A restart cannot fix any of them.
# UnauthorizedError/AuthKeyError are RPCError subclasses, so every generic
# `except RPCError` would otherwise swallow them.
AUTH_ERRORS: tuple[type[BaseException], ...] = (
    errors.UnauthorizedError,
    errors.AuthKeyError,
    common.AuthKeyNotFound,
    errors.AccessTokenInvalidError,
    errors.AccessTokenExpiredError,
)


def build_client(cfg: BotConfig, logger: Logger) -> TelegramClient:
    """Build the bot client.

    The session file is the bot's login, so it and its directory are narrowed
    to the owner. `Path.chmod` is a documented no-op for the group and other
    bits on Windows, so no platform guard is needed.
    """
    session_path = cfg.session_path

    if not session_path.name.endswith(".session"):
        # `SQLiteSession` appends the suffix to a name not ending in it;
        # passing it the normalized path keeps the file narrowed below the one
        # it actually opens.
        session_path = session_path.with_name(session_path.name + ".session")

    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.parent.chmod(0o700)

    client = TelegramClient(
        str(session_path),
        cfg.api_id,
        cfg.api_hash,
        flood_sleep_threshold=cfg.flood_sleep_threshold,
        # After its automatic retries of a server-side error Telethon otherwise
        # raises a bare `ValueError`, which escapes every `RPCError` handler;
        # this raises the last `RPCError` instead.
        raise_last_call_error=True,
        # Telethon's own loggers become children of this name, which
        # `get_logger` levels separately from ours.
        base_logger=f"{logger.name}.{constants.TELETHON_LOGGER_CHILD}",
    )
    client.parse_mode = "html"

    if session_path.exists():
        session_path.chmod(0o600)

    return client


def revive_dead_file_senders(client: TelegramClient, logger: Logger) -> None:
    """Make Telethon reconnect cached per-DC file senders that gave up.

    Downloads of files on another DC borrow a cached exported sender, which
    Telethon reconnects only when its export state says so and never checks
    `sender.is_connected()`. A sender that gave up reconnecting therefore stays
    dead, and every later download from that DC raises `ConnectionError`
    until a restart.

    Telethon exposes no public hook, hence the private `_borrowed_senders` and
    `_ExportState._connected`. Clearing `_connected` puts the sender back on
    Telethon's own borrow path, which reconnects the SAME sender (keeping its
    auth key and imported authorization). A sender Telethon is still retrying
    (`is_connected()` True) is left alone.
    """
    for state, sender in client._borrowed_senders.values():
        if not state.need_connect() and not sender.is_connected():
            state._connected = False
            logger.warning("Reviving dead file sender for DC %d", sender.dc_id)
