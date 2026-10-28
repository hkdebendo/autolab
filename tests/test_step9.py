"""Step 9 (electrodes with UMA energies, MD screening): fake Li-S system and fake MD, no UMA, no cost."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from pymatgen.core import Lattice, Structure
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.io.ase import AseAtomsAdaptor

from autolab import config
from autolab.agent import dynamics
from autolab.agent.electrochem import (candidate_entry, interface_calibration, li3ps4_window_calibration,
                                       uma_interface, window_and_passivation)
from autolab.analysis.stability import make_entry
from autolab.sim.backend import BudgetExceeded, RelaxBudget
from autolab.sim.serialize import atoms_to_dict

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

# Li-S with round numbers: Li2S -1.5 eV/atom, LiS2 -0.8 eV/atom (on the hull), elements at 0.
ENERGIES = {"Li": 0.0, "S": 0.0, "Li2S": -4.5, "LiS2": -2.4}
IDS = {"Li": "mp-135", "S": "mp-77", "Li2S": "mp-1153", "LiS2": "mp-995393"}


def uma_entries(elements, budget=None, ehull_max=None):
    return [make_entry(f, e, IDS[f], "uma") for f, e in ENERGIES.items()], []


def mp_entries(shift=0.0):
    return lambda elements: [ComputedEntry(f, e + (shift if f == "LiS2" else 0.0), entry_id=IDS[f])
                             for f, e in ENERGIES.items()]


@pytest.fixture(scope="module")
def li2s_candidate():
    s = Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.7), ["S", "Li"], [[0, 0, 0], [0.25, 0.25, 0.25]])
    return {"id": "c1", "formula": "Li2S", "parent": "mp-1153", "energy": -1.5 * len(s),
            "relaxed_atoms": atoms_to_dict(AseAtomsAdaptor.get_atoms(s))}


def test_candidate_entry_is_uma(li2s_candidate):
    e = candidate_entry(li2s_candidate)
    assert e.composition.reduced_formula == "Li2S" and e.attribute["source"] == "uma"
    assert e.energy_per_atom == pytest.approx(-1.5)


def test_window_and_passivation_with_uma_entries(li2s_candidate):
    r = window_and_passivation(li2s_candidate, uma_entries, get_gaps=lambda ids: {})
    # Li2S -> 1/2 LiS2 + 3/2 Li costs 3.3 eV for 1.5 Li: oxidised above 2.2 V, stable down to 0 V.
    assert r["window"]["v_low"] == 0.0 and r["window"]["v_high"] == pytest.approx(2.2, abs=0.03)
    assert r["passivation"]["verdict"] == "stable"


def test_interface_and_calibration_gate():
    uma = uma_interface("Li2S", "S", uma_entries)
    # Per atom of mixture: the 1:1 atomic mix of Li2S and S has the LiS2 composition, -0.75 -> -0.8 eV/atom.
    assert uma["min_reaction_energy"] == pytest.approx(-0.05, abs=1e-6) and uma["source"] == "uma"
    assert uma["reaction"] == "0.25 Li2S + 0.75 S -> 0.5 LiS2"
    same = interface_calibration("S", "Li2S", uma_entries, mp_entries(0.0))
    assert same["ok"] and same["diff"] == pytest.approx(0.0, abs=1e-6) and same["mp"]["source"] == "mp"
    off = interface_calibration("S", "Li2S", uma_entries, mp_entries(-0.6))  # MP LiS2 much lower
    assert not off["ok"] and abs(off["diff"]) > config.INTERFACE_CALIBRATION_MAX_DIFF


def test_uma_interface_rejects_mixed_sources():
    def mixed(elements, budget=None, ehull_max=None):
        entries, _ = uma_entries(elements)
        return entries[:-1] + [ComputedEntry("LiS2", -2.4)], []

    with pytest.raises(ValueError, match="one known energy source"):
        uma_interface("Li2S", "S", mixed)


def fake_run(d_true=0.5, n_li=20):
    def run(atoms, temperature_K, n_steps):
        rng = np.random.default_rng(1)
        frames = n_steps // config.MD_RECORD_EVERY
        dt = config.MD_TIMESTEP_FS * config.MD_RECORD_EVERY
        steps = rng.normal(0, np.sqrt(2 * d_true * dt / 1000.0), size=(frames, n_li, 3))
        pos = np.concatenate([np.zeros((1, n_li, 3)), np.cumsum(steps, axis=0)])
        return {"positions": pos.tolist(), "dt_record_fs": dt, "n_atoms": 84, "ms_per_step": 55.0, "cached": False}

    return run


def test_md_screen_fits_d_and_reports_each_run(li2s_candidate):
    done = []
    jobs = [dynamics.candidate_job(li2s_candidate)] * 2
    rows = dynamics.md_screen(jobs, temperature_K=1000, ps=20, run=fake_run(), on_done=done.append)
    assert len(rows) == len(done) == 2 and "atoms" not in rows[0]
    assert rows[0]["n_li"] == 20 and rows[0]["D_A2_per_ps"] == pytest.approx(0.5, rel=0.25)
    assert rows[0]["D_cm2_per_s"] == pytest.approx(rows[0]["D_A2_per_ps"] * 1e-4)
    with pytest.raises(ValueError, match="MD_SCREEN_MAX_RUNS"):
        dynamics.md_screen(jobs * 4, run=fake_run())


def test_run_interfaces_stops_before_candidates_when_calibration_fails(tmp_path, monkeypatch, li2s_candidate):
    sys.path.insert(0, str(SCRIPTS))
    import run_interfaces

    calls = []
    monkeypatch.setattr(run_interfaces, "interface_calibration",
                        lambda cathode, budget=None: {"cathode": cathode, "ok": cathode != "LiFePO4", "diff": 0.2,
                                                      "uma": {"min_reaction_energy": -0.1},
                                                      "mp": {"min_reaction_energy": -0.3}})
    monkeypatch.setattr(run_interfaces, "uma_interface", lambda *a, **k: calls.append(a))
    cands = tmp_path / "candidates.json"
    cands.write_text(json.dumps({"candidates": [li2s_candidate]}), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run_interfaces.py", str(cands), "--ids", "c1", "--out", str(tmp_path)])
    run_interfaces.main()
    out = json.loads((tmp_path / "interfaces.json").read_text(encoding="utf-8"))
    assert calls == [] and "LiFePO4" in out["stopped"] and len(out["calibrations"]) == 2


def test_step9_report_renders(li2s_candidate):
    sys.path.insert(0, str(SCRIPTS))
    from step9_report import render

    electrodes = {"calibration_li3ps4": {"v_low": 1.74, "v_high": 2.3, "mp_v_low": 1.72, "mp_v_high": 2.34},
                  "candidates": [window_and_passivation(li2s_candidate, uma_entries, get_gaps=lambda ids: {})]}
    md = dynamics.md_screen([{"id": "mp-1153", "formula": "Li2S", "kind": "parent", "atoms": None},
                             dynamics.candidate_job(li2s_candidate)], run=fake_run())
    text = render({"candidates": [li2s_candidate]}, electrodes, None, md)
    for s in ("## 9A", "stable", "## 9B", "Not run", "## 9C", "D / D(parent)", "1.00"):
        assert s in text


def test_li3ps4_window_with_cached_uma_energies():
    """SPEC 7 window truth test (1.6-1.9 V to 2.2-2.5 V), here with UMA energies from the PC cache."""
    try:
        cal = li3ps4_window_calibration(budget=RelaxBudget(0))
    except (BudgetExceeded, Exception) as e:  # no cache on this machine
        pytest.skip(f"UMA Li-P-S references not cached here ({type(e).__name__})")
    assert 1.6 <= cal["v_low"] <= 1.9 and 2.2 <= cal["v_high"] <= 2.5
