"""Cathode properties from UMA energies (second domain, cobalt-free cathodes): charge neutrality with mixed valence,
how much Li can be removed, average voltage, theoretical capacity, energy density and volume change.

Average voltage of the reaction Li_n H -> Li_(n-k) H + k Li (metal), per removed Li:
    V = -(E[Li_n H] - E[Li_(n-k) H] - k E[Li]) / k        (eV per Li = V vs Li/Li+)
with every energy from UMA (the MP2020 corrections of O and of the transition metals cancel: same atoms on both
sides; Li has none). Theoretical capacity: k F / (3.6 M) in mAh/g, M the molar mass of the lithiated cell.
"""

from __future__ import annotations

from pymatgen.core import Composition, Structure

from autolab import config

FARADAY = 96485.33212  # C/mol


def _composition(obj) -> Composition:
    return obj.composition if isinstance(obj, Structure) else Composition(obj)


def charge_range(obj, ranges: dict = config.CATHODE_OXIDATION_RANGES) -> tuple[float, float] | None:
    """Lowest and highest total charge allowed by the oxidation ranges; None if an element is not in the table."""
    comp = _composition(obj)
    if any(el.symbol not in ranges for el in comp.elements):
        return None
    low = sum(ranges[el.symbol][0] * n for el, n in comp.items())
    high = sum(ranges[el.symbol][1] * n for el, n in comp.items())
    return float(low), float(high)


def cathode_charge_check(obj, ranges: dict = config.CATHODE_OXIDATION_RANGES) -> dict:
    """Verdict in the format of chem.oxidation.check_charge: neutral when 0 lies in the allowed charge range (every
    range is contiguous, so mixed valence covers every integer in between); cobalt is refused (cobalt-free)."""
    comp = _composition(obj)
    forbidden = sorted(el.symbol for el in comp.elements if el.symbol in config.CATHODE_FORBIDDEN)
    if forbidden:
        return {"ok": False, "charge": None, "unsupported": forbidden,
                "reason": f"{', '.join(forbidden)} is excluded: the cathodes searched are cobalt-free"}
    bounds = charge_range(comp, ranges)
    if bounds is None:
        bad = sorted(el.symbol for el in comp.elements if el.symbol not in ranges)
        return {"ok": False, "charge": None, "unsupported": bad,
                "reason": f"elements outside the cathode oxidation table: {', '.join(bad)}"}
    low, high = bounds
    if not low - config.CHARGE_TOLERANCE <= 0 <= high + config.CHARGE_TOLERANCE:
        return {"ok": False, "charge": low if low > 0 else high, "unsupported": [],
                "reason": f"cannot be charge neutral (total charge between {low:+g} and {high:+g})"}
    return {"ok": True, "charge": 0.0, "unsupported": [], "reason": None}


def removable_li(obj, ranges: dict = config.CATHODE_OXIDATION_RANGES) -> int:
    """How many Li can leave the cell while it stays neutral: the other elements must be able to rise in oxidation
    state to compensate (oxygen fixed at -2). k = min(n_Li, n_Li + highest charge of the rest)."""
    comp = _composition(obj)
    n_li = int(round(comp["Li"]))
    rest = Composition({el: n for el, n in comp.items() if el.symbol != "Li"})
    bounds = charge_range(rest, ranges)
    if bounds is None or n_li == 0:
        return 0
    return max(0, min(n_li, int(n_li + bounds[1] + config.CHARGE_TOLERANCE)))


def average_voltage(e_lith: float, e_delith: float, k: int, e_li: float) -> float:
    """Average voltage (V vs Li/Li+) for removing k Li, from total energies (eV) and the energy of one Li in Li metal."""
    if k <= 0:
        raise ValueError("no Li removed")
    return -(e_lith - e_delith - k * e_li) / k


def capacity_mAh_g(lithiated, k: int) -> float:
    """Theoretical gravimetric capacity of removing k Li from the lithiated cell (mAh per gram of lithiated cathode)."""
    mass = _composition(lithiated).weight  # g/mol of the cell
    return k * FARADAY / (3.6 * float(mass))


def volume_change_pct(v_lith: float, v_delith: float) -> float:
    """Volume change on charge, in % of the lithiated volume (positive = the cell shrinks when Li leaves)."""
    return 100.0 * (v_lith - v_delith) / v_lith


def energy_density_Wh_kg(voltage: float, capacity: float) -> float:
    """Gravimetric energy density of the cathode material alone (Wh/kg = V x mAh/g)."""
    return voltage * capacity
