"""Simulation backend: local NVIDIA GPU or Modal, behind one interface (SPEC 2).

Callers use relax_structures / run_md; results are cached on disk and a
relaxation already in cache is never recomputed. This module never imports
fairchem: the local backend goes through sim/uma.py, the Modal one calls the
functions deployed by modal_app/uma_app.py.
"""

from __future__ import annotations

from typing import Iterator

from autolab import config
from autolab.sim.serialize import atoms_from_dict, atoms_key, atoms_to_dict
from autolab.store.cache import JsonCache


class BudgetExceeded(RuntimeError):
    """Raised before any computation when a run would exceed its limit."""


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

    def _fn(self, name: str):
        import modal

        return modal.Function.from_name(config.MODAL_APP, name)

    def relax_chunks(self, chunks: list[list[dict]], precision: str, fmax: float, steps: int) -> Iterator[list[dict]]:
        kwargs = {"precision": precision, "fmax": fmax, "steps": steps}
        yield from self._fn("relax_chunk").map(chunks, kwargs=kwargs)

    def md(self, atoms: dict, precision: str, **kwargs) -> dict:
        return self._fn("md_run").remote(atoms, precision=precision, **kwargs)


def get_backend(name: str | None = None):
    name = name or config.SIM_BACKEND
    if name == "local":
        return LocalBackend()
    if name == "modal":
        return ModalBackend()
    raise ValueError(f"unknown SIM_BACKEND {name!r} (expected 'modal' or 'local')")


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
) -> list[dict]:
    """Relax structures (pymatgen, ASE or atoms dicts) with UMA, using the disk cache.

    Results come back in input order with a 'cache_key' and 'cached' flag.
    Raises BudgetExceeded before computing anything if more than `max_new`
    relaxations are missing from the cache.
    """
    cache = cache or JsonCache(config.RELAX_CACHE_DIR)
    dicts = [_as_atoms_dict(s) for s in structures]
    settings = {"model": config.UMA_MODEL, "precision": precision, "fmax": fmax, "steps": steps}
    keys = [atoms_key(d, **settings) for d in dicts]

    missing: dict[str, dict] = {}
    for key, d in zip(keys, dicts):
        if cache.get(key) is None:
            missing.setdefault(key, d)
    if len(missing) > max_new:
        raise BudgetExceeded(f"{len(missing)} new relaxations requested, limit is {max_new} (MAX_RELAXATIONS_PER_RUN)")

    fresh = set()
    if missing:
        backend = backend or get_backend()
        todo = list(missing.items())
        n = config.MODAL_RELAX_CHUNK
        chunks = [todo[i:i + n] for i in range(0, len(todo), n)]
        results = backend.relax_chunks([[d for _, d in c] for c in chunks], precision, fmax, steps)
        for chunk, out in zip(chunks, results):
            for (key, _), res in zip(chunk, out):
                cache.set(key, {**res, "settings": settings})  # saved as soon as each chunk returns
                fresh.add(key)

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
