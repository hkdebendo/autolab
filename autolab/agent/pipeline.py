"""Filter funnel for one candidate (SPEC 6.1).

generate (rule + neutrality) -> composition already in Materials Project? (then not computed)
-> relax every arrangement with UMA, keep the lowest -> E_hull against UMA-relaxed references
-> GapModel band gap -> S-S bond flag.
The first failed filter rejects the candidate; every step emits an event.
Electrodes (top 20) and molecular dynamics (top 3-5) are not run here yet.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from pymatgen.core import Composition, Structure

from autolab import config
from autolab.agent.events import EventLog


def _default_relax(structures, budget):
    from autolab.sim.backend import relax_structures

    return relax_structures(structures, budget=budget)


def _default_hull_entries(elements, budget):
    from autolab.analysis.stability import uma_reference_entries

    return uma_reference_entries(elements, budget=budget)


def _default_bandgap(structure):
    from autolab.analysis.bandgap import evaluate_bandgap

    return evaluate_bandgap(structure)


def _default_known(formula):
    from autolab.data.mp import known_formulas

    return known_formulas([formula])[formula]


@dataclass
class Tools:
    """Expensive steps, injectable so that tests run without UMA, GapModel or Materials Project."""

    relax: Callable = _default_relax  # (structures, budget) -> list of relax results
    hull_entries: Callable = _default_hull_entries  # (elements, budget) -> (entries, skipped ids)
    bandgap: Callable = _default_bandgap  # (structure) -> evaluate_bandgap dict
    known: Callable = _default_known  # (formula) -> MP materials with that reduced composition
    not_run: list[str] = field(default_factory=lambda: ["electrodes", "molecular_dynamics"])


def _relaxed_structure(res: dict) -> Structure:
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_from_dict

    return AseAtomsAdaptor.get_structure(atoms_from_dict(res["atoms"]))


def lattice(cell) -> dict:
    """a, b, c (Angstrom), alpha, beta, gamma (degrees) and volume (Angstrom^3) of a cell matrix."""
    import numpy as np

    m = np.asarray(cell, dtype=float)
    a, b, c = (float(np.linalg.norm(v)) for v in m)
    ang = lambda u, v: float(np.degrees(np.arccos(np.clip(np.dot(u, v) / np.linalg.norm(u) / np.linalg.norm(v), -1, 1))))
    return {"a": round(a, 3), "b": round(b, 3), "c": round(c, 3), "alpha": round(ang(m[1], m[2]), 2),
            "beta": round(ang(m[0], m[2]), 2), "gamma": round(ang(m[0], m[1]), 2),
            "volume": round(abs(float(np.linalg.det(m))), 2)}


def live_structure(start: Structure, best: dict, substitution: dict | None) -> dict:
    """What the interface shows of a relaxation: the arrangement before relaxation and after it (same atom order),
    their cells, the substituted element and, when recorded, the relaxation path. Display only."""
    from ase.data import chemical_symbols

    import numpy as np

    end = best["atoms"]
    rnd = lambda rows, d: [[round(float(x), d) for x in r] for r in rows]
    # the relaxed positions taken next to their start (an atom across a cell face is not drawn jumping over the cell)
    cell = np.asarray(end["cell"], dtype=float)
    frac = np.asarray(end["positions"], dtype=float) @ np.linalg.inv(cell)
    frac -= np.round(frac - start.frac_coords)
    end = {**end, "positions": (frac @ cell).tolist()}
    sub = substitution or {}
    return {"symbols": [chemical_symbols[z] for z in end["numbers"]],
            "start": {"positions": rnd(start.cart_coords, 3), "cell": rnd(start.lattice.matrix, 4),
                      "lattice": lattice(start.lattice.matrix)},
            "end": {"positions": rnd(end["positions"], 3), "cell": rnd(end["cell"], 4), "lattice": lattice(end["cell"]),
                    "energy_per_atom": round(best["energy_per_atom"], 5)},
            "added": sub.get("add"), "removed": sub.get("remove"),
            "li_vacancies": sub.get("li_vacancies") or sub.get("vacancies") or 0,
            "trajectory": best.get("trajectory") or [], "steps": best.get("steps")}


def n_modified(parent: Structure, substitution: dict) -> int:
    """Number of modified sites: replaced sites plus Li vacancies (each vacancy is a modification)."""
    if substitution["count"] == "all":
        replaced = sum(site.specie.symbol == substitution["remove"] for site in parent)
    else:
        replaced = int(substitution["count"])
    from autolab.chem.generator import vacancies_of

    return replaced + max(0, vacancies_of(substitution))


def evaluate_candidate(
    candidate_id: str,
    parent_id: str,
    parent: Structure,
    substitution: dict,
    tools: Tools | None = None,
    events: EventLog | None = None,
    budget=None,
    charge_check=None,
    ehull_max: float = config.EHULL_SYNTHESIZABLE,
    gap_min: float = config.BANDGAP_MIN,
) -> dict:
    """Run the funnel on one substitution; return a JSON-serialisable result. `charge_check`, `ehull_max` and
    `gap_min`: the domain's (the electrolyte ones by default).

    sim.backend.BudgetExceeded propagates: the caller stops the run cleanly.
    """
    from autolab.chem.generator import generate_candidates

    tools = tools or Tools()
    events = events or EventLog()
    t0 = time.perf_counter()
    used0 = budget.used if budget else 0
    out = {
        "id": candidate_id, "parent": parent_id, "parent_formula": parent.composition.reduced_formula,
        "substitution": substitution, "formula": None, "status": "rejected", "rejected_at": None, "reason": None,
        "arrangements": 0, "converged": 0, "energy_spread_meV": None, "n_atoms": None, "n_modified": None,
        "e_hull": None, "e_hull_per_substitution": None, "decomposition": None, "known_in_mp": [],
        "skipped_references": [], "energy": None, "relaxed_atoms": None,
        "gap_optb88": None, "gap_mbj": None, "gap_low_confidence": None, "ss_bonds": None,
        "not_run": list(tools.not_run),
    }

    def emit(step, **data):
        events.emit("candidate", step, data, candidate_id)

    def finish(status="rejected", step=None, reason=None):
        out.update(status=status, rejected_at=step, reason=reason,
                   new_relaxations=(budget.used - used0) if budget else None,
                   seconds=round(time.perf_counter() - t0, 1))
        emit("done", status=status, rejected_at=step, reason=reason)
        return out

    # 1. Chemical rule + charge neutrality, before any simulation.
    gen = (generate_candidates(parent, substitution, parent_id) if charge_check is None
           else generate_candidates(parent, substitution, parent_id, charge_check=charge_check))
    out["formula"] = gen["formula"]
    emit("generate", accepted=gen["accepted"], formula=gen["formula"], charge=gen["charge"],
         arrangements=len(gen["candidates"]), reason=gen["reason"])
    if not gen["accepted"]:
        return finish(step="generate", reason=gen["reason"])
    out["n_modified"] = n_modified(parent, substitution)

    # 2. A composition already in Materials Project is reported, not recomputed.
    try:
        known = tools.known(gen["formula"])
    except Exception as e:  # MP unreachable: compute anyway, but say so
        known = []
        emit("known_check", error=f"{type(e).__name__}: {e}")
    else:
        emit("known_check", known=known)
    if known:
        out["known_in_mp"] = [k["material_id"] for k in known]
        return finish(step="known", reason=f"composition already in Materials Project: {', '.join(out['known_in_mp'])}")
    structures = [Structure.from_dict(c["structure"]) for c in gen["candidates"]]
    return evaluate_structures(out, structures, tools, emit, finish, budget, ehull_max=ehull_max, gap_min=gap_min)


def evaluate_structures(out: dict, structures: list[Structure], tools: Tools, emit: Callable, finish: Callable,
                        budget=None, hidden_formulas: frozenset[str] = frozenset(),
                        ehull_max: float = config.EHULL_SYNTHESIZABLE, gap_min: float = config.BANDGAP_MIN) -> dict:
    """Steps 3-6 of the funnel on ready structures (arrangements of one composition): relaxation, E_hull,
    band gap, S-S flag. `hidden_formulas`: reduced formulas removed from the hull references (blind benchmark of
    a known compound, judged as if it were new)."""
    from autolab.analysis.stability import e_hull, uma_entry
    from autolab.chem.checks import has_ss_bonds

    out["arrangements"] = len(structures)

    # 3. UMA relaxation of every arrangement; keep the lowest converged one.
    results = tools.relax(structures, budget)
    converged = [r for r in results if r["converged"]]
    out["converged"] = len(converged)
    epa = [r["energy_per_atom"] for r in converged]
    if epa:
        out["energy_spread_meV"] = round(1000 * (max(epa) - min(epa)), 1)
    best = min(converged, key=lambda r: r["energy_per_atom"]) if converged else None
    emit("relax", arrangements=len(results), converged=len(converged),
         energies_per_atom=[round(e, 4) for e in epa], spread_meV=out["energy_spread_meV"],
         cached=all(r.get("cached") for r in results),
         structure=live_structure(structures[results.index(best)], best, out.get("substitution")) if best else None)
    if not converged:
        return finish(step="relax", reason="no arrangement converged")
    structure = _relaxed_structure(best)
    out.update(energy=best["energy"], relaxed_atoms=best["atoms"])  # for electrodes and dynamics

    # 4. E_hull against references of the same chemical system, all relaxed by UMA.
    #    Per substitution: E_hull x atoms / modified sites (replaced + Li vacancies), the energy cost
    #    of each modification, so that a single dopant in a large cell is not favoured for changing little.
    elements = sorted(el.symbol for el in structure.composition.elements)
    entries, skipped = tools.hull_entries(elements, budget)
    if hidden_formulas:
        entries = [e for e in entries if e.composition.reduced_formula not in hidden_formulas]
    out["skipped_references"] = skipped
    target = uma_entry(Composition(structure.composition), best["energy"], out["id"], structure=structure)
    hull = e_hull(target, entries)
    out["n_atoms"] = len(structure)
    # Reduced confidence when the decomposition goes through a polysulfide (S-S bonds), where UMA is least reliable.
    out["decomposition_polysulfides"] = hull["decomposition_polysulfides"]
    out["reduced_confidence"] = bool(hull["decomposition_polysulfides"])
    out.update(e_hull=hull["e_hull"], decomposition=hull["decomposition"][:4],
               e_hull_per_substitution=round(hull["e_hull"] * out["n_atoms"] / out["n_modified"], 4))
    emit("hull", e_hull=hull["e_hull"], e_hull_per_substitution=out["e_hull_per_substitution"],
         decomposition=out["decomposition"], references=len(entries), skipped_references=skipped)
    if hull["e_hull"] > ehull_max:
        return finish(step="hull", reason=f"E_hull {hull['e_hull']:.3f} > {ehull_max} eV/atom")

    # 5. Band gap (GapModel): the electrolyte must be an electronic insulator.
    gap = tools.bandgap(structure)
    if gap_min != config.BANDGAP_MIN:  # the domain's limit (e.g. sodium)
        gap = {**gap, "passes": gap["gap_optb88"] is not None and gap["gap_optb88"] >= gap_min}
    out.update(gap_optb88=gap["gap_optb88"], gap_mbj=gap["gap_mbj"], gap_low_confidence=gap["low_confidence"])
    emit("bandgap", **{k: gap[k] for k in ("gap_optb88", "gap_mbj", "passes", "low_confidence")})
    if not gap["passes"]:
        return finish(step="bandgap", reason=f"gap {gap['gap_optb88']:.2f} < {gap_min} eV")

    # 6. S-S bonds: a warning only (UMA less reliable for polysulfides).
    out["ss_bonds"] = bool(has_ss_bonds(structure))
    emit("ss_check", ss_bonds=out["ss_bonds"])
    return finish(status="passed")
