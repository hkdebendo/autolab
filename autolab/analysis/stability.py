"""Convex hull, E_hull and decomposition products (SPEC 5.7).

All energies of one hull must come from a single source ("uma" or "mp"):
mixing them raises ValueError.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable

from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram
from pymatgen.core import Composition
from pymatgen.entries.computed_entries import ComputedEntry

from autolab import config

FRACTION_EPS = 1e-8


def make_entry(composition: Composition | str, energy: float, name: str, source: str, structure=None) -> PDEntry:
    """PDEntry tagged with its energy source; `energy` is the total energy (eV).

    `structure` (pymatgen, optional) lets the MP2020 scheme tell sulfides from sulfates.
    """
    attribute = {"source": source, **({"structure": structure} if structure is not None else {})}
    return PDEntry(Composition(composition), energy, name=name, attribute=attribute)


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


@lru_cache(maxsize=None)
def oxidation_guess(reduced_formula: str) -> dict:
    """Most likely oxidation states, without the 20-atom limit pymatgen uses inside the MP2020 scheme
    (above it, only the most electronegative element would be corrected: S but not Se in Li7P3SeS10)."""
    guesses = Composition(reduced_formula).oxi_state_guesses()
    return dict(guesses[0]) if guesses else {}


def mp2020_inputs(entries: list) -> list[ComputedEntry]:
    """Raw UMA entries as the MP2020 scheme needs them: run type, U values, oxidation states, structure.

    GGA+U for compounds holding O or F and a metal of config.MP2020_HUBBARD_U (as in the MP sets).
    Oxidation states and structures (sulfide vs sulfate, oxide vs peroxide) make the corrected anion
    atoms the same on both sides of a reaction.
    """
    from pymatgen.entries.computed_entries import ComputedStructureEntry

    if check_single_source(entries) != "uma":
        raise ValueError("MP2020 corrections apply to raw UMA entries only")
    u = config.MP2020_HUBBARD_U
    raw = []
    for e in entries:
        els = {el.symbol for el in e.composition.elements}
        plus_u = bool(els & {"O", "F"}) and bool(els & set(u))
        kwargs = {"entry_id": e.name, "data": {"oxidation_states": oxidation_guess(e.composition.reduced_formula)},
                  "parameters": {"run_type": "GGA+U" if plus_u else "GGA",
                                 "hubbards": {el: u[el] for el in els & set(u)} if plus_u else {}}}
        structure = (e.attribute or {}).get("structure") if isinstance(e.attribute, dict) else None
        raw.append(ComputedStructureEntry(structure, e.energy, **kwargs) if structure is not None
                   else ComputedEntry(e.composition, e.energy, **kwargs))
    return raw


def uma_entry(composition: Composition | str, energy: float, name: str, structure=None) -> PDEntry:
    """Entry of a UMA total energy, with the MP2020 corrections when config.UMA_MP2020 (source 'uma+mp2020')."""
    entry = make_entry(composition, energy, name, "uma", structure=structure)
    return mp2020_corrected([entry])[0] if config.UMA_MP2020 else entry


def mp2020_corrected(entries: list) -> list[PDEntry]:
    """UMA entries plus the MP2020 corrections (anions, GGA/GGA+U mixing), tagged 'uma+mp2020'.

    The energies stay UMA's: only the empirical per-element adjustments of the MP2020 scheme are added.
    """
    from pymatgen.entries.compatibility import MaterialsProject2020Compatibility

    raw = mp2020_inputs(entries)
    done = MaterialsProject2020Compatibility(check_potcar=False).process_entries(raw, clean=True, inplace=False)
    if len(done) != len(raw):
        kept = {c.entry_id for c in done}
        raise ValueError(f"MP2020 scheme rejected {[c.entry_id for c in raw if c.entry_id not in kept]}")
    return [make_entry(c.composition, c.energy, c.entry_id, "uma+mp2020", structure=getattr(c, "structure", None))
            for c in done]


def anion_balance(entries: list, tol: float = 1e-6) -> list[str]:
    """Phases of a hull whose MP2020-corrected anion atoms differ from those of their decomposition products.

    `entries`: raw UMA entries of one hull (candidates included). For each phase, the corrected anion atoms
    per atom (from the scheme's own adjustments) must equal the fraction-weighted sum over its decomposition
    in the corrected hull. An empty list means the corrections cancel consistently.
    Phases with an anion of formal oxidation state between -1 and 0 (e.g. Sb in the alloy LiSb3) are left out:
    the scheme does not correct them on purpose (strict_anions="require_bound"), in MP's own data too.
    """
    from pymatgen.entries.compatibility import MaterialsProject2020Compatibility

    compat = MaterialsProject2020Compatibility(check_potcar=False)
    per_atom = {}
    for ce in mp2020_inputs(entries):
        atoms: dict[str, float] = {}
        for adj in compat.get_adjustments(ce):
            if "anion correction" in adj.name:
                el = adj.name.split("(")[-1].rstrip(")")
                el = "O" if el in ("oxide", "peroxide", "superoxide", "ozonide") else el
                atoms[el] = atoms.get(el, 0.0) + adj.n_atoms / ce.composition.num_atoms
        per_atom[ce.entry_id] = atoms
    pd = PhaseDiagram(mp2020_corrected(entries))
    bad = []
    for e in pd.all_entries:
        decomp, _ = pd.get_decomp_and_e_above_hull(e, allow_negative=True)
        products: dict[str, float] = {}
        for p, f in decomp.items():
            for el, n in per_atom[p.name].items():
                products[el] = products.get(el, 0.0) + f * n
        if any(-1 < ox < 0 for ox in oxidation_guess(e.composition.reduced_formula).values()):
            continue
        own = per_atom[e.name]
        diff = {el: round(own.get(el, 0.0) - products.get(el, 0.0), 6) for el in set(own) | set(products)
                if abs(own.get(el, 0.0) - products.get(el, 0.0)) > tol}
        if diff:
            bad.append(f"{e.name} {e.composition.reduced_formula}: {diff}")
    return bad


def polysulfide_products(decomp: dict) -> list[str]:
    """Decomposition products that are compounds with S-S bonds (e.g. LiS4), where UMA is least reliable:
    LiS4 is 0.178 eV/atom above the hull with raw UMA, -0.174 with UMA + MP2020, 0 in MP."""
    from autolab.chem.checks import has_ss_bonds

    out = []
    for e, f in decomp.items():
        attribute = getattr(e, "attribute", None)
        structure = getattr(e, "structure", None) or (attribute.get("structure") if isinstance(attribute, dict) else None)
        if f > FRACTION_EPS and len(e.composition.elements) > 1 and structure is not None and has_ss_bonds(structure):
            out.append(e.composition.reduced_formula)
    return sorted(set(out))


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


def uma_reference_entries(elements: Iterable[str], backend=None, budget=None,
                          ehull_max: float = config.MP_REF_EHULL_MAX) -> tuple[list[PDEntry], list[str]]:
    """Hull references of a chemical system, relaxed by UMA (cached).

    MP only provides the structures (phases up to `ehull_max` on the MP hull); every
    energy comes from UMA. Returns the entries and the material ids skipped because
    their relaxation did not converge. `budget` (sim.backend.RelaxBudget) limits the
    new relaxations of a whole run.
    """
    from autolab.data.mp import get_references
    from autolab.sim.backend import relax_structures

    refs = get_references(elements, ehull_max=ehull_max)
    results = relax_structures([r["structure"] for r in refs], backend=backend, budget=budget)
    entries, skipped = [], []
    for ref, res in zip(refs, results):
        if not res["converged"]:
            skipped.append(ref["material_id"])
            continue
        entries.append(uma_entry(ref["structure"].composition, res["energy"], ref["material_id"],
                                 structure=ref["structure"]))
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
        "decomposition_polysulfides": polysulfide_products(decomp),
        "synthesizable": ehull <= config.EHULL_SYNTHESIZABLE,
        "very_good": ehull <= config.EHULL_VERY_GOOD,
        "source": energy_source(target),
    }
