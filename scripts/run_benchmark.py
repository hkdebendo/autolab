"""Validation benchmark (roadmap step 2): known good and bad compounds through the funnel, judged blind.

    SIM_BACKEND=modal python scripts/run_benchmark.py --out results/<dir> [--max-relaxations 80]

Compounds: config.BENCHMARK_GOOD and config.BENCHMARK_BAD. Relaxations on Modal (cached); band gaps and
electrodes on this machine. Writes benchmark.json, benchmark.md and events.jsonl.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.benchmark import evaluate_known, render, summarize
from autolab.agent.events import EventLog
from autolab.data.mp import get_structure
from autolab.domains import get_domain
from autolab.sim.backend import BudgetExceeded, RelaxBudget


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    events = EventLog(args.out / "events.jsonl")
    budget = RelaxBudget(args.max_relaxations)
    tools = get_domain("electrolyte").make_tools()
    items = [(m, "pass", n) for m, n in config.BENCHMARK_GOOD.items()] + \
            [(m, "reject", n) for m, n in config.BENCHMARK_BAD.items()]
    rows = []
    for mid, expected, note in items:
        try:
            r = evaluate_known(mid, expected, note, tools, get_structure, events, budget)
        except BudgetExceeded as e:  # stop cleanly: what is done is kept
            print(f"stopped at {mid}: {e}")
            break
        rows.append(r)
        print(f"{mid} {r['formula']}: expected {expected}, E_hull {r['e_hull']}, gap {r['gap_optb88']}, "
              f"{r.get('passivation')} -> {r['outcome']} ({r['rejected_at']}: {r['reason']})", flush=True)
        (args.out / "benchmark.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    s = summarize(rows)
    (args.out / "benchmark.json").write_text(json.dumps({"summary": s, "rows": rows, "new_relaxations": budget.used},
                                                        indent=1, default=str), encoding="utf-8")
    (args.out / "benchmark.md").write_text(render(rows, s) + f"\n\nNew UMA relaxations: {budget.used}.\n",
                                           encoding="utf-8")
    print(render(rows, s))


if __name__ == "__main__":
    main()
