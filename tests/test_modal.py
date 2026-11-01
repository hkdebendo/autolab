"""Modal backend (sim/backend.py ModalBackend): fake Modal functions, no network, no GPU, no cost."""

import modal.exception
import pytest

from autolab import config
from autolab.agent.dynamics import md_runs_to_compute, md_screen, md_verdicts, with_md_gpu
from autolab.sim.backend import ModalBackend, md_settings, run_md, run_md_runs

from test_kaggle import fake_md, licl


class FakeCall:
    def __init__(self, result, polls_before_done: int):
        self.result, self.left, self.cancelled = result, polls_before_done, False

    def get(self, timeout=None):
        if self.left > 0:
            self.left -= 1
            raise modal.exception.TimeoutError("not yet")
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def cancel(self, terminate_containers=False):
        self.cancelled = True


class FakeFn:
    def __init__(self, refuse_after: int | None = None):
        self.options, self.spawned, self.refuse_after = None, [], refuse_after

    def with_options(self, **opts):
        self.options = opts
        return self

    def spawn(self, atoms, precision, temperature_K, n_steps, seed=0):
        if self.refuse_after is not None and len(self.spawned) >= self.refuse_after:
            raise modal.exception.Error("spending limit reached")
        n = len(self.spawned)
        result = RuntimeError("CUDA out of memory") if temperature_K == 700 else fake_md(atoms)
        call = FakeCall(result, polls_before_done=2 - n)  # later runs end first
        self.spawned.append((temperature_K, n_steps, seed, call))
        return call

    def remote(self, atoms, precision, temperature_K, n_steps, seed=0):
        self.spawned.append((temperature_K, n_steps, seed, None))
        return fake_md(atoms)


def runs():
    return [{"atoms": licl(5.1), "temperature_K": t, "n_steps": n, "seed": s}
            for t, n, s in ((600, 40000, 0), (700, 30000, 0), (1000, 20000, 1))]


def test_modal_runs_in_parallel_and_saves_each_result_when_it_ends(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    fn = FakeFn()
    backend = ModalBackend(gpu="A10G", md_timeout_s=3600, poll_s=0)
    monkeypatch.setattr(backend, "_fn", lambda name: fn)
    assert run_md_runs(runs(), backend=backend) == 3
    assert fn.options == {"max_containers": 3, "gpu": "A10G", "timeout": 3600}  # one container per run
    assert [s[:3] for s in fn.spawned] == [(600, 40000, 0), (700, 30000, 0), (1000, 20000, 1)]
    assert "out of memory" in backend.errors[1]  # the failed run is reported, not retried
    assert run_md(licl(5.1), 600, 40000, backend=backend)["cached"]
    assert run_md(licl(5.1), 1000, 20000, seed=1, backend=backend)["cached"]
    fn.spawned.clear()
    assert run_md_runs([runs()[0], runs()[2]], backend=backend) == 0 and fn.spawned == []


def test_modal_refused_call_cancels_what_was_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    fn = FakeFn(refuse_after=1)
    backend = ModalBackend(poll_s=0)
    monkeypatch.setattr(backend, "_fn", lambda name: fn)
    with pytest.raises(modal.exception.Error, match="spending limit"):
        run_md_runs(runs(), backend=backend)
    assert len(fn.spawned) == 1 and fn.spawned[0][3].cancelled


def test_md_cache_keys_name_the_gpu_except_the_legacy_one():
    legacy = {"model": config.UMA_MODEL, "precision": config.UMA_PRECISION_MD, "T": 600, "n_steps": 40000, "seed": 1}
    assert md_settings(600, 40000, 1, gpu=config.MD_LEGACY_GPU) == legacy  # keys of the runs cached before 2026-11-01
    assert md_settings(600, 40000, 1) == legacy
    assert md_settings(600, 40000, 1, gpu="H100") == {**legacy, "gpu": "H100"}


def _backend(gpu, fn, monkeypatch):
    backend = ModalBackend(gpu=gpu, md_timeout_s=3600, poll_s=0)
    monkeypatch.setattr(backend, "_fn", lambda name: fn)
    return backend


def test_a_run_on_another_gpu_never_reads_the_legacy_result(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    run = [{"atoms": licl(5.1), "temperature_K": 600, "n_steps": 40000, "seed": 0}]
    assert run_md_runs(run, backend=_backend("A10G", FakeFn(), monkeypatch)) == 1
    fn = FakeFn()
    assert run_md_runs(run, backend=_backend("H100", fn, monkeypatch)) == 1  # computed again, on the H100
    assert fn.options["gpu"] == "H100"
    assert run_md(licl(5.1), 600, 40000, gpu="H100", backend=_backend("H100", FakeFn(), monkeypatch))["cached"]
    assert run_md(licl(5.1), 600, 40000, gpu="A10G", backend=_backend("H100", FakeFn(), monkeypatch))["cached"]
    with pytest.raises(ValueError, match="H100"):  # a new run is never cached under a GPU it did not run on
        run_md(licl(5.3), 600, 40000, gpu="A10G", backend=_backend("H100", FakeFn(), monkeypatch))


def test_single_md_run_goes_to_the_md_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    fn = FakeFn()
    run_md(licl(5.1), 600, 40000, backend=_backend(None, fn, monkeypatch))
    assert fn.options == {"gpu": config.MODAL_MD_GPU, "timeout": 3600}


def test_legacy_runs_are_read_and_missing_ones_run_on_the_new_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    n_steps = round(config.MD_SCREEN_PS * 1000 / config.MD_TIMESTEP_FS)
    parent = {"id": "mp-22905", "formula": "LiCl", "kind": "parent", "atoms": licl(5.1)}
    old = {"id": "c1", "formula": "LiCl", "kind": "candidate", "parent": "mp-22905", "atoms": licl(5.15)}
    new = {"id": "c2", "formula": "LiCl", "kind": "candidate", "parent": "mp-22905", "atoms": licl(5.2)}
    run_md_runs([{"atoms": j["atoms"], "temperature_K": config.MD_SCREEN_TEMPERATURE_K, "n_steps": n_steps, "seed": s}
                 for j in (parent, old) for s in range(config.MD_SCREEN_SEEDS)],
                backend=_backend("A10G", FakeFn(), monkeypatch))
    jobs = with_md_gpu([parent, old, new], gpu="H100")
    assert [j["md_gpu"] for j in jobs] == ["A10G", "A10G", "H100"]
    todo = md_runs_to_compute(jobs, gpu="H100")
    assert [(r["id"], r["gpu"]) for r in todo] == [("c2", "H100")] * config.MD_SCREEN_SEEDS  # parent never rerun
    fn = FakeFn()
    rows = md_verdicts(md_screen(jobs, backend=_backend("H100", fn, monkeypatch)))
    assert len(fn.spawned) == config.MD_SCREEN_SEEDS and fn.options["gpu"] == "H100"
    assert [r["md_gpu"] for r in rows] == ["A10G", "A10G", "H100"]
    assert rows[2]["vs_parent"] is not None  # H100 candidate compared with its A10G parent
