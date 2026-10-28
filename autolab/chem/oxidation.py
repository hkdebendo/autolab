"""Fixed oxidation states and charge neutrality (SPEC 5.1)."""

from __future__ import annotations

from pymatgen.core import Composition, Structure

from autolab import config


def _composition(obj: Structure | Composition | str) -> Composition:
    if isinstance(obj, Structure):
        return obj.composition
    return Composition(obj)


def unsupported_elements(obj: Structure | Composition | str) -> list[str]:
    """Elements absent from the fixed closed-shell oxidation table."""
    comp = _composition(obj)
    return sorted(el.symbol for el in comp.elements if el.symbol not in config.OXIDATION_STATES)


def total_charge(obj: Structure | Composition | str) -> float:
    """Sum of fixed oxidation states; raises ValueError on an unsupported element."""
    bad = unsupported_elements(obj)
    if bad:
        raise ValueError(f"unsupported elements: {', '.join(bad)}")
    comp = _composition(obj)
    return float(sum(config.OXIDATION_STATES[el.symbol] * amt for el, amt in comp.items()))


def is_neutral(obj: Structure | Composition | str) -> bool:
    """True if every element is supported and the charges sum to zero."""
    if unsupported_elements(obj):
        return False
    return abs(total_charge(obj)) < config.CHARGE_TOLERANCE


def check_charge(obj: Structure | Composition | str) -> dict:
    """JSON-serialisable verdict: ok, charge, unsupported elements, reason."""
    bad = unsupported_elements(obj)
    if bad:
        return {"ok": False, "charge": None, "unsupported": bad,
                "reason": f"elements outside the closed-shell table: {', '.join(bad)}"}
    charge = total_charge(obj)
    if abs(charge) >= config.CHARGE_TOLERANCE:
        return {"ok": False, "charge": charge, "unsupported": [],
                "reason": f"not charge neutral (total charge {charge:+g})"}
    return {"ok": True, "charge": charge, "unsupported": [], "reason": None}
