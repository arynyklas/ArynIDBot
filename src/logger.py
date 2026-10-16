from datetime import UTC, datetime
import json
import logging
from logging.handlers import RotatingFileHandler
import sys

from src import constants
from src.config import LoggingConfig

# Attributes every LogRecord has; anything else came in through `extra`.
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, msg, exc, extras."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        ts = datetime.fromtimestamp(record.created, tz=UTC)
        payload: dict[str, object] = {
            "ts": ts.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": message.strip(),
        }

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exc"] = record.exc_text

        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, ensure_ascii=False, default=str)


_LEVELS = logging.getLevelNamesMapping()


def get_logger(name: str, cfg: LoggingConfig) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    console_level = _LEVELS[cfg.console.level]
    file_level = _LEVELS[cfg.file.level]

    logger.setLevel(min(console_level, file_level))

    formatter = JsonFormatter()

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    cfg.file.path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=str(cfg.file.path),
        mode="a",
        maxBytes=cfg.file.max_bytes,
        backupCount=cfg.file.backup_count,
        encoding=constants.ENCODING,
    )

    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Telethon logs through children of this logger (see `build_client`); clamping
    # the shared parent keeps its DEBUG firehose out of ours without losing it.
    logging.getLogger(f"{name}.{constants.TELETHON_LOGGER_CHILD}").setLevel(
        _LEVELS[cfg.telethon_level]
    )

    return logger
