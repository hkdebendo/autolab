"""Kaggle GPU backend (sim/kaggle_gpu.py, scripts/kaggle_worker.py): fake kaggle CLI, no network, no GPU, no cost."""

import base64
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from pymatgen.core import Lattice, Structure

from autolab import config
from autolab.agent import dynamics
from autolab.sim import kaggle_gpu
from autolab.sim.backend import relax_structures, run_md, run_md_batch
from autolab.sim.serialize import atoms_to_dict
from autolab.store.cache import JsonCache

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def licl(a: float) -> dict:
    from pymatgen.io.ase import AseAtomsAdaptor

    s = Structure.from_spacegroup("Fm-3m", Lattice.cubic(a), ["Li", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    return atoms_to_dict(AseAtomsAdaptor.get_atoms(s))


def fake_relax(d: dict) -> dict:
    return {"formula": "LiCl", "energy": -7.0, "energy_per_atom": -0.875, "converged": True, "steps": 3,
            "seconds": 1.0, "atoms": d}


def test_split_puts_largest_first_on_least_loaded_gpu():
    parts = kaggle_gpu.split([5, 1, 4, 3, 3], 2)
    loads = [sum([5, 1, 4, 3, 3][i] for i in p) for p in parts]
    assert sorted(loads) == [8, 8] and sorted(i for p in parts for i in p) == [0, 1, 2, 3, 4]
    job = kaggle_gpu.relax_job([licl(5.0)] * 3, "high-precision", 0.05, 500)
    assert kaggle_gpu.estimate_seconds(job) == pytest.approx(2 * config.KAGGLE_RELAX_S)
    assert kaggle_gpu.session_limit(job) <= config.KAGGLE_MAX_SESSION_S


def test_jobs_are_deterministic_and_md_cost_counts_the_supercell():
    a = kaggle_gpu.relax_job([licl(5.0)], "high-precision", 0.05, 500)
    assert a["job_id"] == kaggle_gpu.relax_job([licl(5.0)], "high-precision", 0.05, 500)["job_id"]
    assert a["job_id"] != kaggle_gpu.relax_job([licl(5.1)], "high-precision", 0.05, 500)["job_id"]
    md = kaggle_gpu.md_job([{"atoms": licl(5.13), "seed": 0}], "default", 1000, 20000)
    # Conventional LiCl (8 atoms, 5.13 A sides) becomes a 2x2x2 supercell of 64 atoms for the 10 A minimum.
    assert md["tasks"][0]["cost"] == pytest.approx(64 * 20000 * config.KAGGLE_MD_MS_PER_ATOM_STEP / 1000)


def test_notebook_carries_the_job_and_no_secret():
    job = kaggle_gpu.relax_job([licl(5.0)], "high-precision", 0.05, 500)
    nb = kaggle_gpu.notebook(job, "abc1234")
    src = "".join(nb["cells"][0]["source"])
    payload = re.search(r'b64decode\("([^"]+)"\)', src).group(1)
    assert json.loads(gzip.decompress(base64.b64decode(payload))) == job
    assert '"abc1234"' in src and "HF_HUB_OFFLINE" in src
    assert "kaggle_secrets" not in src and "HF_TOKEN" not in src and "API_KEY" not in src
    meta = kaggle_gpu.metadata()
    assert meta["dataset_sources"] == [config.KAGGLE_UMA_DATASET] and meta["enable_gpu"] and meta["is_private"]
    assert "docker_image" not in meta


class FakeCli:
    """Plays the kaggle CLI: a stale output first (previous version), then the job's results."""

    def __init__(self, job, results, errors=(), push_reply="Kernel version 7 successfully pushed."):
        self.job, self.results, self.errors, self.push_reply = job, results, dict(errors), push_reply
        self.calls, self.states = [], iter(["COMPLETE", "RUNNING", "COMPLETE"])
        self.served = 0

    def __call__(self, args):
        self.calls.append(args[:2])
        if args[1] == "push":
            assert (Path(args[3]) / "kernel-metadata.json").exists() and (Path(args[3]) / kaggle_gpu.NOTEBOOK).exists()
            return self.push_reply
        if args[1] == "status":
            return f'adladeeba/autolab-gpu has status "KernelWorkerStatus.{next(self.states)}"'
        out = Path(args[args.index("-p") + 1])
        out.mkdir(parents=True, exist_ok=True)
        self.served += 1
        if self.served == 1:  # previous version's files
            (out / "status.json").write_text(json.dumps({"job_id": "old"}), encoding="utf-8")
            return ""
        (out / "status.json").write_text(json.dumps({"job_id": self.job["job_id"], "done": True,
                                                     "gpus": ["Tesla T4", "Tesla T4"]}), encoding="utf-8")
        for gpu in (0, 1):
            lines = [{"job_id": "old", "i": 0, "gpu": gpu, "result": {"stale": True}}]
            for i, r in enumerate(self.results):
                if i % 2 == gpu:
                    lines.append({"job_id": self.job["job_id"], "i": i, "gpu": gpu,
                                  **({"error": self.errors[i]} if i in self.errors else {"result": r})})
            (out / f"results_part{gpu}.jsonl").write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
        return ""


def test_run_job_waits_for_its_own_output(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    job = kaggle_gpu.relax_job([licl(5.0), licl(5.3), licl(5.6)], "high-precision", 0.05, 500)
    cli = FakeCli(job, [fake_relax(t["atoms"]) for t in job["tasks"]], errors={2: "RuntimeError: boom"})
    sleeps = []
    results, info = kaggle_gpu.run_job(job, cli=cli, sleep=sleeps.append, commit="abc1234", log=lambda s: None)
    assert [r is not None for r in results] == [True, True, False] and info["errors"] == {2: "RuntimeError: boom"}
    assert info["gpus"] == {0: 0, 1: 1} and len(sleeps) == 3
    assert cli.calls.count(["kernels", "push"]) == 1  # never pushed twice


def test_run_job_stops_when_the_push_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    job = kaggle_gpu.relax_job([licl(5.0)], "high-precision", 0.05, 500)
    cli = FakeCli(job, [], push_reply="The following are not valid dataset sources ...\nKernel version 8 "
                                      "successfully pushed.")
    with pytest.raises(kaggle_gpu.KaggleJobError, match="push refused"):
        kaggle_gpu.run_job(job, cli=cli, sleep=lambda s: None, commit="abc1234", log=lambda s: None)
    assert cli.calls == [["kernels", "push"]]


def test_relax_structures_keeps_finished_results_when_one_fails(tmp_path):
    sent = []

    def run(job):
        sent.append(len(job["tasks"]))
        return [None if i == 1 and len(sent) == 1 else fake_relax(t["atoms"])
                for i, t in enumerate(job["tasks"])], {}

    backend, cache = kaggle_gpu.KaggleBackend(run), JsonCache(tmp_path)
    structures = [licl(5.0), licl(5.3), licl(5.6)]
    with pytest.raises(RuntimeError, match="1 of 3 relaxations failed on the kaggle backend"):
        relax_structures(structures, backend=backend, cache=cache)
    res = relax_structures(structures, backend=backend, cache=cache)
    assert sent == [3, 1] and [r["cached"] for r in res] == [True, False, True]


def fake_md(atoms, seed=0, n_li=20, d_true=0.5, n_steps=20000):
    rng = np.random.default_rng(seed + 1)  # same draw as fake_run in test_step9
    dt = config.MD_TIMESTEP_FS * config.MD_RECORD_EVERY
    steps = rng.normal(0, np.sqrt(2 * d_true * dt / 1000.0), size=(n_steps // config.MD_RECORD_EVERY, n_li, 3))
    pos = np.concatenate([np.zeros((1, n_li, 3)), np.cumsum(steps, axis=0)])
    return {"positions": pos.tolist(), "dt_record_fs": dt, "n_atoms": 54, "ms_per_step": 30.0, "seconds": 600.0}


def test_md_screen_sends_one_batch_then_reads_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "SIM_BACKEND", "kaggle")
    jobs_sent = []

    def run(job):
        jobs_sent.append(job)
        return [fake_md(t["atoms"]) for t in job["tasks"]], {}

    monkeypatch.setattr(kaggle_gpu, "run_job", run)
    jobs = [{"id": f"s{a}", "formula": "LiCl", "kind": "candidate", "atoms": licl(a)} for a in (5.1, 5.2)]
    rows = dynamics.md_screen(jobs, temperature_K=1000, ps=20)
    assert len(jobs_sent) == 1 and jobs_sent[0]["kind"] == "md" and len(jobs_sent[0]["tasks"]) == 2
    assert jobs_sent[0]["settings"] == {"precision": config.UMA_PRECISION_MD, "temperature_K": 1000, "n_steps": 20000}
    assert [r["cached"] for r in rows] == [True, True] and rows[0]["D_A2_per_ps"] == pytest.approx(0.5, rel=0.25)
    run_md_batch([licl(5.1)], 1000, 20000)  # already cached: nothing sent
    assert len(jobs_sent) == 1
    assert run_md(licl(5.2), 1000, 20000)["cached"]


def test_worker_part_writes_one_line_per_task_even_after_a_failure(tmp_path, monkeypatch):
    sys.path.insert(0, str(SCRIPTS))
    import kaggle_worker
    from autolab.sim import backend

    class FakeLocal:
        def relax_chunks(self, chunks, precision, fmax, steps):
            d = chunks[0][0]
            if d["cell"][0][0] > 5.5:
                raise RuntimeError("did not fit on the GPU")
            yield [fake_relax(d)]

    monkeypatch.setattr(backend, "LocalBackend", FakeLocal)
    job = kaggle_gpu.relax_job([licl(5.0), licl(5.6)], "high-precision", 0.05, 500)
    kaggle_worker.run_part(job, [0, 1], tmp_path, gpu=1)
    results, info = kaggle_gpu.read_results(tmp_path, job)
    assert results[0]["formula"] == "LiCl" and results[1] is None
    assert "did not fit" in info["errors"][1] and info["gpus"] == {0: 1}
