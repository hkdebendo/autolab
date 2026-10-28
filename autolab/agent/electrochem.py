"""Electrode checks with UMA energies (step 9): window, passivation, cathode interfaces, calibrations.

UMA and MP energies are never mixed: each phase diagram uses one source only.
Interfaces use on-hull MP structures only (config.INTERFACE_REF_EHULL_MAX), relaxed by UMA.
"""

from __future__ import annotations

from typing import Callable

from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Composition

from autolab import config
from autolab.analysis.electrodes import cathode_interface, electrochemical_window, passivation
from autolab.analysis.stability import make_entry


def candidate_entry(c: dict):
    """UMA entry of a candidate from its funnel result (best relaxed cell and its total energy)."""
    from autolab.sim.serialize import atoms_from_dict

    comp = Composition(atoms_from_dict(c["relaxed_atoms"]).get_chemical_formula())
    return make_entry(comp, c["energy"], c["id"], "uma")


def _elements(*formulas) -> list[str]:
    return sorted({el.symbol for f in formulas for el in Composition(f).elements})


def _default_entries(elements, budget, ehull_max=config.MP_REF_EHULL_MAX):
    from autolab.analysis.stability import uma_reference_entries

    return uma_reference_entries(elements, budget=budget, ehull_max=ehull_max)


def _mp_gaps(ids: list[str]) -> dict:
    """MP band gaps for MP ids only (candidate entries have no MP id)."""
    from autolab.data.mp import get_band_gaps

    return get_band_gaps([i for i in ids if i.startswith("mp-")])


def window_and_passivation(c: dict, entries_fn: Callable = _default_entries, get_gaps: Callable = _mp_gaps,
                           budget=None) -> dict:
    """Electrochemical window and passivation against Li metal, with UMA references of the candidate's system."""
    target = candidate_entry(c)
    entries, skipped = entries_fn(_elements(target.composition), budget)
    return {"id": c["id"], "formula": target.composition.reduced_formula,
            "window": electrochemical_window(target, entries),
            "passivation": passivation(target, entries, get_gaps), "skipped_references": skipped}


def li3ps4_window_calibration(entries_fn: Callable = _default_entries, budget=None) -> dict:
    """Li3PS4 (mp-985583) window with UMA energies, to compare with the MP result."""
    entries, _ = entries_fn(["Li", "P", "S"], budget)
    target = next(e for e in entries if e.name == "mp-985583")
    win = electrochemical_window(target, entries)
    lo, hi = config.LI3PS4_WINDOW_MP
    return {**win, "mp_v_low": lo, "mp_v_high": hi,
            "diff_low": None if win["v_low"] is None else round(win["v_low"] - lo, 3),
            "diff_high": None if win["v_high"] is None else round(win["v_high"] - hi, 3)}


def uma_interface(electrolyte, cathode: str, entries_fn: Callable = _default_entries, budget=None) -> dict:
    """Interface reaction with a cathode, UMA energies (on-hull MP structures of the joint system).

    `electrolyte` is a candidate result dict or a formula.
    """
    extra = [candidate_entry(electrolyte)] if isinstance(electrolyte, dict) else []
    comp = extra[0].composition if extra else Composition(electrolyte)
    entries, skipped = entries_fn(_elements(comp, cathode), budget, ehull_max=config.INTERFACE_REF_EHULL_MAX)
    res = cathode_interface(comp, cathode, PhaseDiagram([*entries, *extra]))
    return {**res, "source": "uma", "references": len(entries), "skipped_references": skipped}


def mp_interface(electrolyte: str, cathode: str, get_entries: Callable | None = None) -> dict:
    """Same interface with MP energies (all GGA/GGA+U entries), for calibration only."""
    if get_entries is None:
        from autolab.data.mp import get_entries
    entries = get_entries(_elements(electrolyte, cathode))
    return {**cathode_interface(electrolyte, cathode, PhaseDiagram(entries)), "source": "mp",
            "references": len(entries)}


def interface_calibration(cathode: str, electrolyte: str = "Li3PS4", entries_fn: Callable = _default_entries,
                          get_entries: Callable | None = None, budget=None) -> dict:
    """UMA vs MP reaction energy for a known electrolyte/cathode pair; ok when within the tolerance."""
    uma = uma_interface(electrolyte, cathode, entries_fn, budget)
    mp = mp_interface(electrolyte, cathode, get_entries)
    diff = uma["min_reaction_energy"] - mp["min_reaction_energy"]
    return {"electrolyte": electrolyte, "cathode": cathode, "uma": uma, "mp": mp, "diff": round(diff, 4),
            "ok": abs(diff) <= config.INTERFACE_CALIBRATION_MAX_DIFF,
            "tolerance": config.INTERFACE_CALIBRATION_MAX_DIFF}
