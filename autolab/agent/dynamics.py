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


def md_screen(jobs: list[dict], temperature_K: float = config.MD_SCREEN_TEMPERATURE_K,
              ps: float = config.MD_SCREEN_PS, run: Callable | None = None,
              on_done: Callable[[dict], None] | None = None,
              max_runs: int = config.MD_SCREEN_MAX_RUNS) -> list[dict]:
    """Run each job (cached), fit D on the second half of the MSD, call on_done after each job."""
    from autolab.analysis.diffusion import diffusion_coefficient, framework_check

    if len(jobs) > max_runs:
        raise ValueError(f"{len(jobs)} MD jobs requested, limit is {max_runs} (MD_SCREEN_MAX_RUNS)")
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    if run is None:
        from autolab.sim.backend import run_md as run, run_md_batch

        run_md_batch([job["atoms"] for job in jobs], temperature_K, n_steps)  # one Kaggle session for all jobs
    out = []
    for job in jobs:
        t0 = time.perf_counter()
        res = run(job["atoms"], temperature_K=temperature_K, n_steps=n_steps)
        d = diffusion_coefficient(res["positions"], res["dt_record_fs"])
        row = {k: v for k, v in job.items() if k != "atoms"}
        row.update(temperature_K=temperature_K, ps=ps, n_atoms=res["n_atoms"], n_li=len(res["positions"][0]),
                   ms_per_step=res["ms_per_step"], cached=res.get("cached", False),
                   wall_s=round(time.perf_counter() - t0, 1), **{k: d[k] for k in d})
        if res.get("framework_msd"):  # runs recorded before this check have Li positions only
            row["framework"] = framework_check(res["framework_msd"], res["dt_record_fs"], d["D_A2_per_ps"])
        out.append(row)
        if on_done:
            on_done(row)
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
