"""Funnel and loop tests with fake tools and fake language models: no UMA, no ALIGNN, no API, no cost."""

import json

import pytest
from pymatgen.io.ase import AseAtomsAdaptor

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.pipeline import Tools, evaluate_candidate
from autolab.agent.report import render
from autolab.analysis.stability import make_entry
from autolab.llm import client as llm
from autolab.sim.backend import BudgetExceeded as SimBudgetExceeded
from autolab.sim.backend import RelaxBudget
from autolab.sim.serialize import atoms_to_dict
from conftest import load_structure

PARENT = "mp-985583"
SUB_CL = {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}


@pytest.fixture(scope="module")
def li3ps4():
    return load_structure("Li3PS4_mp-985583")


def fake_relax(epa=lambda s, i: -1.2 - 0.001 * i, converged=True, calls=None):
    """Relaxation stand-in: energy per atom from `epa(structure, index)`, honouring the run budget."""

    def relax(structures, budget):
        if calls is not None:
            calls.append(len(structures))
        if budget is not None:
            if len(structures) > budget.remaining:
                raise SimBudgetExceeded(f"{len(structures)} requested, {budget.remaining} left")
            budget.used += len(structures)
        out = []
        for i, s in enumerate(structures):
            e = epa(s, i)
            out.append({"converged": converged, "energy": e * len(s), "energy_per_atom": e,
                        "atoms": atoms_to_dict(AseAtomsAdaptor.get_atoms(s))})
        return out

    return relax


@pytest.fixture(autouse=True)
def raw_uma_energies(monkeypatch):
    """The fake hull holds raw energies with round numbers: the funnel target must not get MP2020 corrections."""
    monkeypatch.setattr(config, "UMA_MP2020", False)


def fake_hull(elements, budget):
    """Elements at 0 eV/atom, plus Li3PS4 at -1.0 eV/atom when Li, P and S are all present."""
    entries = [make_entry(el, 0.0, el, "uma") for el in elements]
    if {"Li", "P", "S"} <= set(elements):
        entries.append(make_entry("Li3PS4", -8.0, "mp-985583", "uma"))
    return entries, []


def fake_gap(gap=3.1):
    return lambda s: {"gap_optb88": gap, "gap_mbj": gap + 1, "passes": gap >= config.BANDGAP_MIN,
                      "low_confidence": False}


def tools(**kw):
    return Tools(relax=kw.get("relax", fake_relax()), hull_entries=fake_hull, bandgap=kw.get("bandgap", fake_gap()),
                 known=kw.get("known", lambda formula: []))


# --- funnel ------------------------------------------------------------------

def test_non_neutral_rejected_before_any_simulation(li3ps4):
    calls = []
    out = evaluate_candidate("c1", PARENT, li3ps4, {"remove": "S", "add": "Cl", "count": 1},
                             tools(relax=fake_relax(calls=calls)))
    assert (out["status"], out["rejected_at"]) == ("rejected", "generate")
    assert "charge" in out["reason"] and calls == []


def test_passing_candidate_keeps_lowest_arrangement_and_emits_events(li3ps4):
    events = EventLog()
    out = evaluate_candidate("c1", PARENT, li3ps4, SUB_CL, tools(), events, RelaxBudget(20))
    assert out["status"] == "passed" and out["formula"] == "Li11P4S15Cl"
    assert out["arrangements"] == out["converged"] >= 2
    assert out["energy_spread_meV"] == pytest.approx(1.0 * (out["arrangements"] - 1))
    assert out["e_hull"] < 0 and out["gap_optb88"] == 3.1 and out["ss_bonds"] is False
    assert (out["n_atoms"], out["n_modified"]) == (31, 2)  # 1 S->Cl + 1 Li vacancy
    assert out["e_hull_per_substitution"] == pytest.approx(out["e_hull"] * 31 / 2, abs=1e-3)
    assert out["new_relaxations"] == out["arrangements"]
    assert [e["step"] for e in events.events] == ["generate", "known_check", "relax", "hull", "bandgap", "ss_check",
                                                  "done"]
    assert all(set(e) == {"type", "candidate_id", "step", "data", "timestamp"} for e in events.events)
    json.dumps(out)  # serialisable


def test_known_composition_reported_not_computed(li3ps4):
    calls = []
    out = evaluate_candidate("c1", PARENT, li3ps4, {"remove": "P", "add": "Sb", "count": "all"},
                             tools(relax=fake_relax(calls=calls),
                                   known=lambda f: [{"material_id": "mp-756316", "theoretical": True}]))
    assert (out["status"], out["rejected_at"], out["known_in_mp"]) == ("rejected", "known", ["mp-756316"])
    assert out["n_modified"] == 4 and calls == []  # all 4 P of Li12P4S16, nothing relaxed


