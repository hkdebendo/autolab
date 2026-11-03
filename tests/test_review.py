"""Campaign review by Muse Wonder (agent/review.py) with a fake model: no network, no cost."""

import json
from types import SimpleNamespace

import pytest

from autolab import config
from autolab.agent import review
from autolab.agent.events import EventLog
from autolab.agent.service import Service
from autolab.domains import get_domain
from autolab.llm.schemas import SchemaError, parse_reply
from autolab.store.conversations import MemoryStore
from test_agent import FakeLLM
from test_loop import campaign_review_reply


def campaign(prior=()):
    cl = {"id": "it1-c1", "formula": "Li5P2S7Cl", "status": "passed", "e_hull": 0.012, "md_verdict": "lower",
          "excluded_at": "molecular_dynamics", "exclusion_reason": "framework moved: Cl at 17.7 % of Li",
          "relaxed_atoms": {"positions": [[0.0, 0.0, 0.0]] * 500}, "rationale": "softer anion"}
    se = {"id": "it2-c1", "formula": "Li6P2SeS7", "status": "passed", "e_hull": -0.007, "md_verdict": "tied",
          "D_ratio_to_parent": 0.66, "conductivity": {"Ea_eV": 0.42, "points": [{"T": 500.0}] * 3}}
    return {"goal": "Find fast stable sulfides", "domain": "electrolyte", "stop_reason": "iterations done",
            "parents": [{"id": "mp-985583", "formula": "Li3PS4"}], "settings": {"thresholds": {"BANDGAP_MIN": 2.0}},
            "prior": list(prior),
            "iterations": [
                {"iteration": 1, "proposal": {"reply": {"hypothesis": "halides soften the lattice"}}, "candidates": [cl],
                 "feedback": [{"formula": "Li5P2S7Cl", "test": "Li diffusion", "reason": "framework moved",
                               "message": "long sentence"}],
                 "analysis": {"reply": {"failure_analysis": [{"id": "it1-c1", "hypothesis": "weak Cl binding",
                                                              "correction": "drop Cl"}],
                                        "lessons": ["Cl moves"], "next_direction": "try Se", "ranking": []}}},
                {"iteration": 2, "proposal": {"reply": {"hypothesis": "isovalent Se"}}, "candidates": [se],
                 "feedback": [], "analysis": {"reply": {"lessons": ["Se keeps the framework"],
                                                         "next_direction": "stop", "ranking": ["it2-c1"]}}}],
            "stages": {"ranking": {"status": "done", "finalists": ["it2-c1"], "excluded": {"it1-c1": "framework"},
                                   "summary": {"finalists": ["it2-c1"]}},
                       "novelty": {"status": "done", "candidates": [{"formula": "Li6P2SeS7", "label": "close family",
                                                                      "level": "related", "sources": ["u"] * 9}]},
                       "report": {"status": "done", "champion": "it2-c1", "completeness": "partial",
                                  "narrative": {"executive_summary": "Se kept the framework.", "tradeoffs": ["t"]}},
                       "campaign_review": {"status": "start"}}}


def camp(result, director):
    return SimpleNamespace(agent=SimpleNamespace(director=director, result=result, events=EventLog()))


def test_the_dossier_holds_the_whole_campaign_without_bulky_data():
    d = review.dossier(campaign())
    assert [r["hypothesis"] for r in d["rounds"]] == ["halides soften the lattice", "isovalent Se"]
    assert d["rounds"][0]["candidates"][0]["exclusion_reason"].startswith("framework moved")
    assert d["rounds"][0]["analysis"]["failure_analysis"][0]["hypothesis"] == "weak Cl binding"
    assert d["finalists"][0]["formula"] == "Li6P2SeS7" and d["finalists"][0]["conductivity"] == {"Ea_eV": 0.42}
    assert d["report"]["executive_summary"] == "Se kept the framework." and "tradeoffs" not in d["report"]
    assert d["literature"] == [{"formula": "Li6P2SeS7", "label": "close family", "level": "related"}]
    text = json.dumps(d)
    assert "relaxed_atoms" not in text and "long sentence" not in text and "campaign_review" not in d["stages"]


