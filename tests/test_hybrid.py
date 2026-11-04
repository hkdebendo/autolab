"""Hybrid replay (agent/hybrid.py) of a recorded research with fake models: no network, no cost."""

import json
from pathlib import Path

import pytest

from autolab.agent import hybrid
from autolab.agent.importer import import_run
from autolab.agent.service import Service
from autolab.llm import client as llm
from autolab.store.conversations import MemoryStore
from test_loop import campaign_review_reply

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "results/2026-11-01_feedback_run"
REPLIES = {
    "analysis": {"ranking": [], "lessons": ["live lesson"], "next_direction": "live direction", "stop": False,
                 "failure_analysis": [{"id": "it1-c1", "hypothesis": "live hypothesis", "correction": "live fix"}]},
    "candidate_analysis": {"strengths": ["live strength"], "risks": ["live risk"], "md_priority": "high",
                           "summary": "live review"},
    "campaign_review": campaign_review_reply(),
}


class Fake:
    def __init__(self, provider, fail=()):
        self.provider, self.model, self.fail = provider, "fake", set(fail)
        self.tracker = llm.UsageTracker()
        self.calls = []

    def complete_json(self, messages, schema, **kw):
        self.calls.append(schema)
        if schema in self.fail:
            raise llm.LLMError(f"{self.provider}: HTTP 500")
        return REPLIES[schema], [llm.Reply(self.provider, "fake", json.dumps(REPLIES[schema]), "live reasoning", 10, 10,
                                           None, 0.0, 0.1)]

    def chat(self, messages, **kw):
        self.calls.append("summary")
        return llm.Reply(self.provider, "fake", "live summary", "", 10, 10, None, 0.0, 0.1)


@pytest.fixture
def recorded():
    store = MemoryStore()
    svc = Service(store, lambda: [], lambda cid: None)
    goal = json.loads((RUN / "result.json").read_text(encoding="utf-8"))["goal"]
    import_run(svc, RUN, "src", "Recorded", goal)
    store.create({"id": "live", "title": "t", "goal": goal, "status": "running"})
    return svc, store


def models(**fail):
    brain, reviewer, director = Fake("meta", fail.get("brain", ())), Fake("baseten"), Fake("wonder")
    return {"brain": brain, "reviewer": reviewer, "summarizer": None, "writer": Fake("meta"), "director": director}


def test_the_agents_work_live_on_the_recorded_computations(recorded):
    svc, store = recorded
    m = models()
    result = hybrid.replay(store, "live", "src", m, svc.finish, sleep=lambda s: None)
    ev = store.events("live")
    src = store.events("src")
    assert len(ev) == len(src)  # the same steps, in the same order
    assert [(e["type"], e["step"]) for e in ev] == [(e["type"], e["step"]) for e in src]
    analyses = [e for e in ev if e["step"] == "analysis" and e["type"] == "llm"]
    assert len(analyses) == 3 and all(e["data"]["reply"]["lessons"] == ["live lesson"] for e in analyses)
    assert all(e["data"]["hybrid"] for e in analyses) and m["brain"].calls.count("analysis") == 3
    reviews = [e for e in ev if e["step"] == "candidate_analyses:done"]
    assert reviews and all(e["data"]["summary"] == "live review" for e in reviews)
    assert all(e["data"]["text"] == "live summary" for e in ev if e["step"] == "summary")
    wonder = next(e for e in ev if e["step"] == "campaign_review" and e["type"] == "llm")
    assert wonder["data"]["reply"]["headline"] == campaign_review_reply()["headline"]
    # the computations are the recorded ones
    assert [e["data"] for e in ev if e["step"] == "molecular_dynamics:done"] == \
        [e["data"] for e in src if e["step"] == "molecular_dynamics:done"]
    assert result["iterations"][0]["analysis"]["reply"]["next_direction"] == "live direction"
    assert store.get("live")["status"] == "done"
    kinds = [x["kind"] for x in store.messages("live")]
    assert kinds[-3:] == ["summary", "report", "review"]
    assert store.messages("live")[-1]["data"]["headline"] == campaign_review_reply()["headline"]


def test_a_failed_call_keeps_the_recorded_answer_and_says_so(recorded):
    svc, store = recorded
    hybrid.replay(store, "live", "src", models(brain=("analysis",)), svc.finish, sleep=lambda s: None)
    rec = [e["data"]["reply"] for e in store.events("src") if e["step"] == "analysis" and e["type"] == "llm"]
    live = [e["data"]["reply"] for e in store.events("live") if e["step"] == "analysis" and e["type"] == "llm"]
    assert live == rec
    assert "could not be reached" in store.messages("live")[-1]["content"]


def test_a_stop_request_ends_the_replay(recorded):
    svc, store = recorded
    store.update("live", cancel_requested_at="now")
    hybrid.replay(store, "live", "src", models(), svc.finish, sleep=lambda s: None)
    assert store.events("live") == [] and store.get("live")["status"] == "interrupted"


class Matcher:
    provider = "meta"

    def __init__(self, answer):
        self.answer, self.requests = answer, []

    def complete_json(self, messages, schema, **kw):
        self.requests.append((messages, schema))
        return {"match": self.answer, "reason": "same goal"}, []


RECORDED_DEMO = [{"id": "0245f94a24cf", "request": "Find new solid electrolytes...", "goal": "sulfide electrolytes"}]


def test_a_reworded_request_is_matched_to_its_recorded_research_only_by_a_known_id():
    m = Matcher("0245f94a24cf")
    assert hybrid.match_recorded(m, "Look for lithium solid electrolytes as fast as their parent", RECORDED_DEMO) == "0245f94a24cf"
    messages, schema = m.requests[0]
    assert schema == "recorded_match" and "does not match" in messages[0]["content"]
    assert "Look for lithium solid electrolytes" in messages[1]["content"]
    assert hybrid.match_recorded(Matcher("none"), "Br in Li3PS4", RECORDED_DEMO) is None
    assert hybrid.match_recorded(Matcher("made-up-id"), "anything", RECORDED_DEMO) is None
    assert hybrid.match_recorded(Matcher("0245f94a24cf"), "anything", []) is None and hybrid.match_recorded(None, "x", RECORDED_DEMO) is None
