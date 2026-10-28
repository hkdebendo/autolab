"""Disk cache for expensive results (UMA relaxations, MD): one JSON file per key."""

from __future__ import annotations

import json
from pathlib import Path


class JsonCache:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def _path(self, key: str) -> Path:
        return self.folder / f"{key}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def set(self, key: str, value: dict) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        tmp = self._path(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(value), encoding="utf-8")
        tmp.replace(self._path(key))
