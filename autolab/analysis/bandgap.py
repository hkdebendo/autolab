"""Band gap with ALIGNN2 pretrained models, CPU, no DGL (SPEC 5.8).

Filter on optb88vdw_bandgap_knn (PBE-like scale, threshold BANDGAP_MIN);
display mbj_bandgap_knn (closer to experiment).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import warnings
from functools import lru_cache

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


def _to_jarvis(structure: Structure):
    from jarvis.core.atoms import Atoms as JAtoms

    return JAtoms(
        lattice_mat=structure.lattice.matrix,
        coords=structure.frac_coords,
        elements=[site.specie.symbol for site in structure],
        cartesian=False,
    )


@contextlib.contextmanager
def _quiet():
    """Silence ALIGNN's repetitive prints and warnings."""
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        warnings.simplefilter("ignore")
        yield


@lru_cache(maxsize=None)
def _alignn():
    """alignn.pretrained, imported once without its pydantic deprecation noise."""
    with _quiet():
        import alignn.pretrained as ap
    return ap


@lru_cache(maxsize=None)
def _model_dir(model_name: str) -> str:
    """Folder of a pretrained ALIGNN2 model (downloaded once by alignn, then reused)."""
    with _quiet():
        return os.path.dirname(_alignn().get_alignn2_model(model_name)["best_model.pt"])


def _cache_path(model_name: str):
    return config.BANDGAP_CACHE_DIR / f"{model_name}.json"


def predict_gap(structure: Structure, model_name: str) -> float:
    """Band gap (eV) predicted by one ALIGNN2 model, cached by structure hash."""
    path = _cache_path(model_name)
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    key = structure_hash(structure)
    if key not in cache:
        folder = _model_dir(model_name)
        with _quiet():
            gap = _alignn().get_prediction_pure(model_name=folder, atoms=_to_jarvis(structure))[0]
        cache[key] = float(gap)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
    return cache[key]


def evaluate_bandgap(structure: Structure) -> dict:
    """Filter gap (optb88), displayed gap (mbj), pass/fail and confidence.

    Raw predictions can be slightly negative for metals; reported gaps are clipped at 0.
    """
    filter_gap = max(predict_gap(structure, config.BANDGAP_FILTER_MODEL), 0.0)
    display_gap = max(predict_gap(structure, config.BANDGAP_DISPLAY_MODEL), 0.0)
    insulating_filter = filter_gap >= config.BANDGAP_MIN
    insulating_display = display_gap >= config.BANDGAP_MIN
    return {
        "formula": structure.composition.reduced_formula,
        "gap_optb88": round(filter_gap, 3),
        "gap_mbj": round(display_gap, 3),
        "passes": insulating_filter,
        "low_confidence": insulating_filter != insulating_display,
    }
