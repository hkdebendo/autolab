"""Check of the barrier tolerance MEMRISTOR_EA_SIGNIFICANT_EV (memristor domain), rule fixed before the runs
(config.MEMRISTOR_TOLERANCE_CHECK).

    SIM_BACKEND=modal python scripts/memristor_tolerance.py --out results/<dir> [--dry-run]

On rutile TiO2: (1) numerical noise: each hop of the truth test recomputed between another, symmetry-equivalent pair
of sites of the same supercell; (2) finite-size effect: the lowest hop recomputed in a larger supercell. The spread is
the largest difference; above the tolerance, the tolerance becomes the spread rounded up to 0.05 eV.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from pymatgen.io.ase import AseAtomsAdaptor

from autolab import config
from autolab.analysis.migration import compact_supercell, lowest_barrier
from autolab.sim.backend import neb_missing, neb_plan, run_nebs
from autolab.sim.neb import vacancy_hops
from autolab.sim.serialize import atoms_to_dict

from memristor_truth import relaxed


def equivalent_pair(sc, hop: dict) -> dict | None:
    """Another pair of sites with the same symmetry classes and distance, as far as possible from the first one."""
    import numpy as np
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    eq = SpacegroupAnalyzer(sc, symprec=0.05).get_symmetry_dataset().equivalent_atoms
    i, j = hop["i"], hop["j"]
    want = sorted((eq[i], eq[j]))
    mid0 = (sc[i].coords + sc[j].coords) / 2
    best, far = None, -1.0
    for a in range(len(sc)):
        if sc[a].specie.symbol != config.MEMRISTOR_MOBILE_ION or a in (i, j):
            continue
        for n in sc.get_neighbors(sc[a], config.NEB_HOP_CUTOFF_A):
            b = n.index
            if b in (i, j) or sorted((eq[a], eq[b])) != want or abs(n.nn_distance - hop["distance_A"]) > 0.02:
                continue
            d = float(np.linalg.norm(sc.lattice.get_cartesian_coords(
                sc.lattice.get_fractional_coords((sc[a].coords + n.coords) / 2 - mid0) % 1.0)))
            if d > far:
                best, far = {"i": a, "j": b, "distance_A": round(float(n.nn_distance), 2)}, d
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    chk = config.MEMRISTOR_TOLERANCE_CHECK
    s, formula = relaxed(chk["material"])
    sc = compact_supercell(s)
    hops = vacancy_hops(sc, species=config.MEMRISTOR_MOBILE_ION, max_hops=config.NEB_MAX_HOPS)
    atoms = atoms_to_dict(AseAtomsAdaptor.get_atoms(sc))
    twins = [equivalent_pair(sc, h) for h in hops]
    big = compact_supercell(s, min_length=chk["larger_min_length"])
    big_hop = vacancy_hops(big, species=config.MEMRISTOR_MOBILE_ION, max_hops=1)  # the shortest hop only
    big_atoms = atoms_to_dict(AseAtomsAdaptor.get_atoms(big))
    items = ([{"atoms": atoms, "i": h["i"], "j": h["j"]} for h in hops]
             + [{"atoms": atoms, "i": t["i"], "j": t["j"]} for t in twins if t]
             + [{"atoms": big_atoms, "i": h["i"], "j": h["j"]} for h in big_hop])
    plan = neb_plan(neb_missing(items))
    print(f"{formula}: {len(sc)} atoms (hops {[h['distance_A'] for h in hops]}, equivalent pairs "
          f"{[t and t['distance_A'] for t in twins]}), larger cell {len(big)} atoms (hops {[h['distance_A'] for h in big_hop]})")
    print(f"{plan['hops']} NEB hops to compute on a T4: about {plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $)")
    if args.dry_run:
        return
    res = run_nebs(items)
    n, m = len(hops), len([t for t in twins if t])
    base = lowest_barrier(res[:n], hops)
    twin_rows = lowest_barrier(res[n:n + m], [t for t in twins if t])["hops"]
    big_low = lowest_barrier(res[n + m:], big_hop)
    diffs = []
    lines = ["# Check of the barrier tolerance (memristor domain)", "",
             f"Rule, fixed before the runs: the largest difference between equivalent hops (noise) and between cell sizes "
             f"(finite size) must stay within MEMRISTOR_EA_SIGNIFICANT_EV = {config.MEMRISTOR_EA_SIGNIFICANT_EV} eV; else "
             "the tolerance becomes that spread rounded up to 0.05 eV.", "",
             "| Hop | Barrier (eV) | Equivalent pair (eV) | Difference (eV) |", "|---|---|---|---|"]
    k = 0
    for h, row in zip(hops, base["hops"]):
        t = None
        if twins[hops.index(h)]:
            t = twin_rows[k]
            k += 1
        ok = row["converged"] and t is not None and t["converged"]
        d = abs(row["barrier_eV"] - t["barrier_eV"]) if ok else None
        if d is not None:
            diffs.append(d)
        lines.append(f"| {h['distance_A']} Å | {row['barrier_eV']} | {t and t['barrier_eV']} | {'—' if d is None else f'{d:.3f}'} |")
    size = (abs(big_low["barrier_eV"] - base["barrier_eV"]) if None not in (big_low["barrier_eV"], base["barrier_eV"])
            else None)
    if size is not None:
        diffs.append(size)
    spread = max(diffs) if diffs else None
    keep = spread is not None and spread <= config.MEMRISTOR_EA_SIGNIFICANT_EV
    new_tol = (config.MEMRISTOR_EA_SIGNIFICANT_EV if keep else
               None if spread is None else math.ceil(spread * 20 - 1e-9) / 20)
    lines += ["", f"Lowest hop: {base['barrier_eV']} eV in {len(sc)} atoms, {big_low['barrier_eV']} eV in {len(big)} atoms"
              f" (finite-size difference {'—' if size is None else f'{size:.3f}'} eV).", "",
              f"**Spread: {'—' if spread is None else f'{spread:.3f}'} eV → tolerance "
              f"{'kept at ' + str(config.MEMRISTOR_EA_SIGNIFICANT_EV) if keep else 'set to ' + str(new_tol)} eV.**", ""]
    out = {"material": formula, "hops": base, "equivalent_pairs": twin_rows, "larger_cell": big_low,
           "n_atoms": [len(sc), len(big)], "differences_eV": diffs, "spread_eV": spread, "tolerance_kept": keep,
           "tolerance_eV": new_tol, "estimated_usd": plan["usd"]}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "result.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    (args.out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
