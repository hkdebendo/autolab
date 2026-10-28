"""Convex hull, E_hull and decomposition products (SPEC 5.7).

All energies of one hull must come from a single source ("uma" or "mp"):
mixing them raises ValueError.
"""

from __future__ import annotations

from typing import Iterable

from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry

from autolab import config

FRACTION_EPS = 1e-8


def make_entry(composition: Composition | str, energy: float, name: str, source: str) -> PDEntry:
    """PDEntry tagged with its energy source; `energy` is the total energy (eV)."""
    return PDEntry(Composition(composition), energy, name=name, attribute={"source": source})


def energy_source(entry) -> str:
    """'uma', 'mp', ... from the entry tag; MP ComputedEntry objects count as 'mp'."""
    attribute = getattr(entry, "attribute", None)
    if isinstance(attribute, dict) and "source" in attribute:
        return attribute["source"]
    if isinstance(entry, ComputedEntry):
        return "mp"
    return "unknown"


def check_single_source(entries: Iterable) -> str:
    """Return the common energy source, or raise if sources are mixed or unknown."""
    sources = {energy_source(e) for e in entries}
    if len(sources) != 1 or "unknown" in sources:
        raise ValueError(f"hull entries must share one known energy source, got {sorted(sources)}")
    return sources.pop()


def entry_label(entry) -> str:
    """Readable id of an entry: MP id when available, else its name."""
    return str(getattr(entry, "entry_id", None) or entry.name)


def phase_diagram(entries: list) -> PhaseDiagram:
    """PhaseDiagram after checking that all energies share one source."""
    check_single_source(entries)
    return PhaseDiagram(entries)


def decomposition_dict(decomp: dict) -> list[dict]:
    """JSON-friendly decomposition, largest fraction first."""
    items = [
        {"formula": e.composition.reduced_formula, "id": entry_label(e), "fraction": round(float(f), 6)}
        for e, f in decomp.items()
        if f > FRACTION_EPS
    ]
    return sorted(items, key=lambda d: -d["fraction"])


def uma_reference_entries(elements: Iterable[str], backend=None, budget=None) -> tuple[list[PDEntry], list[str]]:
    """Hull references of a chemical system, relaxed by UMA (cached).

    MP only provides the structures; every energy comes from UMA. Returns the
    entries and the material ids skipped because their relaxation did not converge.
    `budget` (sim.backend.RelaxBudget) limits the new relaxations of a whole run.
    """
    from autolab.data.mp import get_references
    from autolab.sim.backend import relax_structures

    refs = get_references(elements)
    results = relax_structures([r["structure"] for r in refs], backend=backend, budget=budget)
    entries, skipped = [], []
    for ref, res in zip(refs, results):
        if not res["converged"]:
            skipped.append(ref["material_id"])
            continue
        entries.append(make_entry(ref["structure"].composition, res["energy"], ref["material_id"], "uma"))
    return entries, skipped


def e_hull(target, entries: list, pd: PhaseDiagram | None = None) -> dict:
    """E_hull (eV/atom, may be negative if below the hull) and decomposition products."""
    check_single_source([*entries, target])
    pd = pd or phase_diagram(entries)
    decomp, ehull = pd.get_decomp_and_e_above_hull(target, allow_negative=True)
    ehull = float(ehull)
    return {
        "formula": target.composition.reduced_formula,
        "e_hull": round(ehull, 6),
        "decomposition": decomposition_dict(decomp),
        "synthesizable": ehull <= config.EHULL_SYNTHESIZABLE,
        "very_good": ehull <= config.EHULL_VERY_GOOD,
        "source": energy_source(target),
    }
