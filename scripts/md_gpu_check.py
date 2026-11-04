"""Same D on two GPUs? One run per calibration parent on a new GPU against the pooled legacy runs (2026-11-01).

    SIM_BACKEND=modal python scripts/md_gpu_check.py --out results/<dir> --gpu H100 [--dry-run]

Criterion, fixed before the runs (SPEC.md 5.10): for each parent (Li7P3S11, beta-Li3PS4), the D of one run on
the new GPU (seed 0, 4 blocks) and the pooled D of the calibration v2 on the legacy GPU (seeds 0-2, 12 blocks) differ
by at most 2 combined standard errors, and the framework stays intact. Both parents must pass. Writes
md_gpu_check.json and md_gpu_check.md. --dry-run prints the estimated cost only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from autolab import config
from autolab.agent.dynamics import md_cached_result, md_runs_to_compute, modal_md_plan, parent_job
from autolab.analysis.diffusion import diffusion_coefficient, framework_check, pool
from autolab.sim.backend import ModalBackend, gpu_type, run_md_runs

N_SIGMA = 2.0
SEED = 0  # reused by later screenings on the new GPU


def _row(job: dict, res: dict) -> dict:
    d = diffusion_coefficient(res["positions"], res["dt_record_fs"])
    fw = framework_check(res["framework_msd"], res["dt_record_fs"], d["D_A2_per_ps"]) if res.get("framework_msd") else None
    return {**d, "framework": fw, "ms_per_step": res["ms_per_step"], "gpu": res.get("gpu"), "n_atoms": res["n_atoms"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gpu", default=config.MODAL_MD_GPU)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t, ps = config.MD_CALIBRATION_V2_T, config.MD_CALIBRATION_V2_PS
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    jobs = {role: parent_job(mid) for role, mid in config.MD_CALIBRATION_PARENTS.items()}

    legacy = {}
    for role, job in jobs.items():
        runs = [md_cached_result(job, s, t, ps, gpu=config.MD_LEGACY_GPU) for s in config.MD_CALIBRATION_V2_SEEDS]
        if any(r is None for r in runs):
            raise SystemExit(f"legacy calibration runs of {job['formula']} missing from the cache: nothing to compare")
        legacy[role] = {"pooled": pool([diffusion_coefficient(r["positions"], r["dt_record_fs"]) for r in runs]),
                        "seed0": _row(job, runs[0])}

    todo = [r for job in jobs.values() for r in md_runs_to_compute([job], t, ps, seeds=1, gpu=args.gpu)]
    plan = modal_md_plan(todo, args.gpu) if todo else None
    if plan:
        print(f"{len(todo)} runs on Modal {args.gpu}, in parallel: about {plan['wall_s'] / 60:.0f} min, about "
              f"{plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $ if every run hit its "
              f"{plan['timeout_s'] / 60:.0f} min limit)", flush=True)
    if args.dry_run:
        return
    if todo:
        backend = ModalBackend(gpu=args.gpu, md_timeout_s=plan["timeout_s"])
        run_md_runs(todo, backend=backend, gpu=args.gpu)
        if backend.errors:
            print(f"failed runs (not retried): {backend.errors}")

    rows, ok = {}, True
    for role, job in jobs.items():
        res = md_cached_result(job, SEED, t, ps, gpu=args.gpu)
        if res is None:
            raise SystemExit(f"{job['formula']}: run on {args.gpu} missing after the session")
        new, old = _row(job, res), legacy[role]["pooled"]
        err = float(np.hypot(new["D_sem_cm2_per_s"], old["D_sem_cm2_per_s"]))
        diff = new["D_cm2_per_s"] - old["D_cm2_per_s"]
        intact = bool(new["framework"] and new["framework"]["intact"])
        same = abs(diff) <= N_SIGMA * err
        ok &= same and intact
        rows[role] = {"formula": job["formula"], "new": new, "legacy_pooled": old, "legacy_seed0": legacy[role]["seed0"],
                      "diff_in_sigma": diff / err, "same": same, "framework_intact": intact,
                      "speedup": legacy[role]["seed0"]["ms_per_step"] / new["ms_per_step"]}
    out = {"gpu": args.gpu, "legacy_gpu": config.MD_LEGACY_GPU, "temperature_K": t, "ps": ps, "seed": SEED,
           "n_sigma": N_SIGMA, "passed": ok, "parents": rows, "plan": plan}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "md_gpu_check.json").write_text(json.dumps(out, indent=1, default=lambda o: None), encoding="utf-8")
    text = render(out)
    (args.out / "md_gpu_check.md").write_text(text, encoding="utf-8")
    print(text)


def render(out: dict) -> str:
    e = lambda x: f"{x:.2e}"
    lines = [f"# Same D on {out['gpu']} and {out['legacy_gpu']}? ({out['temperature_K']} K, {out['ps']:g} ps)", "",
             f"**Result: {'SAME' if out['passed'] else 'DIFFERENT'}** — criterion fixed before the runs: |D({out['gpu']}, "
             f"seed {out['seed']}) - D({out['legacy_gpu']}, calibration v2 pooled)| <= {out['n_sigma']:g} combined "
             f"standard errors, framework intact, for both parents.", "",
             f"| Parent | D {out['gpu']} (cm²/s) | D {out['legacy_gpu']} pooled (cm²/s) | D {out['legacy_gpu']} seed 0 | "
             f"Difference (σ) | Framework | ms/step {out['gpu']} / {out['legacy_gpu']} |", "|---|---|---|---|---|---|---|"]
    for r in out["parents"].values():
        n, o, s0 = r["new"], r["legacy_pooled"], r["legacy_seed0"]
        lines.append(f"| {r['formula']} | {e(n['D_cm2_per_s'])} ± {e(n['D_sem_cm2_per_s'])} | {e(o['D_cm2_per_s'])} ± "
                     f"{e(o['D_sem_cm2_per_s'])} | {e(s0['D_cm2_per_s'])} ± {e(s0['D_sem_cm2_per_s'])} | "
                     f"{r['diff_in_sigma']:+.1f} | {'intact' if r['framework_intact'] else 'MOVED'} | "
                     f"{n['ms_per_step']} / {s0['ms_per_step']} ({r['speedup']:.1f}x) |")
    gpus = {gpu_type(r["new"]["gpu"]) for r in out["parents"].values()}
    lines += ["", f"Device reported by the runs: {', '.join(sorted(g or '?' for g in gpus))}."]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
