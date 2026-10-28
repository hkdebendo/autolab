"""Langevin NVT molecular dynamics (SPEC 5.10)."""

from __future__ import annotations

import math
import time

import numpy as np
from ase import Atoms, units
from ase.constraints import FixCom
from ase.md.langevin import Langevin
from ase.md.velocitydistribution import thermalize_momenta

from autolab import config


def supercell_reps(atoms: Atoms, min_length: float = config.MD_MIN_LENGTH) -> tuple[int, int, int]:
    """Repetitions per axis so that every side is at least `min_length` Angstrom."""
    return tuple(max(1, math.ceil(min_length / length)) for length in atoms.cell.lengths())


def run_md(
    atoms: Atoms,
    calc,
    temperature_K: float,
    n_steps: int,
    species: str = "Li",
    timestep_fs: float = config.MD_TIMESTEP_FS,
    friction_per_fs: float = config.MD_FRICTION_PER_FS,
    record_every: int = config.MD_RECORD_EVERY,
    min_length: float = config.MD_MIN_LENGTH,
    seed: int = 0,
    trajectory_path: str | None = None,
) -> dict:
    """Run NVT dynamics on a supercell and record unwrapped positions of `species`."""
    reps = supercell_reps(atoms, min_length)
    sc = atoms.repeat(reps)
    sc.calc = calc
    sc.set_constraint(FixCom())
    rng = np.random.default_rng(seed)
    thermalize_momenta(sc, temperature_K, rng=rng)
    dyn = Langevin(
        sc,
        timestep=timestep_fs * units.fs,
        temperature_K=temperature_K,
        friction=friction_per_fs / units.fs,
        fixcm=False,
        rng=rng,
    )
    idx = [i for i, s in enumerate(sc.get_chemical_symbols()) if s == species]
    frames: list[np.ndarray] = []
    dyn.attach(lambda: frames.append(sc.get_positions()[idx].copy()), interval=record_every)
    if trajectory_path:
        from ase.io.trajectory import Trajectory

        traj = Trajectory(trajectory_path, "w", sc)
        dyn.attach(traj.write, interval=record_every)

    t0 = time.perf_counter()
    dyn.run(n_steps)
    elapsed = time.perf_counter() - t0
    return {
        "species": species,
        "temperature_K": temperature_K,
        "n_steps": n_steps,
        "n_atoms": len(sc),
        "reps": list(reps),
        "dt_record_fs": timestep_fs * record_every,
        "positions": np.round(np.array(frames), 3).tolist(),  # 0.001 A is plenty; halves the JSON size
        "seconds": round(elapsed, 2),
        "ms_per_step": round(1000 * elapsed / max(n_steps, 1), 2),
        "trajectory": trajectory_path,
    }
