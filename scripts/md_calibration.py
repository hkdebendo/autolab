"""MD calibration (truth test of the block D, SPEC 5.10): the two parents at several temperatures, one Kaggle session.

    SIM_BACKEND=modal python scripts/md_calibration.py --out results/<dir> --gpu A10G [--dry-run]
    SIM_BACKEND=kaggle python scripts/md_calibration.py --out results/<dir> [--dry-run]     # fallback

On Modal every run gets its own container (all in parallel) and is cached as soon as it ends; on Kaggle the six
runs share one session.

Runs config.MD_CALIBRATION_RUNS on Li7P3S11 and beta-Li3PS4 (no candidate), then checks that the P/S framework
stayed in place and that Li7P3S11 diffuses faster than Li3PS4 at the test temperatures, and estimates the
activation energies. Writes md_calibration.json and md_calibration.md. --dry-run prints the estimated duration only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import calibration_runs, md_calibration, parent_job
from autolab.analysis.diffusion import diffusion_coefficient, framework_check
from autolab.sim.backend import ModalBackend, _as_atoms_dict, get_backend, run_md_runs
from autolab.sim.serialize import atoms_key
from autolab.store.cache import JsonCache


def _cached(run: dict, cache: JsonCache) -> dict | None:
    settings = {"model": config.UMA_MODEL, "precision": config.UMA_PRECISION_MD, "T": run["temperature_K"],
                "n_steps": run["n_steps"], "seed": run["seed"]}
    return cache.get(atoms_key(_as_atoms_dict(run["atoms"]), **settings))


def analyse(run: dict, res: dict) -> dict:
    d = diffusion_coefficient(res["positions"], res["dt_record_fs"])
    row = {k: v for k, v in run.items() if k != "atoms"}
    row.update(n_atoms=res["n_atoms"], n_li=len(res["positions"][0]), ms_per_step=res["ms_per_step"], **d)
    if res.get("framework_msd"):
        row["framework"] = framework_check(res["framework_msd"], res["dt_record_fs"], d["D_A2_per_ps"])
    return row


def modal_plan(runs: list[dict], gpu: str) -> dict:
    """Per-run seconds on a Modal GPU (measured speed), the Modal time limit of each run, the wall time with
    every run in parallel and the cost (GPU price; container start and model compilation included)."""
    import math

    from autolab.sim.md import supercell_reps
    from autolab.sim.serialize import atoms_from_dict

    ms = config.MODAL_MD_MS_PER_ATOM_STEP[gpu]
    secs = []
    for r in runs:
        atoms = atoms_from_dict(r["atoms"])
        n = len(atoms) * math.prod(supercell_reps(atoms))
        secs.append(n * r["n_steps"] * ms / 1000 + config.MODAL_STARTUP_S)
    limit = int(min(config.MODAL_TIMEOUT_FACTOR * max(secs), config.MODAL_MAX_TIMEOUT_S))
    return {"gpu": gpu, "seconds": secs, "timeout_s": limit, "wall_s": max(secs),
            "usd": sum(secs) * config.MODAL_GPU_USD_PER_H[gpu] / 3600,
            "usd_max": len(secs) * limit * config.MODAL_GPU_USD_PER_H[gpu] / 3600}


def _e(x, digits=2):
    return "—" if x is None else f"{x:.{digits}e}"


def render(rows: list[dict], cal: dict) -> str:
    lines = ["# MD calibration: Li7P3S11 vs beta-Li3PS4 (UMA, block D)", "",
             f"**Truth test: {'PASSED' if cal['passed'] else 'FAILED'}** — framework intact at "
             f"{', '.join(str(t) for t in config.MD_CALIBRATION_TEST_T)} K: {cal['tests']['framework_intact']}; "
             f"Li7P3S11 faster than Li3PS4 by more than {cal['n_sigma']:g} combined standard errors: "
             f"{cal['tests']['fast_faster_than_slow']}.", "",
             "## Diffusion coefficients", "",
             "| Parent | T (K) | ps | seed | Atoms / Li | D, blocks ± s.e. (cm²/s) | D, one origin (cm²/s) | "
             "P MSD final (Å²) | S MSD final (Å²) | Framework | ms/step |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["role"], r["temperature_K"])):
        fw = r.get("framework") or {}
        el = fw.get("elements", {})
        msd = lambda e: f"{el[e]['msd_final_A2']:.2f}" if e in el else "—"
        lines.append(f"| {r['formula']} | {r['temperature_K']:.0f} | {r['ps']:g} | {r['seed']} | {r['n_atoms']} / "
                     f"{r['n_li']} | {_e(r['D_cm2_per_s'])} ± {_e(r['D_sem_cm2_per_s'], 1)} | "
                     f"{_e(r['D_one_origin_cm2_per_s'])} | {msd('P')} | {msd('S')} | "
                     f"{'—' if not fw else ('intact' if fw['intact'] else 'MOVED')} | {r['ms_per_step']} |")
    lines += ["", "## Order of the parents (expected: Li7P3S11 faster)", "",
              "| T (K) | D(Li7P3S11) / D(Li3PS4) | Difference in standard errors | Test |", "|---|---|---|---|"]
    for o in cal["order"]:
        lines.append(f"| {o['temperature_K']:.0f} | {o['ratio']:.2f} | "
                     f"{'—' if o['diff_in_sigma'] is None else format(o['diff_in_sigma'], '.1f')} | "
                     f"{'ok' if o['ok'] else 'FAILED'} |")
    lines += ["", "## Activation energies (Arrhenius fit of the block D)", "",
              "| Parent | Ea, test temperatures (eV) | Ea, all temperatures (eV) | Literature MD (eV) |",
              "|---|---|---|---|"]
    for formula, b in cal["barriers"].items():
        ea = lambda f: "—" if f is None else f"{f['Ea_eV']:.2f} ± {f['Ea_err_eV']:.2f}"
        lit = b["literature_eV"]
        lit = "—" if not lit else (f"{lit[0]:.2f}" if lit[0] == lit[1] else f"{lit[0]:.2f}–{lit[1]:.2f}")
        lines.append(f"| {formula} | {ea(b['low_T'])} | {ea(b['all_T'])} | {lit} |")
    lines += ["", "Framework: every element other than Li must diffuse at less than "
                  f"{config.MD_FRAMEWORK_D_RATIO_MAX:.0%} of Li (a bounded MSD of P and S is vibration or PS4 "
                  "rotation; a growing one means the structure melted or disordered). beta-Li3PS4 turns into its "
                  "alpha phase near 746 K, so the order is tested below it and 1000 K is shown for information."]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gpu", default=config.MODAL_GPU, help="Modal GPU type (SIM_BACKEND=modal)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    on_modal = config.SIM_BACKEND == "modal"

    parents = {role: parent_job(mid) for role, mid in config.MD_CALIBRATION_PARENTS.items()}
    runs = calibration_runs(parents)
    cache = JsonCache(config.CACHE_DIR / "md")
    todo = [r for r in runs if _cached(r, cache) is None]
    if on_modal:
        plan = modal_plan(todo, args.gpu)
        for r, s in zip(todo, plan["seconds"]):
            print(f"{r['formula']:9s} {r['temperature_K']:5.0f} K {r['ps']:3g} ps seed {r['seed']}: about {s / 60:.0f} min")
        print(f"{len(todo)} of {len(runs)} runs on Modal {args.gpu}, all in parallel: about {plan['wall_s'] / 60:.0f} min, "
              f"about {plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $ if every run hit its "
              f"{plan['timeout_s'] / 60:.0f} min limit)")
        if args.dry_run:
            return
    elif args.dry_run:
        from autolab.sim import kaggle_gpu

        job = kaggle_gpu.md_job([{k: r[k] for k in ("atoms", "seed", "temperature_K", "n_steps")} for r in todo],
                                config.UMA_PRECISION_MD)
        for r, t in zip(todo, job["tasks"]):
            print(f"{r['formula']:9s} {r['temperature_K']:5.0f} K {r['ps']:3g} ps seed {r['seed']}: "
                  f"about {t['cost'] / 60:.0f} min")
        print(f"{len(todo)} of {len(runs)} runs to compute: about {kaggle_gpu.estimate_seconds(job) / 60:.0f} min on "
              f"{config.KAGGLE_N_GPUS} GPUs + setup, session limit {kaggle_gpu.session_limit(job) / 60:.0f} min")
        return

    backend = ModalBackend(gpu=args.gpu, md_timeout_s=plan["timeout_s"]) if on_modal else get_backend()
    sent = run_md_runs(runs, backend=backend)
    print(f"sent: {sent} MD runs" + (f", failed: {backend.errors}" if getattr(backend, "errors", None) else ""))
    missing = [f"{r['formula']} {r['temperature_K']} K" for r in runs if _cached(r, cache) is None]
    if missing:  # never start a second session on its own
        raise SystemExit(f"runs missing after the session: {', '.join(missing)}")
    rows = [analyse(r, _cached(r, cache)) for r in runs]
    cal = md_calibration(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "md_calibration.json").write_text(json.dumps({"runs": rows, "calibration": cal}, indent=1),
                                                  encoding="utf-8")
    text = render(rows, cal)
    (args.out / "md_calibration.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
