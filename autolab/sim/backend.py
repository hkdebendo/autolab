"""Simulation backend: local NVIDIA GPU, Modal or Kaggle, behind one interface (SPEC 2).

Callers use relax_structures / run_md; results are cached on disk and a
relaxation already in cache is never recomputed. This module never imports
fairchem: the local backend goes through sim/uma.py, the Modal one calls the
functions deployed by modal_app/uma_app.py, the Kaggle one sends batches to a Kaggle
notebook (sim/kaggle_gpu.py).
"""

from __future__ import annotations

from typing import Iterator

from autolab import config
from autolab.sim.serialize import atoms_from_dict, atoms_key, atoms_to_dict
from autolab.store.cache import JsonCache


class BudgetExceeded(RuntimeError):
    """Raised before any computation when a run would exceed its limit."""


class RelaxBudget:
    """New (uncached) relaxations allowed for a whole run, shared by all relax_structures calls."""

    def __init__(self, max_new: int = config.MAX_RELAXATIONS_PER_RUN):
        self.max_new = max_new
        self.used = 0

    @property
    def remaining(self) -> int:
        return self.max_new - self.used


class LocalBackend:
    """Runs UMA in this process (machine with an NVIDIA GPU, e.g. Colab)."""

    name = "local"

    def relax_chunks(self, chunks: list[list[dict]], precision: str, fmax: float, steps: int) -> Iterator[list[dict]]:
        from autolab.sim import uma
        from autolab.sim.relax import relax

        calc = uma.get_calculator(precision)
        for chunk in chunks:
            yield [relax(atoms_from_dict(d), calc, fmax, steps) for d in chunk]

    def md(self, atoms: dict, precision: str, **kwargs) -> dict:
        from autolab.sim import uma
        from autolab.sim.md import run_md

        return run_md(atoms_from_dict(atoms), uma.get_calculator(precision), **kwargs)


class ModalBackend:
    """Calls the GPU functions deployed on Modal (modal deploy modal_app/uma_app.py)."""

    name = "modal"

    def __init__(self, gpu: str | None = None, md_timeout_s: int | None = None, poll_s: float = 10.0):
        self.gpu = gpu
        self.md_timeout_s = md_timeout_s
        self.poll_s = poll_s
        self.errors: dict[int, str] = {}

    def _fn(self, name: str):
        import modal

        return modal.Function.from_name(config.MODAL_APP, name)

    def relax_chunks(self, chunks: list[list[dict]], precision: str, fmax: float, steps: int) -> Iterator[list[dict]]:
        kwargs = {"precision": precision, "fmax": fmax, "steps": steps}
        yield from self._fn("relax_chunk").map(chunks, kwargs=kwargs)

    def md(self, atoms: dict, precision: str, **kwargs) -> dict:
        return self._fn("md_run").remote(atoms, precision=precision, **kwargs)

    def md_batch_iter(self, items: list[dict], precision: str) -> Iterator[tuple[int, dict | None]]:
        """All MD runs at once, one container each ({"atoms", "temperature_K", "n_steps", "seed"}); yields
        (index, result) as each run ends, None for a failed run (error in self.errors). No retry: a refused
        call (quota, payment) stops everything and cancels what was already sent."""
        import time

        import modal.exception

        opts = {"max_containers": len(items), "gpu": self.gpu or config.MODAL_MD_GPU,
                "timeout": self.md_timeout_s or config.MODAL_MD_TIMEOUT}
        fn = self._fn("md_run").with_options(**opts)
        calls = {}
        try:
            for i, it in enumerate(items):
                calls[i] = fn.spawn(it["atoms"], precision=precision, temperature_K=it["temperature_K"],
                                    n_steps=it["n_steps"], seed=it.get("seed", 0))
        except Exception:
            for c in calls.values():
                c.cancel(terminate_containers=True)
            raise
        while calls:
            for i, call in list(calls.items()):
                try:
                    res = call.get(timeout=0)
                except modal.exception.FunctionTimeoutError as e:
                    res, self.errors[i] = None, f"function timeout: {e}"[:300]
                except (modal.exception.TimeoutError, TimeoutError):
                    continue  # still running
                except Exception as e:
                    res, self.errors[i] = None, f"{type(e).__name__}: {e}"[:300]
                del calls[i]
                yield i, res
            if calls:
                time.sleep(self.poll_s)


