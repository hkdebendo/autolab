"""Electrochemical window, passivation and cathode interface (SPEC 5.9).

Method of Zhu, He & Mo (2015): the electrolyte is put in contact with a Li
reservoir at chemical potential mu_Li = mu_Li(metal) - V.
All entries must share one energy source (see stability.check_single_source).
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from pymatgen.analysis.interface_reactions import InterfacialReactivity
from pymatgen.analysis.phase_diagram import GrandPotentialPhaseDiagram, GrandPotPDEntry, PDEntry, PhaseDiagram
from pymatgen.core import Composition, Element

from autolab import config
from autolab.analysis.stability import FRACTION_EPS, check_single_source, decomposition_dict, entry_label
from autolab.data.mp import material_id_of

LI = Element("Li")


def _key(entry) -> tuple[str, float]:
    """Identity of an entry independent of the object (grand potential entries wrap originals)."""
    return entry.composition.reduced_formula, round(entry.energy_per_atom, 6)


def _with_target(target, entries: list) -> list:
    return entries if any(_key(e) == _key(target) for e in entries) else [*entries, target]


def li_metal_mu(entries: list) -> float:
    """Chemical potential of Li metal: lowest energy per atom among elemental Li entries."""
    li = [e for e in entries if e.composition.reduced_formula == "Li"]
    if not li:
        raise ValueError("entries contain no elemental Li")
    return min(e.energy_per_atom for e in li)


def _natural_products(target, pd: PhaseDiagram) -> set:
    decomp = pd.get_decomposition(target.composition)
    return {_key(e) for e, f in decomp.items() if f > FRACTION_EPS}


def _open_decomposition(target, entries: list, mu_li: float) -> tuple[dict, float]:
    """Products and reaction energy (eV/atom of the open-system composition) at fixed mu_Li."""
    gpd = GrandPotentialPhaseDiagram(entries, {LI: mu_li})
    gentry = GrandPotPDEntry(target, {LI: mu_li})
    decomp, e_above = gpd.get_decomp_and_e_above_hull(gentry, allow_negative=True)
    products = {g.original_entry: f for g, f in decomp.items()}
    return products, float(e_above)


def electrochemical_window(
    target,
    entries: list,
    v_min: float = config.WINDOW_V_MIN,
    v_max: float = config.WINDOW_V_MAX,
    step: float = config.WINDOW_V_STEP,
) -> dict:
    """Voltage range (V vs Li/Li+) where the target keeps its natural decomposition.

    Works for metastable compounds: 'stable' means no Li exchange with the
    reservoir, i.e. the products are exactly those of the closed system.
    """
    entries = _with_target(target, entries)
    check_single_source(entries)
    mu_metal = li_metal_mu(entries)
    natural = _natural_products(target, PhaseDiagram(entries))

    stable_v = []
    for v in np.round(np.arange(v_min, v_max + step / 2, step), 6):
        products, _ = _open_decomposition(target, entries, mu_metal - v)
        if {_key(e) for e, f in products.items() if f > FRACTION_EPS} == natural:
            stable_v.append(float(v))

    return {
        "formula": target.composition.reduced_formula,
        "stable": bool(stable_v),
        "v_low": stable_v[0] if stable_v else None,
        "v_high": stable_v[-1] if stable_v else None,
        "contiguous": bool(stable_v) and len(stable_v) == round((stable_v[-1] - stable_v[0]) / step) + 1,
    }


def passivation(
    target,
    entries: list,
    get_gaps: Callable[[list[str]], dict[str, float | None]] | None = None,
) -> dict:
    """Reaction with Li metal (0 V): products, metallic products and verdict.

    get_gaps maps MP material ids to MP band gaps (default: one batched MP
    request through data.mp). Verdicts: stable, passivating, quasi_stable,
    non_passivating.
    """
    entries = _with_target(target, entries)
    check_single_source(entries)
    natural = _natural_products(target, PhaseDiagram(entries))
    products, e_above = _open_decomposition(target, entries, li_metal_mu(entries))
    products = {e: f for e, f in products.items() if f > FRACTION_EPS}
    force = max(e_above, 0.0)

    if get_gaps is None:
        from autolab.data.mp import get_band_gaps as get_gaps
    ids = {e: material_id_of(entry_label(e)) for e in products}
    gaps = get_gaps(sorted(set(ids.values())))
    # A missing gap is unknown, not insulating: `g is not None and g < max`.
    metallic = [
        e.composition.reduced_formula
        for e in products
        if (g := gaps.get(ids[e])) is not None and g < config.METALLIC_GAP_MAX
    ]
    product_keys = {_key(e) for e in products}

    if product_keys == natural:
        verdict = "stable"
    elif not metallic:
        verdict = "passivating"
    elif force < config.PASSIVATION_FORCE_MAX:
        verdict = "quasi_stable"
    else:
        verdict = "non_passivating"

    return {
        "formula": target.composition.reduced_formula,
        "verdict": verdict,
        "reaction_energy": round(force, 6),
        "products": decomposition_dict(products),
        "metallic_products": sorted(set(metallic)),
    }


def cathode_interface(electrolyte: Composition | str, cathode: Composition | str, pd: PhaseDiagram) -> dict:
    """Most negative interfacial reaction energy (eV/atom) between electrolyte and cathode."""
    check_single_source(pd.all_entries)
    # InterfacialReactivity rebuilds products with Composition(entry.name): entries named by an id
    # (UMA references are named by MP material id) must be renamed by their formula first.
    if any(e.name != e.composition.reduced_formula for e in pd.all_entries):
        pd = PhaseDiagram([PDEntry(e.composition, e.energy, name=e.composition.reduced_formula)
                           for e in pd.all_entries])
    ir = InterfacialReactivity(Composition(electrolyte), Composition(cathode), pd, norm=True, use_hull_energy=True)
    kinks = list(ir.get_kinks())
    worst = min(kinks, key=lambda k: k[2])
    return {
        "electrolyte": Composition(electrolyte).reduced_formula,
        "cathode": Composition(cathode).reduced_formula,
        "min_reaction_energy": round(float(worst[2]), 6),
        "mixing_ratio": round(float(worst[1]), 6),
        "reaction": str(worst[3]),
    }
