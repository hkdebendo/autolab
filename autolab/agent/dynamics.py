"""Li diffusion screening by molecular dynamics (step 9C, SPEC 5.10).

Each job is one structure at one temperature; results are cached by sim.backend.run_md,
so an interrupted screening resumes where it stopped. Parents are run too: a
diffusion coefficient only means something next to the parent's.
"""

from __future__ import annotations

import time
from typing import Callable

from autolab import config


def parent_job(material_id: str, relax: Callable | None = None) -> dict:
    """MD job for an MP parent, started from its UMA-relaxed structure (from the relaxation cache)."""
    from autolab.data.mp import get_structure
    from autolab.sim.backend import relax_structures

    relax = relax or (lambda s: relax_structures([s], max_new=1)[0])  # a parent not relaxed yet (new domain): one relaxation
    s = get_structure(material_id)
    return {"id": material_id, "formula": s.composition.reduced_formula, "kind": "parent", "atoms": relax(s)["atoms"]}


def candidate_job(c: dict) -> dict:
    """MD job for a candidate, started from its best relaxed arrangement."""
    return {"id": c["id"], "formula": c["formula"], "kind": "candidate", "parent": c["parent"],
            "atoms": c["relaxed_atoms"]}


def md_runs_to_compute(jobs: list[dict], temperature_K: float = config.MD_SCREEN_TEMPERATURE_K,
                       ps: float = config.MD_SCREEN_PS, seeds: int = config.MD_SCREEN_SEEDS,
                       all_runs: bool = False, gpu: str | None = None) -> list[dict]:
    """The runs (job x seed) of a screening missing from the MD cache ({"id", "atoms", "temperature_K", "n_steps",
    "seed", "gpu", "cached"}), each on the GPU type of its job ("md_gpu", see with_md_gpu), else `gpu` (default:
    sim.backend.md_gpu()); with all_runs, cached ones too. Same keys as sim.backend.run_md."""
    from autolab.sim.backend import _as_atoms_dict, md_gpu, md_settings
    from autolab.sim.serialize import atoms_key
    from autolab.store.cache import JsonCache

    cache = JsonCache(config.CACHE_DIR / "md")
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    gpu = gpu or md_gpu()
    out = []
    for job in jobs:
        d = _as_atoms_dict(job["atoms"])
        g = job.get("md_gpu") or gpu
        for s in range(seeds):
            cached = cache.get(atoms_key(d, **md_settings(temperature_K, n_steps, s, gpu=g))) is not None
            if all_runs or not cached:
                out.append({"id": job["id"], "atoms": job["atoms"], "temperature_K": temperature_K,
                            "n_steps": n_steps, "seed": s, "gpu": g, "cached": cached})
    return out


def md_cached_result(job: dict, seed: int, temperature_K: float = config.MD_SCREEN_TEMPERATURE_K,
                     ps: float = config.MD_SCREEN_PS, gpu: str | None = None) -> dict | None:
    """The cached MD run of a job on the GPU type `gpu` (default: sim.backend.md_gpu(); same key as
    sim.backend.run_md), or None; never computes."""
    from autolab.sim.backend import _as_atoms_dict, md_gpu, md_settings
    from autolab.sim.serialize import atoms_key
    from autolab.store.cache import JsonCache

    settings = md_settings(temperature_K, round(ps * 1000 / config.MD_TIMESTEP_FS), seed, gpu=gpu or md_gpu())
    return JsonCache(config.CACHE_DIR / "md").get(atoms_key(_as_atoms_dict(job["atoms"]), **settings))


def with_md_gpu(jobs: list[dict], gpu: str | None = None, legacy: str = config.MD_LEGACY_GPU,
                temperature_K: float = config.MD_SCREEN_TEMPERATURE_K, ps: float = config.MD_SCREEN_PS,
                seeds: int = config.MD_SCREEN_SEEDS) -> list[dict]:
    """The jobs with the GPU type of their runs ("md_gpu"): a job whose runs are all cached on the legacy GPU reads
    them (never recomputed), the others run on `gpu` (default: sim.backend.md_gpu()). A10G and H100 give the same D
    (results/2026-11-01_md_gpu_check), so a candidate may be compared with a parent simulated on the other GPU."""
    from autolab.sim.backend import md_gpu

    gpu = gpu or md_gpu()
    if gpu in (None, legacy):
        return [{**j, "md_gpu": gpu} for j in jobs]
    return [{**j, "md_gpu": legacy if not md_runs_to_compute([j], temperature_K, ps, seeds, gpu=legacy) else gpu}
            for j in jobs]


