"""Room-temperature ionic conductivity: extra MD temperatures, Arrhenius fits and the truth test (limit "D at 600 K").

    SIM_BACKEND=modal python scripts/conductivity.py --out results/<dir> [--result results/<run>/result.json
        --ids it1-c2 ...] [--dry-run]

Adds config.CONDUCTIVITY_EXTRA_RUNS (500 K and 700 K, 40 ps, one seed) on Modal (config.MODAL_MD_GPU) for the two
calibration parents and for the given candidates (missing runs only: everything cached is reused), then fits
ln D against 1/T over the cached runs up to config.CONDUCTIVITY_FIT_T_MAX_K, extrapolates to 300 K and applies
Nernst-Einstein (agent/conductivity.py). Truth test fixed before the runs (config.CONDUCTIVITY_REFERENCE_MS_CM):
Li7P3S11 above beta-Li3PS4 and each within CONDUCTIVITY_TRUTH_FACTOR of its experimental conductivity.
Writes conductivity.json and conductivity.md. --dry-run prints the runs to compute and their estimated cost.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.conductivity import structure_conductivity
from autolab.agent.dynamics import candidate_job, md_runs_to_compute, modal_md_plan, parent_job
from autolab.sim.backend import ModalBackend, run_md_runs


def extra_runs(jobs: list[dict]) -> list[dict]:
    """Missing runs of config.CONDUCTIVITY_EXTRA_RUNS for these jobs (a temperature already cached in any length or
    seed, e.g. the parents' 700 K calibration run, is not run again)."""
    from autolab.agent.conductivity import cached_points

    todo = []
    for job in jobs:
        have = {p["T"] for p in cached_points(job)}
        for t, ps, seed in config.CONDUCTIVITY_EXTRA_RUNS:
            if float(t) in have:
                continue
            for r in md_runs_to_compute([job], t, ps, seeds=seed + 1, gpu=config.MODAL_MD_GPU):
                if r["seed"] == seed:
                    todo.append({**r, "formula": job["formula"]})
    return todo


def truth_test(parents: dict) -> dict:
    """Li7P3S11 above beta-Li3PS4, each within the factor of its experimental range."""
    by_formula = {r["formula"]: r for r in parents.values()}
    rows, ok = {}, True
    f = config.CONDUCTIVITY_TRUTH_FACTOR
    for formula, (lo, hi) in config.CONDUCTIVITY_REFERENCE_MS_CM.items():
        r = by_formula.get(formula)
        within = r is not None and lo / f <= r["sigma_mS_cm"] <= hi * f
        ok &= within
        rows[formula] = {"sigma_mS_cm": r and r["sigma_mS_cm"], "experiment_mS_cm": [lo, hi], "within": within}
    order = (by_formula.get("Li7P3S11") or {}).get("sigma_mS_cm", 0) > (by_formula.get("Li3PS4") or {}).get("sigma_mS_cm", 1e9)
    return {"passed": bool(ok and order), "order_ok": order, "factor": f, "parents": rows}


def render(out: dict) -> str:
    t = out["truth_test"]
    lines = [f"# Ionic conductivity at {config.CONDUCTIVITY_T_K} K from UMA molecular dynamics", "",
             f"**Truth test: {'PASSED' if t['passed'] else 'FAILED'}** (fixed before the runs): Li7P3S11 above "
             f"beta-Li3PS4 ({'yes' if t['order_ok'] else 'no'}), each within a factor {t['factor']:g} of experiment.", "",
             "Method: blocks of the cached runs pooled per temperature (runs up to "
             f"{config.CONDUCTIVITY_FIT_T_MAX_K} K), weighted Arrhenius fit of ln D against 1/T, extrapolation to "
             f"{config.CONDUCTIVITY_T_K} K, Nernst-Einstein with the Li density of the relaxed cell (Haven ratio 1). "
             "Range: one standard error of the extrapolated ln D.", "",
             "| Structure | Temperatures (K) | Ea (eV) | σ 300 K (mS/cm) | Range (mS/cm) | Experiment (mS/cm) | Method |",
             "|---|---|---|---|---|---|---|"]
    for kind in ("parents", "candidates"):
        for key, r in out[kind].items():
            exp = (t["parents"].get(r["formula"]) or {}).get("experiment_mS_cm") if kind == "parents" else None
            lines.append(f"| {r['formula']} ({key}) | {', '.join(str(round(p['T'])) for p in r['points'])} | "
                         f"{r['Ea_eV']:.2f} ± {r['Ea_err_eV']:.2f} | {r['sigma_mS_cm']:.3g} | "
                         f"{r['sigma_low_mS_cm']:.2g}–{r['sigma_high_mS_cm']:.2g} | "
                         f"{'—' if not exp else (format(exp[0], 'g') if exp[0] == exp[1] else f'{exp[0]:g}–{exp[1]:g}')} | "
                         f"{r['method']} |")
    lines += ["", "D per temperature (cm²/s, blocks of all cached runs pooled):", ""]
    for kind in ("parents", "candidates"):
        for key, r in out[kind].items():
            lines.append(f"- {r['formula']} ({key}): " + "; ".join(
                f"{p['T']:.0f} K: {p['D_cm2_per_s']:.2e} ± {p['D_sem_cm2_per_s']:.1e} ({p['runs']} run(s))" for p in r["points"]))
    if out.get("plan"):
        p = out["plan"]
        lines += ["", f"New runs: {p['runs']} on Modal {p['gpu']}, estimate {p['usd']:.2f} $."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--result", type=Path, help="result.json holding the candidates of --ids")
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    parents = {mid: parent_job(mid) for mid in config.MD_CALIBRATION_PARENTS.values()}
    cands = {}
    if args.ids:
        res = json.loads(args.result.read_text(encoding="utf-8"))
        pool = {c["id"]: c for c in res.get("prior", []) + [c for r in res["iterations"] for c in r["candidates"]]}
        cands = {i: pool[i] for i in args.ids}
        for c in cands.values():
            parents.setdefault(c["parent"], parent_job(c["parent"]))
    jobs = list(parents.values()) + [candidate_job(c) for c in cands.values()]
    todo = extra_runs(jobs)
    plan = modal_md_plan(todo, config.MODAL_MD_GPU) if todo else None
    for r in todo:
        print(f"{r['formula']:14s} {r['temperature_K']} K {r['n_steps'] / 1000:g} ps seed {r['seed']}")
    if plan:
        print(f"{plan['runs']} runs on Modal {plan['gpu']}, in parallel: about {plan['wall_s'] / 60:.0f} min, about "
              f"{plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $ if every run hit its "
              f"{plan['timeout_s'] / 60:.0f} min limit)", flush=True)
    if args.dry_run:
        return
    if todo:
        backend = ModalBackend(gpu=config.MODAL_MD_GPU, md_timeout_s=plan["timeout_s"])
        run_md_runs(todo, backend=backend, gpu=config.MODAL_MD_GPU)
        if backend.errors:
            print(f"failed runs (not retried): {backend.errors}")

    out = {"parents": {}, "candidates": {}, "plan": plan}
    for pid, job in parents.items():
        r = structure_conductivity(job)
        if r:
            out["parents"][pid] = {**r, "formula": job["formula"]}
    for cid, c in cands.items():
        r = structure_conductivity(candidate_job(c), out["parents"].get(c["parent"]))
        if r:
            out["candidates"][cid] = {**r, "formula": c["formula"]}
    out["truth_test"] = truth_test({k: v for k, v in out["parents"].items()
                                    if k in config.MD_CALIBRATION_PARENTS.values()})
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "conductivity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    text = render(out)
    (args.out / "conductivity.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
