from pathlib import Path

from dature.errors import DatureConfigError
import jsonschema
import pytest
from ruamel.yaml import YAML

from src.config import Config
from src.config_schema import (
    REGENERATE_COMMAND,
    build_schema,
    render_readme_table,
    render_schema_json,
    splice_readme,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> object:
    return YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))


def _schema_accepts(data: object) -> bool:
    return jsonschema.Draft7Validator(build_schema(Config)).is_valid(data)


def _loader_accepts(path: Path) -> bool:
    try:
        Config.load(path)

    except DatureConfigError:
        return False

    return True


def test_config_schema_json_is_current():
    committed = (REPO_ROOT / "config.schema.json").read_text(encoding="utf-8")

    assert committed == render_schema_json(Config), (
        f"config.schema.json is stale; run: {REGENERATE_COMMAND}"
    )


def test_readme_key_table_is_current():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert splice_readme(readme, render_readme_table(Config)) == readme, (
        f"the README key table is stale; run: {REGENERATE_COMMAND}"
    )


def test_the_schema_is_a_valid_draft_07_schema():
    jsonschema.Draft7Validator.check_schema(build_schema(Config))


def test_the_example_config_satisfies_the_schema():
    assert _schema_accepts(_load_yaml(REPO_ROOT / "config.example.yaml"))


@pytest.mark.parametrize(
    ("edits", "delete"),
    [
        pytest.param({"unexpected": 1}, (), id="unknown-top-level-key"),
        pytest.param({"logging.file.filepath": "x.log"}, (), id="unknown-nested-key"),
        pytest.param({}, ("bot.token",), id="missing-required-key"),
        pytest.param({"limits.user_interval": 0}, (), id="zero-interval"),
        pytest.param({"limits.user_burst": 0}, (), id="zero-burst"),
        pytest.param({"inline.cache_time": -1}, (), id="negative-cache-time"),
        pytest.param({"logging.console.level": "debug"}, (), id="lower-case-level"),
        pytest.param({"logging.file.max_bytes": 1.5}, (), id="float-for-int"),
        pytest.param({"database": None}, (), id="null-database-section"),
        pytest.param({"database.url": 1}, (), id="int-for-url"),
        pytest.param({"database.url": None}, (), id="null-url"),
        pytest.param({"limits.user_interval": 1}, (), id="int-for-float"),
        pytest.param({}, ("database",), id="omitted-database"),
        pytest.param({}, ("limits",), id="omitted-defaulted-section"),
    ],
)
def test_the_schema_accepts_exactly_what_the_loader_accepts(config_file, edits, delete):
    path = config_file(edits, delete=delete)

    assert _schema_accepts(_load_yaml(path)) is _loader_accepts(path)


def test_the_example_config_names_its_schema():
    path = REPO_ROOT / "config.example.yaml"
    first = path.read_text(encoding="utf-8").splitlines()[0]

    assert first == "# yaml-language-server: $schema=./config.schema.json"