def test_known_check_failure_still_computes(li3ps4):
    def unreachable(formula):
        raise ConnectionError("MP down")

    events = EventLog()
    out = evaluate_candidate("c1", PARENT, li3ps4, SUB_CL, tools(known=unreachable), events)
    assert out["status"] == "passed"
    assert any("MP down" in e["data"].get("error", "") for e in events.events if e["step"] == "known_check")


def test_unstable_candidate_rejected_at_hull(li3ps4):
    gap_calls = []
    out = evaluate_candidate("c1", PARENT, li3ps4, SUB_CL,
                             tools(relax=fake_relax(epa=lambda s, i: 0.5),
                                   bandgap=lambda s: gap_calls.append(s)))
    assert (out["status"], out["rejected_at"]) == ("rejected", "hull")
    assert out["e_hull"] > config.EHULL_SYNTHESIZABLE and out["decomposition"] and gap_calls == []


def test_metallic_candidate_rejected_at_bandgap(li3ps4):
    out = evaluate_candidate("c1", PARENT, li3ps4, SUB_CL, tools(bandgap=fake_gap(0.4)))
    assert (out["status"], out["rejected_at"], out["gap_optb88"]) == ("rejected", "bandgap", 0.4)


def test_no_converged_arrangement_rejected_at_relax(li3ps4):
    out = evaluate_candidate("c1", PARENT, li3ps4, SUB_CL, tools(relax=fake_relax(converged=False)))
    assert (out["status"], out["rejected_at"]) == ("rejected", "relax")


# --- loop --------------------------------------------------------------------

def proposal(*subs, hypothesis="h"):
    return {"hypothesis": hypothesis,
            "proposals": [{"parent": p, "substitution": s, "rationale": "r"} for p, s in subs]}


def analysis(ranking=(), stop=False):
    return {"ranking": list(ranking), "lessons": ["lesson"], "next_direction": "next", "stop": stop}


class FakeLLM:
    """complete_json stand-in: returns prepared objects (or raises prepared errors) and counts usage."""

    def __init__(self, provider, replies):
        self.provider = provider
        self.tracker = llm.UsageTracker()
        self.replies = list(replies)
        self.requests = []

    def complete_json(self, messages, schema, **kwargs):
        self.requests.append({"messages": messages, "schema": schema, **kwargs})
        item = self.replies.pop(0)
        if isinstance(item, Exception):
            raise item
        self.tracker.count_call(self.provider)
        reply = llm.Reply(self.provider, "m", json.dumps(item), "thinking about " + schema, 100, 400, 300,
                          llm.cost_usd("baseten", 100, 400), 1.0)
        self.tracker.add(reply)
        return item, [reply]


def agent(li3ps4, brain, fallback=None, budget=20, **kw):
    return Agent(brain, fallback, tools=tools(**kw), budget=RelaxBudget(budget),
                 get_structure=lambda pid: li3ps4)


SB_ALL = {"remove": "P", "add": "Sb", "count": "all"}
BR = {"remove": "S", "add": "Br", "count": 1, "li_vacancies": 1}