def modal_md_plan(runs: list[dict], gpu: str = config.MODAL_MD_GPU) -> dict:
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
    limit = int(min(config.MODAL_TIMEOUT_FACTOR * max(secs, default=0), config.MODAL_MAX_TIMEOUT_S))
    return {"gpu": gpu, "runs": len(runs), "seconds": secs, "timeout_s": limit, "wall_s": max(secs, default=0),
            "usd": sum(secs) * config.MODAL_GPU_USD_PER_H[gpu] / 3600,
            "usd_max": len(secs) * limit * config.MODAL_GPU_USD_PER_H[gpu] / 3600}


def md_screen(jobs: list[dict], temperature_K: float = config.MD_SCREEN_TEMPERATURE_K,
              ps: float = config.MD_SCREEN_PS, run: Callable | None = None,
              on_done: Callable[[dict], None] | None = None, seeds: int = config.MD_SCREEN_SEEDS,
              max_runs: int = config.MD_SCREEN_MAX_RUNS, backend=None, gpu: str | None = None) -> list[dict]:
    """Run each job with `seeds` seeds (cached), pool the blocks of its seeds into one D with its error
    (calibration v2, SPEC 5.10), check the framework of every run, call on_done after each job. Runs are read on the
    GPU type of their job ("md_gpu", see with_md_gpu); missing ones run on `gpu`, else that of the backend."""
    from autolab.analysis.diffusion import diffusion_coefficient, framework_check, pool

    if len(jobs) * seeds > max_runs:
        raise ValueError(f"{len(jobs)} MD jobs x {seeds} seeds requested, limit is {max_runs} (MD_SCREEN_MAX_RUNS)")
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    if run is None:
        from functools import partial

        from autolab.sim.backend import md_gpu, run_md, run_md_runs

        # one Kaggle session, or all runs in parallel on Modal
        from autolab.agent import cancel

        gpu = gpu or md_gpu(backend)
        run_md_runs([{"atoms": job["atoms"], "temperature_K": temperature_K, "n_steps": n_steps, "seed": s,
                      "gpu": job.get("md_gpu") or gpu} for job in jobs for s in range(seeds)], backend=backend, gpu=gpu)
        cancel.check()  # stopped: the missing runs must not be computed one by one below
        on_modal = hasattr(backend, "md_batch_iter") or (backend is None and config.SIM_BACKEND == "modal")
        run = partial(_cached_only if on_modal else run_md, backend=backend)
    out = []
    for job in jobs:
        t0 = time.perf_counter()
        g = job.get("md_gpu") or gpu
        kw = {"gpu": g} if g else {}
        results = [run(job["atoms"], temperature_K=temperature_K, n_steps=n_steps, seed=s, **kw) for s in range(seeds)]
        ds = [diffusion_coefficient(r["positions"], r["dt_record_fs"]) for r in results]
        d = pool(ds)
        row = {k: v for k, v in job.items() if k != "atoms"}
        res = results[0]
        row.update(temperature_K=temperature_K, ps=ps, seeds=seeds, n_atoms=res["n_atoms"],
                   n_li=len(res["positions"][0]), species=res.get("species", "Li"), ms_per_step=res["ms_per_step"],
                   cached=all(r.get("cached", False) for r in results), wall_s=round(time.perf_counter() - t0, 1),
                   gpu=res.get("gpu"), md_gpu=g, **d)
        checks = [framework_check(r["framework_msd"], r["dt_record_fs"], di["D_A2_per_ps"])
                  for r, di in zip(results, ds) if r.get("framework_msd")]
        if checks:  # runs recorded before this check have Li positions only
            row["framework"] = {"intact": all(c["intact"] for c in checks), "per_seed": checks}
        out.append(row)
        if on_done:
            on_done(row)
    return out


