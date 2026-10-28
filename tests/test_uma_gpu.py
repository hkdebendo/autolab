"""UMA truth tests (SPEC section 7). GPU only: run with `pytest --gpu` (SIM_BACKEND=modal or local).

Every relaxation goes through the disk cache: a second run costs nothing.
"""

import pytest
from pymatgen.core import Lattice, Structure

from autolab.analysis.stability import e_hull, make_entry, uma_reference_entries
from autolab.sim.backend import relax_structures
from autolab.sim.serialize import atoms_from_dict
from conftest import requires_mp

pytestmark = pytest.mark.gpu


def rocksalt(a: float, cation: str, anion: str) -> Structure:
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(a), [cation, anion], [[0, 0, 0], [0.5, 0.5, 0.5]])


def test_licl_relaxation():
    res = relax_structures([rocksalt(5.0, "Li", "Cl")])[0]
    a = atoms_from_dict(res["atoms"]).cell.lengths().mean()
    print(f"\nLiCl: a = {a:.3f} A (validated 5.145, exp. ~5.13), steps {res['steps']}, {res['seconds']} s")
    assert res["converged"]
    assert 5.10 <= a <= 5.18


@requires_mp
def test_li2s_ehull_uma():
    entries, skipped = uma_reference_entries(["Li", "S"])
    li2s = min((e for e in entries if e.composition.reduced_formula == "Li2S"), key=lambda e: e.energy_per_atom)
    out = e_hull(li2s, entries)
    print(f"\nLi2S E_hull (UMA) = {out['e_hull']}; skipped (not converged): {skipped}")
    assert out["e_hull"] <= 0.005


@requires_mp
def test_fictitious_rocksalt_lis_is_unstable():
    entries, _ = uma_reference_entries(["Li", "S"])
    res = relax_structures([rocksalt(5.0, "Li", "S").get_primitive_structure()])[0]
    target = make_entry("LiS", res["energy"], "LiS-rocksalt", "uma")
    out = e_hull(target, entries)
    print(f"\nRocksalt LiS E_hull (UMA) = {out['e_hull']}, converged {res['converged']}")
    assert out["e_hull"] >= 0.3


@requires_mp
def test_li3ps4_calibration_uma():
    entries, skipped = uma_reference_entries(["Li", "P", "S"])
    target = next(e for e in entries if e.name == "mp-985583")
    out = e_hull(target, entries)
    print(f"\nLi3PS4 mp-985583 E_hull (UMA) = {out['e_hull']} (validated 0.000); skipped: {skipped}")
    assert out["e_hull"] <= 0.01
