from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


class _Section:
    """Секция yaml-конфига: явное чтение значения с типом и дефолтом."""

    def __init__(self, data: Any) -> None:
        self._data: dict[str, Any] = data if isinstance(data, dict) else {}

    def value(
        self, key: str, default: Any, cast: Callable[[Any], Any] = lambda x: x
    ) -> Any:
        if key not in self._data:
            return default
        return cast(self._data[key])


class YamlConfig:
    """Загрузка yaml-файла и доступ к его секциям."""

    def __init__(self, path: Path) -> None:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                self._data: dict[str, Any] = yaml.safe_load(f) or {}
        else:
            self._data = {}

    def section(self, name: str) -> _Section:
        return _Section(self._data.get(name))


def int_tuple(raw: Any) -> tuple[int, ...]:
    return tuple(int(x) for x in raw)
