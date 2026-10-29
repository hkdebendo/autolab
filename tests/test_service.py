"""The AutoLab service (agent/service.py) over a memory store, with fake models and tools: no network, no cost."""

import json

import pytest

from autolab import config
from autolab.agent.loop import Agent
from autolab.agent.scope import NEW_CHAT_NOTICE
from autolab.agent.service import BUSY, LIMIT, RUNNING, Service
from autolab.llm import client as llm
from autolab.sim.backend import RelaxBudget
from autolab.store.conversations import MemoryStore, question_key
from test_agent import PARENT, SUB_CL, FakeLLM, analysis, li3ps4, proposal  # noqa: F401
from test_loop import Calls, fake_tools, md_selection, report_reply, tmp_cache  # noqa: F401


def scope(intent="new_discovery", status="supported", domain="electrolyte", title="Halide sulfide electrolytes"):
    return {"intent": intent, "status": status, "domain": domain, "title": title, "constraints": ["Li metal"],
            "reply": "AutoLab will screen halide-substituted thiophosphates."}


class Model(FakeLLM):
    """complete_json (scope) and chat (follow-up answers) with prepared replies."""

    def __init__(self, replies=(), answers=()):
        super().__init__("meta", list(replies))
        self.answers = list(answers)
        self.chats = []

    def chat(self, messages, **kwargs):
        self.chats.append(messages)
        return llm.Reply("meta", "m", self.answers.pop(0), "", 10, 10, None, 0.0, 0.1)


def service(model, spawned=None):
    store = MemoryStore()
    return Service(store, lambda: [model], (spawned.append if spawned is not None else lambda cid: None)), store


def test_a_supported_request_starts_a_research_with_a_title():
    spawned = []
    svc, store = service(Model([scope()]), spawned)
    v = svc.start("Find halide-doped sulfide electrolytes for lithium metal")
    c = v["conversation"]
    assert c["title"] == "Halide sulfide electrolytes" and c["status"] == "queued" and spawned == [c["id"]]
    assert [m["kind"] for m in v["messages"]] == ["request", "scope"]
    assert svc.history()[0]["id"] == c["id"]


def test_unsupported_planned_busy_and_capped_requests_do_not_start():
    spawned = []
    svc, store = service(Model([scope(status="unsupported", domain=""), scope(domain="cathode"), scope(), scope()]),
                         spawned)
    assert svc.start("design a catalyst")["conversation"]["status"] == "answered"
    assert svc.start("cobalt-free cathodes")["conversation"]["scope"]["status"] == "planned"
    first = svc.start("electrolytes")["conversation"]["id"]
    busy = svc.start("electrolytes again")
    assert busy["conversation"]["status"] == "answered" and busy["messages"][-1]["content"] == BUSY
    assert spawned == [first]
    store.update(first, status="done")
    store.live_runs_used = lambda: config.LIVE_MAX_RUNS
    capped = Service(store, lambda: [Model([scope()])], spawned.append).start("more electrolytes")
    assert capped["messages"][-1]["content"] == LIMIT and spawned == [first]


def test_follow_ups_reuse_stored_answers_and_refuse_new_discoveries():
    model = Model([scope(), scope(intent="follow_up"), scope(intent="new_discovery")], answers=["Because of X."])
    svc, store = service(model)
    cid = svc.start("electrolytes")["conversation"]["id"]
    assert svc.post(cid, "Why is it stable?")["messages"][-1]["content"] == RUNNING  # still running
    store.update(cid, status="done")
    store.save_result(cid, {"goal": "electrolytes", "stages": {}, "iterations": [], "prior": []})
    v = svc.post(cid, "Why is it stable?")
    assert v["messages"][-1]["content"] == "Because of X." and len(model.chats) == 1
    again = svc.post(cid, "why is it   STABLE")  # same question: stored answer, no model call at all
    assert again["messages"][-1]["content"] == "Because of X." and again["messages"][-1]["data"] == {"reused": True}
    assert len(model.chats) == 1 and len(model.requests) == 2
    new = svc.post(cid, "Now find cathode materials")
    assert new["messages"][-1]["content"] == NEW_CHAT_NOTICE and new["messages"][-1]["data"] == {"action": "new_chat"}
    assert question_key("Why is it stable?") == question_key("why is it   STABLE")


def test_a_research_runs_stores_its_events_result_report_and_can_be_stopped(li3ps4):
    model = Model([scope()])
    svc, store = service(model)
    cid = svc.start("electrolytes")["conversation"]["id"]
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1"), report_reply()])

    def make_agent(events, should_stop):
        return Agent(brain, tools=fake_tools(Calls()), events=events, budget=RelaxBudget(20),
                     get_structure=lambda pid: li3ps4, should_stop=should_stop)

    exported = []
    result = svc.run(cid, make_agent, prior=[], export=lambda c, r: exported.append(c))
    v = svc.view(cid)
    assert v["conversation"]["status"] == "done" and v["has_result"] and exported == [cid]
    assert [m["kind"] for m in v["messages"]][-2:] == ["summary", "report"]
    assert "### Champion: Li11P4S15Cl" in v["messages"][-1]["content"]
    states = {s["key"]: s["state"] for s in v["steps"]}
    assert states["goal"] == "done" and states["md"] == "done" and states["report"] == "done"
    assert store.cands[cid][0]["formula"] == "Li11P4S15Cl" and result["final_ranking"] == ["it1-c1"]
    p = svc.progress(cid, after=v["events_count"] - 1)
    assert len(p["events"]) == 1 and p["events"][0]["step"] == "stop"
    json.dumps(v, default=str)

    # a second research, stopped before it starts
    svc.models = lambda: [Model([scope()])]
    cid2 = svc.start("electrolytes 2")["conversation"]["id"]
    assert svc.cancel(cid2)["conversation"]["status"] == "stopping"
    assert svc.run(cid2, make_agent, prior=[]) is None and store.get(cid2)["status"] == "interrupted"
    assert not svc.delete(cid) or store.get(cid) is None


def test_requests_are_checked():
    svc, _ = service(Model([]))
    with pytest.raises(ValueError):
        svc.start(" ")
    assert svc.view("nope") is None and svc.post("nope", "x") is None and svc.cancel("nope") is None
