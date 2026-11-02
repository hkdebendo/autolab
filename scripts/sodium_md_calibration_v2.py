"""Calibration v2 of the sodium molecular dynamics: Na vacancies must speed up Na in Na3SbS4 (criterion fixed before
the runs, config.SODIUM_MD_CALIBRATION_V2).

    SIM_BACKEND=modal python scripts/sodium_md_calibration_v2.py --out results/<dir> [--dry-run]

The domain compares a candidate with its own parent: this test asks whether the MD sees the effect the agent plays
with. W6+ on one Sb5+ site with one Na vacancy in the 2x2x2 supercell of the relaxed Na3SbS4 cell (Na23Sb7WS32, the
composition of the fast Na2.88Sb0.88W0.12S4, about 32 mS/cm in experiment, against 1-3 mS/cm for Na3SbS4); the lowest
of a few relaxed arrangements against the cached Na3SbS4 runs, same cell, same seeds, at config.MD_SCREEN_TEMPERATURE_K.
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import md_runs_to_compute, md_screen, modal_md_plan, parent_job, with_md_gpu
from autolab.analysis.diffusion import compare


def doped_job(parent: dict, cal: dict) -> tuple[dict, dict]:
    """The vacancy compound built from the relaxed parent cell, relaxed with UMA (lowest arrangement kept)."""
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.chem.generator import generate_candidates
    from autolab.chem.oxidation import check_charge
    from autolab.sim.backend import relax_structures
    from autolab.sim.serialize import atoms_from_dict

    cell = AseAtomsAdaptor.get_structure(atoms_from_dict(parent["atoms"]))
    cell.make_supercell(list(cal["supercell"]))
    gen = generate_candidates(cell, cal["substitution"], cal["parent"], n_arrangements=cal["n_arrangements"],
                              charge_check=partial(check_charge, table=config.SODIUM_OXIDATION_STATES))
    if not gen["accepted"]:
        raise SystemExit(f"substitution refused: {gen['reason']}")
    from pymatgen.core import Structure

    structures = [Structure.from_dict(c["structure"]) for c in gen["candidates"]]
    relaxed = relax_structures(structures, max_new=cal["n_arrangements"])
    ok = [r for r in relaxed if r["converged"]]
    if not ok:
        raise SystemExit("no arrangement converged")
    best = min(ok, key=lambda r: r["energy_per_atom"])
    spread = (max(r["energy_per_atom"] for r in ok) - best["energy_per_atom"]) * 1000
    info = {"formula": gen["formula"], "arrangements": len(relaxed), "converged": len(ok),
            "energy_spread_meV_per_atom": round(spread, 2)}
    return {"id": "cal-v2-" + gen["formula"], "formula": gen["formula"], "kind": "candidate", "parent": cal["parent"],
            "atoms": best["atoms"]}, info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true", help="estimate the MD cost (the arrangements are relaxed)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cal, seeds = config.SODIUM_MD_CALIBRATION_V2, config.SODIUM_MD_CALIBRATION_SEEDS
    parent = parent_job(cal["parent"])
    doped, info = doped_job(parent, cal)
    print(f"{info['formula']}: {info['converged']}/{info['arrangements']} arrangements converged, spread "
          f"{info['energy_spread_meV_per_atom']} meV/atom")
    jobs = with_md_gpu([doped, parent], seeds=seeds)
    todo = md_runs_to_compute(jobs, seeds=seeds)
    plan = modal_md_plan(todo) if todo else {"runs": 0, "usd": 0.0, "wall_s": 0, "timeout_s": 0, "usd_max": 0.0}
    print(f"{len(todo)} MD runs to compute ({', '.join(j['formula'] for j in jobs)}, {seeds} seeds of "
          f"{config.MD_SCREEN_PS} ps at {config.MD_SCREEN_TEMPERATURE_K} K): about {plan['wall_s'] / 60:.0f} min, "
          f"about {plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $)")
    if args.dry_run:
        return
    backend = None
    if config.SIM_BACKEND == "modal" and todo:
        from autolab.sim.backend import ModalBackend

        backend = ModalBackend(md_timeout_s=plan["timeout_s"])
    rows = md_screen(jobs, seeds=seeds, backend=backend)
    fast, slow = rows
    cmp = compare(fast["D_cm2_per_s"], fast["D_sem_cm2_per_s"], slow["D_cm2_per_s"], slow["D_sem_cm2_per_s"])
    intact = all((r.get("framework") or {}).get("intact", False) for r in rows)
    passed = cmp["verdict"] == "higher" and intact
    sigma = cmp["diff_sigma"]
    keep = ("id", "formula", "species", "n_li", "n_atoms", "D_cm2_per_s", "D_sem_cm2_per_s", "framework", "md_gpu")
    result = {"criterion": f"D({fast['formula']}) > D({slow['formula']}) by more than {config.MD_TIE_SIGMA:g} combined "
                           f"errors at {config.MD_SCREEN_TEMPERATURE_K} K, both frameworks intact (fixed before the runs)",
              "doped": info, "rows": [{k: r.get(k) for k in keep} for r in rows], "comparison": cmp, "sigma": sigma,
              "frameworks_intact": intact, "passed": passed, "estimated_usd": plan["usd"]}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "result.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    lines = ["# Calibration v2 of the sodium molecular dynamics: Na vacancies in Na3SbS4", "",
             f"Criterion, fixed before the runs: {result['criterion']}.", "",
             f"{info['formula']} = one W6+ for one Sb5+ and one Na vacancy in the 2x2x2 Na3SbS4 cell (the composition of "
             f"Na2.88Sb0.88W0.12S4, about 32 mS/cm in experiment); lowest of {info['converged']} relaxed arrangements.", "",
             "| Structure | Na in the supercell | D (cm²/s) | ± s.e. | Framework |", "|---|---|---|---|---|"]
    for r in rows:
        fw = (r.get("framework") or {}).get("intact")
        lines.append(f"| {r['formula']} ({r['id']}) | {r.get('n_li')} | {r['D_cm2_per_s']:.2e} | {r['D_sem_cm2_per_s']:.1e} | "
                     f"{'intact' if fw else 'moved' if fw is False else 'not checked'} |")
    lines += ["", f"D({fast['formula']}) / D({slow['formula']}) = {cmp['ratio']:.2f} ± {cmp['ratio_err']:.2f}"
                  f"; difference D - D(ref) = {sigma:+.1f} combined standard errors: {cmp['verdict']}." if sigma is not None else "",
              f"**Verdict: {'passed: the sodium MD verdict against the parent may exclude and rank' if passed else 'FAILED: the sodium MD stays information only'}.**", ""]
    (args.out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