def get_backend(name: str | None = None):
    name = name or config.SIM_BACKEND
    if name == "local":
        return LocalBackend()
    if name == "modal":
        return ModalBackend()
    if name == "kaggle":
        from autolab.sim.kaggle_gpu import KaggleBackend

        return KaggleBackend()
    raise ValueError(f"unknown SIM_BACKEND {name!r} (expected 'modal', 'local' or 'kaggle')")


def _as_atoms_dict(obj) -> dict:
    if isinstance(obj, dict):
        return obj
    from ase import Atoms

    if isinstance(obj, Atoms):
        return atoms_to_dict(obj)
    from pymatgen.io.ase import AseAtomsAdaptor

    return atoms_to_dict(AseAtomsAdaptor.get_atoms(obj))


def relax_structures(
    structures: list,
    precision: str = config.UMA_PRECISION_ENERGY,
    backend=None,
    fmax: float = config.RELAX_FMAX,
    steps: int = config.RELAX_STEPS,
    max_new: int = config.MAX_RELAXATIONS_PER_RUN,
    cache: JsonCache | None = None,
    budget: RelaxBudget | None = None,
) -> list[dict]:
    """Relax structures (pymatgen, ASE or atoms dicts) with UMA, using the disk cache.

    Results come back in input order with a 'cache_key' and 'cached' flag.
    Raises BudgetExceeded before computing anything if more than `max_new`
    relaxations (or the run budget's remaining ones) are missing from the cache.
    """
    cache = cache or JsonCache(config.RELAX_CACHE_DIR)
    dicts = [_as_atoms_dict(s) for s in structures]
    settings = {"model": config.UMA_MODEL, "precision": precision, "fmax": fmax, "steps": steps}
    keys = [atoms_key(d, **settings) for d in dicts]

    missing: dict[str, dict] = {}
    for key, d in zip(keys, dicts):
        if cache.get(key) is None:
            missing.setdefault(key, d)
    limit = budget.remaining if budget else max_new
    if len(missing) > limit:
        raise BudgetExceeded(f"{len(missing)} new relaxations requested, {limit} left (MAX_RELAXATIONS_PER_RUN)")

    fresh = set()
    if missing:
        if budget:
            budget.used += len(missing)
        backend = backend or get_backend()
        todo = list(missing.items())
        n = config.MODAL_RELAX_CHUNK
        chunks = [todo[i:i + n] for i in range(0, len(todo), n)]
        results = backend.relax_chunks([[d for _, d in c] for c in chunks], precision, fmax, steps)
        failed = []
        for chunk, out in zip(chunks, results):
            for (key, _), res in zip(chunk, out):
                if res is None:  # failed on a remote backend: keep the others, then stop
                    failed.append(key)
                    continue
                cache.set(key, {**res, "settings": settings})  # saved as soon as each chunk returns
                fresh.add(key)
        for _ in results:  # finish the iterator (Modal's map otherwise warns when it is closed half-read)
            pass
        if failed:
            raise RuntimeError(f"{len(failed)} of {len(missing)} relaxations failed on the {getattr(backend, 'name', 'remote')} backend")

    return [{**cache.get(k), "cache_key": k, "cached": k not in fresh} for k in keys]


def run_md(atoms, temperature_K: float, n_steps: int, precision: str = config.UMA_PRECISION_MD,
           backend=None, seed: int = 0, cache: JsonCache | None = None) -> dict:
    """Molecular dynamics through the backend, cached by structure and settings."""
    cache = cache or JsonCache(config.CACHE_DIR / "md")
    d = _as_atoms_dict(atoms)
    settings = {"model": config.UMA_MODEL, "precision": precision, "T": temperature_K, "n_steps": n_steps, "seed": seed}
    key = atoms_key(d, **settings)
    cached = cache.get(key)
    if cached is not None:
        return {**cached, "cached": True}
    backend = backend or get_backend()
    res = backend.md(d, precision=precision, temperature_K=temperature_K, n_steps=n_steps, seed=seed)
    cache.set(key, {**res, "settings": settings})
    return {**res, "settings": settings, "cached": False}


def run_md_batch(atoms_list: list, temperature_K: float, n_steps: int, precision: str = config.UMA_PRECISION_MD,
                 backend=None, seed: int = 0, cache: JsonCache | None = None) -> None:
    """Fill the MD cache for several structures in one backend call when the backend can batch (Kaggle).

    Other backends are left alone: run_md computes each structure when it is asked for.
    """
    run_md_runs([{"atoms": a, "temperature_K": temperature_K, "n_steps": n_steps, "seed": seed} for a in atoms_list],
                precision, backend, cache)


