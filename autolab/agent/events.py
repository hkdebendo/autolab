"""Events emitted by every step of the funnel and the loop (SPEC 6.1), for live display and replay."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class EventLog:
    """Keeps events in memory, appends them to a JSONL file and passes them to an optional sink."""

    def __init__(self, path: Path | str | None = None, sink: Callable[[dict], None] | None = None):
        self.events: list[dict] = []
        self.path = Path(path) if path else None
        self.sink = sink
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, type: str, step: str, data: dict | None = None, candidate_id: str | None = None) -> dict:
        event = {
            "type": type,
            "candidate_id": candidate_id,
            "step": step,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.events.append(event)
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")
        if self.sink:
            self.sink(event)
        return event
