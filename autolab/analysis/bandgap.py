"""Electronic insulation (SPEC 5.8): a closed-shell rule in the funnel, a DFT band gap for the champion.

No machine-learning model: every model called at run time must be a Meta model (organisers' rule, 2026-11-03).
- Funnel: every ion, at its fixed oxidation state, must have a closed electron shell (config.CLOSED_SHELL_ELECTRONS).
- Champion: PBE band gap with GPAW on Modal CPU (modal_app/dft_app.py), cached by structure and settings.
Gaps recorded before 2026-11-03 (fields gap_optb88 / gap_mbj) were GapModel predictions; they stay in the cache.
"""

from __future__ import annotations

import hashlib
import json

from pymatgen.core import Structure

from autolab import config
from autolab.sim.serialize import KEY_GRID


def structure_hash(structure: Structure) -> str:
    """Fingerprint of a structure, stable across machines (values snapped to KEY_GRID)."""
    payload = {
        "lattice": [[round(x * KEY_GRID) for x in row] for row in structure.lattice.matrix.tolist()],
        "species": [site.specie.symbol for site in structure],
        "coords": [[round(x * KEY_GRID) % KEY_GRID for x in fc] for fc in structure.frac_coords.tolist()],
    }
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def oxidation_table() -> dict[str, int]:
    """Fixed oxidation states of every domain's electrolytes (the lithium and sodium tables agree where they meet)."""
    table = dict(config.OXIDATION_STATES)
    for el, ox in config.SODIUM_OXIDATION_STATES.items():
        if table.setdefault(el, ox) != ox:
            raise ValueError(f"oxidation tables disagree on {el}")
    return table


def closed_shell_check(structure: Structure, table: dict[str, int] | None = None) -> dict:
    """Electrons left on each ion (Z - oxidation state) and whether every shell is closed (no easy electron hopping)."""
    from pymatgen.core import Element

    table = table or oxidation_table()
    ions, open_shell = {}, []
    for el in sorted({site.specie.symbol for site in structure}):
        if el not in table:
            open_shell.append(el)
            continue
        ions[el] = {"charge": table[el], "electrons": Element(el).Z - table[el]}
        if ions[el]["electrons"] not in config.CLOSED_SHELL_ELECTRONS:
            open_shell.append(el)
    return {"rule": "closed_shell", "formula": structure.composition.reduced_formula, "ions": ions,
            "open_shell": open_shell, "passes": not open_shell}


def evaluate_bandgap(structure: Structure) -> dict:
    """The funnel's insulation filter: the closed-shell rule (instant, no model)."""
    return closed_shell_check(structure)


def _dft_settings() -> dict:
    return {"ecut": config.DFT_GAP_ECUT_EV, "kdensity": config.DFT_GAP_KDENSITY, "smearing": config.DFT_GAP_SMEARING_EV,
            "path_points": config.DFT_GAP_PATH_POINTS}


def _dft_cache_path():
    return config.DFT_GAP_CACHE_DIR / "pbe_gpaw.json"


def dft_key(structure: Structure) -> str:
    return f"{structure_hash(structure)}-{hashlib.sha1(json.dumps(_dft_settings(), sort_keys=True).encode()).hexdigest()[:8]}"


def cached_dft_gap(structure: Structure) -> dict | None:
    path = _dft_cache_path()
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    hit = cache.get(dft_key(structure))
    return {**hit, "cached": True} if hit else None


def dft_gap(structure: Structure, remote=None) -> dict:
    """PBE band gap (eV) of one structure with GPAW on Modal, cached: a structure is never computed twice.

    `remote`: the function that computes (default: the deployed Modal function; tests inject a fake)."""
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_to_dict

    hit = cached_dft_gap(structure)
    if hit:
        return hit
    if len(structure) > config.DFT_GAP_MAX_ATOMS:
        raise ValueError(f"{len(structure)} atoms > DFT_GAP_MAX_ATOMS ({config.DFT_GAP_MAX_ATOMS})")
    if remote is None:
        import modal

        remote = modal.Function.from_name(config.DFT_GAP_APP, "pbe_gap").remote
    res = remote(atoms_to_dict(AseAtomsAdaptor.get_atoms(structure)), **_dft_settings())
    res = {**res, "gap_eV": round(float(res["gap_eV"]), 3), "formula": structure.composition.reduced_formula,
           "method": "GPAW PBE plane waves", **{f"setting_{k}": v for k, v in _dft_settings().items()}}
    path = _dft_cache_path()
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cache[dft_key(structure)] = res
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return {**res, "cached": False}
