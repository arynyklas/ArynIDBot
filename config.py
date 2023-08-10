from pathlib import Path
from pydantic import BaseModel
from yaml import load as yaml_load, Loader as YAMLLoader


CONFIG_FILEPATH: Path = Path(__file__).parent / "config.yml"

ENCODING: str = "utf-8"


class DBConfig(BaseModel):
    url: str
    name: str


class Config(BaseModel):
    bot_token: str
    db: DBConfig
    inline_cache_time: int
    rating_update_seconds: int


with CONFIG_FILEPATH.open("r", encoding=ENCODING) as file:
    config_data: dict = yaml_load(
        stream = file,
        Loader = YAMLLoader
    )


config: Config = Config(
    **config_data
)
