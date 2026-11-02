"""How far UMA energies are from DFT (Materials Project), measured on known phases (limit "UMA, not DFT").

For a chemical system, each known compound among the near-hull MP references is treated like a new candidate: its
composition is left out of the hull and its energy relative to the remaining phases (decomposition energy, may be
negative) is computed twice, with UMA + MP2020 energies (all references relaxed by UMA, cached) and with MP energies
(GGA/GGA+U, MP2020) in a separate hull. Energy sources are never mixed in one hull. The spread of the differences is
the error bar given with the E_hull of a candidate of that system. Polysulfides (S-S bonds) are reported apart: UMA
is least reliable there, and their error sets the energy shift of the window sensitivity test
(analysis.electrodes.window_sensitivity). Computed from the caches (one light MP request per system for the energies).
"""

from __future__ import annotations

import math
from typing import Callable, Iterable

from pymatgen.analysis.phase_diagram import PDEntry, PhaseDiagram

from autolab import config


def is_polysulfide(entry) -> bool:
    """A compound whose structure has S-S bonds (the rule of stability.polysulfide_products)."""
    from autolab.chem.checks import has_ss_bonds

    attribute = getattr(entry, "attribute", None)
    structure = attribute.get("structure") if isinstance(attribute, dict) else None
    return len(entry.composition.elements) > 1 and structure is not None and has_ss_bonds(structure)


def _stats(diffs: list[float]) -> dict:
    if not diffs:
        return {"n": 0, "mae": None, "rmse": None, "max_abs": None, "bias": None}
    return {"n": len(diffs), "mae": round(sum(map(abs, diffs)) / len(diffs), 4),
            "rmse": round(math.sqrt(sum(d * d for d in diffs) / len(diffs)), 4),
            "max_abs": round(max(map(abs, diffs)), 4), "bias": round(sum(diffs) / len(diffs), 4)}


def leave_one_out(entries: list) -> dict[str, float]:
    """Energy of each compound's lowest polymorph relative to the hull of the other compositions (eV/atom, negative
    when it is stable), keyed by reduced formula; elements are left out (they are the hull's terminals)."""
    best: dict[str, object] = {}
    for e in entries:
        f = e.composition.reduced_formula
        if len(e.composition.elements) > 1 and (f not in best or e.energy_per_atom < best[f].energy_per_atom):
            best[f] = e
    out = {}
    for f, e in best.items():
        others = [x for x in entries if x.composition.reduced_formula != f]
        _, de = PhaseDiagram(others).get_decomp_and_e_above_hull(e, allow_negative=True)
        out[f] = float(de)
    return out


def system_errors(elements: Iterable[str], uma_entries: list | None = None, mp_energies: dict | None = None,
                  refs: list | None = None, ehull_max: float = config.MP_REF_EHULL_MAX) -> dict:
    """UMA (+ MP2020) vs MP decomposition energies of the known compounds of a system and its sub-systems.

    Returns {"system", "available", "reason", "rows": [{formula, id, mp, uma, diff, polysulfide}], "compounds": stats,
    "polysulfides": stats}. Inputs are injectable (tests); by default the MP references, their cached UMA relaxations
    (no new relaxation) and their MP energies (data.mp.get_reference_energies)."""
    from autolab.data.mp import chemsys_key

    elements = sorted(set(elements))
    out = {"system": chemsys_key(elements), "available": False, "rows": [], "reason": None,
           "method": "decomposition energy of each known compound against the other phases, UMA + MP2020 vs MP"}
    if uma_entries is None:
        from autolab.analysis.stability import uma_reference_entries
        from autolab.sim.backend import BudgetExceeded, RelaxBudget

        try:
            uma_entries, _ = uma_reference_entries(elements, budget=RelaxBudget(0), ehull_max=ehull_max)
        except BudgetExceeded as e:
            out["reason"] = f"references not all relaxed by UMA in the cache ({e})"
            return out
    if mp_energies is None or refs is None:
        from autolab.data.mp import get_reference_energies, get_references

        refs = get_references(elements, ehull_max=ehull_max)
        mp_energies = get_reference_energies(elements)
    mp_entries = [PDEntry(r["structure"].composition, mp_energies[r["material_id"]] * r["structure"].num_sites,
                          name=r["material_id"], attribute={"source": "mp"})
                  for r in refs if r["material_id"] in mp_energies]
    uma = leave_one_out(uma_entries)
    mp = leave_one_out(mp_entries)
    polys = {e.composition.reduced_formula for e in uma_entries if is_polysulfide(e)}
    ids = {}
    for e in uma_entries:
        ids.setdefault(e.composition.reduced_formula, e.name)
    for f in sorted(set(uma) & set(mp)):
        out["rows"].append({"formula": f, "id": ids.get(f), "mp": round(mp[f], 4), "uma": round(uma[f], 4),
                            "diff": round(uma[f] - mp[f], 4), "polysulfide": f in polys})
    out["available"] = bool(out["rows"])
    if not out["available"]:
        out["reason"] = "no known compound with both energies"
    out["compounds"] = _stats([r["diff"] for r in out["rows"]])
    out["polysulfides"] = _stats([r["diff"] for r in out["rows"] if r["polysulfide"]])
    return out


def cached_system_errors(elements: Iterable[str], ehull_max: float = config.MP_REF_EHULL_MAX) -> dict:
    """system_errors with a disk cache (config.CACHE_DIR / uma_errors), recomputed only when missing; `ehull_max`: the
    hull references of the domain (the cathode domain uses the stable phases only)."""
    from autolab.data.mp import chemsys_key
    from autolab.store.cache import JsonCache

    cache = JsonCache(config.CACHE_DIR / "uma_errors")
    key = chemsys_key(sorted(set(elements))) + ("" if ehull_max == config.MP_REF_EHULL_MAX else f"_e{ehull_max}")
    hit = cache.get(key)
    if hit is not None:
        return hit
    res = system_errors(elements, ehull_max=ehull_max)
    if res["available"]:  # an unavailable system may become available once its references are relaxed
        cache.set(key, res)
    return res


def ehull_uncertainty(formula: str, errors: Callable[[list[str]], dict] = cached_system_errors) -> dict | None:
    """Error bar of a candidate's E_hull: mean absolute UMA-vs-MP difference on the known compounds of its system
    (eV/atom), with their number, the largest difference and the mean signed difference; None when not available."""
    from pymatgen.core import Composition

    try:
        res = errors([el.symbol for el in Composition(formula).elements])
    except Exception as e:  # e.g. MP unreachable: the E_hull stays, without its error bar
        return {"available": False, "reason": f"{type(e).__name__}: {e}"[:200]}
    s = res.get("compounds") or {}
    if not res.get("available") or not s.get("n"):
        return None
    return {"system": res["system"], "mae_eV_per_atom": s["mae"], "max_abs_eV_per_atom": s["max_abs"], "n": s["n"],
            "bias_eV_per_atom": s["bias"]}
