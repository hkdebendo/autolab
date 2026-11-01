"""Error-driven loop (config.FEEDBACK_LOOP): the slow tests run inside each iteration, their failures go back to the
model with their measurements, and its reading of them shapes the next proposals. Fake tools and models: no cost."""

import json

import pytest

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.progress import steps_from_events
from autolab.agent.report import render
from autolab.domains.electrolyte import feedback, framework_view
from autolab.llm.schemas import SchemaError, validate
from autolab.sim.backend import RelaxBudget
from test_agent import BR, PARENT, SUB_CL, FakeLLM, analysis, li3ps4, proposal  # noqa: F401
from test_loop import I_SUB, Calls, fake_tools, md_selection, report_reply

FAILURE = {"id": "it1-c2", "hypothesis": "the large iodide strains the PS4 framework",
           "correction": "use a smaller halide with one Li vacancy"}


@pytest.fixture(autouse=True)
def feedback_on(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "UMA_MP2020", False)  # the fake hull holds raw energies (as in test_agent)
    monkeypatch.setattr(config, "FEEDBACK_LOOP", True)
    monkeypatch.setattr(config, "ITERATION_MD_SELECT_MAX", 1)
    monkeypatch.setattr(config, "FINAL_MD_SELECT_MAX", 0)


def run(li3ps4, brain, tools, n_iterations=2):
    events = EventLog()
    agent = Agent(brain, tools=tools, events=events, budget=RelaxBudget(60), get_structure=lambda pid: li3ps4)
    return agent.run(parents=[PARENT], n_iterations=n_iterations), events


def two_rounds(calls, **kw):
    # round 1: S->Cl reacts with Li metal (excluded), S->I slower than its parent (excluded); round 2: S->Br tied
    tools = fake_tools(calls, passivation={"Li11P4S15Cl": "non_passivating"},
                       verdicts={"Li11P4S15I": "lower", "Li11P4S15Br": "tied"}, **kw)
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, I_SUB)), md_selection("it1-c2"),
                             {**analysis(), "failure_analysis": [FAILURE]},
                             proposal((PARENT, BR), hypothesis="smaller halide corrects it1-c2"),
                             md_selection("it2-c1"), analysis(["it2-c1"]), report_reply()])
    return tools, brain


def test_failures_go_back_to_the_model_and_shape_the_next_round(li3ps4):
    calls = Calls()
    tools, brain = two_rounds(calls)
    result, events = run(li3ps4, brain, tools)

    # order of the model calls: the MD choice of each round comes before its analysis; no new MD choice at the end
    assert [r["schema"] for r in brain.requests] == ["proposal", "md_selection", "analysis", "proposal",
                                                     "md_selection", "analysis", "report"]
    # one MD per round, chosen by the model; nothing simulated again after the iterations
    assert calls.md_screen == [["it1-c2"], ["it2-c1"]]
    assert result["stages"]["md_selection"]["summary"]["reason"].startswith("candidates were chosen")
    # electrodes computed once per candidate (the final stage reuses them): it1-c2 and it2-c1 got an interface
    assert sorted(c for c, _ in calls.interfaces) == ["it1-c2", "it2-c1"]

    fb = result["iterations"][0]["feedback"]
    assert [(f["id"], f["test"].split(" (")[0], f["outcome"]) for f in fb] == [
        ("it1-c1", "contact with Li metal", "failed"), ("it1-c2", "Li diffusion at 600 K", "failed")]
    assert fb[0]["measured"]["metallic_products"] == ["Li3P"] and fb[0]["message"].startswith("Negative result:")
    assert fb[1]["measured"]["verdict"] == "lower" and "slower than its parent" in fb[1]["reason"]
    # the analysis of round 1 sees the measured failures, and is asked for a hypothesis and a correction
    req = json.loads(brain.requests[2]["messages"][1]["content"])
    assert [f["id"] for f in req["slow_tests"]] == ["it1-c1", "it1-c2"]
    system = brain.requests[2]["messages"][0]["content"]
    assert "failure_analysis" in system and "explicitly a hypothesis" in system
    # the proposal of round 2 sees the failures and the model's reading of them
    hist = json.loads(brain.requests[3]["messages"][1]["content"])["history"][-1]
    assert [f["outcome"] for f in hist["slow_tests"]] == ["failed", "failed"]
    assert hist["failure_analysis"] == [FAILURE]
    assert "do not repeat a strategy that failed" in brain.requests[3]["messages"][0]["content"]
    # results the model sees for the earlier candidates now hold their exclusions
    seen = {c["id"]: c for c in hist["results"]}
    assert seen["it1-c2"]["excluded_at"] == "molecular_dynamics" and seen["it1-c2"]["md_verdict"] == "lower"

    fb2 = result["iterations"][1]["feedback"]
    assert [(f["id"], f["outcome"]) for f in fb2] == [("it2-c1", "passed")] and "tied" in fb2[0]["reason"]
    assert result["stages"]["ranking"]["finalists"] == ["it2-c1"]
    assert result["usage"]["md_usd"] == pytest.approx(2.4)  # 2 MD steps of 1.2 $ (fake plans)

    # events: one feedback event per round; stage events inside a round carry its number
    fbe = [e for e in events.events if (e["type"], e["step"]) == ("loop", "feedback")]
    assert [e["data"]["iteration"] for e in fbe] == [1, 2]
    md_ev = [e for e in events.events if e["type"] == "stage" and e["step"] == "molecular_dynamics"]
    assert [e["data"].get("iteration") for e in md_ev] == [1, 1, 2, 2, None, None]
    steps = {s["key"]: s for s in steps_from_events(events.events, "done")}
    assert steps["md"]["state"] == "done" and steps["md_choice"]["state"] == "done"
    assert steps["propose"]["state"] == "done"

    report = render(json.loads(json.dumps(result)))
    assert "Slow tests of this iteration (fed back to the model)" in report
    assert "hypothesis: the large iodide strains the PS4 framework" in report