def test_a_too_large_dossier_drops_the_earlier_researches_then_stops(monkeypatch):
    prior = [{"id": f"ref:{i}", "formula": "Li3PS4", "status": "rejected", "reason": "x" * 300} for i in range(40)]
    result = campaign(prior)
    full = len(json.dumps(review.dossier(result), default=str))
    lean = len(json.dumps(review.dossier(result, earlier=False), default=str))
    monkeypatch.setattr(config, "CAMPAIGN_REVIEW_MAX_INPUT_CHARS", (full + lean) // 2)
    assert "earlier_candidates" not in review.review_messages(result)[1]["content"]
    monkeypatch.setattr(config, "CAMPAIGN_REVIEW_MAX_INPUT_CHARS", lean - 1)
    with pytest.raises(ValueError, match="CAMPAIGN_REVIEW_MAX_INPUT_CHARS"):
        review.review_messages(result)


def test_without_muse_wonder_the_stage_is_skipped_and_said():
    out = review.campaign_review(camp(campaign(), None))
    assert out["skipped"] == "no campaign reviewer configured" and out["summary"]["skipped"]


def test_muse_wonder_is_called_once_and_its_review_is_an_event():
    director = FakeLLM("wonder", [campaign_review_reply()])
    c = camp(campaign(), director)
    out = review.campaign_review(c)
    req = director.requests[0]
    assert len(director.requests) == 1 and req["schema"] == "campaign_review"
    assert req["max_output_tokens"] == config.CAMPAIGN_REVIEW_MAX_OUTPUT_TOKENS
    assert req["reasoning_effort"] == config.CAMPAIGN_REVIEW_REASONING_EFFORT
    assert "never claim a material is proven" in req["messages"][0]["content"]
    assert out["review"]["next_campaign"]["goal"] == "Try Br and I in Li7P3S11"
    assert out["summary"] == {"headline": "One bromide passed every test.", "next_goal": "Try Br and I in Li7P3S11"}
    ev = [e for e in c.agent.events.events if e["step"] == "campaign_review"][0]
    assert ev["type"] == "llm" and ev["data"]["provider"] == "wonder" and ev["data"]["reply"] == out["review"]


def test_the_reply_must_hold_a_complete_next_campaign():
    bad = {**campaign_review_reply(), "next_campaign": {"goal": "g"}}
    with pytest.raises(SchemaError, match="next_campaign"):
        parse_reply(json.dumps(bad), "campaign_review")
    assert parse_reply(json.dumps(campaign_review_reply()), "campaign_review")["headline"]


def test_the_review_is_the_last_message_and_is_copied_when_a_research_is_reused():
    out = review.campaign_review(camp(campaign(), FakeLLM("wonder", [campaign_review_reply()])))
    result = {**campaign(), "stages": {"campaign_review": {"status": "done", **out}}}
    store = MemoryStore()
    store.create({"id": "src", "title": "t", "goal": "g", "status": "done"})
    store.save_result("src", result)
    svc = Service(store, lambda: [], lambda cid: None)
    svc.finish("src", result, get_domain("electrolyte"))
    rv = [m for m in store.messages("src") if m["kind"] == "review"]
    assert len(rv) == 1 and "### Next campaign" in rv[0]["content"] and "> Try Br and I in Li7P3S11" in rv[0]["content"]
    assert rv[0]["data"]["headline"] == "One bromide passed every test."
    store.create({"id": "copy", "title": "t", "goal": "g", "status": "queued"})
    svc.reuse("copy", store.get("src"), {})
    assert [m["kind"] for m in store.messages("copy")][-1] == "review"


def test_every_domain_ends_with_the_campaign_review():
    for name in ("electrolyte", "cathode", "sodium"):
        assert [s.name for s in get_domain(name).stages][-2:] == ["report", "campaign_review"]
