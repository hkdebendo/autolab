"""Conversation logic (interface.md): steps from events, scope check, follow-up context, stopping a research.
Fake tools and models: no network, no cost."""

import json

from autolab import config
from autolab.agent import cancel
from autolab.agent.events import EventLog
from autolab.agent.followup import context, followup_messages
from autolab.agent.loop import INTERRUPTED, Agent
from autolab.agent.progress import steps_from_events
from autolab.agent.scope import enforce, scope_messages
from autolab.sim.backend import RelaxBudget
from test_agent import BR, PARENT, SUB_CL, FakeLLM, analysis, li3ps4, proposal  # noqa: F401
from test_loop import Calls, fake_tools, md_selection, report_reply, tmp_cache  # noqa: F401


def ev(type_, step, **data):
    return {"type": type_, "step": step, "candidate_id": None, "data": data, "timestamp": "2026-10-29T10:00:00+00:00"}


def states(steps):
    return {s["key"]: s["state"] for s in steps}


def test_steps_come_only_from_real_events():
    running = [ev("loop", "scope"), ev("llm", "proposal", reply={"proposals": [1, 2]}), ev("candidate", "relax"),
               ev("candidate", "hull", e_hull=0.02)]
    s = states(steps_from_events(running, "running"))
    assert s["goal"] == "done" and s["stability"] == "running" and s["bandgap"] == "pending" and s["md"] == "pending"
    later = running + [ev("stage", "electrodes", status="start"), ev("stage", "electrodes", status="done"),
                       ev("stage", "candidate_analyses", status="done", skipped="no analyst model"),
                       ev("stage", "md_selection", status="start")]
    s = states(steps_from_events(later, "running"))
    assert s["stability"] == "done" and s["electrodes"] == "done" and s["review"] == "skipped"
    assert s["md_choice"] == "running" and s["report"] == "pending"
    stopped = later + [ev("stage", "molecular_dynamics", status="interrupted")]
    s = states(steps_from_events(stopped, "interrupted"))
    assert s["md_choice"] == "interrupted" and s["md"] == "interrupted" and s["report"] == "interrupted"
    detail = {x["key"]: x["detail"] for x in steps_from_events(running, "running")}
    assert detail["propose"].startswith("2 substitutions") and detail["stability"].startswith("1 of 1")
    assert all("Muse" not in x["label"] + x["why"] for x in steps_from_events(running, "running"))


def test_scope_is_held_to_the_capabilities():
    r = enforce({"intent": "new_discovery", "status": "supported", "domain": "electrolyte", "title": "Halide sulfides",
                 "constraints": ["no cobalt"], "reply": "ok"}, in_conversation=False)
    assert r["action"] == "start" and r["domain"] == "electrolyte"
    r = enforce({"intent": "new_discovery", "status": "supported", "domain": "cathode", "title": "x", "constraints": [],
                 "reply": "ok"}, in_conversation=False)
    assert r["status"] == "planned" and r["action"] == "explain"  # not implemented: never "supported"
    r = enforce({"intent": "new_discovery", "status": "supported", "domain": "catalysts", "title": "x",
                 "constraints": [], "reply": ""}, in_conversation=False)
    assert r["status"] == "unsupported" and r["domain"] == "" and r["action"] == "explain"
    r = enforce({"intent": "new_discovery", "status": "supported", "domain": "electrolyte", "title": "x",
                 "constraints": [], "reply": ""}, in_conversation=True)
    assert r["action"] == "new_chat"  # a new discovery never starts inside an old conversation
    r = enforce({"intent": "follow_up", "status": "supported", "domain": "electrolyte", "title": "x", "constraints": [],
                 "reply": ""}, in_conversation=True)
    assert r["action"] == "answer"
    system = scope_messages("find cobalt-free electrolytes")[0]["content"]
    assert "electrolyte" in system and "planned" in system.lower() and "cobalt" in system


def test_follow_up_context_comes_from_the_stored_result(li3ps4):
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1"), report_reply()])
    result = Agent(brain, tools=fake_tools(Calls()), budget=RelaxBudget(20), get_structure=lambda pid: li3ps4).run(
        parents=[PARENT], n_iterations=1)
    facts = context(json.loads(json.dumps(result, default=str)))
    assert facts["finalists"][0]["formula"] == "Li11P4S15Cl" and facts["finalists"][0]["md_verdict"] == "tied"
    assert facts["report"]["champion"] == "it1-c1" and "not_computed" in facts
    msgs = followup_messages("Why is it stable?", facts, [{"question": "q1", "answer": "a1"}])
    assert msgs[-1]["content"] == "Why is it stable?" and msgs[-2] == {"role": "assistant", "content": "a1"}
    assert "never invent" in msgs[0]["content"]


def test_a_stop_request_interrupts_without_starting_anything_new(li3ps4):
    stop = {"now": False}
    calls = Calls()
    tools = fake_tools(calls)
    relax = tools.relax

    def relax_then_stop(structures, budget):  # the user presses Stop while the first candidate is relaxing
        out = relax(structures, budget)
        stop["now"] = True
        return out

    tools.relax = relax_then_stop
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR))])
    events = EventLog()
    result = Agent(brain, tools=tools, events=events, budget=RelaxBudget(40), get_structure=lambda pid: li3ps4,
                   should_stop=lambda: stop["now"]).run(parents=[PARENT], n_iterations=2)
    cands = result["iterations"][0]["candidates"]
    assert cands[0]["status"] == "passed" and cands[1]["status"] == "interrupted"  # the running one finishes
    assert result["stop_reason"] == INTERRUPTED and len(result["iterations"]) == 1 and len(brain.requests) == 1
    assert all(s["status"] == "interrupted" for s in result["stages"].values()) and calls.md_screen == []
    assert not cancel.requested()  # the watch ends with the run
    s = states(steps_from_events(events.events, "interrupted"))
    assert s["md"] == "interrupted" and s["report"] == "interrupted"
    assert config.MD_SELECT_MAX == 3
