"""Truth tests for analysis/electrodes.py with Materials Project energies (SPEC 5.9, section 7)."""

import pytest
from pymatgen.core import Composition

from autolab.analysis.electrodes import cathode_interface, electrochemical_window, passivation
from autolab.analysis.stability import phase_diagram
from autolab.data import mp
from conftest import requires_mp

pytestmark = requires_mp


def _by_id(entries, material_id):
    return next(e for e in entries if mp.material_id_of(e.entry_id) == material_id)


def _lowest(entries, formula):
    target = Composition(formula).reduced_composition
    return min((e for e in entries if e.composition.reduced_composition == target), key=lambda e: e.energy_per_atom)


def test_window_li3ps4():
    entries = mp.get_entries(["Li", "P", "S"])
    out = electrochemical_window(_by_id(entries, "mp-985583"), entries)
    print(f"\nLi3PS4 window: {out['v_low']} - {out['v_high']} V (published 1.71 - 2.31)")
    assert 1.6 <= out["v_low"] <= 1.9
    assert 2.2 <= out["v_high"] <= 2.5
    assert out["contiguous"]


def test_passivation_lgps():
    entries = mp.get_entries(["Li", "Ge", "P", "S"])
    out = passivation(_lowest(entries, "Li10GeP2S12"), entries)
    print(f"\nLGPS at 0 V: {out}")
    assert out["verdict"] == "non_passivating"
    assert "Li15Ge4" in out["metallic_products"]


def test_passivation_llzo():
    entries = mp.get_entries(["Li", "La", "Zr", "O"])
    out = passivation(_lowest(entries, "Li7La3Zr2O12"), entries)
    print(f"\nLLZO at 0 V: {out}")
    assert out["verdict"] == "quasi_stable"


def test_interface_li3ps4_licoo2():
    entries = mp.get_entries(["Li", "P", "S", "Co", "O"])
    out = cathode_interface("Li3PS4", "LiCoO2", phase_diagram(entries))
    print(f"\nLi3PS4 / LiCoO2: {out['min_reaction_energy']} eV/atom (validated -0.416)")
    assert out["min_reaction_energy"] == pytest.approx(-0.416, abs=0.02)
