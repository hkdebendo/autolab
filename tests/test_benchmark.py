"""Validation benchmark (agent/benchmark.py) with fake tools: no UMA, no GapModel, no MP, no cost."""

import json

import pytest

from autolab import config
from autolab.agent.benchmark import evaluate_known, md_check, md_jobs, render, summarize
from autolab.agent.dynamics import md_verdicts
from autolab.domains.electrolyte import ElectrolyteTools
from test_agent import fake_gap, fake_hull, fake_relax, li3ps4  # noqa: F401


@pytest.fixture(autouse=True)
def raw_energies(monkeypatch):
    monkeypatch.setattr(config, "UMA_MP2020", False)  # the fake hull holds raw energies


def bench_tools(insulating=True, epa=-0.9, verdict="passivating"):
    def window_passivation(c, budget):
        return {"window": {"v_low": 1.7, "v_high": 2.3, "stable": True},
                "passivation": {"verdict": verdict, "reaction_energy": 0.2, "products": [],
                                "metallic_products": ["Li15Ge4"] if verdict == "non_passivating" else []}}

    return ElectrolyteTools(relax=fake_relax(epa=lambda s, i: epa), hull_entries=fake_hull, bandgap=fake_gap(insulating),
                            known=lambda f: [], window_passivation=window_passivation, not_run=[])


def test_known_compound_is_judged_without_itself_in_the_hull(li3ps4):
    # -0.9 eV/atom: above the fake Li3PS4 reference (-1.0) but below the elements; hidden, it passes
    r = evaluate_known("mp-985583", "pass", "beta-Li3PS4", bench_tools(), lambda mid: li3ps4)
    assert r["formula"] == "Li3PS4" and r["e_hull"] == pytest.approx(-0.9) and r["outcome"] == "pass" and r["correct"]
    assert r["e_hull_per_substitution"] == pytest.approx(r["e_hull"])  # nothing substituted


def test_bad_compounds_are_rejected_at_the_gap_or_at_li_metal(li3ps4):
    gap = evaluate_known("mp-x", "reject", "conductor", bench_tools(insulating=False), lambda mid: li3ps4)
    assert (gap["outcome"], gap["rejected_at"], gap["correct"]) == ("reject", "bandgap", True)
    lgps = evaluate_known("mp-y", "pass", "LGPS-like", bench_tools(verdict="non_passivating"), lambda mid: li3ps4)
    assert (lgps["funnel_outcome"], lgps["outcome"], lgps["rejected_at"]) == ("pass", "reject", "electrodes")
    assert lgps["correct"] is False and "Li15Ge4" in lgps["reason"]
    s = summarize([gap, lgps])
    assert {k: v for k, v in s.items() if k != "rejected_by"} == {
        "good": 1, "bad": 1, "hard": 0, "good_pass_funnel": 1, "good_pass_all": 0, "bad_rejected_funnel": 1,
        "bad_rejected_all": 1, "hard_rejected_funnel": 0, "hard_rejected_all": 0}
    assert s["rejected_by"]["bad"] == {"bandgap": 1}
    text = render(json.loads(json.dumps([gap, lgps])), s)
    assert "**1 / 1**" in text and "**0 / 1**" in text and "| **no** |" in text


def test_hard_negatives_pass_the_funnel_and_are_rejected_by_diffusion(li3ps4, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    good = evaluate_known("mp-985583", "pass", "beta-Li3PS4", bench_tools(), lambda mid: li3ps4)
    slow = evaluate_known("mp-1153", "reject", "Li2S-like", bench_tools(), lambda mid: li3ps4, group="hard")
    frozen = evaluate_known("mp-22905", "reject", "LiCl-like", bench_tools(), lambda mid: li3ps4, group="hard")
    assert slow["funnel_outcome"] == "pass" and slow["group"] == "hard"
    ref = {"id": "mp-985583", "formula": "Li3PS4", "kind": "parent", "atoms": good["relaxed_atoms"]}
    jobs = md_jobs([good, slow, frozen], ref)
    assert [j["id"] for j in jobs] == ["mp-985583", good["id"], slow["id"], frozen["id"]]
    assert all(j["parent"] == "mp-985583" for j in jobs[1:])
    md = md_verdicts([{"id": "mp-985583", "kind": "parent", "D_cm2_per_s": 6e-6, "D_sem_cm2_per_s": 1e-6},
                      {"id": good["id"], "kind": "candidate", "parent": "mp-985583", "D_cm2_per_s": 6e-6,
                       "D_sem_cm2_per_s": 1e-6},
                      {"id": slow["id"], "kind": "candidate", "parent": "mp-985583", "D_cm2_per_s": 5e-7,
                       "D_sem_cm2_per_s": 2e-7},
                      {"id": frozen["id"], "kind": "candidate", "parent": "mp-985583", "D_cm2_per_s": -1e-9,
                       "D_sem_cm2_per_s": 1e-9}])
    rows = [good, slow, frozen]
    md_check(rows, md, "Li3PS4")
    assert good["outcome"] == "pass" and good["md_verdict"] == "tied"
    assert (slow["outcome"], slow["rejected_at"], slow["correct"]) == ("reject", "molecular_dynamics", True)
    assert "slower than Li3PS4" in slow["reason"]
    assert frozen["rejected_at"] == "molecular_dynamics" and frozen["reason"] == "no Li diffusion seen"
    s = summarize(rows)
    assert (s["hard"], s["hard_rejected_funnel"], s["hard_rejected_all"]) == (2, 0, 2)
    assert s["rejected_by"]["hard"] == {"molecular_dynamics": 2}
    text = render(json.loads(json.dumps(rows)), s)
    assert "Hard negatives" in text and "no Li hop" in text and "(lower)" in text
