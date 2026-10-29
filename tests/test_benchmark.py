"""Validation benchmark (agent/benchmark.py) with fake tools: no UMA, no ALIGNN, no MP, no cost."""

import json

import pytest

from autolab import config
from autolab.agent.benchmark import evaluate_known, render, summarize
from autolab.domains.electrolyte import ElectrolyteTools
from test_agent import fake_gap, fake_hull, fake_relax, li3ps4  # noqa: F401


@pytest.fixture(autouse=True)
def raw_energies(monkeypatch):
    monkeypatch.setattr(config, "UMA_MP2020", False)  # the fake hull holds raw energies


def bench_tools(gap=3.1, epa=-0.9, verdict="passivating"):
    def window_passivation(c, budget):
        return {"window": {"v_low": 1.7, "v_high": 2.3, "stable": True},
                "passivation": {"verdict": verdict, "reaction_energy": 0.2, "products": [],
                                "metallic_products": ["Li15Ge4"] if verdict == "non_passivating" else []}}

    return ElectrolyteTools(relax=fake_relax(epa=lambda s, i: epa), hull_entries=fake_hull, bandgap=fake_gap(gap),
                            known=lambda f: [], window_passivation=window_passivation, not_run=[])


def test_known_compound_is_judged_without_itself_in_the_hull(li3ps4):
    # -0.9 eV/atom: above the fake Li3PS4 reference (-1.0) but below the elements; hidden, it passes
    r = evaluate_known("mp-985583", "pass", "beta-Li3PS4", bench_tools(), lambda mid: li3ps4)
    assert r["formula"] == "Li3PS4" and r["e_hull"] == pytest.approx(-0.9) and r["outcome"] == "pass" and r["correct"]
    assert r["e_hull_per_substitution"] == pytest.approx(r["e_hull"])  # nothing substituted


def test_bad_compounds_are_rejected_at_the_gap_or_at_li_metal(li3ps4):
    gap = evaluate_known("mp-x", "reject", "conductor", bench_tools(gap=0.5), lambda mid: li3ps4)
    assert (gap["outcome"], gap["rejected_at"], gap["correct"]) == ("reject", "bandgap", True)
    lgps = evaluate_known("mp-y", "pass", "LGPS-like", bench_tools(verdict="non_passivating"), lambda mid: li3ps4)
    assert (lgps["funnel_outcome"], lgps["outcome"], lgps["rejected_at"]) == ("pass", "reject", "electrodes")
    assert lgps["correct"] is False and "Li15Ge4" in lgps["reason"]
    s = summarize([gap, lgps])
    assert s == {"good": 1, "bad": 1, "good_pass_funnel": 1, "good_pass_all": 0, "bad_rejected_funnel": 1,
                 "bad_rejected_all": 1}
    text = render(json.loads(json.dumps([gap, lgps])), s)
    assert "**1 / 1**" in text and "**0 / 1**" in text and "| **no** |" in text
