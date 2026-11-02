"""Fixed oxidation states and charge neutrality (SPEC 5.1)."""

from __future__ import annotations

from pymatgen.core import Composition, Structure

from autolab import config


def _composition(obj: Structure | Composition | str) -> Composition:
    if isinstance(obj, Structure):
        return obj.composition
    return Composition(obj)


def unsupported_elements(obj: Structure | Composition | str, table: dict | None = None) -> list[str]:
    """Elements absent from the fixed closed-shell oxidation table (config.OXIDATION_STATES unless given)."""
    table = table or config.OXIDATION_STATES
    comp = _composition(obj)
    return sorted(el.symbol for el in comp.elements if el.symbol not in table)


def total_charge(obj: Structure | Composition | str, table: dict | None = None) -> float:
    """Sum of fixed oxidation states; raises ValueError on an unsupported element."""
    table = table or config.OXIDATION_STATES
    bad = unsupported_elements(obj, table)
    if bad:
        raise ValueError(f"unsupported elements: {', '.join(bad)}")
    comp = _composition(obj)
    return float(sum(table[el.symbol] * amt for el, amt in comp.items()))


def is_neutral(obj: Structure | Composition | str) -> bool:
    """True if every element is supported and the charges sum to zero."""
    if unsupported_elements(obj):
        return False
    return abs(total_charge(obj)) < config.CHARGE_TOLERANCE


def check_charge(obj: Structure | Composition | str, table: dict | None = None) -> dict:
    """JSON-serialisable verdict: ok, charge, unsupported elements, reason (`table`: a domain's oxidation states)."""
    bad = unsupported_elements(obj, table)
    if bad:
        return {"ok": False, "charge": None, "unsupported": bad,
                "reason": f"elements outside the closed-shell table: {', '.join(bad)}"}
    charge = total_charge(obj, table)
    if abs(charge) >= config.CHARGE_TOLERANCE:
        return {"ok": False, "charge": charge, "unsupported": [],
                "reason": f"not charge neutral (total charge {charge:+g})"}
    return {"ok": True, "charge": charge, "unsupported": [], "reason": None}
