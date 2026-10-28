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
    from autolab.analysis.diffusion import diffusion_coefficient

    if len(jobs) > max_runs:
        raise ValueError(f"{len(jobs)} MD jobs requested, limit is {max_runs} (MD_SCREEN_MAX_RUNS)")
    if run is None:
        from autolab.sim.backend import run_md as run
    n_steps = round(ps * 1000 / config.MD_TIMESTEP_FS)
    out = []
    for job in jobs:
        t0 = time.perf_counter()
        res = run(job["atoms"], temperature_K=temperature_K, n_steps=n_steps)
        d = diffusion_coefficient(res["positions"], res["dt_record_fs"])
        row = {k: v for k, v in job.items() if k != "atoms"}
        row.update(temperature_K=temperature_K, ps=ps, n_atoms=res["n_atoms"], n_li=len(res["positions"][0]),
                   ms_per_step=res["ms_per_step"], cached=res.get("cached", False),
                   wall_s=round(time.perf_counter() - t0, 1), **{k: d[k] for k in d})
        out.append(row)
        if on_done:
            on_done(row)
    return out