def _cached_only(atoms, temperature_K, n_steps, seed=0, backend=None, gpu=None) -> dict:
    """After a Modal batch, a run still missing has failed (error or time limit): it is never recomputed here
    (no hidden retry, budget rules); the MD step stops with the reason."""
    from autolab.sim.backend import _as_atoms_dict, md_gpu, md_settings, run_md
    from autolab.sim.serialize import atoms_key
    from autolab.store.cache import JsonCache

    key = atoms_key(_as_atoms_dict(atoms), **md_settings(temperature_K, n_steps, seed, gpu=gpu or md_gpu(backend)))
    if JsonCache(config.CACHE_DIR / "md").get(key) is None:
        errors = getattr(backend, "errors", None) or {}
        raise RuntimeError(f"MD run failed on Modal and was not retried (seed {seed}, {temperature_K} K)"
                           + (f": {next(iter(errors.values()))}" if errors else ""))
    return run_md(atoms, temperature_K, n_steps, seed=seed, backend=backend, gpu=gpu)


def _moved_reason(framework: dict, ion: str = "Li") -> str:
    """The element that moved most, as in the calibration criterion (a framework element's D > MD_FRAMEWORK_D_RATIO_MAX
    of the mobile ion's)."""
    worst = None
    for k, check in enumerate(framework.get("per_seed") or [framework]):
        for el, v in check.get("elements", {}).items():
            if v.get("D_ratio_to_Li") is not None and (worst is None or v["D_ratio_to_Li"] > worst[1]):
                worst = (el, v["D_ratio_to_Li"], k, v["msd_final_A2"])
    if worst is None:
        return "framework moved"
    return (f"framework moved: {worst[0]} diffuses at {worst[1]:.1%} of {ion} (limit {config.MD_FRAMEWORK_D_RATIO_MAX:.0%}), "
            f"seed {worst[2]}, final MSD {worst[3]:.1f} A2")


def md_verdicts(rows: list[dict], n_sigma: float = config.MD_TIE_SIGMA,
                excluded=config.MD_EXCLUDED_VERDICTS,
                exclude_moved: bool = config.MD_EXCLUDE_IF_FRAMEWORK_MOVED) -> list[dict]:
    """Each candidate row against its parent's row (same screening): D / D(parent) with its error, verdict
    ("tied", "higher", "lower"), and conduction "passes" or "excluded" (config.MD_EXCLUDED_VERDICTS). A candidate
    whose framework moved is excluded too (config.MD_EXCLUDE_IF_FRAMEWORK_MOVED). Rows are returned with these
    fields added (nothing is removed)."""
    from autolab.analysis.diffusion import compare

    parents = {r["id"]: r for r in rows if r.get("kind") == "parent"}
    out = []
    for r in rows:
        r = dict(r)
        p = parents.get(r.get("parent"))
        if r.get("kind") == "candidate" and p is not None:
            if r.get("D_sem_cm2_per_s") and p.get("D_sem_cm2_per_s") and r["D_cm2_per_s"] > 0 and p["D_cm2_per_s"] > 0:
                r["vs_parent"] = compare(r["D_cm2_per_s"], r["D_sem_cm2_per_s"], p["D_cm2_per_s"],
                                         p["D_sem_cm2_per_s"], n_sigma)
                verdict = r["vs_parent"]["verdict"]
            else:  # no uncertainty (or no Li hop): cannot be told apart from its parent
                r["vs_parent"], verdict = None, "undetermined"
            moved = exclude_moved and r.get("framework") is not None and not r["framework"]["intact"]
            no_hop = r["D_cm2_per_s"] <= 0
            r["conduction"] = "excluded" if verdict in excluded or moved or no_hop else "passes"
            ion = r.get("species") or "Li"
            r["conduction_reason"] = (_moved_reason(r["framework"], ion) if moved else f"no {ion} diffusion seen" if no_hop else
                                      f"slower than its parent by more than {n_sigma:g} combined errors"
                                      if verdict in excluded else verdict)
        out.append(r)
    return out


def calibration_runs(parents: dict[str, dict], runs=config.MD_CALIBRATION_RUNS) -> list[dict]:
    """The MD runs of the calibration: every (temperature, ps, seed) of `runs` for each parent job
    (`parents`: role -> parent_job, roles "fast" and "slow")."""
    return [{"role": role, "id": job["id"], "formula": job["formula"], "atoms": job["atoms"], "temperature_K": t,
             "ps": ps, "n_steps": round(ps * 1000 / config.MD_TIMESTEP_FS), "seed": seed}
            for role, job in parents.items() for t, ps, seed in runs]


