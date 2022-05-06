from base64 import urlsafe_b64decode
from struct import unpack

import logging, datetime, os

from typing import Any, Tuple


ID32_FORMAT_SIZE: int = 27
ID64_FORMAT_SIZE: int = 32

_log_prefix: str = "inline_message_id"
_log_level: int = logging.DEBUG
_log_level_file: int = logging.WARNING
_log_format: str = "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).(%(lineno)d) - %(message)s"
_log_dir: str = "logs"


def decode_telegram_base64(string):
    return urlsafe_b64decode(string + '=' * (len(string) % 4))


def resolve_inline_message_id(inline_message_id: str) -> Tuple[int, int, int, int]:
    dc_id: int
    message_id: int
    pid: int
    access_hash: int

    if len(inline_message_id) == ID32_FORMAT_SIZE:
        dc_id, message_id, pid, access_hash = unpack('<iiiq', decode_telegram_base64(inline_message_id))
    else:
        dc_id, pid, message_id, access_hash = unpack('<iqiq', decode_telegram_base64(inline_message_id))

    return dc_id, message_id, pid, access_hash


class CustomAdapter(logging.LoggerAdapter):
    def process(self, message: str, kwargs: dict) -> Tuple[str, dict]:
        return (
            "[{key}] {message}".format(
                key = kwargs.pop(
                    _log_prefix,
                    self.extra[_log_prefix]
                ),
                message = message
            ),
            kwargs
        )


def get_file_handler() -> logging.FileHandler:
    date: datetime.datetime = datetime.datetime.now()

    file_handler: logging.FileHandler = logging.FileHandler(
        filename = "{dir}/{hours}.{minute}.{second} {day}.{month}.{year}.log".format(
            dir = _log_dir,
            hours = date.hour,
            minute = date.minute,
            second = date.second,
            day = date.day,
            month = date.month,
            year = date.year
        ),
        encoding = "utf-8"
    )

    file_handler.setLevel(
        level = _log_level_file
    )

    file_handler.setFormatter(
        fmt = logging.Formatter(
            fmt = _log_format
        )
    )

    return file_handler


def get_stream_handler() -> logging.StreamHandler:
    stream_handler: logging.StreamHandler = logging.StreamHandler()

    stream_handler.setLevel(
        level = _log_level
    )

    stream_handler.setFormatter(
        fmt = logging.Formatter(
            fmt = _log_format
        )
    )

    return stream_handler


def get_logger(name: str) -> logging.LoggerAdapter:
    logger: logging.Logger = logging.getLogger(
        name = name
    )

    logger.setLevel(
        level = _log_level
    )

    if _log_dir not in os.listdir():
        os.mkdir(_log_dir)

    logger.addHandler(
        hdlr = get_file_handler()
    )

    logger.addHandler(
        hdlr = get_stream_handler()
    )

    logger: logging.LoggerAdapter = CustomAdapter(
        logger = logger,
        extra = {
            _log_prefix: None
        }
    )

    return logger
