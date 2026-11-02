"""UMA-vs-DFT error bars (analysis.uma_errors) and the window sensitivity to polysulfide energies
(analysis.electrodes.window_sensitivity): toy entries, no network, no UMA."""

import pytest
from pymatgen.analysis.phase_diagram import PDEntry
from pymatgen.core import Composition, Lattice, Structure

from autolab import config
from autolab.analysis import electrodes, uma_errors


def entry(formula, epa, source="uma", name=None):
    c = Composition(formula)
    return PDEntry(c, epa * c.num_atoms, name=name or formula, attribute={"source": source})


def test_leave_one_out_is_the_energy_against_the_other_phases():
    es = [entry("Li", 0.0), entry("S", 0.0), entry("Li2S", -1.0), entry("LiS2", -0.40)]
    de = uma_errors.leave_one_out(es)
    assert set(de) == {"Li2S", "LiS2"}  # elements are the terminals, never left out
    # Li2S against Li + LiS2 (hull -0.20 at x_S = 1/3): stable, negative; LiS2 against Li2S + S (hull -0.50): above
    assert de["Li2S"] == pytest.approx(-0.80) and de["LiS2"] == pytest.approx(0.10)


def test_system_errors_compares_two_separate_hulls():
    def ref(f, mid):  # a structure only gives the composition and the atom count here
        c = Composition(f)
        species = [str(e) for e in c.elements for _ in range(int(c[e]))]
        return {"material_id": mid, "structure": Structure(Lattice.cubic(6), species,
                                                           [[i / 7, 0, 0] for i in range(len(species))])}

    refs = [ref("Li", "mp-1"), ref("S", "mp-2"), ref("Li2S", "mp-3"), ref("LiS2", "mp-4")]
    mp = {"mp-1": 0.0, "mp-2": 0.0, "mp-3": -1.0, "mp-4": -0.40}
    uma = [entry("Li", 0.0, name="mp-1"), entry("S", 0.0, name="mp-2"), entry("Li2S", -1.02, name="mp-3"),
           entry("LiS2", -0.40, name="mp-4")]
    res = uma_errors.system_errors(["Li", "S"], uma_entries=uma, mp_energies=mp, refs=refs)
    rows = {r["formula"]: r for r in res["rows"]}
    assert res["available"] and set(rows) == {"Li2S", "LiS2"}
    assert rows["Li2S"]["diff"] < 0  # UMA puts Li2S lower than MP does
    assert res["compounds"]["n"] == 2 and res["compounds"]["mae"] == pytest.approx(
        (abs(rows["Li2S"]["diff"]) + abs(rows["LiS2"]["diff"])) / 2, abs=1e-4)
    err = uma_errors.ehull_uncertainty("Li3S", errors=lambda els: res)
    assert err["mae_eV_per_atom"] == res["compounds"]["mae"] and err["n"] == 2 and err["system"] == "Li-S"
    assert uma_errors.ehull_uncertainty("Li3S", errors=lambda els: {"available": False}) is None


def test_window_sensitivity_flags_only_windows_that_move(monkeypatch):
    shifts = {}

    def window(target, entries, **kw):  # the upper limit follows the polysulfide energy
        poly = next(e for e in entries if e.composition.reduced_formula == "LiS4")
        shift = poly.energy_per_atom - (-0.5)
        shifts.setdefault("seen", []).append(round(shift, 4))
        return {"stable": True, "v_low": 1.7, "v_high": 2.3 + shifts["slope"] * shift}

    monkeypatch.setattr(electrodes, "electrochemical_window", window)
    monkeypatch.setattr(uma_errors, "is_polysulfide", lambda e: e.composition.reduced_formula == "LiS4")
    target = entry("Li3PS4", -1.0)
    entries = [entry("Li", 0.0), entry("S", 0.0), entry("LiS4", -0.5), target]
    base = {"stable": True, "v_low": 1.7, "v_high": 2.3}
    shifts["slope"] = 1.0  # 0.025 eV/atom moves the limit by 0.025 V: robust
    s = electrodes.window_sensitivity(target, entries, base=base)
    assert s["polysulfides"] == ["LiS4"] and s["robust"] and s["max_shift_V"] == pytest.approx(0.025)
    assert shifts["seen"] == [-config.POLYSULFIDE_ENERGY_ERROR_EV, config.POLYSULFIDE_ENERGY_ERROR_EV]
    shifts["slope"] = 8.0  # 0.2 V: the window depends on the polysulfide energy
    s = electrodes.window_sensitivity(target, entries, base=base)
    assert not s["robust"] and s["max_shift_V"] == pytest.approx(0.2)


def test_window_that_vanishes_is_not_robust(monkeypatch):
    monkeypatch.setattr(electrodes, "electrochemical_window",
                        lambda t, es, **kw: {"stable": False, "v_low": None, "v_high": None})
    monkeypatch.setattr(uma_errors, "is_polysulfide", lambda e: e.composition.reduced_formula == "P2S7")
    target = entry("Li7P3S11", -1.0)
    s = electrodes.window_sensitivity(target, [entry("P2S7", -0.3), target],
                                      base={"stable": True, "v_low": 2.28, "v_high": 2.30})
    assert not s["robust"] and s["max_shift_V"] is None
    no_poly = electrodes.window_sensitivity(target, [entry("Li2S", -0.3), target],
                                            base={"stable": True, "v_low": 2.28, "v_high": 2.30})
    assert no_poly["robust"] and no_poly["windows"] == []


def test_shifted_keeps_the_source_tag():
    out = electrodes._shifted([entry("LiS4", -0.5), entry("Li", 0.0)], {"LiS4"}, 0.025)
    assert out[0].energy_per_atom == pytest.approx(-0.475) and out[0].attribute == {"source": "uma"}
    assert out[1].energy_per_atom == 0.0
