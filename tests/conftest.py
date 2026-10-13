from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_CONFIG_PATH = REPO_ROOT / "config.example.yaml"


@pytest.fixture
def config_file(tmp_path: Path) -> Callable[..., Path]:
    """Write config.example.yaml, edited, to `tmp_path / "config.yaml"`.

    `config_file({"database.url": None})` sets a dotted key (adding it if new);
    `config_file(delete=("database",))` drops one.
    """

    def write(
        edits: Mapping[str, object] | None = None, *, delete: tuple[str, ...] = ()
    ) -> Path:
        yaml = YAML(typ="safe", pure=True)
        yaml.default_flow_style = False
        yaml.allow_unicode = True
        data = yaml.load(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"))

        for dotted, value in (edits or {}).items():
            parent, key = _parent(data, dotted)
            parent[key] = value

        for dotted in delete:
            parent, key = _parent(data, dotted)
            del parent[key]

        path = tmp_path / "config.yaml"

        with path.open("w", encoding="utf-8") as stream:
            yaml.dump(data, stream)

        return path

    return write


def _parent(data: dict[str, Any], dotted: str) -> tuple[dict[str, Any], str]:
    *sections, key = dotted.split(".")

    for section in sections:
        data = data[section]

    return data, key
