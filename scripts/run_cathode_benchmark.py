"""Blind benchmark of the cathode funnel on known compounds (config.CATHODE_BENCHMARK).

    SIM_BACKEND=modal python scripts/run_cathode_benchmark.py --out results/<dir> [--dry-run]

Relaxations are cached (T4 on Modal); the run stops at config.CATHODE_BENCHMARK_MAX_RELAXATIONS new relaxations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autolab import config
from autolab.agent.cathode_benchmark import evaluate_known, outcome, render, summarize
from autolab.agent.events import EventLog
from autolab.analysis.cathode import cathode_charge_check, removable_li
from autolab.data.mp import get_structure
from autolab.domains.cathode import CathodeTools
from autolab.sim.backend import RelaxBudget


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    structures = {e["id"]: get_structure(e["id"]) for e in config.CATHODE_BENCHMARK}
    for e in config.CATHODE_BENCHMARK:
        s = structures[e["id"]]
        simulated = cathode_charge_check(s)["ok"] and removable_li(s) > 0
        print(f"{e['formula']} ({e['id']}, {len(s)} atoms): {'simulated' if simulated else 'decided before any simulation'}"
              f"; expected {e['expected']}")
    if args.dry_run:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    tools, budget = CathodeTools(not_run=[]), RelaxBudget(config.CATHODE_BENCHMARK_MAX_RELAXATIONS)
    events = EventLog(args.out / "events.jsonl")
    rows = []
    for e in config.CATHODE_BENCHMARK:
        try:
            res = evaluate_known(e, structures[e["id"]], tools, events, budget)
        except Exception as err:  # reported, not retried (e.g. the relaxation budget)
            res = {"id": e["id"], "formula": e["formula"], "status": "error", "reason": f"{type(err).__name__}: {err}"}
        row = {**{k: v for k, v in res.items() if k not in ("relaxed_atoms", "delithiated_atoms", "decomposition")},
               "group": e["group"], "expected": e["expected"], "why": e["why"], "outcome": outcome(res)}
        rows.append(row)
        print(f"{e['formula']}: {row['outcome']} (expected {e['expected']}) {row.get('reason') or ''}", flush=True)
    summary = summarize(rows)
    (args.out / "result.json").write_text(json.dumps({"rows": rows, "summary": summary, "new_relaxations": budget.used},
                                                     indent=1, default=str), encoding="utf-8")
    text = render(rows, summary)
    (args.out / "report.md").write_text(text + f"\nNew relaxations: {budget.used}.\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
