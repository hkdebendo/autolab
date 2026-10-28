"""Code-computed comparisons, warning filters and MP formula lookup."""

import subprocess
import sys

from autolab.agent.compare import comparisons
from autolab.data.mp import formula_key, known_formulas
from conftest import requires_mp

CL = {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}
I = {"remove": "S", "add": "I", "count": 1, "li_vacancies": 1}  # noqa: E741

# Numbers of the first Colab loop (2026-10-28), where the model misread the iodine/chlorine gaps.
RUN = [
    {"id": "it1-c1", "parent": "mp-985583", "substitution": CL, "formula": "Li11P4S15Cl",
     "e_hull": 0.025728, "e_hull_per_substitution": 0.7976, "gap_optb88": 2.669},
    {"id": "it2-c1", "parent": "mp-641703", "substitution": CL, "formula": "Li13P6S21Cl",
     "e_hull": 0.030159, "e_hull_per_substitution": 1.2365, "gap_optb88": 2.25},
    {"id": "it2-c5", "parent": "mp-985583", "substitution": I, "formula": "Li11P4S15I",
     "e_hull": 0.023389, "e_hull_per_substitution": 0.7251, "gap_optb88": 2.522},
    {"id": "it1-c3", "parent": "mp-985583", "substitution": {"remove": "P", "add": "Sb", "count": "all"},
     "formula": "Li3SbS4", "e_hull": None, "gap_optb88": None},  # not computed: never compared
]


def by_kind(kind):
    return [c for c in comparisons(RUN) if c["kind"] == kind]


def test_iodine_vs_chlorine_on_the_same_parent():
    [pair] = by_kind("same parent, different added element")
    text = " | ".join(pair["statements"])
    assert "E_hull per atom: Li11P4S15I (it2-c5) 0.023 < Li11P4S15Cl (it1-c1) 0.026 eV/atom" in text
    assert "band gap optB88: Li11P4S15Cl (it1-c1) 2.669 > Li11P4S15I (it2-c5) 2.522" in text  # Cl has the larger gap


def test_same_substitution_on_two_parents():
    [pair] = by_kind("same substitution, different parents")
    assert "S->Cl x1, -1 Li on mp-985583 vs mp-641703" in pair["about"]
    assert any(s.startswith("E_hull per substitution: Li11P4S15Cl (it1-c1) 0.798 <") for s in pair["statements"])


def test_rankings_per_parent_skip_uncomputed_candidates():
    [ranking] = by_kind("ranking on one parent")
    assert ranking["about"] == "mp-985583"
    assert "band gap optB88 (highest first): it1-c1 2.669, it2-c5 2.522" in ranking["statements"]
    assert all("it1-c3" not in s for c in comparisons(RUN) for s in c["statements"])


def test_known_warnings_are_masked():
    code = ("import warnings, autolab\n"
            "warnings.warn('logm result may be inaccurate, approximate err = 3e-13', RuntimeWarning)\n"
            "warnings.warn('Not all sites have property magmom. Missing values are set to None.', UserWarning)\n"
            "warnings.warn('other warning', UserWarning)\n")
    err = subprocess.run([sys.executable, "-W", "default", "-c", code], capture_output=True, text=True).stderr
    assert "logm" not in err and "magmom" not in err and "other warning" in err


def test_formula_key_is_canonical():
    assert formula_key("NaLi11(PS4)4") == formula_key("Li11NaP4S16") == "Li11NaP4S16"
    assert formula_key("Li6P2S8") == formula_key("Li3PS4") == "Li3PS4"


@requires_mp
def test_known_formulas_from_materials_project():
    known = known_formulas(["Li3SbS4", "Li11P4S15Cl"])
    assert {"mp-756316", "mp-760415"} <= {k["material_id"] for k in known["Li3SbS4"]}
    assert known["Li11P4S15Cl"] == []
