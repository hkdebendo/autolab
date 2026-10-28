"""JSON-serialisable ASE atoms, shared by the local and Modal backends."""

from __future__ import annotations

import hashlib
import json

from ase import Atoms


def atoms_to_dict(atoms: Atoms) -> dict:
    return {
        "numbers": atoms.get_atomic_numbers().tolist(),
        "cell": atoms.cell.array.tolist(),
        "positions": atoms.get_positions().tolist(),
        "pbc": [bool(p) for p in atoms.pbc],
    }


def atoms_from_dict(d: dict) -> Atoms:
    return Atoms(numbers=d["numbers"], cell=d["cell"], positions=d["positions"], pbc=d["pbc"])


# Binary grid (2**-16): a decimal value with up to 8 digits, as in Materials Project files, is never
# exactly halfway between two grid points, so float noise between machines cannot flip the rounding
# (rounding to 5 decimals did: 0.737775 gave different keys on Colab and on the PC).
KEY_GRID = 2**16


def atoms_key(d: dict, **settings) -> str:
    """Fingerprint of a structure plus the calculation settings (model, precision, ...).

    Stable across machines: cell and wrapped fractional coordinates are snapped to KEY_GRID.
    """
    atoms = atoms_from_dict(d)
    frac = atoms.get_scaled_positions(wrap=True).tolist()
    payload = {
        "numbers": d["numbers"],
        "cell": [[round(x * KEY_GRID) for x in row] for row in d["cell"]],
        "frac": [[round(x * KEY_GRID) % KEY_GRID for x in row] for row in frac],
        "settings": settings,
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()
