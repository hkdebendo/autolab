"""What the live view of the interface receives: the relaxation path, the start and relaxed structures, repaired text."""

import importlib.util
from pathlib import Path

import pytest
from pymatgen.core import Lattice, Structure

from autolab.agent.pipeline import lattice, live_structure
from autolab.sim.relax import _thin


def test_relaxation_path_keeps_first_last_and_evenly_spaced_frames():
    path = list(range(100))
    kept = _thin(path, 12)
    assert len(kept) == 12 and kept[0] == 0 and kept[-1] == 99
    assert _thin([1, 2, 3], 12) == [1, 2, 3]


def test_live_structure_takes_relaxed_atoms_next_to_their_start():
    start = Structure(Lattice.cubic(5.0), ["Li", "Cl"], [[0.02, 0.5, 0.5], [0.5, 0.5, 0.5]])
    # the Li crossed the cell face during the relaxation: stored at x = 4.95 A instead of -0.05 A
    best = {"atoms": {"numbers": [3, 17], "cell": [[5.1, 0, 0], [0, 5.1, 0], [0, 0, 5.1]],
                      "positions": [[4.95, 2.55, 2.55], [2.55, 2.55, 2.55]]}, "energy_per_atom": -3.21}
    st = live_structure(start, best, {"add": "Cl", "remove": "S", "count": 1, "li_vacancies": 0})
    assert st["symbols"] == ["Li", "Cl"] and st["added"] == "Cl" and st["removed"] == "S"
    assert st["end"]["positions"][0][0] == pytest.approx(-0.15, abs=1e-3)  # drawn next to its start, not across the cell
    assert st["start"]["lattice"]["a"] == 5.0 and st["end"]["lattice"]["volume"] == pytest.approx(5.1 ** 3, rel=1e-3)
    assert lattice([[1, 0, 0], [0, 2, 0], [0, 0, 3]])["gamma"] == 90.0


def test_text_saved_with_the_wrong_encoding_is_repaired():
    spec = importlib.util.spec_from_file_location("lv", Path(__file__).parents[1] / "scripts" / "live_view_events.py")
    lv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lv)
    assert lv.repaired({"m": ["D/D(parent) = 1.34 Â± 0.34"]}) == {"m": ["D/D(parent) = 1.34 ± 0.34"]}
    assert lv.repaired("Li₇P₃S₁₁ — ±") == "Li₇P₃S₁₁ — ±"  # correct text is left alone