def test_loop_two_iterations_filters_and_report(li3ps4):
    first = proposal((PARENT, SUB_CL), ("mp-999", SUB_CL), (PARENT, {"remove": "S", "add": "Cl", "count": 1}),
                     (PARENT, SUB_CL), (PARENT, SB_ALL), (PARENT, BR), (PARENT, BR))
    brain = FakeLLM("meta", [first, analysis(["it1-c5"]), proposal((PARENT, BR)), analysis(["it2-c1"])])

    def epa(s, i):
        return -1.1 if "Sb" in s.composition else -1.2 - 0.001 * i

    result = agent(li3ps4, brain, relax=fake_relax(epa=epa)).run(parents=[PARENT], n_iterations=2, max_candidates=5)

    it1 = result["iterations"][0]["candidates"]
    assert len(it1) == 5  # capped at max_candidates
    assert [(c["status"], c.get("reason")) for c in it1[1:4]] == [
        ("rejected", "unknown parent"), ("rejected", it1[2]["reason"]), ("rejected", "already evaluated")]
    assert "charge" in it1[2]["reason"]
    assert [c["status"] for c in it1] == ["passed", "rejected", "rejected", "rejected", "passed"]
    assert len(result["iterations"]) == 2 and result["stop_reason"] == "iterations done"
    # lowest E_hull first: Li3SbS4 at -1.1 eV/atom vs the elements is far below Li11P4S15Cl
    assert result["final_ranking"][0] == "it1-c5" and set(result["final_ranking"]) == {"it1-c1", "it1-c5", "it2-c1"}
    assert result["model_ranking"] == ["it2-c1"]

    second_request = json.loads(brain.requests[2]["messages"][1]["content"])
    assert second_request["history"][0]["lessons"] == ["lesson"]
    system = brain.requests[0]["messages"][0]["content"]
    assert str(config.EHULL_SYNTHESIZABLE) in system and str(config.BANDGAP_MIN) in system
    assert "per substitution" in system
    assert brain.requests[0]["reasoning_effort"] == config.AGENT_REASONING_EFFORT

    # The analysis gets code-computed comparisons over all candidates so far, and is told to rely on them.
    analysis_request = brain.requests[3]["messages"]
    assert "never compare values yourself" in analysis_request[0]["content"]
    comps = json.loads(analysis_request[1]["content"])["comparisons"]
    assert any(c["kind"] == "same parent, different added element" and "S->Br" in c["about"] for c in comps)
    assert result["iterations"][1]["comparisons"] == comps

    assert result["usage"]["llm"]["meta"]["calls"] == 4
    passed = [c for r in result["iterations"] for c in r["candidates"] if c["status"] == "passed"]
    by_id = {c["id"]: c for c in passed}
    costs = [by_id[cid]["e_hull_per_substitution"] for cid in result["final_ranking"]]
    assert costs == sorted(costs)  # final ranking by E_hull per substitution
    report = render(result)
    for text in ("## Iteration 2", "## Final ranking", "Li3SbS4", "Reasoning summary", "meta: 4 calls",
                 "E_hull per substitution", "Comparisons computed by the code"):
        assert text in report
    json.dumps(result)


def test_model_stop_ends_loop(li3ps4):
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(stop=True)])
    result = agent(li3ps4, brain).run(parents=[PARENT], n_iterations=2)
    assert len(result["iterations"]) == 1 and result["stop_reason"] == "the model asked to stop"


def test_fallback_used_once_when_brain_fails(li3ps4):
    brain = FakeLLM("meta", [llm.LLMError("HTTP 500"), llm.LLMError("HTTP 500")])
    fallback = FakeLLM("baseten", [proposal((PARENT, SUB_CL)), analysis()])
    a = agent(li3ps4, brain, fallback)
    result = a.run(parents=[PARENT], n_iterations=1)
    assert result["iterations"][0]["proposal"]["provider"] == "baseten"
    assert "reasoning_effort" not in fallback.requests[0]
    assert sum(e["step"] == "error" and e["type"] == "llm" for e in a.events.events) == 2


def test_llm_budget_stops_without_fallback(li3ps4):
    brain = FakeLLM("meta", [llm.BudgetExceeded("cap reached")])
    fallback = FakeLLM("baseten", [proposal((PARENT, SUB_CL))])
    result = agent(li3ps4, brain, fallback).run(parents=[PARENT], n_iterations=2)
    assert result["stop_reason"].startswith("language model") and fallback.requests == []


def test_relaxation_budget_stops_cleanly(li3ps4):
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis()])
    result = agent(li3ps4, brain, budget=3).run(parents=[PARENT], n_iterations=2)
    cands = result["iterations"][0]["candidates"]
    assert [c["status"] for c in cands] == ["budget", "budget"]
    assert result["stop_reason"].startswith("relaxation budget") and len(result["iterations"]) == 1
    assert result["iterations"][0]["analysis"] is not None  # the model still sees what happened


def test_loop_limits_come_from_config(li3ps4):
    with pytest.raises(ValueError):
        agent(li3ps4, FakeLLM("meta", [])).run(parents=[PARENT], n_iterations=config.MAX_ITERATIONS + 1)
    with pytest.raises(ValueError):
        agent(li3ps4, FakeLLM("meta", [])).run(parents=[PARENT], max_candidates=config.MAX_CANDIDATES_PER_ITERATION + 1)


def test_the_same_substitution_however_written_is_one_key():
    from autolab.agent.loop import _substitution_key

    a = _substitution_key(PARENT, {"remove": "S", "add": "Se", "count": 2})
    b = _substitution_key(PARENT, {"remove": "S", "add": "Se", "count": "2", "li_vacancies": 0, "note": "x"})
    assert a == b and a != _substitution_key(PARENT, {"remove": "S", "add": "Se", "count": 2, "li_vacancies": 1})
