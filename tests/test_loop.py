"""Complete loop (iterations, then electrodes, MD choice, MD, ranking, novelty) with fake tools and fake models:
no UMA, no ALIGNN, no Materials Project, no Modal, no API, no cost."""

import json

import pytest

from autolab import config
from autolab.agent.dynamics import md_verdicts
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.pipeline import evaluate_candidate
from autolab.agent.report import render
from autolab.domains import Domain, Stage, get_domain
from autolab.domains.electrolyte import ElectrolyteTools
from autolab.llm import client as llm
from autolab.sim.backend import BudgetExceeded as SimBudgetExceeded
from autolab.sim.backend import RelaxBudget
from autolab.store.cache import JsonCache
from test_agent import BR, PARENT, SUB_CL, FakeLLM, analysis, fake_gap, fake_hull, fake_relax, li3ps4, proposal  # noqa: F401
from test_novelty import meta, response

I_SUB = {"remove": "S", "add": "I", "count": 1, "li_vacancies": 1}
O_SUB = {"remove": "S", "add": "O", "count": 1}


def report_reply():
    return {"executive_summary": "One candidate passed.", "champion_reasons": ["tied with its parent"],
            "tradeoffs": ["t"], "uncertainties": ["u"], "validation": [{"text": "XRD", "basis": "documented"}],
            "synthesis": [{"text": "ball milling", "basis": "documented"}, {"text": "new route", "basis": "maybe"}],
            "limitations": ["l"]}


def md_selection(*ids, rationale="softer anions"):
    return {"selected": list(ids), "rationale": rationale}


class Calls:
    """Records what the fake stage tools were asked to compute."""

    def __init__(self):
        self.md_screen, self.interfaces, self.novelty = [], [], []


def fake_tools(calls: Calls, passivation=None, polysulfides=None, verdicts=None, md_usd=1.2, cal_ok=True,
               interface_budget=None, window_polysulfides=None):
    """Electrolyte tools with fakes for every expensive step. passivation / polysulfides (cathode reaction) /
    window_polysulfides (decomposition of the electrolyte) / verdicts: by formula."""
    passivation, polysulfides, verdicts = passivation or {}, polysulfides or {}, verdicts or {}
    window_polysulfides = window_polysulfides or {}

    def window_passivation(c, budget):
        v = passivation.get(c["formula"], "passivating")
        return {"window": {"v_low": 1.7, "v_high": 2.3, "stable": True, "reduction_products": ["Li2S", "Li3P"],
                           "oxidation_products": ["S"], "polysulfide_products": window_polysulfides.get(c["formula"], [])},
                "passivation": {"verdict": v, "reaction_energy": 0.3 if v == "non_passivating" else 0.0,
                                "products": [{"formula": "Li2S", "fraction": 1.0}],
                                "metallic_products": ["Li3P"] if v == "non_passivating" else [],
                                "polysulfide_products": []}}

    def interface(c, cathode, budget):
        if interface_budget is not None:
            if budget.remaining < interface_budget:
                raise SimBudgetExceeded(f"{interface_budget} requested, {budget.remaining} left")
            budget.used += interface_budget
        calls.interfaces.append((c["id"], cathode))
        return {"min_reaction_energy": -0.14, "mixing_ratio": 0.36, "reaction": "x -> FeS2 + y",
                "polysulfide_products": polysulfides.get(c["formula"], [])}

    def calibration(cathode, budget):
        return {"electrolyte": "Li3PS4", "cathode": cathode, "diff": -0.011 if cal_ok else 0.2, "ok": cal_ok,
                "tolerance": 0.05, "uma": {"min_reaction_energy": -0.144}, "mp": {"min_reaction_energy": -0.133}}

    def md_plan(cands):
        parents = {c["parent"] for c in cands}
        return {"gpu": "A10G", "runs": 2 * len(cands), "total_runs": 2 * (len(cands) + len(parents)),
                "wall_s": 1600, "usd": md_usd, "usd_max": 3 * md_usd, "timeout_s": 3200}

    def md_screen(cands, plan):
        calls.md_screen.append([c["id"] for c in cands])
        rows = [{"id": p, "formula": "Li3PS4", "kind": "parent", "D_cm2_per_s": 6.3e-6, "D_sem_cm2_per_s": 0.6e-6,
                 "framework": {"intact": True}} for p in sorted({c["parent"] for c in cands})]
        ratios = {"lower": 0.3, "tied": 1.1, "higher": 2.0}
        for c in cands:
            ratio = ratios[verdicts.get(c["formula"], "tied")]
            rows.append({"id": c["id"], "formula": c["formula"], "kind": "candidate", "parent": c["parent"],
                         "D_cm2_per_s": 6.3e-6 * ratio, "D_sem_cm2_per_s": 0.4e-6, "framework": {"intact": True}})
        return md_verdicts(rows)

    def novelty(cands, client):
        from autolab.agent.novelty import novelty_check

        calls.novelty.append([c["id"] for c in cands])
        return novelty_check(cands, client, cache=JsonCache(config.CACHE_DIR / "novelty"))

    return ElectrolyteTools(relax=fake_relax(), hull_entries=fake_hull, bandgap=fake_gap(), known=lambda f: [],
                            window_passivation=window_passivation, interface=interface,
                            interface_calibration=calibration, md_cached=lambda c: False, md_plan=md_plan,
                            md_screen=md_screen, novelty=novelty, not_run=[])


