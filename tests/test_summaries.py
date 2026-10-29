"""Muse Glimmer's background summaries (agent/summaries.py): fake client, no network, no cost."""

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.summaries import Summarizer
from autolab.llm import client as llm
from autolab.sim.backend import RelaxBudget
from test_agent import PARENT, SUB_CL, FakeLLM, analysis, li3ps4, proposal  # noqa: F401
from test_loop import Calls, fake_tools, md_selection, tmp_cache  # noqa: F401


class FakeGlimmer:
    """chat stand-in: a sleeping deployment answers 503 `asleep` times, then replies."""

    def __init__(self, asleep=0, error=None):
        self.provider, self.tracker = "fireworks", llm.UsageTracker()
        self.asleep, self.error, self.requests = asleep, error, []

    def chat(self, messages, **kwargs):
        self.requests.append(messages)
        if self.error:
            raise self.error
        if self.asleep > 0:
            self.asleep -= 1
            raise llm.LLMError("fireworks: HTTP 503: deployment scaling up")
        return llm.Reply("fireworks", "glimmer", "Three candidates passed; two were excluded.", "", 100, 20, None,
                         0.0, 0.5)


def test_a_sleeping_deployment_is_waited_for_then_summarizes():
    events, sleeps = EventLog(), []
    s = Summarizer(FakeGlimmer(asleep=2), events, wait_s=60, poll_s=20, sleep=sleeps.append)
    s.submit("iteration", "iteration 1", {"hypothesis": "h"})
    out = s.close(timeout=10)
    assert out[0]["text"].startswith("Three candidates") and sleeps == [20, 20]
    assert [e["step"] for e in events.events] == ["summary"] and events.events[0]["data"]["label"] == "iteration 1"


def test_a_deployment_that_never_wakes_or_fails_is_reported_not_retried():
    s = Summarizer(FakeGlimmer(asleep=99), EventLog(), wait_s=40, poll_s=20, sleep=lambda x: None)
    s.submit("iteration", "iteration 1", {})
    out = s.close(timeout=10)
    assert out[0]["text"] is None and "503" in out[0]["error"] and len(s.client.requests) == 3
    s = Summarizer(FakeGlimmer(error=llm.QuotaError("fireworks: payment required")), EventLog(), sleep=lambda x: None)
    s.submit("whole run", "run", {})
    assert "payment required" in s.close(timeout=10)[0]["error"] and len(s.client.requests) == 1


def test_the_loop_asks_glimmer_for_iteration_and_run_summaries(li3ps4):
    events = EventLog()
    glimmer = FakeGlimmer()
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    agent = Agent(brain, tools=fake_tools(Calls()), events=events, budget=RelaxBudget(20),
                  get_structure=lambda pid: li3ps4, summarizer=Summarizer(glimmer, events, sleep=lambda x: None))
    result = agent.run(parents=[PARENT], n_iterations=1)
    assert [s["label"] for s in result["summaries"]] == ["iteration 1", "run"]
    assert all(s["text"] for s in result["summaries"]) and len(glimmer.requests) == 2
    assert "Li11P4S15Cl" in glimmer.requests[0][1]["content"]  # the iteration's candidates are in the request
    assert result["settings"]["summarizer"] == "fireworks" and result["usage"]["summaries"] is not None
    from autolab.agent.report import render

    assert "## Summaries (Muse Glimmer)" in render(result) and config.SUMMARY_MAX_PER_RUN >= 2
