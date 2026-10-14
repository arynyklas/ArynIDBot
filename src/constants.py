from pathlib import Path

ENCODING = "utf-8"
LOGGER_NAME = "aryn_id_bot"
TELETHON_LOGGER_CHILD = "telethon"
DEFAULT_CONFIG_PATH = Path("config.yaml")
# `upload.getFile` serves whole 4 KiB blocks. The OpusTags header that names a
# voice message's encoder starts the second Ogg page, and the JPEG header that
# tells a photo's platform opens the file: both lie well inside the first block.
PROBE_HEAD_SIZE = 4096
# A vendor string longer than this is cut: it comes from the file, not from us.
VOICE_VENDOR_MAX_LENGTH = 64
# Voice vendors, photo platforms and custom emoji sets remembered per file id.
CACHE_SIZE = 4096
# Custom emoji documents resolved per message, at most: one request.
MAX_CUSTOM_EMOJIS = 50
# How often rate-limit entries that hold a full budget again are forgotten.
LIMITER_SWEEP_INTERVAL = 60.0
