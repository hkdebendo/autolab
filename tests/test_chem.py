"""Truth tests for chem/ (SPEC 5.1 - 5.3, section 7)."""

from pymatgen.core import Lattice, Structure

from autolab.chem.checks import has_ss_bonds
from autolab.chem.generator import generate_candidates
from autolab.chem.oxidation import check_charge, is_neutral, total_charge
from conftest import load_structure


def li3ps4():
    return load_structure("Li3PS4_mp-985583")


def li2s():
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(5.72), ["S", "Li"], [[0, 0, 0], [0.25, 0.25, 0.25]])


def test_li3ps4_fixture_is_32_atoms():
    s = li3ps4()
    assert s.composition.formula.replace(" ", "") == "Li12P4S16"


def test_oxidation_table():
    assert is_neutral(li3ps4())
    assert total_charge("Li6PS5Cl") == 0
    assert not is_neutral("LiFePO4")  # Fe: variable valence, rejected
    assert check_charge("LiCoO2")["unsupported"] == ["Co"]


def test_neutrality_rejects_s_to_cl_without_li_vacancy():
    out = generate_candidates(li3ps4(), {"remove": "S", "add": "Cl", "count": 1}, parent_id="mp-985583")
    assert not out["accepted"]
    assert out["charge"] == 1.0
    assert out["candidates"] == []
    assert "neutral" in out["reason"]


def test_generator_s_to_cl_with_one_li_vacancy():
    out = generate_candidates(
        li3ps4(), {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}, parent_id="mp-985583"
    )
    assert out["accepted"]
    assert len(out["candidates"]) >= 2
    for c in out["candidates"]:
        assert is_neutral(Structure.from_dict(c["structure"]))
    print(f"\nS->Cl + 1 Li vacancy: {len(out['candidates'])} distinct arrangements out of 8")


def test_generator_is_reproducible():
    sub = {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}
    a = generate_candidates(li3ps4(), sub)
    b = generate_candidates(li3ps4(), sub)
    assert [c["structure"] for c in a["candidates"]] == [c["structure"] for c in b["candidates"]]


def test_total_substitution():
    out = generate_candidates(li3ps4(), {"remove": "P", "add": "Sb", "count": "all"})
    assert out["accepted"]
    assert out["formula"] == "Li3SbS4"
    assert len(out["candidates"]) == 1


def test_bad_substitutions_are_rejected_with_reason():
    s = li3ps4()
    assert "not in the parent" in generate_candidates(s, {"remove": "O", "add": "S", "count": 1})["reason"]
    assert "outside" in generate_candidates(s, {"remove": "P", "add": "Fe", "count": "all"})["reason"]
    assert generate_candidates(s, {"remove": "S", "add": "Cl", "count": 99})["reason"]


def test_ss_bonds():
    assert has_ss_bonds(li2s()) is False
    assert has_ss_bonds(load_structure("LiS4")) is True
