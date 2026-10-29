"""Modal backend (sim/backend.py ModalBackend): fake Modal functions, no network, no GPU, no cost."""

import modal.exception
import pytest

from autolab import config
from autolab.sim.backend import ModalBackend, run_md, run_md_runs

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