def review(priority="high"):
    return {"strengths": ["soft anion"], "risks": ["moisture"], "md_priority": priority, "summary": "worth a look"}


def run_agent(li3ps4, brain, tools, novelty_client=None, budget=40, prior=None, n_iterations=1, analyst=None, **kw):
    events = EventLog()
    agent = Agent(brain, tools=tools, events=events, budget=RelaxBudget(budget), get_structure=lambda pid: li3ps4,
                  novelty_client=novelty_client, analyst=analyst)
    result = agent.run(parents=[PARENT], n_iterations=n_iterations, prior=prior, **kw)
    return result, events


def steps(events, kind):
    return [e["step"] for e in events.events if e["type"] == kind]


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "UMA_MP2020", False)  # the fake hull holds raw energies (as in test_agent)


def novelty_replies(n):
    return [response("LEVEL: published\nLGPS is known.", [("https://doi.org/a", "Kamaya 2011")])] + [
        response("LEVEL: none_found\nNothing found for this composition.") for _ in range(n)]


def test_complete_loop_passes_data_from_step_to_step(li3ps4):
    calls = Calls()
    # Li11P4S15Cl (S->Cl) non-passivating; Li11P4S15I (S->I) slower than its parent and FeS2 with the cathode
    # (information only); Li11P4S15Br tied, decomposing via the polysulfide LiS4 at its window (reduced confidence)
    tools = fake_tools(calls, passivation={"Li11P4S15Cl": "non_passivating"}, polysulfides={"Li11P4S15I": ["FeS2"]},
                       window_polysulfides={"Li11P4S15Br": ["LiS4"]},
                       verdicts={"Li11P4S15I": "lower", "Li11P4S15Br": "tied"})
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, I_SUB), (PARENT, BR)), analysis(["it1-c1"]),
                             md_selection("it1-c1", "it1-c2", "it1-c3", "mp-999"), report_reply()])
    client, fake = meta(novelty_replies(1))
    analyst = FakeLLM("baseten", [review(), review("low")])
    result, events = run_agent(li3ps4, brain, tools, novelty_client=client, analyst=analyst)

    st = result["stages"]
    assert [c["status"] for c in result["iterations"][0]["candidates"]] == ["passed"] * 3
    assert {k: v["status"] for k, v in st.items()} == {
        "electrodes": "done", "candidate_analyses": "done", "md_selection": "done", "report": "done", "molecular_dynamics": "done", "ranking": "done",
        "novelty": "done"}
    # electrodes: the non-passivating candidate is excluded, the FeS2 reaction lowers the confidence
    assert st["electrodes"]["excluded"] == ["it1-c1"]
    by_id = {c["id"]: c for c in result["iterations"][0]["candidates"]}
    assert by_id["it1-c1"]["excluded_at"] == "electrodes" and "non_passivating" in by_id["it1-c1"]["exclusion_reason"]
    assert by_id["it1-c3"]["electrodes_reduced_confidence"] and by_id["it1-c3"]["electrodes_polysulfides"] == ["LiS4"]
    assert not by_id["it1-c2"]["electrodes_reduced_confidence"] and by_id["it1-c2"]["interface_polysulfides"] == ["FeS2"]
    assert len(calls.interfaces) == 2  # not for the excluded candidate
    # MD choice: the model only sees eligible candidates, with electrode results and code comparisons
    request = json.loads(brain.requests[2]["messages"][1]["content"])
    assert [c["id"] for c in request["candidates"]] == ["it1-c2", "it1-c3"] or \
        sorted(c["id"] for c in request["candidates"]) == ["it1-c2", "it1-c3"]
    assert all("interface_reaction_energy" in c and "passivation" in c for c in request["candidates"])
    # Muse Spark Open reviewed the two eligible candidates (in parallel); Muse Spark reads the reviews
    assert sorted(st["candidate_analyses"]["analysed"]) == ["it1-c2", "it1-c3"] and len(analyst.requests) == 2
    assert all(r["schema"] == "candidate_analysis" for r in analyst.requests)
    assert all(c["analysis"]["md_priority"] in ("high", "low") for c in request["candidates"])
    assert "md_priority" in analyst.requests[0]["messages"][0]["content"]
    assert brain.requests[2]["schema"] == "md_selection"
    assert "never compare values yourself" in brain.requests[2]["messages"][0]["content"]
    assert str(config.MD_SCREEN_TEMPERATURE_K) in brain.requests[2]["messages"][0]["content"]
    sel = st["md_selection"]
    assert sel["selected"] == ["it1-c2", "it1-c3"] and sel["ignored"] == ["it1-c1", "mp-999"]
    assert sel["chosen_by"] == "meta"
    # MD: only the selected candidates; "lower" -> excluded for conduction, still listed
    assert calls.md_screen == [["it1-c2", "it1-c3"]]
    assert by_id["it1-c2"]["md_verdict"] == "lower" and by_id["it1-c2"]["excluded_at"] == "molecular_dynamics"
    assert by_id["it1-c3"]["md_verdict"] == "tied" and by_id["it1-c3"]["conduction"] == "passes"
    # ranking: kept first, excluded last with their reasons; one finalist
    assert st["ranking"]["ranking"][0] == "it1-c3" and set(st["ranking"]["ranking"][1:]) == {"it1-c1", "it1-c2"}
    assert st["ranking"]["finalists"] == ["it1-c3"] and result["final_ranking"] == st["ranking"]["ranking"]
    # novelty: LGPS control first, then the finalist
    assert calls.novelty == [["it1-c3"]] and len(fake.requests) == 2
    assert "Li10GeP2S12" in fake.requests[0]["input"][0]["content"]
    assert st["novelty"]["control"]["control_ok"] and by_id["it1-c3"]["novelty"] == "none_found"

    # events: every stage starts and ends, candidate events of each stage
    stage_events = [(e["step"], e["data"].get("status")) for e in events.events if e["type"] == "stage"
                    and ":" not in e["step"]]
    for name in ("electrodes", "candidate_analyses", "md_selection", "molecular_dynamics", "ranking", "novelty"):
        assert (name, "start") in stage_events and (name, "done") in stage_events
    cand_steps = steps(events, "candidate")
    assert cand_steps.count("electrodes:done") == 3 and cand_steps.count("molecular_dynamics:done") == 2
    assert "molecular_dynamics:plan" in steps(events, "stage") and steps(events, "llm").count("md_selection") == 1
    assert steps(events, "loop")[-1] == "stop"

    report = render(json.loads(json.dumps(result)))
    for text in ("## Electrodes", "## Choice of the candidates for molecular dynamics", "## Li diffusion",
                 "## Final ranking", "EXCLUDED at electrodes", "EXCLUDED at molecular_dynamics", "**finalist**",
                 "reduced confidence of the window (decomposes via LiS4)",
                 "cathode reaction forms FeS2 (information)", "## Novelty check", "novelty web search: 2 calls"):
        assert text in report
    assert result["usage"]["llm"]["meta"]["calls"] == 4 and result["usage"]["analyst"]["calls"] == 2
    # final report: numbers from the code, narrative from the model, every item labelled documented or hypothesis
    rep = st["report"]
    assert rep["champion"] == "it1-c3" and rep["finalists"][0]["formula"] == "Li11P4S15Br"
    assert rep["finalists"][0]["ionic_conductivity"] == "not computed" and rep["finalists"][0]["space_group"]
    assert rep["completeness"] == "partial"  # one finalist only
    assert [x["basis"] for x in rep["narrative"]["synthesis"]] == ["documented", "hypothesis"]
    assert "Meta FAIR UMA" in str(rep["methods"]) and brain.requests[3]["schema"] == "report"
    assert "### Comparison of the three finalists" in report and "### Champion: Li11P4S15Br" in report
    assert "## Candidate analyses (Muse Spark Open, in parallel)" in report and "candidate analyses (baseten)" in report


