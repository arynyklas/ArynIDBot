from collections import OrderedDict


class LruCache[K, V]:
    """Mapping that forgets its least recently used entry beyond `size` entries."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._data: OrderedDict[K, V] = OrderedDict()

    def get(self, key: K) -> V | None:
        value = self._data.get(key)

        if value is not None:
            self._data.move_to_end(key)

        return value

    def put(self, key: K, value: V) -> None:
        self._data[key] = value
        self._data.move_to_end(key)

        if len(self._data) > self._size:
            self._data.popitem(last=False)
