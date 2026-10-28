"""Step 9C (GPU): Li diffusion screening by molecular dynamics, candidates next to their parents.

    SIM_BACKEND=local python scripts/run_md_screen.py results/<step>/candidates.json --ids it2-c5 it1-c2 \
        --parents mp-985583 mp-641703 --out <dir> [--temperature 1000 --ps 20 --backup <drive dir>]

Each finished run is cached (an interrupted screening resumes) and copied to --backup if given.
md_screen.json is rewritten after each run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import candidate_job, md_screen, parent_job

from run_interfaces import backup


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", type=Path)
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--parents", nargs="*", default=[])
    ap.add_argument("--temperature", type=float, default=config.MD_SCREEN_TEMPERATURE_K)
    ap.add_argument("--ps", type=float, default=config.MD_SCREEN_PS)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--backup", type=Path)
    args = ap.parse_args()

    by_id = {c["id"]: c for c in json.loads(args.candidates.read_text(encoding="utf-8"))["candidates"]}
    jobs = [parent_job(p) for p in args.parents] + [candidate_job(by_id[i]) for i in args.ids]
    args.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    def done(row: dict) -> None:
        rows.append(row)
        print(f"{row['id']} {row['formula']} ({row['kind']}): {row['n_atoms']} atoms, {row['n_li']} Li, "
              f"{row['ms_per_step']} ms/step, D = {row['D_cm2_per_s']:.2e} cm2/s at {row['temperature_K']:.0f} K, "
              f"MSD {row['msd_final_A2']:.1f} A2{' (cached)' if row['cached'] else ''}", flush=True)
        (args.out / "md_screen.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
        backup(args.backup)

    md_screen(jobs, args.temperature, args.ps, on_done=done)
    print(f"done: {len(rows)} runs")


if __name__ == "__main__":
    main()
