"""Stopping a research on request (interface.md 9): one flag per process, checked between steps.

The agent sets `watch(should_stop)` for the duration of a run; long waits (MD runs on Modal) poll `requested()`
and cancel what they started. A step already running finishes its current unit of work (a relaxation chunk, a
model reply) and nothing new starts after it: the interface says "stopping" until the run reports "interrupted".
"""

from __future__ import annotations

from typing import Callable

_should_stop: Callable[[], bool] | None = None


class Cancelled(RuntimeError):
    """The user asked to stop the research."""


def watch(should_stop: Callable[[], bool] | None) -> None:
    global _should_stop
    _should_stop = should_stop


def requested() -> bool:
    try:
        return bool(_should_stop and _should_stop())
    except Exception:  # an unreachable store must not stop a research by mistake
        return False


def check() -> None:
    if requested():
        raise Cancelled("stopped by the user")
