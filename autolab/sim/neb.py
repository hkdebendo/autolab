"""Migration barrier of a vacancy (nudged elastic band, climbing image), with any ASE calculator.

A hop moves one ion of `species` into a vacant neighbouring site: the initial cell lacks the ion at site i, the final
cell lacks it at site j (the ion of j sits at i). Both end points are relaxed at fixed cell, then the path between
them; the barrier is the highest image above the lower end point (the rate-limiting step of a back-and-forth walk).
The vacancy is neutral (no charge can be set on a machine-learned potential's cell): its electrons stay in the cell.
Only autolab/sim/uma.py brings UMA; tests use EMT.
"""

from __future__ import annotations

import time

from typing import TYPE_CHECKING

import numpy as np
from ase import Atoms

from autolab import config

if TYPE_CHECKING:  # pymatgen is not in the GPU image: only the hop choice (on the caller's side) uses it
    from pymatgen.core import Structure


def supercell_for(structure: "Structure", min_length: float = config.NEB_MIN_LENGTH) -> Structure:
    """The cell repeated until every perpendicular width reaches min_length (vacancy images far from each other)."""
    lat = structure.lattice
    vol = lat.volume
    widths = [vol / np.linalg.norm(np.cross(lat.matrix[(k + 1) % 3], lat.matrix[(k + 2) % 3])) for k in range(3)]
    reps = [max(1, int(np.ceil(min_length / w - 1e-6))) for w in widths]
    sc = structure.copy()
    sc.make_supercell(reps)
    return sc


def vacancy_hops(structure: "Structure", species: str = "O", near: str | None = None,
                 max_hops: int = config.NEB_MAX_HOPS, cutoff: float = config.NEB_HOP_CUTOFF_A,
                 near_cutoff: float = config.NEB_NEAR_CUTOFF_A) -> list[dict]:
    """Distinct nearest-neighbour hops of `species` (site pairs closer than `cutoff`), shortest first. With `near`
    (a substituted element), only hops between two ions bonded to one atom of `near`: the hops the dopant changes.
    Distinct = different symmetry classes of the two sites (or, near a dopant, different local surroundings)."""
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    sites = [i for i, s in enumerate(structure) if s.specie.symbol == species]
    if near:
        dopants = [i for i, s in enumerate(structure) if s.specie.symbol == near]
        bonded = {n.index for d in dopants for n in structure.get_neighbors(structure[d], near_cutoff)
                  if n.specie.symbol == species}
        sites = [i for i in sites if i in bonded]
        if not sites:
            return []
    try:
        equiv = SpacegroupAnalyzer(structure, symprec=0.05).get_symmetry_dataset().equivalent_atoms
    except Exception:  # symmetry not found: every site its own class
        equiv = list(range(len(structure)))
    seen, hops = set(), []
    for i in sites:
        for n in structure.get_neighbors(structure[i], cutoff):
            j = n.index
            if j == i or structure[j].specie.symbol != species or (near and j not in sites):
                continue
            d = round(float(n.nn_distance), 2)
            if near:  # local surroundings: the elements around the hop's midpoint
                mid = (structure[i].coords + n.coords) / 2
                env = tuple(sorted(x.specie.symbol for x in structure.get_sites_in_sphere(mid, 2.4)))
                key = (d, env)
            else:
                key = (min(equiv[i], equiv[j]), max(equiv[i], equiv[j]), d)
            if key in seen:
                continue
            seen.add(key)
            hops.append({"i": int(i), "j": int(j), "distance_A": d})
    return sorted(hops, key=lambda h: h["distance_A"])[:max_hops]


def endpoints(structure, i: int, j: int) -> tuple[Atoms, Atoms]:
    """Initial cell (ion i removed) and final cell (ion j moved onto site i), same atom order. `structure`: ASE
    Atoms or a pymatgen Structure."""
    if isinstance(structure, Atoms):
        atoms = structure
    else:
        from pymatgen.io.ase import AseAtomsAdaptor

        atoms = AseAtomsAdaptor.get_atoms(structure)
    keep = [k for k in range(len(atoms)) if k != i]
    initial = atoms[keep]
    final = initial.copy()
    jj = keep.index(j)
    # the image of site i closest to j (the hop may cross the cell boundary)
    d = atoms.get_distance(j, i, mic=True, vector=True)
    final.positions[jj] = atoms.positions[j] + d
    return initial, final


def run_neb(initial: Atoms, final: Atoms, calc, n_images: int = config.NEB_IMAGES, fmax: float = config.NEB_FMAX,
            steps: int = config.NEB_STEPS, endpoint_fmax: float = config.RELAX_FMAX,
            endpoint_steps: int = config.RELAX_STEPS) -> dict:
    """Relax both end points (fixed cell), then a climbing-image NEB between them; JSON-serialisable result."""
    from ase.mep import NEB
    from ase.optimize import FIRE

    t0 = time.perf_counter()
    ends = []
    for a in (initial.copy(), final.copy()):
        a.calc = calc
        opt = FIRE(a, logfile=None)
        ok = bool(opt.run(fmax=endpoint_fmax, steps=endpoint_steps))
        ends.append((a, ok, float(a.get_potential_energy())))
    images = [ends[0][0]] + [ends[0][0].copy() for _ in range(n_images)] + [ends[1][0]]
    neb = NEB(images, climb=True, allow_shared_calculator=True)
    try:
        neb.interpolate(method="idpp", mic=True)
    except Exception:  # IDPP failed on an odd path: plain linear interpolation
        neb.interpolate(mic=True)
    for im in images[1:-1]:
        im.calc = calc
    opt = FIRE(neb, logfile=None)
    converged = bool(opt.run(fmax=fmax, steps=steps))
    energies = [float(im.get_potential_energy()) for im in images[1:-1]]
    energies = [ends[0][2]] + energies + [ends[1][2]]
    top = max(energies)
    return {"barrier_eV": top - min(ends[0][2], ends[1][2]), "forward_eV": top - ends[0][2],
            "backward_eV": top - ends[1][2], "reaction_eV": ends[1][2] - ends[0][2],
            "energies_eV": [e - ends[0][2] for e in energies], "converged": converged,
            "endpoints_converged": ends[0][1] and ends[1][1], "steps": int(opt.nsteps), "n_images": n_images,
            "n_atoms": len(initial), "seconds": round(time.perf_counter() - t0, 1)}


def vacancy_barrier(atoms: dict, i: int, j: int, calc, **kwargs) -> dict:
    """Barrier of the hop i -> j in a perfect supercell given as an atoms dict (what the GPU function receives;
    ASE only, no pymatgen)."""
    from autolab.sim.serialize import atoms_from_dict

    perfect = atoms_from_dict(atoms)
    initial, final = endpoints(perfect, i, j)
    return {**run_neb(initial, final, calc, **kwargs), "hop": [int(i), int(j)],
            "hop_distance_A": round(float(perfect.get_distance(i, j, mic=True)), 3)}
