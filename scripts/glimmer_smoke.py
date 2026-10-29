"""Smoke test of Muse Glimmer on its Fireworks deployment: wait until it is created, then one summary of a real
iteration (paid: one wake-up of the scale-to-zero deployment, ~0.7-1 $).

    python scripts/glimmer_smoke.py results/2026-10-29_reference_run/result.json
"""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.runs import summarizer


def wait_created(max_s: float = 1800, poll_s: float = 30) -> str:
    dep = os.environ["GLIMMER_DEPLOYMENT"]
    h = {"Authorization": f"Bearer {config.require_key('FIREWORKS_API_KEY')}"}
    t0 = time.time()
    while True:
        state = httpx.get(f"https://api.fireworks.ai/v1/{dep}", headers=h, timeout=60).json().get("state")
        print(f"{time.time() - t0:5.0f} s deployment state: {state}", flush=True)
        if state != "CREATING" or time.time() - t0 > max_s:
            return state
        time.sleep(poll_s)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if wait_created() not in ("READY", "PARTIAL_READY", "UPDATING"):  # PARTIAL_READY: created, scaled to zero
        raise SystemExit("deployment not ready: nothing called")
    result = json.loads(open(sys.argv[1], encoding="utf-8").read())
    it = result["iterations"][0]
    data = {"iteration": 1, "hypothesis": it["proposal"]["reply"]["hypothesis"],
            "candidates": [{k: c.get(k) for k in ("formula", "status", "rejected_at", "reason", "e_hull", "gap_optb88")
                            if c.get(k) is not None} for c in it["candidates"]],
            "lessons": it["analysis"]["reply"]["lessons"], "next_direction": it["analysis"]["reply"]["next_direction"]}
    events = EventLog(sink=lambda e: print(json.dumps(e["data"], ensure_ascii=False)[:600], flush=True))
    s = summarizer(events)
    t0 = time.time()
    s.submit("iteration", "iteration 1", data)
    out = s.close(timeout=config.GLIMMER_WARMUP_MAX_S + 120)
    print(f"done in {time.time() - t0:.0f} s: {out[0].get('text') or out[0].get('error')}")


if __name__ == "__main__":
    main()
