"""Step 9B (GPU): cathode interfaces with UMA energies, after a UMA-vs-MP calibration.

    SIM_BACKEND=local python scripts/run_interfaces.py results/<step>/candidates.json --ids it1-c2 it2-c5 \
        --cathode LiFePO4 --max-relaxations 140 --out <dir>

Calibrations first (Li3PS4 against each config.CALIBRATION_CATHODES, UMA vs MP): if one differs by more
than config.INTERFACE_CALIBRATION_MAX_DIFF, the candidate interfaces are not computed.
interfaces.json is rewritten after each item, and the cache is copied to --backup if given.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from autolab import config
from autolab.agent.electrochem import (candidate_entry, interface_calibration, prefetch_interface_references,
                                       uma_interface)
from autolab.sim.backend import BudgetExceeded, RelaxBudget


def backup(dest: Path | None) -> None:
    """Copy the UMA caches (relaxations, MD) to a persistent folder, e.g. Google Drive."""
    if dest is None:
        return
    for sub in ("relax", "md"):
        if (config.CACHE_DIR / sub).exists():
            shutil.copytree(config.CACHE_DIR / sub, dest / sub, dirs_exist_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", type=Path)
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--cathode", default="LiFePO4")
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--backup", type=Path)
    args = ap.parse_args()

    by_id = {c["id"]: c for c in json.loads(args.candidates.read_text(encoding="utf-8"))["candidates"]}
    budget = RelaxBudget(args.max_relaxations)
    out = {"cathode": args.cathode, "tolerance": config.INTERFACE_CALIBRATION_MAX_DIFF,
           "max_relaxations": args.max_relaxations, "calibrations": [], "candidates": [], "stopped": None}
    args.out.mkdir(parents=True, exist_ok=True)

    def save():
        out["new_relaxations"] = budget.used
        (args.out / "interfaces.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        backup(args.backup)

    try:
        # References in batches (one GPU session each on Kaggle): calibrations first, candidates only if they pass.
        n = prefetch_interface_references([("Li3PS4", c) for c in config.CALIBRATION_CATHODES], budget=budget)
        print(f"calibration references: {n} structures, new relaxations {budget.used}", flush=True)
        for cathode in config.CALIBRATION_CATHODES:
            t0 = time.perf_counter()
            cal = interface_calibration(cathode, budget=budget)
            cal["seconds"] = round(time.perf_counter() - t0, 1)
            out["calibrations"].append(cal)
            print(f"calibration Li3PS4/{cathode}: UMA {cal['uma']['min_reaction_energy']:.3f} vs MP "
                  f"{cal['mp']['min_reaction_energy']:.3f} eV/atom, diff {cal['diff']:+.3f} "
                  f"({'ok' if cal['ok'] else 'TOO LARGE'}), {cal['seconds']} s", flush=True)
            save()
        bad = [c["cathode"] for c in out["calibrations"] if not c["ok"]]
        if bad:
            out["stopped"] = f"calibration outside tolerance for {bad}: candidate interfaces not computed"
        else:
            n = prefetch_interface_references(
                [(candidate_entry(by_id[cid]).composition, args.cathode) for cid in args.ids], budget=budget)
            print(f"candidate references: {n} structures, new relaxations {budget.used}", flush=True)
            for cid in args.ids:
                t0 = time.perf_counter()
                res = uma_interface(by_id[cid], args.cathode, budget=budget)
                res.update(id=cid, seconds=round(time.perf_counter() - t0, 1))
                out["candidates"].append(res)
                print(f"{cid} {res['electrolyte']} / {args.cathode}: {res['min_reaction_energy']:.3f} eV/atom "
                      f"({res['reaction']}), {res['references']} references, {res['seconds']} s", flush=True)
                save()
    except BudgetExceeded as e:
        out["stopped"] = f"relaxation budget: {e}"
    finally:  # an unexpected error still keeps the finished items and the cache
        save()
    print(f"stopped: {out['stopped']}" if out["stopped"] else "done", f"| new relaxations {budget.used}/{budget.max_new}")


if __name__ == "__main__":
    main()
