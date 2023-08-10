from base64 import urlsafe_b64decode
from struct import unpack
from datetime import datetime
from os import listdir, mkdir
from time import time

import logging

from typing import Tuple


ID32_FORMAT_SIZE: int = 27
ID64_FORMAT_SIZE: int = 32


_log_prefix: str = "inline_message_id"
_log_level: int = logging.DEBUG
_log_level_file: int = logging.WARNING
_log_format: str = "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).(%(lineno)d) - %(message)s"
_log_dir: str = "logs"


def decode_response_base64(string: str) -> bytes:
    return urlsafe_b64decode(string + ("=" * (len(string) % 4)))


def resolve_inline_message_id(inline_message_id: str) -> Tuple[int, int, int, int]:
    dc_id: int
    message_id: int
    chat_id: int
    access_hash: int

    decoded_response: bytes = decode_response_base64(
        string = inline_message_id
    )

    if len(inline_message_id) == ID32_FORMAT_SIZE:
        dc_id, message_id, chat_id, access_hash = unpack("<iiiq", decoded_response)
    else:
        dc_id, chat_id, message_id, access_hash = unpack("<iqiq", decoded_response)

    return (
        dc_id,
        message_id,
        chat_id,
        access_hash
    )


def parse_chat_id(chat_id: int) -> Tuple[bool, int]:
    is_chat: bool = chat_id < 0
    chat_id_: int

    if is_chat:
        chat_id_ = chat_id * -1
    else:
        chat_id_ = chat_id

    return (
        is_chat,
        chat_id_
    )


class CustomAdapter(logging.LoggerAdapter):
    def process(self, message: str, extra: dict) -> Tuple[str, dict]:
        return (
            "[{key}] {message}".format(
                key = extra.pop(_log_prefix, ""),
                message = message
            ),
            extra
        )


def get_file_handler() -> logging.FileHandler:
    date: datetime = datetime.now()

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

    if _log_dir not in listdir():
        mkdir(_log_dir)

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


def get_timestamp() -> int:
    return int(time())
