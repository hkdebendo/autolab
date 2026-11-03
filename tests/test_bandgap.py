"""Truth tests for analysis/bandgap.py (SPEC 5.8, section 7): the closed-shell rule, and the DFT gap's cache.

The DFT itself runs on Modal (scripts/dft_gap_truth_test.py, results/2026-11-03_dft_gap_truth); here it is a stand-in.
"""

import json

from pymatgen.core import Element, Lattice, Structure

from autolab import config
from autolab.analysis import bandgap
from autolab.analysis.bandgap import closed_shell_check, dft_gap, oxidation_table


def rocksalt(a, b, lat=5.0):
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(lat), [a, b], [[0, 0, 0], [0.5, 0.5, 0.5]])


def test_every_ion_of_the_domain_tables_has_a_closed_shell():
    table = oxidation_table()
    assert {"Li", "Na", "P", "S", "W", "Sb", "Zr"} <= set(table)
    assert all(Element(el).Z - ox in config.CLOSED_SHELL_ELECTRONS for el, ox in table.items())


def test_open_shell_ions_and_unknown_elements_fail():
    assert closed_shell_check(rocksalt("Li", "Cl"))["passes"] is True
    feo = closed_shell_check(rocksalt("Fe", "O"), {"Fe": 2, "O": -2})  # Fe2+: 24 electrons, partly filled 3d
    assert feo["passes"] is False and feo["open_shell"] == ["Fe"] and feo["ions"]["Fe"]["electrons"] == 24
    assert closed_shell_check(rocksalt("Co", "O"))["open_shell"] == ["Co"]  # not in any table


def test_dft_gap_is_computed_once_then_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DFT_GAP_CACHE_DIR", tmp_path)
    calls = []

    def remote(atoms, **settings):
        calls.append(settings)
        return {"gap_eV": 3.4012, "seconds": 42.0, "n_atoms": len(atoms["numbers"])}

    s = rocksalt("Li", "Cl")
    first = dft_gap(s, remote=remote)
    again = dft_gap(s, remote=remote)
    assert (first["gap_eV"], first["cached"], again["cached"]) == (3.401, False, True) and len(calls) == 1
    assert calls[0] == {"ecut": config.DFT_GAP_ECUT_EV, "kdensity": config.DFT_GAP_KDENSITY,
                        "smearing": config.DFT_GAP_SMEARING_EV, "path_points": config.DFT_GAP_PATH_POINTS}
    assert json.loads((tmp_path / "pbe_gpaw.json").read_text())[bandgap.dft_key(s)]["method"].startswith("GPAW")


def test_dft_gap_refuses_a_too_large_cell(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DFT_GAP_CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "DFT_GAP_MAX_ATOMS", 1)
    try:
        dft_gap(rocksalt("Li", "Cl"), remote=lambda *a, **k: 1 / 0)
    except ValueError as e:
        assert "DFT_GAP_MAX_ATOMS" in str(e)
    else:
        raise AssertionError("expected a refusal")
