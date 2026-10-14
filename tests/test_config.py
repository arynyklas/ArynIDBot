from pathlib import Path

from dature.errors import DatureConfigError
import pytest

from src.config import Config

EXAMPLE_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.example.yaml"


def _errors(path: Path) -> list[str]:
    """The `[key]  message` line of every error the load reports."""
    with pytest.raises(DatureConfigError) as excinfo:
        Config.load(path)

    return [str(error).splitlines()[0].strip() for error in excinfo.value.exceptions]


def test_example_config_loads():
    cfg = Config.load(EXAMPLE_CONFIG_PATH)

    assert cfg.bot.api_id == 1234
    assert cfg.bot.token == "1234:abcd"
    assert cfg.bot.session_path == Path("sessions/bot.session")
    assert cfg.database.url == "mongodb://user:password@localhost:27017"
    assert cfg.limits.user_burst == 8
    assert cfg.logging.file.path == Path("logs/main.log")


@pytest.mark.parametrize(
    ("edits", "delete"),
    [
        pytest.param({}, ("database",), id="section-omitted"),
        pytest.param({"database.url": None}, (), id="url-null"),
    ],
)
def test_the_rating_is_off_without_a_database_url(config_file, edits, delete):
    database = Config.load(config_file(edits, delete=delete)).database

    assert database.url is None
    assert database.name == "ArynIDBot"


def test_only_the_bot_section_is_required(config_file):
    path = config_file(delete=("database", "inline", "rating", "limits", "logging"))

    assert Config.load(path).limits.chat_burst == 3


def test_integers_are_accepted_for_float_fields(config_file):
    """JSON Schema's `number` accepts `2`, so the loader has to as well."""
    cfg = Config.load(config_file({"limits.user_interval": 2}))

    assert cfg.limits.user_interval == 2.0
    assert isinstance(cfg.limits.user_interval, float)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("database.url", 27017, "expected a string or null, got int"),
        ("database.url", True, "expected a string or null, got bool"),
        ("inline.cache_time", -1, "greater than or equal to 0"),
        ("rating.size", 0, "greater than or equal to 1"),
        ("limits.user_burst", 0, "greater than or equal to 1"),
        ("limits.user_interval", 0, "greater than 0"),
        ("limits.chat_interval", True, "expected a number, got bool"),
        ("limits.voice_probes", 0, "greater than or equal to 1"),
        ("logging.console.level", "debug", "Invalid variant"),
    ],
)
def test_invalid_values_are_reported_with_their_key(config_file, key, value, message):
    (error,) = _errors(config_file({key: value}))

    assert error.startswith(f"[{key}]")
    assert message in error


def test_errors_never_echo_a_secret(config_file):
    secret = "123456:SECRET-TOKEN-VALUE"
    path = config_file({"bot.token": 123, "bot.tokn": secret})

    with pytest.raises(DatureConfigError) as excinfo:
        Config.load(path)

    assert secret not in "\n".join(str(error) for error in excinfo.value.exceptions)
