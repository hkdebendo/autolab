"""Validation benchmark (roadmap step 2): known good and bad compounds through the funnel, judged blind.

    SIM_BACKEND=modal python scripts/run_benchmark.py --out results/<dir> [--max-relaxations 80] [--no-md] [--dry-run]

Compounds: config.BENCHMARK_GOOD, config.BENCHMARK_BAD and the hard negatives config.BENCHMARK_HARD (stable
insulators that conduct Li poorly). Relaxations on Modal (cached); band gaps and electrodes on this machine; then the
compounds still passing go to MD at the screening settings (Modal config.MODAL_MD_GPU, cached runs reused) and are
judged against beta-Li3PS4 (config.BENCHMARK_MD_REFERENCE); not launched above config.BENCHMARK_MD_MAX_USD.
--dry-run stops before the MD and prints its estimated cost. Writes benchmark.json, benchmark.md and events.jsonl.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.benchmark import evaluate_known, md_check, md_jobs, render, summarize
from autolab.agent.events import EventLog
from autolab.data.mp import get_structure
from autolab.domains import get_domain
from autolab.sim.backend import BudgetExceeded, RelaxBudget


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    ap.add_argument("--no-md", action="store_true", help="funnel and Li-metal check only")
    ap.add_argument("--dry-run", action="store_true", help="stop before the MD, print its estimated cost")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    events = EventLog(args.out / "events.jsonl")
    budget = RelaxBudget(args.max_relaxations)
    tools = get_domain("electrolyte").make_tools()
    items = [(m, "pass", n, "good") for m, n in config.BENCHMARK_GOOD.items()] + \
            [(m, "reject", n, "bad") for m, n in config.BENCHMARK_BAD.items()] + \
            [(m, "reject", n, "hard") for m, n in config.BENCHMARK_HARD.items()]
    rows = []
    for mid, expected, note, group in items:
        try:
            r = evaluate_known(mid, expected, note, tools, get_structure, events, budget, group=group)
        except BudgetExceeded as e:  # stop cleanly: what is done is kept
            print(f"stopped at {mid}: {e}")
            break
        rows.append(r)
        print(f"{mid} {r['formula']}: expected {expected}, E_hull {r['e_hull']}, gap {r['gap_optb88']}, "
              f"{r.get('passivation')} -> {r['outcome']} ({r['rejected_at']}: {r['reason']})", flush=True)
        (args.out / "benchmark.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")

    md = None
    if not args.no_md:
        from autolab.agent.dynamics import md_runs_to_compute, md_screen, md_verdicts, modal_md_plan, parent_job
        from autolab.sim.backend import ModalBackend

        ref = parent_job(config.BENCHMARK_MD_REFERENCE)
        jobs = md_jobs(rows, ref)
        todo = md_runs_to_compute(jobs)
        plan = modal_md_plan(todo) if todo else {"gpu": config.MODAL_MD_GPU, "runs": 0, "usd": 0.0, "usd_max": 0.0,
                                                 "wall_s": 0, "timeout_s": 0}
        print(f"MD: {len(jobs) - 1} compounds against {ref['formula']}, {plan['runs']} runs to compute on Modal "
              f"{plan['gpu']}: about {plan['wall_s'] / 60:.0f} min in parallel, about {plan['usd']:.2f} $ (at most "
              f"{plan['usd_max']:.2f} $)", flush=True)
        if args.dry_run:
            return
        if plan["usd"] > config.BENCHMARK_MD_MAX_USD:
            md = {"stopped": f"estimated {plan['usd']:.2f} $ above BENCHMARK_MD_MAX_USD ({config.BENCHMARK_MD_MAX_USD} $)"}
        else:
            backend = ModalBackend(md_timeout_s=plan["timeout_s"]) if plan["runs"] else None
            md_rows = md_verdicts(md_screen(jobs, backend=backend, max_runs=len(jobs) * config.MD_SCREEN_SEEDS))
            md_check(rows, md_rows, ref["formula"])
            md = {"plan": {k: plan.get(k) for k in ("gpu", "runs", "usd", "usd_max")},
                  "rows": [{k: v for k, v in m.items() if k != "D_blocks_cm2_per_s"} for m in md_rows],
                  "errors": getattr(backend, "errors", None)}
    s = summarize(rows)
    (args.out / "benchmark.json").write_text(json.dumps({"summary": s, "rows": rows, "md": md,
                                                         "new_relaxations": budget.used}, indent=1, default=str),
                                             encoding="utf-8")
    tail = f"\n\nNew UMA relaxations: {budget.used}."
    if md and md.get("plan"):
        tail += f" MD: {md['plan']['runs']} new runs on Modal {md['plan']['gpu']}, estimate {md['plan']['usd']:.2f} $."
    elif md:
        tail += f" MD not launched: {md['stopped']}."
    (args.out / "benchmark.md").write_text(render(rows, s) + tail + "\n", encoding="utf-8")
    print(render(rows, s) + tail)


if __name__ == "__main__":
    main()
