"""Structure relaxation with ASE (SPEC 5.6): FIRE on positions and cell."""

from __future__ import annotations

import time

from ase import Atoms
from ase.filters import FrechetCellFilter
from ase.optimize import FIRE

from autolab import config
from autolab.sim.serialize import atoms_to_dict


def relax(atoms: Atoms, calc, fmax: float = config.RELAX_FMAX, steps: int = config.RELAX_STEPS) -> dict:
    """Relax positions and cell; never mark a non-converged run as converged."""
    atoms = atoms.copy()
    atoms.calc = calc
    opt = FIRE(FrechetCellFilter(atoms), logfile=None)
    t0 = time.perf_counter()
    converged = bool(opt.run(fmax=fmax, steps=steps))
    energy = float(atoms.get_potential_energy())
    return {
        "formula": atoms.get_chemical_formula(mode="metal"),
        "energy": energy,
        "energy_per_atom": energy / len(atoms),
        "converged": converged,
        "steps": int(opt.nsteps),
        "seconds": round(time.perf_counter() - t0, 2),
        "atoms": atoms_to_dict(atoms),
    }
