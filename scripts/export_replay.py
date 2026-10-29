"""Export the light files of the replay visuals of a run (3D Li diffusion, MSD curves, relaxed structures).

    python scripts/export_replay.py results/<run> [--frames 400]

Reads result.json and the caches (never computes) and writes results/<run>/replay/: index.json,
structures/<id>.json (every passed candidate) and md/<id>_seed<k>.json (every structure of the MD stage, parents
included). Ids are written with "_" instead of ":" in file names.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import candidate_job, md_cached_result, parent_job
from autolab.analysis.replay_export import md_view, structure_view


def fname(cid: str) -> str:
    return cid.replace(":", "_")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--frames", type=int, default=config.REPLAY_MD_FRAMES)
    args = ap.parse_args()
    result = json.loads((args.run / "result.json").read_text(encoding="utf-8"))
    pool = {c["id"]: c for c in result["prior"] + [c for r in result["iterations"] for c in r["candidates"]]}
    out = args.run / "replay"
    (out / "structures").mkdir(parents=True, exist_ok=True)
    (out / "md").mkdir(parents=True, exist_ok=True)
    index = {"structures": [], "md": []}

    for c in pool.values():
        if c.get("status") != "passed" or not c.get("relaxed_atoms"):
            continue
        view = structure_view(c["relaxed_atoms"], (c.get("substitution") or {}).get("add"))
        view.update(id=c["id"], formula=c["formula"], parent=c.get("parent"), e_hull=c.get("e_hull"))
        (out / "structures" / f"{fname(c['id'])}.json").write_text(json.dumps(view), encoding="utf-8")
        index["structures"].append({"id": c["id"], "formula": c["formula"], "file": f"structures/{fname(c['id'])}.json"})

    for row in result["stages"].get("molecular_dynamics", {}).get("rows", []):
        job = parent_job(row["id"]) if row["kind"] == "parent" else candidate_job(pool[row["id"]])
        for seed in range(row.get("seeds", config.MD_SCREEN_SEEDS)):
            md = md_cached_result(job, seed, row["temperature_K"], row["ps"])
            if md is None:
                print(f"{row['id']} seed {seed}: not in the MD cache, skipped")
                continue
            view = md_view(job["atoms"], md, args.frames)
            v = row.get("vs_parent") or {}
            view.update(id=row["id"], formula=row["formula"], kind=row["kind"], parent=row.get("parent"), seed=seed,
                        D_cm2_per_s=row["D_cm2_per_s"], D_sem_cm2_per_s=row["D_sem_cm2_per_s"],
                        D_seed_cm2_per_s=(row.get("D_per_seed_cm2_per_s") or [None] * (seed + 1))[seed],
                        ratio=v.get("ratio"), ratio_err=v.get("ratio_err"), verdict=v.get("verdict"),
                        conduction=row.get("conduction"), conduction_reason=row.get("conduction_reason"))
            name = f"md/{fname(row['id'])}_seed{seed}.json"
            (out / name).write_text(json.dumps(view), encoding="utf-8")
            index["md"].append({"id": row["id"], "formula": row["formula"], "kind": row["kind"], "seed": seed,
                                "verdict": v.get("verdict"), "file": name})
            print(f"{name}: {len(view['frames'])} frames, {(out / name).stat().st_size // 1024} KB")
    (out / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"{len(index['structures'])} structures, {len(index['md'])} MD runs in {out}")


if __name__ == "__main__":
    main()
