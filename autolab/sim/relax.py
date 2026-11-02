"""Structure relaxation with ASE (SPEC 5.6): FIRE on positions and cell."""

from __future__ import annotations

import time

from ase import Atoms
from ase.filters import FrechetCellFilter
from ase.optimize import FIRE

from autolab import config
from autolab.sim.serialize import atoms_to_dict


def _snapshot(atoms: Atoms) -> dict:
    return {"positions": [[round(float(x), 3) for x in p] for p in atoms.get_positions()],
            "cell": [[round(float(x), 4) for x in v] for v in atoms.cell.array],
            "energy_per_atom": round(float(atoms.get_potential_energy()) / len(atoms), 5)}


def _thin(path: list, n: int) -> list:
    """At most n frames of a path, evenly spaced, the first and the last kept."""
    if len(path) <= n or n < 2:
        return path
    return [path[round(i * (len(path) - 1) / (n - 1))] for i in range(n)]


def relax(atoms: Atoms, calc, fmax: float = config.RELAX_FMAX, steps: int = config.RELAX_STEPS,
          frames: int = config.RELAX_TRAJECTORY_FRAMES) -> dict:
    """Relax positions and cell; never mark a non-converged run as converged. `frames` snapshots of the path
    (positions, cell, energy), evenly spaced, are kept for display ("trajectory")."""
    atoms = atoms.copy()
    atoms.calc = calc
    opt = FIRE(FrechetCellFilter(atoms), logfile=None)
    path = []
    if frames:
        opt.attach(lambda: path.append(_snapshot(atoms)), interval=1)
    t0 = time.perf_counter()
    converged = bool(opt.run(fmax=fmax, steps=steps))
    energy = float(atoms.get_potential_energy())
    return {
        "trajectory": _thin(path, frames),
        "formula": atoms.get_chemical_formula(mode="metal"),
        "energy": energy,
        "energy_per_atom": energy / len(atoms),
        "converged": converged,
        "steps": int(opt.nsteps),
        "seconds": round(time.perf_counter() - t0, 2),
        "atoms": atoms_to_dict(atoms),
    }
