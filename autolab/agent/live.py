"""Live runs for the jury (production, roadmap): access code, one run at a time, a total cap, cache first.

The store is any dict-like object (a modal.Dict in production, a plain dict in tests). Events are appended to
store["<run_id>/events"] as they happen, so the web page shows the agents at work; the result goes to
store["<run_id>/result"]. A request already answered replays for free: every model reply comes from the reply
cache (same question) and every computation from the caches, so nothing new is paid or computed.
"""

from __future__ import annotations

import contextlib
import hmac
import time

from autolab import config


class LiveRefused(RuntimeError):
    """The request cannot start (wrong code, a run already going, cap reached, bad goal)."""


def check_request(goal: str, code: str, expected_code: str | None, store) -> None:
    """Raise LiveRefused when a live run must not start."""
    if not expected_code or not hmac.compare_digest(str(code or ""), expected_code):
        raise LiveRefused("wrong access code")
    goal = (goal or "").strip()
    if not goal or len(goal) > config.LIVE_GOAL_MAX_CHARS:
        raise LiveRefused(f"the request must be 1 to {config.LIVE_GOAL_MAX_CHARS} characters")
    lock = store.get("lock")
    if lock and time.time() - lock["started"] < config.LIVE_RUN_TIMEOUT_S:
        raise LiveRefused(f"a run is already going ({lock['run_id']}): one at a time")
    if store.get("live_runs", 0) >= config.LIVE_MAX_RUNS:
        raise LiveRefused(f"the {config.LIVE_MAX_RUNS} live runs allowed in production are used")


def reserve(store, run_id: str, goal: str) -> None:
    store["lock"] = {"run_id": run_id, "started": time.time()}
    store["live_runs"] = store.get("live_runs", 0) + 1
    store[f"{run_id}/events"] = []
    store[f"{run_id}/status"] = {"state": "starting", "goal": goal}


class StoreSink:
    """EventLog sink: appends each event to the store (read by the web page)."""

    def __init__(self, store, run_id: str):
        self.store, self.key = store, f"{run_id}/events"

    def __call__(self, event: dict) -> None:
        self.store[self.key] = [*self.store.get(self.key, []), event]


def events_after(store, run_id: str, after: int = 0) -> dict:
    events = store.get(f"{run_id}/events")
    if events is None:
        return {"events": [], "next": after, "status": None}
    return {"events": events[after:], "next": len(events), "status": store.get(f"{run_id}/status")}


@contextlib.contextmanager
def live_limits():
    """The config limits of a live run, restored afterwards."""
    saved = {"MD_SELECT_MAX": config.MD_SELECT_MAX}
    config.MD_SELECT_MAX = config.LIVE_MD_SELECT_MAX
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(config, k, v)


def run_live(run_id: str, goal: str, store, make_agent, prior: list[dict]) -> dict:
    """One live run. `make_agent(events)` builds the Agent (models, budget, tools); the lock is always released."""
    from autolab.agent.events import EventLog

    store[f"{run_id}/status"] = {"state": "running", "goal": goal}
    try:
        with live_limits():
            agent = make_agent(EventLog(sink=StoreSink(store, run_id)))
            result = agent.run(goal, None, config.LIVE_ITERATIONS, config.LIVE_CANDIDATES, prior=prior)
        store[f"{run_id}/result"] = result
        store[f"{run_id}/status"] = {"state": "done", "goal": goal}
        return result
    except Exception as e:  # reported to the page, never retried
        store[f"{run_id}/status"] = {"state": "error", "goal": goal, "error": f"{type(e).__name__}: {e}"[:500]}
        raise
    finally:
        lock = store.get("lock")
        if lock and lock["run_id"] == run_id:
            store["lock"] = None
