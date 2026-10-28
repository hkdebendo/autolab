"""Steps 9B + 9C in one GPU session: the relaxations of the interface references and the MD runs, sent together.

    SIM_BACKEND=kaggle python scripts/step9_gpu_batch.py results/<step>/candidates.json \
        --interface-ids it1-c4 --md-ids it1-c4 it2-c5 --md-parents mp-985583 mp-641703 [--dry-run]

Fills the caches only (one Kaggle session, one fairchem install); run_interfaces.py and run_md_screen.py then
read them. --dry-run prints what would be sent and the estimated duration, without sending anything.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import candidate_job, parent_job
from autolab.agent.electrochem import _elements, candidate_entry
from autolab.data.mp import get_references
from autolab.sim.backend import RelaxBudget, _as_atoms_dict, prefetch
from autolab.sim.serialize import atoms_key
from autolab.store.cache import JsonCache


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", type=Path)
    ap.add_argument("--interface-ids", nargs="*", default=[])
    ap.add_argument("--cathode", default="LiFePO4")
    ap.add_argument("--md-ids", nargs="*", default=[])
    ap.add_argument("--md-parents", nargs="*", default=[])
    ap.add_argument("--temperature", type=float, default=config.MD_SCREEN_TEMPERATURE_K)
    ap.add_argument("--ps", type=float, default=config.MD_SCREEN_PS)
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    by_id = {c["id"]: c for c in json.loads(args.candidates.read_text(encoding="utf-8"))["candidates"]}
    refs = {}
    for cid in args.interface_ids:
        elements = _elements(candidate_entry(by_id[cid]).composition, args.cathode)
        for r in get_references(elements, ehull_max=config.INTERFACE_REF_EHULL_MAX):
            refs.setdefault(r["material_id"], r["structure"])
    jobs = [parent_job(p) for p in args.md_parents] + [candidate_job(by_id[i]) for i in args.md_ids]
    if len(jobs) > config.MD_SCREEN_MAX_RUNS:
        raise SystemExit(f"{len(jobs)} MD runs requested, limit is {config.MD_SCREEN_MAX_RUNS} (MD_SCREEN_MAX_RUNS)")
    n_steps = round(args.ps * 1000 / config.MD_TIMESTEP_FS)

    if args.dry_run:
        from autolab.sim import kaggle_gpu

        rset = {"model": config.UMA_MODEL, "precision": config.UMA_PRECISION_ENERGY, "fmax": config.RELAX_FMAX,
                "steps": config.RELAX_STEPS}
        cache = JsonCache(config.RELAX_CACHE_DIR)
        missing = [d for d in map(_as_atoms_dict, refs.values()) if cache.get(atoms_key(d, **rset)) is None]
        job = kaggle_gpu.combine(
            *([kaggle_gpu.relax_job(missing, config.UMA_PRECISION_ENERGY, config.RELAX_FMAX, config.RELAX_STEPS)]
              if missing else []),
            kaggle_gpu.md_job([{"atoms": j["atoms"]} for j in jobs], config.UMA_PRECISION_MD, args.temperature,
                              n_steps))
        print(f"{len(refs)} interface references ({len(missing)} to relax), {len(jobs)} MD runs of {args.ps} ps: "
              f"about {kaggle_gpu.estimate_seconds(job) / 60:.0f} min of compute on {config.KAGGLE_N_GPUS} GPUs "
              f"+ {config.KAGGLE_SETUP_S / 60:.0f} min of setup, session limit "
              f"{kaggle_gpu.session_limit(job) / 60:.0f} min (MD runs already cached are not sent)")
        return
    sent = prefetch(relax=list(refs.values()), md=[j["atoms"] for j in jobs], temperature_K=args.temperature,
                    n_steps=n_steps, budget=RelaxBudget(args.max_relaxations))
    print(f"sent in one session: {sent['relax']} relaxations, {sent['md']} MD runs")


if __name__ == "__main__":
    main()
