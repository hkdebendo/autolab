"""Filter funnel for one candidate (SPEC 6.1).

generate (rule + neutrality) -> composition already in Materials Project? (then not computed)
-> relax every arrangement with UMA, keep the lowest -> E_hull against UMA-relaxed references
-> ALIGNN band gap -> S-S bond flag.
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
    """Expensive steps, injectable so that tests run without UMA, ALIGNN or Materials Project."""

    relax: Callable = _default_relax  # (structures, budget) -> list of relax results
    hull_entries: Callable = _default_hull_entries  # (elements, budget) -> (entries, skipped ids)
    bandgap: Callable = _default_bandgap  # (structure) -> evaluate_bandgap dict
    known: Callable = _default_known  # (formula) -> MP materials with that reduced composition
    not_run: list[str] = field(default_factory=lambda: ["electrodes", "molecular_dynamics"])


def _relaxed_structure(res: dict) -> Structure:
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_from_dict

    return AseAtomsAdaptor.get_structure(atoms_from_dict(res["atoms"]))


def n_modified(parent: Structure, substitution: dict) -> int:
    """Number of modified sites: replaced sites plus Li vacancies (each vacancy is a modification)."""
    if substitution["count"] == "all":
        replaced = sum(site.specie.symbol == substitution["remove"] for site in parent)
    else:
        replaced = int(substitution["count"])
    return replaced + int(substitution.get("li_vacancies", 0))


def evaluate_candidate(
    candidate_id: str,
    parent_id: str,
    parent: Structure,
    substitution: dict,
    tools: Tools | None = None,
    events: EventLog | None = None,
    budget=None,
) -> dict:
    """Run the funnel on one substitution; return a JSON-serialisable result.

    sim.backend.BudgetExceeded propagates: the caller stops the run cleanly.
    """
    from autolab.analysis.stability import e_hull, uma_entry
    from autolab.chem.checks import has_ss_bonds
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
    gen = generate_candidates(parent, substitution, parent_id)
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
    out["arrangements"] = len(structures)

    # 3. UMA relaxation of every arrangement; keep the lowest converged one.
    results = tools.relax(structures, budget)
    converged = [r for r in results if r["converged"]]
    out["converged"] = len(converged)
    epa = [r["energy_per_atom"] for r in converged]
    if epa:
        out["energy_spread_meV"] = round(1000 * (max(epa) - min(epa)), 1)
    emit("relax", arrangements=len(results), converged=len(converged),
         energies_per_atom=[round(e, 4) for e in epa], spread_meV=out["energy_spread_meV"])
    if not converged:
        return finish(step="relax", reason="no arrangement converged")
    best = min(converged, key=lambda r: r["energy_per_atom"])
    structure = _relaxed_structure(best)
    out.update(energy=best["energy"], relaxed_atoms=best["atoms"])  # for electrodes and dynamics

    # 4. E_hull against references of the same chemical system, all relaxed by UMA.
    #    Per substitution: E_hull x atoms / modified sites (replaced + Li vacancies), the energy cost
    #    of each modification, so that a single dopant in a large cell is not favoured for changing little.
    elements = sorted(el.symbol for el in structure.composition.elements)
    entries, skipped = tools.hull_entries(elements, budget)
    out["skipped_references"] = skipped
    target = uma_entry(Composition(structure.composition), best["energy"], candidate_id, structure=structure)
    hull = e_hull(target, entries)
    out["n_atoms"] = len(structure)
    out.update(e_hull=hull["e_hull"], decomposition=hull["decomposition"][:4],
               e_hull_per_substitution=round(hull["e_hull"] * out["n_atoms"] / out["n_modified"], 4))
    emit("hull", e_hull=hull["e_hull"], e_hull_per_substitution=out["e_hull_per_substitution"],
         decomposition=out["decomposition"], references=len(entries), skipped_references=skipped)
    if hull["e_hull"] > config.EHULL_SYNTHESIZABLE:
        return finish(step="hull", reason=f"E_hull {hull['e_hull']:.3f} > {config.EHULL_SYNTHESIZABLE} eV/atom")

    # 5. Band gap (ALIGNN): the electrolyte must be an electronic insulator.
    gap = tools.bandgap(structure)
    out.update(gap_optb88=gap["gap_optb88"], gap_mbj=gap["gap_mbj"], gap_low_confidence=gap["low_confidence"])
    emit("bandgap", **{k: gap[k] for k in ("gap_optb88", "gap_mbj", "passes", "low_confidence")})
    if not gap["passes"]:
        return finish(step="bandgap", reason=f"gap {gap['gap_optb88']:.2f} < {config.BANDGAP_MIN} eV")

    # 6. S-S bonds: a warning only (UMA less reliable for polysulfides).
    out["ss_bonds"] = bool(has_ss_bonds(structure))
    emit("ss_check", ss_bonds=out["ss_bonds"])
    return finish(status="passed")
