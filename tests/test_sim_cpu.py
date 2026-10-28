"""CPU tests for sim/ and analysis/diffusion.py: mechanics only, no UMA (cheap ASE calculators)."""

from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.build import bulk
from ase.calculators.emt import EMT

from autolab.analysis.diffusion import diffusion_coefficient, msd
from autolab.sim import backend as sim_backend
from autolab.sim.md import run_md, supercell_reps
from autolab.sim.relax import relax
from autolab.sim.serialize import atoms_from_dict, atoms_key, atoms_to_dict
from autolab.store.cache import JsonCache

ROOT = Path(__file__).resolve().parent.parent


def test_only_uma_module_imports_fairchem():
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "autolab").rglob("*.py")
        if p.name != "uma.py"
        and any(line.lstrip().startswith(("import fairchem", "from fairchem"))
                for line in p.read_text(encoding="utf-8").splitlines())
    ]
    assert offenders == []


def test_serialize_roundtrip_and_key():
    atoms = bulk("Cu", "fcc", a=3.6, cubic=True)
    d = atoms_to_dict(atoms)
    assert np.allclose(atoms_from_dict(d).get_positions(), atoms.get_positions())
    assert atoms_key(d, precision="a") == atoms_key(atoms_to_dict(atoms.copy()), precision="a")
    assert atoms_key(d, precision="a") != atoms_key(d, precision="b")


def test_key_stable_under_float_noise():
    """MP-style 6-decimal coordinates ending in 5 must not flip the key (bug seen between Colab and PC)."""
    cell = [[12.734745, 0, 0], [0, 6.0, 0], [0, 0, 7.5]]
    frac = np.array([[0.737775, 0.954825, 0.0], [0.378425, 0.272405, 0.999999999999]])
    base = Atoms("S2", scaled_positions=frac, cell=cell, pbc=True)
    noisy = base.copy()
    noisy.positions = np.nextafter(noisy.positions, np.inf)
    noisy.cell = np.nextafter(np.array(cell), np.inf)
    assert atoms_key(atoms_to_dict(base), p=1) == atoms_key(atoms_to_dict(noisy), p=1)
    wrapped = base.copy()
    wrapped.set_scaled_positions(np.where(frac > 0.99, 0.0, frac))  # 0.999999999999 ~ 0.0
    assert atoms_key(atoms_to_dict(base), p=1) == atoms_key(atoms_to_dict(wrapped), p=1)


def test_relax_cell_with_emt():
    out = relax(bulk("Cu", "fcc", a=3.8, cubic=True), EMT())
    a = atoms_from_dict(out["atoms"]).cell.lengths()[0]
    assert out["converged"] and out["steps"] > 0
    assert a == pytest.approx(3.59, abs=0.02)  # EMT equilibrium for Cu


def test_supercell_reps():
    assert supercell_reps(bulk("Cu", "fcc", a=3.6, cubic=True)) == (3, 3, 3)
    assert supercell_reps(bulk("Cu", "fcc", a=3.6, cubic=True).repeat((3, 1, 1))) == (1, 3, 3)


def test_md_mechanics_with_emt():
    out = run_md(bulk("Al", "fcc", a=4.05, cubic=True), EMT(), temperature_K=300, n_steps=20, species="Al",
                 record_every=10, min_length=8.0)
    assert out["reps"] == [2, 2, 2] and out["n_atoms"] == 32
    assert np.array(out["positions"]).shape == (3, 32, 3)  # steps 0, 10, 20


def test_diffusion_on_synthetic_random_walk():
    rng = np.random.default_rng(0)
    d_true, dt_fs = 0.5, 10.0  # Angstrom^2/ps
    sigma = np.sqrt(2 * d_true * dt_fs / 1000.0)
    steps = rng.normal(0, sigma, size=(4000, 200, 3))
    pos = np.concatenate([np.zeros((1, 200, 3)), np.cumsum(steps, axis=0)])
    out = diffusion_coefficient(pos, dt_fs)
    assert out["D_A2_per_ps"] == pytest.approx(d_true, rel=0.1)
    assert msd(pos)[0] == 0


class FakeBackend:
    """Records calls; 'relaxes' by returning a fixed energy."""

    def __init__(self):
        self.calls = 0

    def relax_chunks(self, chunks, precision, fmax, steps):
        for chunk in chunks:
            self.calls += len(chunk)
            yield [{"formula": "X", "energy": -1.0, "energy_per_atom": -1.0, "converged": True,
                    "steps": 1, "seconds": 0.0, "atoms": d} for d in chunk]


def test_backend_cache_and_budget(tmp_path):
    cache = JsonCache(tmp_path)
    structures = [bulk("Cu", "fcc", a=a, cubic=True) for a in (3.5, 3.6, 3.6)]
    fake = FakeBackend()
    out = sim_backend.relax_structures(structures, backend=fake, cache=cache)
    assert fake.calls == 2  # duplicate structure relaxed once
    assert [r["cached"] for r in out] == [False, False, False]
    again = sim_backend.relax_structures(structures, backend=fake, cache=cache)
    assert fake.calls == 2 and all(r["cached"] for r in again)
    with pytest.raises(sim_backend.BudgetExceeded):
        sim_backend.relax_structures([bulk("Cu", "fcc", a=a, cubic=True) for a in (3.1, 3.2)],
                                     backend=fake, cache=cache, max_new=1)
    assert fake.calls == 2  # nothing computed when over budget

    budget = sim_backend.RelaxBudget(3)  # one limit for the whole run, across calls
    sim_backend.relax_structures([bulk("Cu", "fcc", a=3.3, cubic=True)] * 2, backend=fake, cache=cache, budget=budget)
    sim_backend.relax_structures([bulk("Cu", "fcc", a=3.4, cubic=True)], backend=fake, cache=cache, budget=budget)
    assert (budget.used, budget.remaining, fake.calls) == (2, 1, 4)
    with pytest.raises(sim_backend.BudgetExceeded):
        sim_backend.relax_structures([bulk("Cu", "fcc", a=a, cubic=True) for a in (3.7, 3.8)],
                                     backend=fake, cache=cache, budget=budget)
    assert fake.calls == 4


def test_unknown_backend():
    with pytest.raises(ValueError):
        sim_backend.get_backend("cloud")