def test_md_cap_covers_the_whole_research(li3ps4, monkeypatch):
    monkeypatch.setattr(config, "MD_MAX_USD_PER_RUN", 2.0)  # the first MD (1.2 $) fits, the second would not
    calls = Calls()
    tools, brain = two_rounds(calls)
    result, _ = run(li3ps4, brain, tools)
    assert calls.md_screen == [["it1-c2"]]
    stopped = result["iterations"][1]["stages"]["molecular_dynamics"]["stopped"]
    assert "1.20 $ already launched" in stopped and "not launched" in stopped
    assert result["iterations"][1]["feedback"] == []  # nothing measured: nothing claimed


def test_progress_while_a_round_runs_its_md(li3ps4):
    events = EventLog()
    events.emit("loop", "iteration", {"iteration": 1})
    events.emit("llm", "proposal", {"reply": {"proposals": [{}]}})
    events.emit("stage", "molecular_dynamics", {"status": "start", "iteration": 1})
    steps = {s["key"]: s for s in steps_from_events(events.events, "running")}
    assert steps["md"]["state"] == "running" and steps["ranking"]["state"] == "pending"
    assert steps["propose"]["state"] == "done"  # an iteration's stage is not the end of the funnel steps
    events.emit("stage", "molecular_dynamics", {"status": "done", "iteration": 1, "verdicts": {"it1-c1": "tied"}})
    events.emit("loop", "iteration", {"iteration": 2})
    events.emit("llm", "proposal", {"reply": {"proposals": [{}]}})
    steps = {s["key"]: s for s in steps_from_events(events.events, "running")}
    assert steps["propose"]["state"] == "running" and steps["md"]["state"] == "done"


def test_feedback_reports_measurements_only():
    moved = {"intact": False, "per_seed": [
        {"intact": False, "elements": {"Cl": {"D_ratio_to_Li": 0.40, "msd_final_A2": 5.4}, "P": {"D_ratio_to_Li": 0.001, "msd_final_A2": 0.1}}},
        {"intact": True, "elements": {"Cl": {"D_ratio_to_Li": 0.03, "msd_final_A2": 0.9}, "P": {"D_ratio_to_Li": 0.002, "msd_final_A2": 0.2}}}]}
    view = framework_view(moved)
    assert view["elements"]["Cl"] == {"D_ratio_to_Li": 0.4, "msd_final_A2": 5.4} and view["intact"] is False
    c = {"id": "it1-c1", "formula": "Li13P6S21Cl", "status": "passed", "parent": "mp-641703", "md_verdict": "tied",
         "D_cm2_per_s": 1e-5, "D_sem_cm2_per_s": 2e-6, "D_ratio_to_parent": 0.9, "D_ratio_err": 0.2,
         "excluded_at": "molecular_dynamics", "md_framework": view,
         "exclusion_reason": "framework moved: Cl diffuses at 40.0% of Li (limit 5%), seed 0, final MSD 5.4 A2"}
    (f,) = feedback([c, {"id": "x", "formula": "LiS", "status": "rejected"}])
    assert f["outcome"] == "failed" and f["measured"]["framework"]["elements"]["Cl"]["D_ratio_to_Li"] == 0.4
    assert "Cl diffuses at 40.0% of Li" in f["message"]
    assert "size" not in f["message"] and "radius" not in f["message"]  # the cause is left to the model


def test_failure_analysis_is_optional_but_checked_when_given():
    validate(analysis(), "analysis")
    validate({**analysis(), "failure_analysis": [FAILURE]}, "analysis")
    with pytest.raises(SchemaError, match="failure_analysis"):
        validate({**analysis(), "failure_analysis": [{"id": "x"}]}, "analysis")
