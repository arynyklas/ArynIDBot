"""Configuration, loaded from YAML by dature.

Every field docstring is user documentation: `scripts/generate_config_schema.py`
turns it into the editor hover text in `config.schema.json` and into the README
key table, and fails on a field without one.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Literal, Self, cast

import dature
from dature import V

from src import constants

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _float_from_number(value: object) -> float:
    """Accept YAML integers for float fields, as JSON Schema's `number` does.

    dature alone rejects `user_interval: 2`, which the editor schema cannot
    tell apart from `2.0`.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"expected a number, got {type(value).__name__}")

    return float(value)


def _optional_str(value: object) -> str | None:
    """Load a `str | None` field without dature 1.6's broken error path.

    dature reports any other type there as "'NoneType' object has no attribute
    '__name__'", without the key. The message never embeds the value: dature
    masks values only in its own errors.
    """
    if value is None or isinstance(value, str):
        return value

    raise TypeError(f"expected a string or null, got {type(value).__name__}")


@dataclass(frozen=True, slots=True, kw_only=True)
class BotConfig:
    """Bot account, logged in over MTProto."""

    api_id: int
    """Telegram API ID from my.telegram.org."""
    api_hash: str
    """Telegram API hash matching `api_id`."""
    token: str
    """Bot token from @BotFather."""
    session_path: Path = Path("sessions/bot.session")
    """Telethon session file. It stays bound to the bot that first logged in with it: delete it after changing `token`."""
    flood_sleep_threshold: int = 60
    """Flood waits shorter than this many seconds are slept through by Telethon."""


@dataclass(frozen=True, slots=True, kw_only=True)
class DatabaseConfig:
    """MongoDB storage of the inline message ID rating."""

    url: str | None = None
    """MongoDB connection string; `null` turns the rating off."""
    name: str = "ArynIDBot"
    """Database name."""
    timeout: float = 2.0
    """Seconds a database call waits for a reachable server before it fails."""


@dataclass(frozen=True, slots=True, kw_only=True)
class InlineConfig:
    """Inline mode."""

    cache_time: Annotated[int, V >= 0] = 3600
    """Seconds Telegram may serve the inline result from its cache."""


@dataclass(frozen=True, slots=True, kw_only=True)
class RatingConfig:
    """Rating of users by the message ID their inline message got."""

    size: Annotated[int, V >= 1] = 10
    """Users listed by /start and /top."""
    refresh_interval: Annotated[float, V >= 0] = 10.0
    """Seconds a read rating is reused before the database is asked again."""


@dataclass(frozen=True, slots=True, kw_only=True)
class LimitsConfig:
    """Flood protection: request budgets per user and per group, and the voice probe budget."""

    user_burst: Annotated[int, V >= 1] = 8
    """Requests one user may make back to back: messages (an album counts once), commands, chosen inline results and button presses. Inline queries are free."""
    user_interval: Annotated[float, V > 0] = 2.0
    """Seconds for a user to earn one request back. A user over budget is told once when to retry, then ignored until then."""
    chat_burst: Annotated[int, V >= 1] = 3
    """Messages the bot may post to one group back to back."""
    chat_interval: Annotated[float, V > 0] = 3.0
    """Seconds for a group to earn one message back; over budget the bot stays silent there."""
    voice_probes: Annotated[int, V >= 1] = 4
    """Voice messages whose first 4 KiB are downloaded at once, across all users."""
    voice_probe_timeout: Annotated[float, V > 0] = 20.0
    """Seconds a voice probe may take, waiting for a free slot included."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsoleLogConfig:
    """Console log output."""

    level: LogLevel = "INFO"
    """Console log level."""


@dataclass(frozen=True, slots=True, kw_only=True)
class FileLogConfig:
    """Rotating log file."""

    level: LogLevel = "INFO"
    """File log level."""
    path: Path = Path("logs/main.log")
    """Log file path."""
    max_bytes: int = 10 * 1024 * 1024
    """Size at which the log file is rotated, in bytes."""
    backup_count: int = 5
    """Number of rotated log files kept."""


@dataclass(frozen=True, slots=True, kw_only=True)
class LoggingConfig:
    """Log levels and destinations."""

    # Telethon is chatty at DEBUG; keep it out of our own DEBUG stream by default.
    telethon_level: LogLevel = "WARNING"
    """Level of Telethon's own loggers, kept apart from ours; `DEBUG` to debug MTProto."""
    console: ConsoleLogConfig = field(default_factory=ConsoleLogConfig)
    """Console log output."""
    file: FileLogConfig = field(default_factory=FileLogConfig)
    """Rotating log file."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    """ArynIDBot configuration."""

    bot: BotConfig
    """Bot account, logged in over MTProto."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    """MongoDB storage of the inline message ID rating; off unless `url` is set."""
    inline: InlineConfig = field(default_factory=InlineConfig)
    """Inline mode."""
    rating: RatingConfig = field(default_factory=RatingConfig)
    """Rating of users by the message ID their inline message got."""
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    """Flood protection."""
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    """Log levels and destinations."""

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load and validate `path`; raises `dature.errors.DatureConfigError`."""
        return dature.load(
            # No fallback to a config.yaml in %APPDATA% or ~/.config.
            dature.Yaml12Source(file=path, encoding=constants.ENCODING, config_dirs=()),
            schema=cls,
            strict="error",
            # A database password may contain `$` or `%`: nothing is an env reference.
            expand_env_vars="disabled",
            # Errors never echo a value: a typo in a secret key would print it.
            masking_mode="all",
            # dature types `type_loaders` keys as `type`; adaptix takes any type hint.
            type_loaders={
                float: _float_from_number,
                cast("type", str | None): _optional_str,
            },
        )