def test_cached_md_applies_to_candidates_not_selected(li3ps4):
    calls = Calls()
    tools = fake_tools(calls, verdicts={"Li11P4S15Br": "lower"})
    tools.md_cached = lambda c: c["formula"] == "Li11P4S15Br"  # simulated earlier: not offered to the model
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis(), md_selection("it1-c1", "it1-c2")])
    result, _ = run_agent(li3ps4, brain, tools)
    sel = result["stages"]["md_selection"]
    assert sel["choices"] == ["it1-c1"] and sel["selected"] == ["it1-c1"] and sel["ignored"] == ["it1-c2"]
    offered = json.loads(brain.requests[2]["messages"][1]["content"])["candidates"]
    assert [c["id"] for c in offered] == ["it1-c1"] and "md_cached" not in offered[0]
    md = result["stages"]["molecular_dynamics"]
    assert md["from_cache"] == ["it1-c2"] and calls.md_screen == [["it1-c1", "it1-c2"]]
    br = result["iterations"][0]["candidates"][1]
    assert br["excluded_at"] == "molecular_dynamics" and "already simulated" in render(result)


def test_a_failed_analysis_leaves_the_candidate_without_review(li3ps4):
    calls = Calls()
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    analyst = FakeLLM("baseten", [llm.QuotaError("baseten: payment required")])
    result, _ = run_agent(li3ps4, brain, fake_tools(calls), analyst=analyst)
    st = result["stages"]["candidate_analyses"]
    assert st["status"] == "stopped" and "payment required" in st["failed"]["it1-c1"]
    assert result["stages"]["md_selection"]["selected"] == ["it1-c1"]  # the next stages go on
    assert "analysis" not in result["iterations"][0]["candidates"][0]


