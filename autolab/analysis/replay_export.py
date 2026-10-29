"""Light files for the replay visuals (roadmap, production): 3D Li diffusion, MSD curves, relaxed structures.

Built from the caches only (never computes): the MD cache holds the unwrapped Li positions every 10 fs and the MSD
of every other element; the framework is drawn at its starting positions (only its MSD is recorded).
"""

from __future__ import annotations

import numpy as np

from autolab import config


def structure_view(atoms: dict, highlight: str | None = None) -> dict:
    """A crystal for the browser: cell, symbols, positions (A, 3 decimals), and the substituted element."""
    return {"cell": np.round(np.array(atoms["cell"]), 4).tolist(),
            "symbols": _symbols(atoms["numbers"]),
            "positions": np.round(np.array(atoms["positions"]), 3).tolist(),
            "highlight": highlight}


def _symbols(numbers) -> list[str]:
    from ase.data import chemical_symbols

    return [chemical_symbols[z] for z in numbers]


def md_view(atoms: dict, md: dict, n_frames: int = config.REPLAY_MD_FRAMES, n_curve: int = 200) -> dict:
    """One MD run for the browser: framework (static), Li frames wrapped into the supercell and subsampled,
    MSD of Li (from the first frame) and of each framework element against time."""
    from autolab.sim.serialize import atoms_from_dict

    sc = atoms_from_dict(atoms).repeat(md["reps"])
    symbols = np.array(sc.get_chemical_symbols())
    species = md["species"]
    cell = sc.cell.array
    pos = np.array(md["positions"])  # (frames, n_Li, 3), unwrapped
    keep = np.unique(np.linspace(0, len(pos) - 1, min(n_frames, len(pos))).round().astype(int))
    frac = (pos[keep] @ np.linalg.inv(cell)) % 1.0
    wrapped = frac @ cell
    t_ps = np.arange(len(pos)) * md["dt_record_fs"] / 1000.0
    msd = ((pos - pos[0]) ** 2).sum(axis=2).mean(axis=1)
    pick = np.unique(np.linspace(0, len(pos) - 1, min(n_curve, len(pos))).round().astype(int))
    framework = {el: np.round(np.array(v)[pick], 3).tolist() for el, v in md.get("framework_msd", {}).items()
                 if len(v) == len(pos)}
    return {"cell": np.round(cell, 4).tolist(), "reps": md["reps"], "species": species,
            "framework": {"symbols": symbols[symbols != species].tolist(),
                          "positions": np.round(sc.get_positions()[symbols != species], 2).tolist()},
            "frame_fs": float(keep[1] - keep[0]) * md["dt_record_fs"] if len(keep) > 1 else md["dt_record_fs"],
            "frames": np.round(wrapped, 2).tolist(),
            "curve": {"t_ps": np.round(t_ps[pick], 3).tolist(), "msd_li_A2": np.round(msd[pick], 3).tolist(),
                      "msd_framework_A2": framework},
            "temperature_K": md["temperature_K"], "n_atoms": md["n_atoms"], "gpu": md.get("gpu")}
