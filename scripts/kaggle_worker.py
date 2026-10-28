"""GPU worker run on Kaggle: computes a job sent by the PC (autolab/sim/kaggle_gpu.py) on every visible GPU.

    python scripts/kaggle_worker.py job.json <out dir>            # spreads the tasks over the GPUs
    python scripts/kaggle_worker.py job.json <out dir> --part k   # one GPU (CUDA_VISIBLE_DEVICES set by the parent)

A job is {"job_id", "kind", "settings": {kind: settings}, "tasks": [{"kind": "relax" | "md", "atoms", "cost"}]}
(relaxations and MD runs may share one job, one session). Each part appends one
JSON line per finished task to <out dir>/results_part<k>.jsonl, so a stopped session keeps what it finished.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from autolab.sim.kaggle_gpu import split


def run_part(job: dict, indices: list[int], out: Path, gpu: int) -> None:
    from autolab.sim.backend import LocalBackend

    backend = LocalBackend()
    with open(out / f"results_part{gpu}.jsonl", "a", encoding="utf-8") as f:
        for i in indices:
            task, t0 = job["tasks"][i], time.perf_counter()
            s = job["settings"][task["kind"]]
            line = {"job_id": job["job_id"], "i": i, "gpu": gpu}
            try:
                if task["kind"] == "relax":
                    line["result"] = next(iter(backend.relax_chunks([[task["atoms"]]], s["precision"], s["fmax"],
                                                                    s["steps"])))[0]
                else:
                    line["result"] = backend.md(task["atoms"], precision=s["precision"],
                                                temperature_K=s["temperature_K"], n_steps=s["n_steps"],
                                                seed=task.get("seed", 0))
            except Exception as e:  # one failed task must not lose the others
                line["error"] = f"{type(e).__name__}: {e}"[:500]
            f.write(json.dumps(line) + "\n")
            f.flush()
            print(f"[gpu{gpu}] task {i} {'FAILED' if 'error' in line else 'done'} in "
                  f"{time.perf_counter() - t0:.0f} s", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("job", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--part", type=int)
    ap.add_argument("--indices", default="")
    args = ap.parse_args()
    job = json.loads(args.job.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    if args.part is not None:
        run_part(job, [int(i) for i in args.indices.split(",") if i], args.out, args.part)
        return

    import torch

    n_gpus = max(torch.cuda.device_count(), 1)
    parts = split([t["cost"] for t in job["tasks"]], n_gpus)
    print(f"job {job['job_id']}: {len(job['tasks'])} {job['kind']} tasks on {n_gpus} GPU(s): "
          f"{[len(p) for p in parts]}", flush=True)
    procs = [subprocess.Popen([sys.executable, __file__, str(args.job), str(args.out), "--part", str(k),
                               "--indices", ",".join(map(str, p))],
                              env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(k)))
             for k, p in enumerate(parts) if p]
    codes = [p.wait() for p in procs]
    print(f"exit codes {codes}", flush=True)
    sys.exit(max(codes, default=0))


if __name__ == "__main__":
    main()
