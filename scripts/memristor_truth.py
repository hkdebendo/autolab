"""Truth test of the oxygen-vacancy barriers (memristor domain), criterion fixed before the runs (config.MEMRISTOR_TRUTH).

    SIM_BACKEND=modal python scripts/memristor_truth.py --out results/<dir> [--dry-run]

CeO2 (fast oxygen conductor) and MgO (slow), plus the three parents of the domain measured without criterion: each
MP structure relaxed with UMA, a neutral O vacancy, the lowest of the distinct nearest hops (NEB), as for a candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autolab import config
from autolab.analysis.migration import hop_items, lowest_barrier
from autolab.sim.backend import neb_missing, neb_plan, relax_structures, run_nebs


def relaxed(material_id: str):
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.data.mp import get_structure
    from autolab.sim.serialize import atoms_from_dict

    s = get_structure(material_id)
    r = relax_structures([s], max_new=1)[0]
    return AseAtomsAdaptor.get_structure(atoms_from_dict(r["atoms"])), s.composition.reduced_formula


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="estimate the cost (the structures are relaxed)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t = config.MEMRISTOR_TRUTH
    ids = [t["fast"], t["slow"], *config.MEMRISTOR_PARENTS]
    jobs = {}
    for m in ids:
        s, formula = relaxed(m)
        items, info = hop_items(s, max_hops=config.NEB_MAX_HOPS)
        jobs[m] = (formula, items, info)
        print(f"{formula} ({m}): {info['n_atoms']} atoms, hops {[h['distance_A'] for h in info['hops']]}")
    all_items = [it for _, items, _ in jobs.values() for it in items]
    plan = neb_plan(neb_missing(all_items))
    print(f"{plan['hops']} NEB hops to compute on a T4: about {plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $)")
    if args.dry_run:
        return
    results = run_nebs(all_items)
    rows, k = {}, 0
    for m, (formula, items, info) in jobs.items():
        mine = results[k:k + len(items)]
        k += len(items)
        rows[m] = {"formula": formula, "n_atoms": info["n_atoms"], **lowest_barrier(mine, info["hops"])}
    fast, slow = rows[t["fast"]], rows[t["slow"]]
    tests = {"fast_low": fast["barrier_eV"] is not None and fast["barrier_eV"] <= t["fast_max_eV"],
             "slow_above_fast": None not in (fast["barrier_eV"], slow["barrier_eV"])
             and slow["barrier_eV"] - fast["barrier_eV"] >= t["gap_eV"],
             "converged": all(r["converged_hops"] == len(r["hops"]) for r in rows.values())}
    result = {"criterion": f"{fast['formula']} <= {t['fast_max_eV']} eV and {slow['formula']} at least {t['gap_eV']} eV "
                           "higher, every band converged (fixed before the runs)",
              "rows": rows, "tests": tests, "passed": all(tests.values()), "estimated_usd": plan["usd"]}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    lines = ["# Truth test of the oxygen-vacancy migration barriers (NEB with UMA)", "",
             f"Criterion, fixed before the runs: {result['criterion']}.", "",
             "| Material | Role | Atoms | Hops (Å) | Barriers (eV) | Lowest (eV) |", "|---|---|---|---|---|---|"]
    for m, r in rows.items():
        role = "fast reference" if m == t["fast"] else "slow reference" if m == t["slow"] else "parent of the domain"
        hops = ", ".join(f"{h['distance_A']}" for h in r["hops"])
        bars = ", ".join("—" if h["barrier_eV"] is None else f"{h['barrier_eV']:.2f}{'' if h['converged'] else ' (not converged)'}"
                         for h in r["hops"])
        lines.append(f"| {r['formula']} ({m}) | {role} | {r['n_atoms']} | {hops} | {bars} | "
                     f"{'—' if r['barrier_eV'] is None else format(r['barrier_eV'], '.2f')} |")
    lines += ["", f"Tests: {tests}.", f"**Verdict: {'passed' if result['passed'] else 'FAILED'}.**", ""]
    (args.out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