def run_md_runs(runs: list[dict], precision: str = config.UMA_PRECISION_MD, backend=None,
                cache: JsonCache | None = None) -> int:
    """Fill the MD cache for runs that each have their own settings ({"atoms", "temperature_K", "n_steps",
    "seed"}) in one backend call when the backend can batch (Kaggle: one session). Returns the number sent."""
    cache = cache or JsonCache(config.CACHE_DIR / "md")
    backend = backend or get_backend()
    if not hasattr(backend, "md_batch") and not hasattr(backend, "md_batch_iter"):
        return 0
    missing: dict[str, tuple[dict, dict]] = {}
    for r in runs:
        d = _as_atoms_dict(r["atoms"])
        settings = {"model": config.UMA_MODEL, "precision": precision, "T": r["temperature_K"],
                    "n_steps": r["n_steps"], "seed": r.get("seed", 0)}
        key = atoms_key(d, **settings)  # the key of run_md, which then reads the cache
        if cache.get(key) is None:
            missing.setdefault(key, (d, settings))
    if not missing:
        return 0
    items = [{"atoms": d, "seed": s["seed"], "temperature_K": s["T"], "n_steps": s["n_steps"]}
             for d, s in missing.values()]
    entries = list(missing.items())
    if hasattr(backend, "md_batch_iter"):  # Modal: runs in parallel, each saved as soon as it ends
        for i, res in backend.md_batch_iter(items, precision=precision):
            if res is not None:
                key, (_, settings) = entries[i]
                cache.set(key, {**res, "settings": settings})
        return len(missing)
    for (key, (_, settings)), res in zip(entries, backend.md_batch(items, precision=precision)):
        if res is not None:
            cache.set(key, {**res, "settings": settings})
    return len(missing)


def prefetch(relax: list = (), md: list = (), temperature_K: float | None = None, n_steps: int | None = None,
             relax_precision: str = config.UMA_PRECISION_ENERGY, md_precision: str = config.UMA_PRECISION_MD,
             fmax: float = config.RELAX_FMAX, steps: int = config.RELAX_STEPS, seed: int = 0, backend=None,
             budget: RelaxBudget | None = None, max_new: int = config.MAX_RELAXATIONS_PER_RUN) -> dict:
    """Fill the relaxation and MD caches in one backend call when it can batch both (Kaggle: one session).

    Keys and stored results are those of relax_structures and run_md, which then read the cache.
    Returns the numbers sent; other backends are left alone (nothing sent).
    """
    backend = backend or get_backend()
    if not hasattr(backend, "batch"):
        return {"relax": 0, "md": 0}
    rcache, mcache = JsonCache(config.RELAX_CACHE_DIR), JsonCache(config.CACHE_DIR / "md")
    rset = {"model": config.UMA_MODEL, "precision": relax_precision, "fmax": fmax, "steps": steps}
    mset = {"model": config.UMA_MODEL, "precision": md_precision, "T": temperature_K, "n_steps": n_steps, "seed": seed}
    r_missing: dict[str, dict] = {}
    for s in relax:
        d = _as_atoms_dict(s)
        key = atoms_key(d, **rset)
        if rcache.get(key) is None:
            r_missing.setdefault(key, d)
    m_missing: dict[str, dict] = {}
    for a in md:
        d = _as_atoms_dict(a)
        key = atoms_key(d, **mset)
        if mcache.get(key) is None:
            m_missing.setdefault(key, d)
    limit = budget.remaining if budget else max_new
    if len(r_missing) > limit:
        raise BudgetExceeded(f"{len(r_missing)} new relaxations requested, {limit} left (MAX_RELAXATIONS_PER_RUN)")
    if not r_missing and not m_missing:
        return {"relax": 0, "md": 0}
    if budget:
        budget.used += len(r_missing)
    r_out, m_out = backend.batch(
        list(r_missing.values()), {"precision": relax_precision, "fmax": fmax, "steps": steps},
        [{"atoms": d, "seed": seed} for d in m_missing.values()],
        {"precision": md_precision, "temperature_K": temperature_K, "n_steps": n_steps})
    for key, res in zip(r_missing, r_out):
        if res is not None:
            rcache.set(key, {**res, "settings": rset})
    for key, res in zip(m_missing, m_out):
        if res is not None:
            mcache.set(key, {**res, "settings": mset})
    return {"relax": len(r_missing), "md": len(m_missing)}