def test_md_cost_above_cap_is_not_launched_and_ranking_goes_on(li3ps4):
    calls = Calls()
    tools = fake_tools(calls, md_usd=config.MD_MAX_USD_PER_RUN + 0.01)
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis(), md_selection("it1-c1")])
    result, events = run_agent(li3ps4, brain, tools)
    md = result["stages"]["molecular_dynamics"]
    assert md["status"] == "stopped" and "MD_MAX_USD_PER_RUN" in md["stopped"] and calls.md_screen == []
    assert result["stages"]["ranking"]["status"] == "done" and len(result["stages"]["ranking"]["finalists"]) == 2
    assert result["stages"]["novelty"]["skipped"].startswith("no web-search client")
    assert "**Not launched:**" in render(result)


def test_llm_budget_at_md_choice_falls_back_to_the_rule(li3ps4):
    calls = Calls()
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR), (PARENT, I_SUB)), analysis(),
                             llm.BudgetExceeded("10 LLM calls made")])
    result, events = run_agent(li3ps4, brain, fake_tools(calls))
    sel = result["stages"]["md_selection"]
    eligible = result["funnel_ranking"]
    assert sel["chosen_by"].startswith("rule") and sel["selected"] == eligible[:config.MD_SELECT_MAX]
    assert "language model unavailable" in sel["rationale"] and "budget" in steps(events, "llm")
    assert calls.md_screen == [sel["selected"]]


