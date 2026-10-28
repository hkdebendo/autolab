"""Filter funnel for one candidate (SPEC 6.1).

generate (rule + neutrality) -> relax every arrangement with UMA, keep the lowest
-> E_hull against UMA-relaxed references -> ALIGNN band gap -> S-S bond flag.
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


@dataclass
class Tools:
    """Expensive steps, injectable so that tests run without UMA, ALIGNN or Materials Project."""

    relax: Callable = _default_relax  # (structures, budget) -> list of relax results
    hull_entries: Callable = _default_hull_entries  # (elements, budget) -> (entries, skipped ids)
    bandgap: Callable = _default_bandgap  # (structure) -> evaluate_bandgap dict
    not_run: list[str] = field(default_factory=lambda: ["electrodes", "molecular_dynamics"])


def _relaxed_structure(res: dict) -> Structure:
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_from_dict

    return AseAtomsAdaptor.get_structure(atoms_from_dict(res["atoms"]))


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
    from autolab.analysis.stability import e_hull, make_entry
    from autolab.chem.checks import has_ss_bonds
    from autolab.chem.generator import generate_candidates

    tools = tools or Tools()
    events = events or EventLog()
    t0 = time.perf_counter()
    used0 = budget.used if budget else 0
    out = {
        "id": candidate_id, "parent": parent_id, "parent_formula": parent.composition.reduced_formula,
        "substitution": substitution, "formula": None, "status": "rejected", "rejected_at": None, "reason": None,
        "arrangements": 0, "converged": 0, "energy_spread_meV": None,
        "e_hull": None, "decomposition": None, "known_in_mp": [], "skipped_references": [],
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
    structures = [Structure.from_dict(c["structure"]) for c in gen["candidates"]]
    out["arrangements"] = len(structures)

    # 2. UMA relaxation of every arrangement; keep the lowest converged one.
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

    # 3. E_hull against references of the same chemical system, all relaxed by UMA.
    elements = sorted(el.symbol for el in structure.composition.elements)
    entries, skipped = tools.hull_entries(elements, budget)
    out["skipped_references"] = skipped
    target = make_entry(Composition(structure.composition), best["energy"], candidate_id, "uma")
    hull = e_hull(target, entries)
    out.update(e_hull=hull["e_hull"], decomposition=hull["decomposition"][:4],
               known_in_mp=sorted(e.name for e in entries
                                  if e.composition.reduced_formula == structure.composition.reduced_formula))
    emit("hull", e_hull=hull["e_hull"], decomposition=out["decomposition"], references=len(entries),
         skipped_references=skipped, known_in_mp=out["known_in_mp"])
    if hull["e_hull"] > config.EHULL_SYNTHESIZABLE:
        return finish(step="hull", reason=f"E_hull {hull['e_hull']:.3f} > {config.EHULL_SYNTHESIZABLE} eV/atom")

    # 4. Band gap (ALIGNN): the electrolyte must be an electronic insulator.
    gap = tools.bandgap(structure)
    out.update(gap_optb88=gap["gap_optb88"], gap_mbj=gap["gap_mbj"], gap_low_confidence=gap["low_confidence"])
    emit("bandgap", **{k: gap[k] for k in ("gap_optb88", "gap_mbj", "passes", "low_confidence")})
    if not gap["passes"]:
        return finish(step="bandgap", reason=f"gap {gap['gap_optb88']:.2f} < {config.BANDGAP_MIN} eV")

    # 5. S-S bonds: a warning only (UMA less reliable for polysulfides).
    out["ss_bonds"] = bool(has_ss_bonds(structure))
    emit("ss_check", ss_bonds=out["ss_bonds"])
    return finish(status="passed")
