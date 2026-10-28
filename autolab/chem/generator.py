"""Substitutions -> candidate structures (SPEC 5.2).

Substitution format:
    {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}   partial, random sites
    {"remove": "P", "add": "Sb", "count": "all"}                   total
"""

from __future__ import annotations

import random

from pymatgen.analysis.structure_matcher import StructureMatcher
from pymatgen.core import Element, Structure

from autolab import config
from autolab.chem.oxidation import check_charge


def _sites_of(structure: Structure, symbol: str) -> list[int]:
    return [i for i, site in enumerate(structure) if site.specie.symbol == symbol]


def _validate(structure: Structure, sub: dict) -> str | None:
    """Return a rejection reason, or None if the substitution can be applied."""
    remove, add, count = sub.get("remove"), sub.get("add"), sub.get("count")
    vacancies = sub.get("li_vacancies", 0)
    if not remove or not add:
        return "substitution needs 'remove' and 'add'"
    for symbol in (remove, add):
        if not Element.is_valid_symbol(symbol):
            return f"unknown element {symbol!r}"
    n_remove = len(_sites_of(structure, remove))
    if n_remove == 0:
        return f"{remove} is not in the parent structure"
    if count != "all" and (not isinstance(count, int) or not 1 <= count <= n_remove):
        return f"count must be 'all' or an integer between 1 and {n_remove}"
    if not isinstance(vacancies, int) or vacancies < 0:
        return "li_vacancies must be a non-negative integer"
    n_replaced = n_remove if count == "all" else count
    n_li = len(_sites_of(structure, "Li")) - n_replaced * (remove == "Li") + n_replaced * (add == "Li")
    if vacancies > n_li:
        return f"cannot remove {vacancies} Li: only {n_li} left"
    return None


def _arrangement(parent: Structure, sub: dict, rng: random.Random) -> Structure:
    s = parent.copy()
    if sub["count"] == "all":
        s.replace_species({sub["remove"]: sub["add"]})
    else:
        for i in rng.sample(_sites_of(s, sub["remove"]), sub["count"]):
            s.replace(i, sub["add"])
    vacancies = sub.get("li_vacancies", 0)
    if vacancies:
        s.remove_sites(rng.sample(_sites_of(s, "Li"), vacancies))
    return s


def generate_candidates(
    parent: Structure,
    substitution: dict,
    parent_id: str | None = None,
    n_arrangements: int = config.GENERATOR_N_ARRANGEMENTS,
    seed: int = config.GENERATOR_SEED,
) -> dict:
    """Apply a substitution and return distinct, charge-checked arrangements.

    A rejected candidate (bad substitution, unsupported element, non-neutral)
    has accepted=False, a reason and no structures.
    """
    result = {
        "parent": parent_id,
        "parent_formula": parent.composition.reduced_formula,
        "substitution": substitution,
        "seed": seed,
        "accepted": False,
        "reason": None,
        "formula": None,
        "charge": None,
        "candidates": [],
    }
    reason = _validate(parent, substitution)
    if reason:
        result["reason"] = reason
        return result

    randomised = substitution["count"] != "all" or substitution.get("li_vacancies", 0) > 0
    rng = random.Random(seed)
    structures = [_arrangement(parent, substitution, rng) for _ in range(n_arrangements if randomised else 1)]

    # All arrangements share one composition: neutrality is checked once, before any UMA call.
    verdict = check_charge(structures[0])
    result["formula"] = structures[0].composition.reduced_formula
    result["charge"] = verdict["charge"]
    if not verdict["ok"]:
        result["reason"] = verdict["reason"]
        return result

    distinct = [group[0] for group in StructureMatcher().group_structures(structures)]
    result["accepted"] = True
    result["candidates"] = [
        {"arrangement": k, "formula": s.composition.formula, "structure": s.as_dict()}
        for k, s in enumerate(distinct)
    ]
    return result
