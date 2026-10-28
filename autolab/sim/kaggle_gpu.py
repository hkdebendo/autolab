"""Kaggle GPU backend: the PC sends a batch of structures to a Kaggle notebook and reads the results back.

No secret goes to Kaggle. The generated notebook clones the public repository at the current (pushed) commit,
installs it, loads UMA offline from the private dataset config.KAGGLE_UMA_DATASET and runs
scripts/kaggle_worker.py on every GPU. The PC drives it with the official kaggle CLI (push, status, output),
which reads its own credentials. One job = one Kaggle session; a failed session is never retried automatically.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterator

from autolab import config

NOTEBOOK = "autolab-gpu.ipynb"
REPO_URL = "https://github.com/hkdebendo/autolab.git"
OUTPUT_PATTERN = r"^(results_part\d+\.jsonl|status\.json)$"


class KaggleJobError(RuntimeError):
    """A Kaggle session failed, timed out or returned incomplete results."""


def kaggle_cli(args: list[str]) -> str:
    """Run the official kaggle CLI and return its output."""
    r = subprocess.run([sys.executable, "-m", "kaggle", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise KaggleJobError(f"kaggle {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()[-400:]}")
    return r.stdout


# --- Jobs ----------------------------------------------------------------------

def split(costs: list[float], n_parts: int) -> list[list[int]]:
    """Task indices per GPU: largest tasks first, each to the least loaded GPU."""
    parts: list[list[int]] = [[] for _ in range(n_parts)]
    loads = [0.0] * n_parts
    for i in sorted(range(len(costs)), key=lambda i: -costs[i]):
        k = loads.index(min(loads))
        parts[k].append(i)
        loads[k] += costs[i]
    return parts


def _job(kind: str, settings: dict, tasks: list[dict]) -> dict:
    body = {"kind": kind, "settings": settings, "tasks": tasks}
    return {"job_id": hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:12], **body}


def relax_job(dicts: list[dict], precision: str, fmax: float, steps: int) -> dict:
    tasks = [{"atoms": d, "cost": float(config.KAGGLE_RELAX_S)} for d in dicts]
    return _job("relax", {"precision": precision, "fmax": fmax, "steps": steps}, tasks)


def md_job(items: list[dict], precision: str, temperature_K: float, n_steps: int) -> dict:
    """`items`: [{"atoms": atoms dict, "seed": int}]; the cost counts the atoms of the MD supercell."""
    from autolab.sim.md import supercell_reps
    from autolab.sim.serialize import atoms_from_dict

    tasks = []
    for it in items:
        atoms = atoms_from_dict(it["atoms"])
        n = len(atoms) * math.prod(supercell_reps(atoms))
        tasks.append({"atoms": it["atoms"], "seed": it.get("seed", 0),
                      "cost": n * n_steps * config.KAGGLE_MD_MS_PER_ATOM_STEP / 1000})
    return _job("md", {"precision": precision, "temperature_K": temperature_K, "n_steps": n_steps}, tasks)


def estimate_seconds(job: dict, n_gpus: int = config.KAGGLE_N_GPUS) -> float:
    """Expected compute time on the GPUs (largest-first split), without the session setup."""
    costs = [t["cost"] for t in job["tasks"]]
    return max((sum(costs[i] for i in part) for part in split(costs, n_gpus)), default=0.0)


def session_limit(job: dict) -> int:
    """Kaggle time limit of the session (s): safety factor x (setup + estimate), capped."""
    return int(min(config.KAGGLE_TIMEOUT_FACTOR * (config.KAGGLE_SETUP_S + estimate_seconds(job)),
                   config.KAGGLE_MAX_SESSION_S))


# --- Notebook --------------------------------------------------------------------

CELL = r'''
# AutoLab GPU job __JOB_ID__, generated on the PC by autolab/sim/kaggle_gpu.py. No secret is used:
# public repository, UMA checkpoint from a private dataset, loaded offline.
import base64, gzip, json, os, shutil, subprocess, sys, time
from pathlib import Path

JOB_ID, COMMIT = "__JOB_ID__", "__COMMIT__"
OUT, REPO = Path("/kaggle/working"), Path("/tmp/autolab")
status = {"job_id": JOB_ID, "commit": COMMIT, "steps": {}}


def save():
    (OUT / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")


def step(name, cmd, **kw):
    t0 = time.time()
    code = subprocess.run([str(c) for c in cmd], **kw).returncode
    status["steps"][name] = {"code": code, "seconds": round(time.time() - t0, 1)}
    save()
    print(f"[{name}] code {code}, {time.time() - t0:.0f} s", flush=True)
    return code == 0


status["gpus"] = [g for g in subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                            capture_output=True, text=True).stdout.splitlines() if g.strip()]
save()
ok = (step("clone", ["git", "clone", "--quiet", "__REPO_URL__", REPO])
      and step("checkout", ["git", "-C", REPO, "checkout", "--quiet", COMMIT])
      and step("install", [sys.executable, "-m", "pip", "install", "-q", "-e", REPO, "fairchem-core==2.24.0"]))
if ok:
    try:
        src = next(p.parent for p in Path("/kaggle/input").rglob("models--facebook--UMA"))
        cache = Path("/tmp/fairchem_cache")
        shutil.copytree(src, cache, dirs_exist_ok=True)
        status["checkpoint"] = str(src)
    except StopIteration:
        ok = False
        status["checkpoint"] = "missing: attach the UMA dataset"
    save()
if ok:
    job = Path("/tmp/job.json")
    job.write_bytes(gzip.decompress(base64.b64decode("__PAYLOAD__")))
    env = dict(os.environ, FAIRCHEM_CACHE_DIR=str(cache), HF_HUB_OFFLINE="1", SIM_BACKEND="local",
               PYTHONUNBUFFERED="1")
    step("worker", [sys.executable, "scripts/kaggle_worker.py", job, OUT], cwd=REPO, env=env)
status["done"] = True
save()
'''


def notebook(job: dict, commit: str) -> dict:
    payload = base64.b64encode(gzip.compress(json.dumps(job).encode())).decode()
    src = (CELL.strip("\n").replace("__JOB_ID__", job["job_id"]).replace("__COMMIT__", commit)
           .replace("__REPO_URL__", REPO_URL).replace("__PAYLOAD__", payload))
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}},
            "cells": [{"cell_type": "code", "id": "job", "metadata": {}, "execution_count": None, "outputs": [],
                       "source": src.splitlines(keepends=True)}]}


def metadata(kernel: str = config.KAGGLE_KERNEL) -> dict:
    return {"id": kernel, "title": kernel.split("/")[1], "code_file": NOTEBOOK, "language": "python",
            "kernel_type": "notebook", "is_private": True, "enable_gpu": True, "enable_tpu": False,
            "enable_internet": True, "dataset_sources": [config.KAGGLE_UMA_DATASET], "kernel_sources": [],
            "competition_sources": [], "model_sources": [], "machine_shape": config.KAGGLE_ACCELERATOR}


def pushed_commit(root: Path = config.ROOT) -> str:
    """Current commit, which must already be on GitHub (the Kaggle notebook clones it)."""
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()

    commit = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=no", "--", "autolab", "scripts"):
        raise KaggleJobError("uncommitted changes in autolab/ or scripts/: commit and push them first")
    if "origin/main" not in git("branch", "-r", "--contains", commit).split():
        raise KaggleJobError(f"commit {commit[:7]} is not on origin/main: push it first")
    return commit


# --- Running a job ---------------------------------------------------------------

def read_results(folder: Path, job: dict) -> tuple[list[dict | None], dict]:
    """One result per task (None if missing or failed) and the session info (status, errors, GPUs used)."""
    status_file = folder / "status.json"
    status = json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}
    results: list[dict | None] = [None] * len(job["tasks"])
    errors, gpus = {}, {}
    for f in sorted(folder.glob("results_part*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("job_id") != job["job_id"]:
                continue
            if "error" in row:
                errors[row["i"]] = row["error"]
            else:
                results[row["i"]] = row["result"]
                gpus[row["i"]] = row["gpu"]
    return results, {"status": status, "errors": errors, "gpus": gpus}


def run_job(job: dict, kernel: str = config.KAGGLE_KERNEL, cli: Callable[[list[str]], str] = kaggle_cli,
            sleep: Callable[[float], None] = time.sleep, commit: str | None = None,
            log: Callable[[str], None] = print) -> tuple[list[dict | None], dict]:
    """Push the job as a new notebook version, wait for the end of the session, download the results."""
    commit = commit or pushed_commit()
    folder = (config.CACHE_DIR / "kaggle" / "jobs" / job["job_id"]).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "kernel-metadata.json").write_text(json.dumps(metadata(kernel), indent=1), encoding="utf-8")
    (folder / NOTEBOOK).write_text(json.dumps(notebook(job, commit)), encoding="utf-8")
    limit = session_limit(job)
    log(f"Kaggle job {job['job_id']}: {len(job['tasks'])} {job['kind']} task(s), about "
        f"{estimate_seconds(job) / 60:.0f} min of compute + {config.KAGGLE_SETUP_S / 60:.0f} min of setup, "
        f"session limit {limit / 60:.0f} min")
    out = cli(["kernels", "push", "-p", str(folder), "-t", str(limit), "--accelerator", config.KAGGLE_ACCELERATOR])
    if "successfully pushed" not in out or "not valid" in out:
        raise KaggleJobError(f"push refused: {out.strip()[-400:]}")

    deadline = time.monotonic() + limit + 3600  # the session may wait in the Kaggle queue first
    out_dir = folder / "output"
    while True:
        sleep(config.KAGGLE_POLL_S)
        state = cli(["kernels", "status", kernel]).upper()
        if any(w in state for w in ("COMPLETE", "ERROR", "CANCEL")):
            cli(["kernels", "output", kernel, "-p", str(out_dir), "-o", "-q", "--file-pattern", OUTPUT_PATTERN])
            results, info = read_results(out_dir, job)
            if info["status"].get("job_id") == job["job_id"]:  # otherwise: the previous version's output
                info["state"] = state.strip()
                break
        if time.monotonic() > deadline:
            raise KaggleJobError(f"job {job['job_id']}: no finished session after {(limit + 3600) / 60:.0f} min")
    n_ok = sum(r is not None for r in results)
    log(f"Kaggle job {job['job_id']}: {n_ok}/{len(results)} results, GPUs {info['status'].get('gpus')}, "
        f"steps {info['status'].get('steps')}")
    if not info["status"].get("done"):
        log(f"warning: the session stopped before its end ({info['state']})")
    return results, info


class KaggleBackend:
    """Same interface as LocalBackend / ModalBackend; each call is one Kaggle session."""

    name = "kaggle"

    def __init__(self, run: Callable | None = None):
        self._run = run

    def run(self, job: dict) -> tuple[list[dict | None], dict]:
        return (self._run or run_job)(job)

    def relax_chunks(self, chunks: list[list[dict]], precision: str, fmax: float, steps: int) -> Iterator[list]:
        flat = [d for c in chunks for d in c]
        results, _ = self.run(relax_job(flat, precision, fmax, steps))
        i = 0
        for c in chunks:  # None marks a relaxation that failed: relax_structures caches the others, then raises
            yield results[i:i + len(c)]
            i += len(c)

    def md_batch(self, items: list[dict], precision: str, temperature_K: float, n_steps: int) -> list[dict | None]:
        results, _ = self.run(md_job(items, precision, temperature_K, n_steps))
        return results

    def md(self, atoms: dict, precision: str, temperature_K: float, n_steps: int, seed: int = 0) -> dict:
        res = self.md_batch([{"atoms": atoms, "seed": seed}], precision, temperature_K, n_steps)[0]
        if res is None:
            raise KaggleJobError("molecular dynamics failed on Kaggle")
        return res
