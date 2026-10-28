"""Truth tests for analysis/bandgap.py (SPEC 5.8, section 7): Li metal / Li2S / LiCl."""

import pytest
from pymatgen.core import Lattice, Structure

pytest.importorskip("alignn")

from autolab.analysis.bandgap import evaluate_bandgap, predict_gap  # noqa: E402
from autolab import config  # noqa: E402


def li_metal():
    return Structure.from_spacegroup("Im-3m", Lattice.cubic(3.44), ["Li"], [[0, 0, 0]])


def li2s():
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.72), ["S", "Li"], [[0, 0, 0], [0.25, 0.25, 0.25]])


def licl():
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.13), ["Li", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])


@pytest.mark.parametrize(
    "make, low, high",
    [(li_metal, None, 0.3), (li2s, 3.0, None), (licl, 5.5, None)],
    ids=["Li", "Li2S", "LiCl"],
)
def test_optb88_gap(make, low, high):
    gap = predict_gap(make(), config.BANDGAP_FILTER_MODEL)
    print(f"\n{make().composition.reduced_formula}: optb88 gap = {gap:.3f} eV")
    if low is not None:
        assert gap > low
    if high is not None:
        assert gap < high


def test_evaluate_bandgap_filter():
    li = evaluate_bandgap(li_metal())
    salt = evaluate_bandgap(licl())
    print(f"\nLi: {li}\nLiCl: {salt}")
    assert li["passes"] is False and li["gap_optb88"] >= 0 and li["gap_mbj"] >= 0
    assert salt["passes"] is True and salt["low_confidence"] is False