def test_relaxation_budget_stops_the_electrodes_cleanly(li3ps4):
    calls = Calls()
    # 2 candidates x 8 arrangements = 16 relaxations; the interfaces would need 30 of the 24 left
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis(), md_selection("it1-c1")])
    result, _ = run_agent(li3ps4, brain, fake_tools(calls, interface_budget=30), budget=40)
    el = result["stages"]["electrodes"]
    assert el["status"] == "stopped" and el["stopped"].startswith("relaxation budget")
    assert sorted(el["not_computed"]) == ["it1-c1", "it1-c2"] and calls.interfaces == []
    # windows and passivation (no new relaxation here) are kept; each skipped interface is said in the report
    assert el["candidates"] == ["it1-c1", "it1-c2"] or sorted(el["candidates"]) == ["it1-c1", "it1-c2"]
    assert result["usage"]["relaxations"]["new"] <= 40 and "not computed (interface with LiFePO4" in render(result)
    assert result["stages"]["md_selection"]["status"] == "done"  # later stages still run on what is known


def test_untrusted_cathode_calibration_skips_the_interfaces(li3ps4):
    calls = Calls()
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    result, _ = run_agent(li3ps4, brain, fake_tools(calls, cal_ok=False))
    c = result["iterations"][0]["candidates"][0]
    assert calls.interfaces == [] and c["interfaces"] == {"LiFePO4": None} and c["interface_reaction_energy"] is None
    assert "NOT trusted" in render(result)


def test_novelty_cap_stops_cleanly_and_answers_are_cached(li3ps4):
    calls = Calls()
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis(), md_selection("it1-c1", "it1-c2")])
    client, fake = meta(novelty_replies(2), cap=0.02)  # the control (~$0.022) already reaches the cap
    result, _ = run_agent(li3ps4, brain, fake_tools(calls), novelty_client=client)
    nov = result["stages"]["novelty"]
    assert nov["status"] == "stopped" and nov["stopped"].startswith("budget") and len(fake.requests) == 1
    assert nov["control"]["control_ok"] and nov["candidates"] == []

    # a second run asks the same control again: answered from the cache, no paid call
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    client2, fake2 = meta(novelty_replies(1))
    result2, _ = run_agent(li3ps4, brain, fake_tools(calls), novelty_client=client2)
    assert result2["stages"]["novelty"]["control"]["cached"] is True and len(fake2.requests) == 1


def test_control_not_found_stops_the_novelty_check(li3ps4):
    calls = Calls()
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    client, fake = meta([response("LEVEL: none_found\nNothing found."), response("LEVEL: none_found\nNothing.")])
    result, _ = run_agent(li3ps4, brain, fake_tools(calls), novelty_client=client)
    nov = result["stages"]["novelty"]
    assert nov["control"]["control_ok"] is False and nov["candidates"] == [] and len(fake.requests) == 1
    assert "not trusted" in nov["stopped"]


def test_prior_candidates_are_not_proposed_again_and_join_the_stages(li3ps4):
    calls = Calls()
    old = evaluate_candidate("s9:it1-c1", PARENT, li3ps4, SUB_CL, fake_tools(calls), EventLog(), RelaxBudget(10))
    assert old["status"] == "passed"
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis(), md_selection("s9:it1-c1")])
    result, _ = run_agent(li3ps4, brain, fake_tools(calls), prior=[old])
    first = json.loads(brain.requests[0]["messages"][1]["content"])
    assert first["history"][0]["iteration"] == "earlier runs" and first["history"][0]["results"][0]["id"] == "s9:it1-c1"
    cands = result["iterations"][0]["candidates"]
    assert (cands[0]["status"], cands[0]["reason"]) == ("rejected", "already evaluated")
    assert "s9:it1-c1" in result["stages"]["md_selection"]["eligible"] and calls.md_screen == [["s9:it1-c1"]]
    assert "s9:it1-c1" in result["stages"]["ranking"]["ranking"]
    assert "**Earlier runs.**" in render(result)


