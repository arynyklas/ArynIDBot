"""Rating of users by the biggest message ID their inline message got, in MongoDB."""

import asyncio
from logging import Logger
import math
import time
from typing import TypedDict

from pymongo import DESCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import PyMongoError

from src.config import DatabaseConfig, RatingConfig

_COLLECTION = "users"


class _User(TypedDict):
    user_id: int
    score: int


class Rating:
    def __init__(
        self,
        url: str,
        database: DatabaseConfig,
        cfg: RatingConfig,
        logger: Logger,
    ) -> None:
        self._client: AsyncMongoClient[_User] = AsyncMongoClient(
            url,
            serverSelectionTimeoutMS=int(database.timeout * 1000),
            # Connect on first use: a database outage must not hold the bot up.
            connect=False,
        )
        self._users: AsyncCollection[_User] = self._client.get_database(
            database.name
        ).get_collection(_COLLECTION)
        self._cfg = cfg
        self._logger = logger
        self._top: tuple[tuple[int, int], ...] | None = None
        self._read_at = -math.inf
        self._lock = asyncio.Lock()

    async def create_indexes(self) -> None:
        """One document per user, and the board read off an index. Best effort."""
        try:
            await self._users.create_index("user_id", unique=True)
            await self._users.create_index([("score", DESCENDING)])

        except PyMongoError as ex:
            self._logger.warning("Rating indexes not created: %s", ex)

    async def record(self, user_id: int, score: int) -> None:
        """Keep `score` if it beats the user's best. Best effort."""
        try:
            await self._users.update_one(
                {"user_id": user_id}, {"$max": {"score": score}}, upsert=True
            )

        except PyMongoError as ex:
            self._logger.warning("Score of user %d not recorded: %s", user_id, ex)

    async def top(self) -> tuple[tuple[int, int], ...] | None:
        """`(user_id, score)` pairs, best first; `None` if never read successfully.

        A read is reused for `refresh_interval` seconds, a failed one too: an
        unreachable database then costs one timeout per interval, not one per
        request.
        """
        async with self._lock:
            if time.monotonic() - self._read_at < self._cfg.refresh_interval:
                return self._top

            try:
                users = (
                    await self._users.find({}, {"_id": False})
                    .sort("score", DESCENDING)
                    .limit(self._cfg.size)
                    .to_list()
                )
                self._top = tuple((user["user_id"], user["score"]) for user in users)

            except PyMongoError as ex:
                self._logger.warning("Rating not read: %s", ex)

            self._read_at = time.monotonic()

            return self._top

    async def close(self) -> None:
        await self._client.close()
