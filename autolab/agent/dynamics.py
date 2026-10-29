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

    relax = relax or (lambda s: relax_structures([s], max_new=0)[0])
    s = get_structure(material_id)
    return {"id": material_id, "formula": s.composition.reduced_formula, "kind": "parent", "atoms": relax(s)["atoms"]}


def candidate_job(c: dict) -> dict:
    """MD job for a candidate, started from its best relaxed arrangement."""
    return {"id": c["id"], "formula": c["formula"], "kind": "candidate", "parent": c["parent"],
            "atoms": c["relaxed_atoms"]}


def md_runs_to_compute(jobs: list[dict], temperature_K: float = config.MD_SCREEN_TEMPERATURE_K,
                       ps: float = config.MD_SCREEN_PS, seeds: int = config.MD_SCREEN_SEEDS,
                       all_runs: bool = False) -> list[dict]:
    """The runs (job x seed) of a screening missing from the MD cache ({"id", "atoms", "temperature_K", "n_steps",
    "seed", "cached"}); with all_runs, cached ones too. Same keys as sim.backend.run_md."""
    from autolab.sim.backend import _as_atoms_dict
    from autolab.sim.serialize import atoms_key
    from autolab.store.cache import JsonCache

    cache = JsonCache(config.CACHE_DIR / "md")
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    out = []
    for job in jobs:
        d = _as_atoms_dict(job["atoms"])
        for s in range(seeds):
            key = atoms_key(d, model=config.UMA_MODEL, precision=config.UMA_PRECISION_MD, T=temperature_K,
                            n_steps=n_steps, seed=s)
            cached = cache.get(key) is not None
            if all_runs or not cached:
                out.append({"id": job["id"], "atoms": job["atoms"], "temperature_K": temperature_K,
                            "n_steps": n_steps, "seed": s, "cached": cached})
    return out


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
              max_runs: int = config.MD_SCREEN_MAX_RUNS, backend=None) -> list[dict]:
    """Run each job with `seeds` seeds (cached), pool the blocks of its seeds into one D with its error
    (calibration v2, SPEC 5.10), check the framework of every run, call on_done after each job."""
    from autolab.analysis.diffusion import diffusion_coefficient, framework_check, pool

    if len(jobs) * seeds > max_runs:
        raise ValueError(f"{len(jobs)} MD jobs x {seeds} seeds requested, limit is {max_runs} (MD_SCREEN_MAX_RUNS)")
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    if run is None:
        from functools import partial

        from autolab.sim.backend import run_md, run_md_runs

        # one Kaggle session, or all runs in parallel on Modal
        run_md_runs([{"atoms": job["atoms"], "temperature_K": temperature_K, "n_steps": n_steps, "seed": s}
                     for job in jobs for s in range(seeds)], backend=backend)
        run = partial(run_md, backend=backend)
    out = []
    for job in jobs:
        t0 = time.perf_counter()
        results = [run(job["atoms"], temperature_K=temperature_K, n_steps=n_steps, seed=s) for s in range(seeds)]
        ds = [diffusion_coefficient(r["positions"], r["dt_record_fs"]) for r in results]
        d = pool(ds)
        row = {k: v for k, v in job.items() if k != "atoms"}
        res = results[0]
        row.update(temperature_K=temperature_K, ps=ps, seeds=seeds, n_atoms=res["n_atoms"],
                   n_li=len(res["positions"][0]), ms_per_step=res["ms_per_step"],
                   cached=all(r.get("cached", False) for r in results), wall_s=round(time.perf_counter() - t0, 1),
                   gpu=res.get("gpu"), **d)
        checks = [framework_check(r["framework_msd"], r["dt_record_fs"], di["D_A2_per_ps"])
                  for r, di in zip(results, ds) if r.get("framework_msd")]
        if checks:  # runs recorded before this check have Li positions only
            row["framework"] = {"intact": all(c["intact"] for c in checks), "per_seed": checks}
        out.append(row)
        if on_done:
            on_done(row)
    return out


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
            r["conduction_reason"] = ("framework moved" if moved else "no Li diffusion seen" if no_hop else
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
