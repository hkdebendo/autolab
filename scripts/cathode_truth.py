"""Truth test of the cathode domain: UMA average voltage, capacity and volume change of four known cobalt-free cathodes.

    SIM_BACKEND=modal python scripts/cathode_truth.py --out results/<dir> [--dry-run]

Criterion fixed before the runs (config.CATHODE_VOLTAGE_REFERENCE_V, CATHODE_VOLTAGE_TRUTH_TOL_V): each parent's
average voltage (x = 1 -> 0, the same relaxation and delithiation as a candidate) within the tolerance of experiment,
LiFePO4 the lowest and LiNi0.5Mn1.5O4 the highest. 4 lithiated + 4 delithiated cells + Li metal = 9 relaxations
(cached; T4 on Modal).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autolab import config
from autolab.analysis.cathode import removable_li
from autolab.data.mp import get_structure
from autolab.domains.cathode import CathodeTools
from autolab.sim.backend import RelaxBudget


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="print the plan, compute nothing")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parents = {pid: get_structure(pid) for pid in config.CATHODE_PARENTS}
    print("Plan:")
    for pid, s in parents.items():
        print(f"  {pid} {s.composition.reduced_formula}: {len(s)} atoms, {removable_li(s)} of "
              f"{int(s.composition['Li'])} Li removable; experiment {config.CATHODE_VOLTAGE_REFERENCE_V[pid]} V")
    print(f"  {2 * len(parents) + 1} relaxations at most (cached ones are not redone), GPU T4 on Modal")
    if args.dry_run:
        return
    tools, budget = CathodeTools(not_run=[]), RelaxBudget(2 * len(parents) + 1)
    rows = []
    for pid, s in parents.items():
        m = tools.parent_metrics(pid, s, budget)
        ref = config.CATHODE_VOLTAGE_REFERENCE_V[pid]
        v = m.get("voltage_V")
        rows.append({"id": pid, "formula": s.composition.reduced_formula, "experiment_V": ref, "uma_V": v,
                     "error_V": None if v is None else round(v - ref, 3),
                     "within_tolerance": v is not None and abs(v - ref) <= config.CATHODE_VOLTAGE_TRUTH_TOL_V,
                     **{k: m.get(k) for k in ("li_removed", "li_total", "capacity_mAh_g", "energy_density_Wh_kg",
                                              "volume_change_pct", "lithiated_volume_A3", "delithiated_volume_A3",
                                              "delithiated_formula", "li_metal_energy", "error")}})
    volts = {r["id"]: r["uma_V"] for r in rows if r["uma_V"] is not None}
    order_ok = len(volts) == len(rows) and min(volts, key=volts.get) == "mp-19017" and max(volts, key=volts.get) == "mp-771112"
    passed = all(r["within_tolerance"] for r in rows) and order_ok
    result = {"criterion": f"each |UMA - experiment| <= {config.CATHODE_VOLTAGE_TRUTH_TOL_V} V; LiFePO4 lowest, "
                           "LiNi0.5Mn1.5O4 highest (fixed before the runs)",
              "rows": rows, "order_ok": order_ok, "passed": passed, "new_relaxations": budget.used}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    lines = ["# Truth test of the cathode domain (UMA voltage of known cobalt-free cathodes)", "",
             f"Criterion, fixed before the runs: {result['criterion']}.", "",
             "| Cathode | Experiment (V) | UMA (V) | Error (V) | Li removed | Capacity (mAh/g) | Energy density (Wh/kg) | "
             "Volume change (%) |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['formula']} ({r['id']}) | {r['experiment_V']:.2f} | {r['uma_V'] if r['uma_V'] is None else format(r['uma_V'], '.2f')} | "
                     f"{r['error_V'] if r['error_V'] is None else format(r['error_V'], '+.2f')} | {r['li_removed']} of {r['li_total']} | "
                     f"{r['capacity_mAh_g']} | {r['energy_density_Wh_kg']} | {r['volume_change_pct']} |")
    lines += ["", f"Order (LiFePO4 lowest, LiNi0.5Mn1.5O4 highest): {'right' if order_ok else 'wrong'}.",
              f"**Verdict: {'passed' if passed else 'FAILED'}.** New relaxations: {budget.used}.", ""]
    (args.out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
