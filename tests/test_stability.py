"""Tests for analysis/stability.py with Materials Project energies (SPEC 5.7).

The UMA-energy truth tests (Li2S, fictitious rocksalt LiS, Li3PS4) come with sim/ (step 6).
"""

import pytest

from autolab.analysis.stability import e_hull, make_entry, phase_diagram
from autolab.data import mp
from conftest import requires_mp


def _by_id(entries, material_id):
    return next(e for e in entries if mp.material_id_of(e.entry_id) == material_id)


def _lowest(entries, formula):
    return min((e for e in entries if e.composition.reduced_formula == formula), key=lambda e: e.energy_per_atom)


def test_mixing_uma_and_mp_energies_is_refused():
    entries = [make_entry("Li", -1.9, "Li", "uma"), make_entry("S", -4.1, "S", "mp")]
    with pytest.raises(ValueError, match="one known energy source"):
        phase_diagram(entries)


def test_toy_hull():
    entries = [make_entry("Li", -2.0, "Li", "uma"), make_entry("S", -4.0, "S", "uma"),
               make_entry("Li2S", 3 * -4.0, "Li2S", "uma")]
    above = make_entry("LiS", 2 * -3.0 + 0.6, "LiS-fake", "uma")
    out = e_hull(above, entries)
    assert out["e_hull"] > 0.25 and not out["synthesizable"]
    assert {d["formula"] for d in out["decomposition"]} == {"Li2S", "S"}


@requires_mp
def test_li2s_on_hull_mp():
    entries = mp.get_entries(["Li", "S"])
    out = e_hull(_lowest(entries, "Li2S"), entries)
    print(f"\nLi2S E_hull (MP) = {out['e_hull']}")
    assert out["e_hull"] <= 0.005


@requires_mp
def test_li3ps4_calibration_mp():
    entries = mp.get_entries(["Li", "P", "S"])
    out = e_hull(_by_id(entries, "mp-985583"), entries)
    print(f"\nLi3PS4 mp-985583 E_hull (MP) = {out['e_hull']}")
    assert out["e_hull"] <= 0.01 and out["very_good"]
