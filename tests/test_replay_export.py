"""Replay files (analysis/replay_export.py) from a small fake MD record: no GPU, no cost."""

import numpy as np
import pytest

from autolab.analysis.replay_export import md_view, structure_view


def test_li_frames_are_wrapped_subsampled_and_the_framework_kept():
    atoms = {"numbers": [3, 16], "cell": [[4, 0, 0], [0, 4, 0], [0, 0, 4]], "positions": [[0, 0, 0], [2, 2, 2]],
             "pbc": [True] * 3}
    n = 1001  # frames every 10 fs: the Li of each cell drifts along x, past the cell walls
    li = np.array([[[0.02 * k, 0, 0]] for k in range(n)], dtype=float)  # 20 A travelled
    md = {"reps": [3, 3, 3], "species": "Li", "dt_record_fs": 10.0, "positions": li.tolist(), "temperature_K": 600,
          "n_atoms": 54, "framework_msd": {"S": [0.1] * n}}
    v = md_view(atoms, md, n_frames=101)
    assert len(v["frames"]) == 101 and v["frame_fs"] == pytest.approx(100.0)
    xs = np.array(v["frames"])[:, 0, 0]
    assert xs.min() >= 0 and xs.max() < 12  # wrapped into the 12 A supercell
    assert v["frames"][-1][0][0] == pytest.approx(20.0 % 12, abs=0.01)
    assert len(v["framework"]["symbols"]) == 27 and set(v["framework"]["symbols"]) == {"S"}
    assert v["curve"]["msd_li_A2"][-1] == pytest.approx(400.0, rel=1e-3)  # computed on unwrapped positions
    assert v["curve"]["msd_framework_A2"]["S"][0] == 0.1


def test_structure_view_names_the_substituted_element():
    s = structure_view({"numbers": [3, 17], "cell": [[5, 0, 0], [0, 5, 0], [0, 0, 5]],
                        "positions": [[0, 0, 0], [2.5, 2.5, 2.5]], "pbc": [True] * 3}, "Cl")
    assert s["symbols"] == ["Li", "Cl"] and s["highlight"] == "Cl"
