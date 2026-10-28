"""Tests for data/mp.py: references, entries, band gaps and the disk cache (SPEC 5.4)."""

import pytest

from autolab import config
from autolab.data import mp
from conftest import requires_mp


def test_subsystems():
    assert mp.subsystems(["S", "Li"]) == ["Li", "S", "Li-S"]
    assert len(mp.subsystems(["Li", "P", "S"])) == 7
    assert mp.chemsys_key(["S", "P", "Li", "S"]) == "Li-P-S"


def test_material_id_of():
    assert mp.material_id_of("mp-1153-GGA") == "mp-1153"
    assert mp.material_id_of("mp-1153") == "mp-1153"


def test_jsonable_handles_element_keys():
    from pymatgen.core import Element

    assert mp._jsonable({Element("S"): 0.0, "ids": (1, Element("Li"))}) == {"S": 0.0, "ids": [1, "Li"]}


def _no_network(monkeypatch):
    def fail():
        raise AssertionError("network call while the answer should come from the cache")

    monkeypatch.setattr(mp, "_rester", fail)


@requires_mp
def test_references_li_s(monkeypatch):
    refs = mp.get_references(["Li", "S"])
    formulas = {r["formula"] for r in refs}
    assert {"Li", "S", "Li2S"} <= formulas
    assert all(r["mp_energy_above_hull"] <= config.MP_REF_EHULL_MAX for r in refs)
    assert all(r["nsites"] <= config.MP_REF_MAX_SITES for r in refs)
    assert all("energy" not in k for r in refs for k in r if k != "mp_energy_above_hull")
    _no_network(monkeypatch)
    assert mp.get_references(["S", "Li"]) == refs


@requires_mp
def test_entries_li_s_and_cache(monkeypatch):
    entries = mp.get_entries(["Li", "S"])
    assert any(e.composition.reduced_formula == "Li2S" for e in entries)
    assert all(str(e.entry_id).startswith("mp-") for e in entries)
    _no_network(monkeypatch)
    assert len(mp.get_entries(["Li", "S"])) == len(entries)
    assert all(e.composition.reduced_formula == "Li" for e in mp.get_entries(["Li"]))


@requires_mp
def test_band_gaps(monkeypatch):
    li2s = next(r["material_id"] for r in mp.get_references(["Li", "S"]) if r["formula"] == "Li2S")
    gaps = mp.get_band_gaps([li2s, "mp-135"])  # mp-135: Li metal
    assert gaps[li2s] > 3.0
    assert gaps["mp-135"] == pytest.approx(0.0, abs=1e-6)
    _no_network(monkeypatch)
    assert mp.get_band_gaps([li2s]) == {li2s: gaps[li2s]}
