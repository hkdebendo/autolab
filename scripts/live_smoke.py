"""Smoke test of the deployed agent app: one live run started directly (no access code needed from the PC, which
holds the Modal token), its events printed as they arrive. Paid: one live run (counts in LIVE_MAX_RUNS).

    python scripts/live_smoke.py "Try Br and I for S in Li7P3S11 with Li vacancies"
"""

from __future__ import annotations

import sys
import time
import uuid

import modal

from autolab import config
from autolab.agent.live import LiveRefused, events_after, reserve


def main() -> None:
    goal = sys.argv[1]
    store = modal.Dict.from_name(config.MODAL_LIVE_STORE)
    lock = store.get("lock")
    if lock and time.time() - lock["started"] < config.LIVE_RUN_TIMEOUT_S:
        raise LiveRefused(f"a run is already going ({lock['run_id']})")
    run_id = "smoke-" + uuid.uuid4().hex[:8]
    reserve(store, run_id, goal)
    call = modal.Function.from_name(config.MODAL_AGENT_APP, "run_agent").spawn(run_id, goal)
    print(f"run {run_id} started", flush=True)
    after, t0 = 0, time.time()
    while True:
        page = events_after(store, run_id, after)
        for e in page["events"]:
            data = {k: v for k, v in e["data"].items() if k not in ("reply", "reasoning_summary", "decomposition")}
            print(f"{time.time() - t0:7.0f} s [{e['type']}:{e['step']}] {e['candidate_id'] or ''} {str(data)[:200]}",
                  flush=True)
        after = page["next"]
        state = (page["status"] or {}).get("state")
        if state in ("done", "error"):
            print(f"state: {page['status']}")
            break
        time.sleep(10)
    print(call.get(timeout=60) if state == "done" else "")


if __name__ == "__main__":
    main()
