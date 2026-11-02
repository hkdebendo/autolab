"""Vacancy migration barriers of a structure (memristor domain): which hops to compute, the lowest barrier, the
comparison with the parent. The NEB itself runs on the GPU backend (sim/backend.run_nebs, sim/neb.py)."""

from __future__ import annotations

from pymatgen.core import Structure

from autolab import config


def compact_supercell(structure: Structure) -> Structure:
    """The smallest supercell (sim.neb.supercell_for) among the given, primitive and conventional cells: the same
    crystal, fewer atoms to move (a cheaper NEB)."""
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    from autolab.sim.neb import supercell_for

    cells = [structure]
    try:
        sga = SpacegroupAnalyzer(structure, symprec=0.05)
        cells += [sga.get_primitive_standard_structure(), sga.get_conventional_standard_structure()]
    except Exception:  # no symmetry found: the given cell
        pass
    return min((supercell_for(c) for c in cells), key=len)


def hop_items(structure: Structure, near: str | None = None, species: str = config.MEMRISTOR_MOBILE_ION,
              max_hops: int = config.NEB_MAX_HOPS) -> tuple[list[dict], dict]:
    """The NEB jobs of a relaxed structure: its supercell (sim.neb.supercell_for) and its distinct hops (next to the
    dopant `near` when given, else the shortest ones). Returns (items for run_nebs, description)."""
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.neb import vacancy_hops
    from autolab.sim.serialize import atoms_to_dict

    sc = compact_supercell(structure)
    hops = vacancy_hops(sc, species=species, near=near, max_hops=max_hops)
    if near and not hops:  # no O bonded to the dopant within the cutoff: the shortest hops of the cell
        hops = vacancy_hops(sc, species=species, max_hops=max_hops)
    atoms = atoms_to_dict(AseAtomsAdaptor.get_atoms(sc))
    return ([{"atoms": atoms, "i": h["i"], "j": h["j"]} for h in hops],
            {"n_atoms": len(sc), "hops": hops, "near": near})


def lowest_barrier(results: list[dict | None], hops: list[dict]) -> dict:
    """The lowest barrier among the converged hops (None if none converged), with every hop listed."""
    rows = []
    for h, r in zip(hops, results):
        rows.append({"distance_A": h["distance_A"], "barrier_eV": None if r is None else round(r["barrier_eV"], 3),
                     "converged": bool(r and r["converged"] and r["endpoints_converged"]),
                     "profile_eV": None if r is None else [round(e, 3) for e in r["energies_eV"]],
                     "cached": None if r is None else r.get("cached")})
    ok = [x for x in rows if x["converged"]]
    best = min(ok, key=lambda x: x["barrier_eV"]) if ok else None
    return {"barrier_eV": best["barrier_eV"] if best else None, "best_hop": best, "hops": rows,
            "converged_hops": len(ok)}


def vs_parent(ea: float | None, ea_parent: float | None, tol: float = config.MEMRISTOR_EA_SIGNIFICANT_EV) -> dict:
    """Barrier against the parent's, decided by the code: a difference within `tol` is "comparable"."""
    if ea is None or ea_parent is None:
        return {"verdict": "undetermined", "difference_eV": None}
    d = round(ea - ea_parent, 3)
    verdict = "comparable" if abs(d) <= tol else ("lower" if d < 0 else "higher")
    return {"verdict": verdict, "difference_eV": d, "tolerance_eV": tol}


def arrhenius_hop_rate(ea: float, temperature_K: float, attempt_hz: float = 1e13) -> float:
    """Hops per second of one vacancy over a barrier `ea` (information only: a single hop, no field)."""
    import math

    return attempt_hz * math.exp(-ea / (8.617333262e-5 * temperature_K))
