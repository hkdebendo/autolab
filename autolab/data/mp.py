"""Materials Project access with a mandatory disk cache (SPEC 5.4).

Every network answer is stored under config.MP_CACHE_DIR and reused:
structures by material_id, references and entries by chemical system,
band gaps by material_id.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any, Iterable

from monty.json import MontyDecoder, MontyEncoder
from pymatgen.core import Composition, Structure
from pymatgen.entries.computed_entries import ComputedEntry

from autolab import config


# --- Cache helpers -----------------------------------------------------------

def _read(path: Path) -> Any | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"), cls=MontyDecoder)
    return None


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, cls=MontyEncoder), encoding="utf-8")
    tmp.replace(path)


def _jsonable(value: Any) -> Any:
    """Plain JSON value: dict keys and unknown objects (Element, MPID, AlphaID) become str."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _clean_entries(entries: list[ComputedEntry]) -> list[ComputedEntry]:
    """Make entries JSON round-trippable.

    MP puts Element keys in data["oxidation_states"] and an emmet EntryID object
    in entry_id; its str() is the classic id, e.g. 'mp-561513-GGA'.
    """
    for e in entries:
        e.entry_id = str(e.entry_id)
        e.data = _jsonable(e.data)
    return entries


def _rester():
    from mp_api.client import MPRester

    return MPRester(config.require_key("MP_API_KEY"), mute_progress_bars=True)


# --- Chemical systems --------------------------------------------------------

def chemsys_key(elements: Iterable[str]) -> str:
    """Canonical chemical system string, e.g. ['S', 'Li', 'P'] -> 'Li-P-S'."""
    return "-".join(sorted(set(elements)))


def subsystems(elements: Iterable[str]) -> list[str]:
    """All sub-systems with 1 to n elements, e.g. Li-S -> ['Li', 'S', 'Li-S']."""
    els = sorted(set(elements))
    return [chemsys_key(c) for n in range(1, len(els) + 1) for c in itertools.combinations(els, n)]


# --- Public API --------------------------------------------------------------

def get_structure(material_id: str) -> Structure:
    """Structure of one MP material (cached by material_id)."""
    path = config.MP_CACHE_DIR / "structures" / f"{material_id}.json"
    cached = _read(path)
    if cached is not None:
        return cached
    with _rester() as mpr:
        structure = mpr.get_structure_by_material_id(material_id)
    _write(path, structure)
    return structure


def _pure_elements(refs: list[dict]) -> set[str]:
    """Elements that have at least one pure phase among the references."""
    return {str(els[0]) for r in refs if len(els := Composition(r["formula"]).elements) == 1}


def get_references(
    elements: Iterable[str],
    ehull_max: float = config.MP_REF_EHULL_MAX,
    max_sites: int = config.MP_REF_MAX_SITES,
) -> list[dict]:
    """Near-hull MP phases of a chemical system and all its sub-systems.

    These structures are the hull references to be relaxed by UMA; their MP
    energies are not returned on purpose (never mix UMA and MP energies).
    A strict `ehull_max` can leave an element without a pure phase (the on-hull P
    of MP has more than `max_sites` sites): its most stable pure phase within
    config.MP_REF_EHULL_MAX and `max_sites` is then added, so every hull has its terminals.
    """
    elements = sorted(set(elements))
    refs = _fetch_references(elements, ehull_max, max_sites)
    if ehull_max < config.MP_REF_EHULL_MAX:
        for el in sorted(set(elements) - _pure_elements(refs)):
            pure = _fetch_references([el], config.MP_REF_EHULL_MAX, max_sites)
            if pure:
                refs = [*refs, min(pure, key=lambda r: (r["mp_energy_above_hull"], r["material_id"]))]
    return refs