def test_md_verdict_rule():
    p = {"id": "mp-1", "kind": "parent", "formula": "P", "D_cm2_per_s": 1e-5, "D_sem_cm2_per_s": 1e-6}
    rows = md_verdicts([p,
                        {"id": "a", "kind": "candidate", "parent": "mp-1", "D_cm2_per_s": 0.5e-5, "D_sem_cm2_per_s": 1e-6},
                        {"id": "b", "kind": "candidate", "parent": "mp-1", "D_cm2_per_s": 1.1e-5, "D_sem_cm2_per_s": 1e-6},
                        {"id": "c", "kind": "candidate", "parent": "mp-1", "D_cm2_per_s": 2e-5, "D_sem_cm2_per_s": 1e-6,
                         "framework": {"intact": False, "per_seed": [
                             {"elements": {"S": {"msd_final_A2": 0.2, "D_ratio_to_Li": 0.01}}},
                             {"elements": {"Cl": {"msd_final_A2": 5.4, "D_ratio_to_Li": 0.40},
                                           "S": {"msd_final_A2": 2.1, "D_ratio_to_Li": 0.11}}}]}}])
    by = {r["id"]: r for r in rows}
    assert (by["a"]["vs_parent"]["verdict"], by["a"]["conduction"]) == ("lower", "excluded")
    assert (by["b"]["vs_parent"]["verdict"], by["b"]["conduction"]) == ("tied", "passes")
    assert (by["c"]["vs_parent"]["verdict"], by["c"]["conduction"]) == ("higher", "excluded")
    assert by["c"]["conduction_reason"] == ("framework moved: Cl diffuses at 40.0% of Li (limit 5%), seed 1, "
                                            "final MSD 5.4 A2")
    assert "conduction" not in by["mp-1"] and config.MD_EXCLUDED_VERDICTS == ("lower",)


def test_the_loop_runs_another_domain_unchanged(li3ps4):
    """A new domain (e.g. cathodes later) brings its funnel, prompts and stages; the loop is not modified."""
    seen = []

    def evaluate(cid, parent_id, parent, substitution, tools, events, budget):
        events.emit("candidate", "toy", {"ok": True}, cid)
        return {"id": cid, "parent": parent_id, "substitution": substitution, "status": "passed",
                "formula": "X", "score": len(seen)}

    def stage(camp):
        seen.extend(c["id"] for c in camp.passed())
        return {"summary": {"n": len(seen)}, "n": len(seen)}

    toy = Domain(name="toy", goal="toy goal", parents=(PARENT,), make_tools=lambda: None, evaluate=evaluate,
                 proposal_messages=lambda goal, parents, history, n: [{"role": "user", "content": "propose"}],
                 analysis_messages=lambda goal, it, hyp, res, hist, comps: [{"role": "user", "content": "analyse"}],
                 comparisons=lambda cands: [], for_model=("id", "status"), rank_key=lambda c: c["score"],
                 stages=(Stage("count", stage, lambda out, result: [f"counted {out['n']}"]),))
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL), (PARENT, BR)), analysis()])
    agent = Agent(brain, domain=toy, get_structure=lambda pid: li3ps4)
    result = agent.run(n_iterations=1)
    assert result["domain"] == "toy" and seen == ["it1-c1", "it1-c2"]
    assert result["stages"]["count"] == {"status": "done", "summary": {"n": 2}, "n": 2}
    assert "counted 2" in render(result, toy)
    assert get_domain("electrolyte").name == "electrolyte"
    with pytest.raises(ValueError, match="unknown domain"):
        get_domain("cathode")


def test_reviews_of_earlier_runs_are_kept_not_paid_twice(li3ps4):
    calls = Calls()
    old = evaluate_candidate("s9:it1-c1", PARENT, li3ps4, BR, fake_tools(calls), EventLog(), RelaxBudget(10))
    old["analysis"] = review("medium")
    brain = FakeLLM("meta", [proposal((PARENT, SUB_CL)), analysis(), md_selection("it1-c1")])
    analyst = FakeLLM("baseten", [review()])
    result, _ = run_agent(li3ps4, brain, fake_tools(calls), prior=[old], analyst=analyst)
    st = result["stages"]["candidate_analyses"]
    assert st["analysed"] == ["it1-c1"] and st["reused"] == ["s9:it1-c1"] and len(analyst.requests) == 1
