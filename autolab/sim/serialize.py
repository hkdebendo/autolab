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


def atoms_key(d: dict, **settings) -> str:
    """Fingerprint of a structure plus the calculation settings (model, precision, ...)."""
    atoms = atoms_from_dict(d)
    payload = {
        "numbers": d["numbers"],
        "cell": [[round(x, 5) for x in row] for row in d["cell"]],
        "frac": [[round(x % 1.0, 5) % 1.0 for x in row] for row in atoms.get_scaled_positions(wrap=True).tolist()],
        "settings": settings,
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()