def _fetch_references(elements: list[str], ehull_max: float, max_sites: int) -> list[dict]:
    """MP phases of a system and its sub-systems up to `ehull_max` (one request, cached)."""
    key = chemsys_key(elements)
    path = config.MP_CACHE_DIR / "references" / f"{key}_e{ehull_max}_n{max_sites}.json"
    cached = _read(path)
    if cached is not None:
        return cached
    with _rester() as mpr:
        docs = mpr.materials.summary.search(
            chemsys=subsystems(elements),
            energy_above_hull=(0, ehull_max),
            num_sites=(1, max_sites),
            fields=["material_id", "formula_pretty", "structure", "energy_above_hull", "nsites"],
        )
    refs = [
        {
            "material_id": str(d.material_id),
            "formula": d.formula_pretty,
            "mp_energy_above_hull": d.energy_above_hull,
            "nsites": d.nsites,
            "structure": d.structure,
        }
        for d in docs
    ]
    refs.sort(key=lambda r: (r["formula"], r["mp_energy_above_hull"], r["material_id"]))
    _write(path, refs)
    return refs


def get_entries(elements: Iterable[str]) -> list[ComputedEntry]:
    """MP GGA/GGA+U entries of a chemical system (all sub-systems included).

    Reuses a cached super-system when one exists, to avoid a new request.
    """
    wanted = set(elements)
    folder = config.MP_CACHE_DIR / "entries"
    path = folder / f"{chemsys_key(wanted)}.json"
    cached = _read(path)
    if cached is not None:
        return cached
    if folder.exists():
        for other in folder.glob("*.json"):
            if wanted <= set(other.stem.split("-")):
                return [e for e in _read(other) if {el.symbol for el in e.composition.elements} <= wanted]
    with _rester() as mpr:
        entries = mpr.get_entries_in_chemsys(
            sorted(wanted), additional_criteria={"thermo_types": config.MP_THERMO_TYPES}
        )
    entries = _clean_entries(entries)
    _write(path, entries)
    return entries


def material_id_of(label: str) -> str:
    """MP material id from an entry id or name, e.g. 'mp-1153-GGA' -> 'mp-1153'."""
    return "-".join(str(label).split("-")[:2])


def get_band_gaps(material_ids: Iterable[str]) -> dict[str, float | None]:
    """MP band gaps (eV), fetched in one request for the ids not yet cached."""
    path = config.MP_CACHE_DIR / "band_gaps.json"
    cache: dict[str, float | None] = _read(path) or {}
    ids = sorted(set(material_ids))
    missing = [m for m in ids if m not in cache]
    if missing:
        with _rester() as mpr:
            docs = mpr.materials.summary.search(material_ids=missing, fields=["material_id", "band_gap"])
        for d in docs:
            cache[str(d.material_id)] = d.band_gap
        for m in missing:
            cache.setdefault(m, None)
        _write(path, cache)
    return {m: cache[m] for m in ids}


def formula_key(formula: str) -> str:
    """Canonical reduced formula, e.g. 'NaLi11(PS4)4' -> 'Li11NaP4S16'."""
    comp = Composition(formula).reduced_composition
    return "".join(f"{el.symbol}{'' if n == 1 else int(n)}" for el, n in sorted(comp.items(), key=lambda x: x[0].symbol))


def known_formulas(formulas: Iterable[str]) -> dict[str, list[dict]]:
    """Materials Project materials with the same reduced composition as each formula.

    One batched request for the formulas not yet cached; [] means none in MP.
    `theoretical` is False when MP links the material to an experimental (ICSD) entry.
    """
    path = config.MP_CACHE_DIR / "formulas.json"
    cache: dict[str, list[dict]] = _read(path) or {}
    keys = {f: formula_key(f) for f in formulas}
    missing = sorted({k for k in keys.values() if k not in cache})
    if missing:
        with _rester() as mpr:
            docs = mpr.materials.summary.search(
                formula=missing, fields=["material_id", "formula_pretty", "energy_above_hull", "theoretical"])
        for k in missing:
            cache[k] = []
        for d in docs:
            k = formula_key(d.formula_pretty)
            if k in cache:
                cache[k].append({"material_id": str(d.material_id), "energy_above_hull": d.energy_above_hull,
                                 "theoretical": d.theoretical})
        _write(path, cache)
    return {f: cache[k] for f, k in keys.items()}
