"""S-S bond detector (SPEC 5.3): UMA is unreliable on polysulfides."""

from __future__ import annotations

import numpy as np
from ase import Atoms
from ase.neighborlist import neighbor_list
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

from autolab import config


def has_ss_bonds(atoms: Atoms | Structure, cutoff: float = config.SS_BOND_CUTOFF) -> bool:
    """True if two S atoms are closer than `cutoff` (Angstrom) in a compound.

    Elemental sulfur (S8 rings) is ignored: only compounds are flagged.
    """
    if isinstance(atoms, Structure):
        atoms = AseAtomsAdaptor.get_atoms(atoms)
    symbols = np.array(atoms.get_chemical_symbols())
    if set(symbols) != {"S"} and "S" in symbols:
        i, j = neighbor_list("ij", atoms, cutoff)
        return bool(np.any((symbols[i] == "S") & (symbols[j] == "S")))
    return False
