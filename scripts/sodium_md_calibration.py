"""Calibration of the sodium molecular dynamics (third domain), criterion fixed before the runs.

    SIM_BACKEND=modal python scripts/sodium_md_calibration.py --out results/<dir> [--dry-run]

At config.MD_SCREEN_TEMPERATURE_K, config.SODIUM_MD_CALIBRATION_SEEDS seeds of config.MD_SCREEN_PS ps each: Na3SbS4
(about 1-3 mS/cm at room temperature) must diffuse faster than tetragonal Na3PS4 (0.01-0.2 mS/cm) by more than
config.MD_TIE_SIGMA combined errors, both frameworks intact. If it fails, config.SODIUM_MD_CAN_EXCLUDE is set to False:
the sodium MD then informs and never excludes a candidate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import md_runs_to_compute, md_screen, modal_md_plan, parent_job, with_md_gpu
from autolab.analysis.diffusion import compare


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    seeds = config.SODIUM_MD_CALIBRATION_SEEDS
    jobs = with_md_gpu([parent_job(m) for m in (config.SODIUM_MD_CALIBRATION["fast"], config.SODIUM_MD_CALIBRATION["slow"])],
                       seeds=seeds)
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
              "rows": [{k: r.get(k) for k in keep} for r in rows], "comparison": cmp, "sigma": sigma,
              "frameworks_intact": intact, "passed": passed, "estimated_usd": plan["usd"]}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "result.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    lines = ["# Calibration of the sodium molecular dynamics", "", f"Criterion, fixed before the runs: {result['criterion']}.", "",
             "| Structure | Na in the supercell | D (cm²/s) | ± s.e. | Framework |", "|---|---|---|---|---|"]
    for r in rows:
        fw = (r.get("framework") or {}).get("intact")
        lines.append(f"| {r['formula']} ({r['id']}) | {r.get('n_li')} | {r['D_cm2_per_s']:.2e} | {r['D_sem_cm2_per_s']:.1e} | "
                     f"{'intact' if fw else 'moved' if fw is False else 'not checked'} |")
    lines += ["", f"D({fast['formula']}) / D({slow['formula']}) = {cmp['ratio']:.2f} ± {cmp['ratio_err']:.2f}"
                  f"; difference D - D(ref) = {sigma:+.1f} combined standard errors: {cmp['verdict']}." if sigma is not None else "",
              f"**Verdict: {'passed' if passed else 'FAILED: the sodium MD informs and never excludes'}.**", ""]
    (args.out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
