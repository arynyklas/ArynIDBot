# ArynIDBot

[@ArynIDBot](https://t.me/ArynIDBot) shows the IDs Telegram keeps out of sight: users, bots, channels, groups and messages, plus where media is stored, who owns a sticker pack and which app recorded a voice message.

**Note:** This project runs on Python 3.13 (pinned in `.python-version`) with [uv](https://docs.astral.sh/uv/).

## Features

Send or forward anything to the bot in a private chat; it replies with what the message tells:

- **IDs.** Your own ID, or for a forwarded message the ID of the user, bot, channel or group it came from (and the original message ID of a channel post). A user who hides their account from forwards shows up as such.
- **Sticker pack owners.** The owner's user ID and the pack's number among the owner's packs, decoded from the set ID that every sticker and custom emoji carries: no extra request. Custom emoji in a text get one line per pack.
- **Voice message app.** Every Telegram app encodes voice messages itself, and the encoder names itself in the Ogg Opus header ([via](https://t.me/chekist42/503)). The bot downloads only the first 4 KiB of the file to read it:

  | Encoder (vendor string) | App |
  | --- | --- |
  | `libopus 1.5.1` | Telegram for iOS |
  | `libopus unknown-fixed` | Telegram for Android |
  | `Lavf…` (FFmpeg) | Telegram Desktop |
  | `libopus 1.3.1-fixed` | Telegram for macOS |
  | `libopus unknown` | Telegram X |
  | `tweb` | Telegram Web K |
  | `telegram-web-a` | Telegram Web A |

  Any other vendor string is shown as is.
- **Media DC.** The data center storing a photo, video, voice message, sticker or file. An album gets one reply listing every file's DC.

In groups the bot posts the group's ID when it is added and the old and new IDs when the group becomes a supergroup; `/id`, `/help` and `/top` work there too.

Inline mode (`@ArynIDBot` in any chat) sends a message that the bot then edits to show its DC, its owner's ID and its message ID. In private chats and basic groups the message lives in the sender's own message box, so its ID counts the messages of the sender's account: that is what the `/top` rating (MongoDB) ranks. Supergroups and channels number their messages themselves and get a link instead.

### Flood protection

Every user has a request budget: `limits.user_burst` requests back to back, then one more every `limits.user_interval` seconds. Messages, commands, chosen inline results and button presses spend it, and an album counts once. The first refused request gets a reply saying when to retry, later ones are dropped silently until then. Inline queries have a budget of their own (`limits.inline_*`): clients send one per keystroke, and every new query text reaches the bot; a query over budget gets no answer, so the client simply shows no results. Each group has its own budget for the bot's messages there (`limits.chat_*`, sized to Telegram's 20 messages a minute per group); over it the bot stays silent. Voice probes are capped at `limits.voice_probes` downloads at a time with a timeout, and the vendors and custom emoji packs already seen are cached, so a forwarded voice message is downloaded once.

## Installation

1. Clone the repository and install the dependencies:

    ```sh
    git clone https://github.com/arynyklas/ArynIDBot.git
    cd ArynIDBot
    uv sync
    ```

2. Create the config and fill in `bot.api_id`, `bot.api_hash` (from my.telegram.org), `bot.token` and `database.url`:

    ```sh
    cp config.example.yaml config.yaml
    ```

    Its first line binds `config.schema.json`, so VS Code with the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) completes keys, shows each key's description on hover, and flags unknown keys, wrong types and out-of-range values as you type. Without `database.url` the bot runs with the rating off.

3. In [@BotFather](https://t.me/BotFather), enable inline mode (`/setinline`) and inline feedback (`/setinlinefeedback`, 100%): without the feedback Telegram never tells the bot which message to edit.

The bot logs in with its token on the first start and keeps the login in `bot.session_path`.

## Usage

```sh
uv run python -m src.main
```

Use `--config path/to/config.yaml` to run against a different config file.

Exit codes: `0` clean shutdown (SIGINT, SIGTERM); `1` configuration or startup failure, or a connection Telethon gave up on; `2` the bot's authorization is gone (a revoked or wrong token), which a restart cannot fix. Messages that arrive while the bot is stopped are answered when it starts again; after a crash or a kill (no clean shutdown) up to a minute of updates may be answered twice. A systemd unit to match:

```ini
[Service]
WorkingDirectory=/root/ArynIDBot
ExecStart=/root/ArynIDBot/.venv/bin/python -m src.main
Environment=PYTHONUNBUFFERED=1 PYTHONUTF8=1
Restart=on-failure
RestartSec=10
RestartPreventExitStatus=2
```

`config.yaml` holds the API hash, the bot token and the database password, and the session file is the bot's login: on POSIX run `chmod 600 config.yaml` (the bot narrows the session file and its directory itself).

## Development

```sh
uv sync --group dev --group tests
uv run ruff check src tests scripts
uv run ruff format src tests scripts --check
uv run ty check src tests scripts
uv run pytest
uv lock --check
```

CI runs the same commands, except that its `uv sync --locked` stands in for `uv lock --check`. The type-check job is advisory: it is marked `continue-on-error` while `ty` is pre-1.0, so a green CI run does not mean the type check passed.

`config.schema.json` and the key table under [Configuration](#configuration) are generated from `src/config.py`; run `uv run python -m scripts.generate_config_schema` after changing it. The pre-commit hook does this, and the tests fail while either file is stale.

## Configuration

`config.yaml` is validated on startup: unknown keys, wrong types and out-of-range values are rejected, and every error names its key and line without echoing the value. This table and `config.schema.json` are generated from `src/config.py`.

<!-- config-table:start -->
| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `bot.api_id` | Integer | required | Telegram API ID from my.telegram.org. |
| `bot.api_hash` | String | required | Telegram API hash matching `api_id`. |
| `bot.token` | String | required | Bot token from @BotFather. |
| `bot.session_path` | Path | `"sessions/bot.session"` | Telethon session file. It stays bound to the bot that first logged in with it: delete it after changing `token`. |
| `bot.flood_sleep_threshold` | Integer | `60` | Flood waits shorter than this many seconds are slept through by Telethon. |
| `database.url` | String or `null` | `null` | MongoDB connection string; `null` turns the rating off. |
| `database.name` | String | `"ArynIDBot"` | Database name. |
| `database.timeout` | Number | `2.0` | Seconds a database call waits for a reachable server before it fails. |
| `inline.cache_time` | Integer | `3600` | Seconds Telegram may serve the inline result from its cache. |
| `rating.size` | Integer | `10` | Users listed by /start and /top. |
| `rating.refresh_interval` | Number | `10.0` | Seconds a read rating is reused before the database is asked again. |
| `limits.user_burst` | Integer | `8` | Requests one user may make back to back: messages (an album counts once), commands, chosen inline results and button presses. Inline queries have a budget of their own. |
| `limits.user_interval` | Number | `2.0` | Seconds for a user to earn one request back. A user over budget is told once when to retry, then ignored until then. |
| `limits.chat_burst` | Integer | `3` | Messages the bot may post to one group back to back. |
| `limits.chat_interval` | Number | `3.0` | Seconds for a group to earn one message back; over budget the bot stays silent there. |
| `limits.inline_burst` | Integer | `20` | Inline queries one user may send back to back. Clients send one per keystroke, and Telegram answers a repeated query text from its cache without asking the bot. |
| `limits.inline_interval` | Number | `0.5` | Seconds for a user to earn one inline query back. A query over budget gets no answer, so the client shows no results. |
| `limits.voice_probes` | Integer | `4` | Voice messages whose first 4 KiB are downloaded at once, across all users. |
| `limits.voice_probe_timeout` | Number | `20.0` | Seconds a voice probe may take, waiting for a free slot included. |
| `logging.telethon_level` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `"WARNING"` | Level of Telethon's own loggers, kept apart from ours; `DEBUG` to debug MTProto. |
| `logging.console.level` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `"INFO"` | Console log level. |
| `logging.file.level` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `"INFO"` | File log level. |
| `logging.file.path` | Path | `"logs/main.log"` | Log file path. |
| `logging.file.max_bytes` | Integer | `10485760` | Size at which the log file is rotated, in bytes. |
| `logging.file.backup_count` | Integer | `5` | Number of rotated log files kept. |
<!-- config-table:end -->

## Thanks

- [@teleX](https://t.me/teleX) and [@DavideGalilei](https://t.me/DavideGalilei), credited by [SPOwnerBot](https://github.com/arynyklas/SPOwnerBot), whose sticker set owner decoding this bot uses.
- [Чекист 42](https://t.me/chekist42/503) for the table of voice message encoders.