def md_calibration(rows: list[dict], test_t=config.MD_CALIBRATION_TEST_T,
                   n_sigma: float = config.MD_CALIBRATION_SIGMA) -> dict:
    """Truth test of the MD (SPEC 5.10) from analysed runs (role, formula, temperature_K, D_cm2_per_s,
    D_sem_cm2_per_s, framework): framework intact everywhere, D(fast) > D(slow) by more than n_sigma combined
    standard errors at each test temperature (framework reported at every T, tested at the test temperatures);
    activation energies below the Li3PS4 transition and over all temperatures."""
    import numpy as np

    from autolab.analysis.diffusion import arrhenius

    by = {(r["role"], r["temperature_K"]): r for r in rows}
    order = []
    for t in test_t:
        f, s = by[("fast", t)], by[("slow", t)]
        diff = f["D_cm2_per_s"] - s["D_cm2_per_s"]
        err = float(np.hypot(f["D_sem_cm2_per_s"], s["D_sem_cm2_per_s"]))
        order.append({"temperature_K": t, "D_fast": f["D_cm2_per_s"], "D_slow": s["D_cm2_per_s"],
                      "ratio": f["D_cm2_per_s"] / s["D_cm2_per_s"], "diff_in_sigma": diff / err if err else None,
                      "ok": diff > n_sigma * err})
    framework = [{"formula": r["formula"], "temperature_K": r["temperature_K"],
                  "intact": r["framework"]["intact"] if r.get("framework") else None} for r in rows]
    barriers = {}
    for role in ("fast", "slow"):
        mine = sorted((r for r in rows if r["role"] == role), key=lambda r: r["temperature_K"])
        low = [r for r in mine if r["temperature_K"] in test_t]
        def fit(rs):  # no barrier from a D at or below zero (no Li hop seen at that temperature)
            if len(rs) < 2 or any(r["D_cm2_per_s"] <= 0 or not r["D_sem_cm2_per_s"] for r in rs):
                return None
            return arrhenius([r["temperature_K"] for r in rs], [r["D_cm2_per_s"] for r in rs],
                             [r["D_sem_cm2_per_s"] for r in rs])

        formula = mine[0]["formula"]
        barriers[formula] = {"role": role, "low_T": fit(low), "all_T": fit(mine),
                             "literature_eV": config.MD_EA_LITERATURE_EV.get(formula)}
    tests = {"framework_intact": all(f["intact"] for f in framework if f["temperature_K"] in test_t),
             "fast_faster_than_slow": all(o["ok"] for o in order)}
    return {"passed": all(tests.values()), "tests": tests, "order": order, "framework": framework,
            "barriers": barriers, "n_sigma": n_sigma}


def md_calibration_v2(rows: list[dict], n_sigma: float = config.MD_CALIBRATION_SIGMA) -> dict:
    """Calibration v2 (SPEC 7): seeds pooled per parent (all blocks together: D = mean, error = std / sqrt(n));
    passes if every framework stayed intact and D(fast) - D(slow) > n_sigma combined errors."""
    import numpy as np

    pooled = {}
    for role in ("fast", "slow"):
        mine = sorted((r for r in rows if r["role"] == role), key=lambda r: r["seed"])
        blocks = np.array([b for r in mine for b in r["D_blocks_cm2_per_s"]])
        pooled[role] = {"formula": mine[0]["formula"], "seeds": [r["seed"] for r in mine],
                        "D_per_seed": [r["D_cm2_per_s"] for r in mine], "n_blocks": len(blocks),
                        "D_cm2_per_s": float(blocks.mean()),
                        "D_sem_cm2_per_s": float(blocks.std(ddof=1) / np.sqrt(len(blocks)))}
    f, s = pooled["fast"], pooled["slow"]
    err = float(np.hypot(f["D_sem_cm2_per_s"], s["D_sem_cm2_per_s"]))
    diff = f["D_cm2_per_s"] - s["D_cm2_per_s"]
    framework = all(r.get("framework") and r["framework"]["intact"] for r in rows)
    order = diff > n_sigma * err
    return {"passed": framework and order, "tests": {"framework_intact": framework, "fast_faster_than_slow": order},
            "pooled": pooled, "ratio": f["D_cm2_per_s"] / s["D_cm2_per_s"], "diff_in_sigma": diff / err,
            "n_sigma": n_sigma}
