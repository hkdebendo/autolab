"""Live runs for the jury (agent/live.py) with a plain dict as the store and fake models: no Modal, no cost."""

import pytest

from autolab import config
from autolab.agent.live import LiveRefused, check_request, events_after, reserve, run_live
from autolab.agent.loop import Agent
from autolab.sim.backend import RelaxBudget
from test_agent import PARENT, SUB_CL, FakeLLM, analysis, li3ps4, proposal  # noqa: F401
from test_loop import Calls, fake_tools, md_selection


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "UMA_MP2020", False)


def test_requests_are_refused_without_the_code_while_busy_or_over_the_cap():
    store = {}
    with pytest.raises(LiveRefused, match="access code"):
        check_request("find electrolytes", "wrong", "secret", store)
    with pytest.raises(LiveRefused, match="access code"):
        check_request("find electrolytes", "", None, store)  # no code configured: nobody gets in
    with pytest.raises(LiveRefused, match="characters"):
        check_request(" ", "secret", "secret", store)
    check_request("find electrolytes", "secret", "secret", store)
    reserve(store, "r1", "find electrolytes")
    with pytest.raises(LiveRefused, match="one at a time"):
        check_request("another", "secret", "secret", store)
    store["lock"], store["live_runs"] = None, config.LIVE_MAX_RUNS
    with pytest.raises(LiveRefused, match="live runs allowed"):
        check_request("another", "secret", "secret", store)


def test_a_live_run_streams_its_events_releases_the_lock_and_restores_the_limits(li3ps4):
    store, calls = {}, Calls()
    reserve(store, "r1", "Cl in Li3PS4")
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    seen_limit = []

    def make_agent(events):
        seen_limit.append(config.MD_SELECT_MAX)
        return Agent(brain, tools=fake_tools(calls), events=events, budget=RelaxBudget(20),
                     get_structure=lambda pid: li3ps4)

    result = run_live("r1", "Cl in Li3PS4", store, make_agent, prior=[])
    assert seen_limit == [config.LIVE_MD_SELECT_MAX] and config.MD_SELECT_MAX == 3  # restored after the run
    assert store["lock"] is None and store["r1/status"]["state"] == "done" and store["r1/result"] is result
    page = events_after(store, "r1")
    assert page["events"][0]["step"] == "start" and page["events"][-1]["step"] == "stop"
    later = events_after(store, "r1", after=page["next"] - 2)
    assert len(later["events"]) == 2 and later["status"]["state"] == "done"
    assert events_after(store, "unknown") == {"events": [], "next": 0, "status": None}


def test_a_failed_live_run_reports_the_error_and_frees_the_lock(li3ps4):
    store = {}
    reserve(store, "r2", "x")

    def make_agent(events):
        raise RuntimeError("Modal: spending limit reached")

    with pytest.raises(RuntimeError):
        run_live("r2", "x", store, make_agent, prior=[])
    assert store["lock"] is None and store["r2/status"]["state"] == "error"
    assert "spending limit" in store["r2/status"]["error"] and config.MD_SELECT_MAX == 3
