"""Hybrid replay of a recorded research, for the local demo run with the judges' own keys.

Muse Spark's proposals and every computation (UMA relaxations and molecular dynamics, DFT, Materials Project) come
from the recorded run: a new proposal would need new GPU computations. The other agents work live on those results,
with the same prompts and events as in a research: Muse Spark analyses each round's failures, Muse Spark Open reviews
the candidates, the plain-language summaries are written again and Muse Wonder reviews the campaign. The recorded
events are sent at the pace the lab plays them. A missing key: another Meta model takes the role (its name shows in
the interface); a failed call keeps the recorded answer for that step. Nothing runs on a GPU.
"""

from __future__ import annotations

import copy
import os
import time
from datetime import datetime, timezone
from types import SimpleNamespace

from autolab import config
from autolab.domains import Campaign, get_domain

PACE_S = 1.9  # seconds between two recorded events that the lab shows as a card (it plays them at about this pace)
QUICK_S = 0.4  # stage markers and small events
GLIMMER_WAIT_S = 90  # a sleeping Muse Glimmer deployment is waited for this long, then Muse Spark writes the summary


def models(glimmer: bool = True) -> dict | None:
    """The live models from the keys in .env, each with its own cost cap; None when no model can be called.
    glimmer=False: Muse Spark writes the summaries (a sleeping Muse Glimmer deployment is not woken up)."""
    from autolab.agent.runs import client, director_client

    caps = config.LLM_COST_CAPS_USD
    brain = client("meta", caps["meta"]) or client("baseten", caps["baseten"])
    if brain is None:
        return None
    reviewer = client(config.CANDIDATE_ANALYSIS_PROVIDER, caps[config.CANDIDATE_ANALYSIS_PROVIDER],
                      config.CANDIDATE_ANALYSIS_MAX * config.JSON_MAX_RETRIES) or brain
    glimmer = client("fireworks", caps["fireworks"], 40) if glimmer and os.getenv("GLIMMER_DEPLOYMENT") else None
    writer = client(brain.provider, caps[brain.provider], config.SUMMARY_MAX_PER_RUN * config.JSON_MAX_RETRIES)
    return {"brain": brain, "reviewer": reviewer, "summarizer": glimmer, "writer": writer,
            "director": director_client() or brain}


MATCH_SYSTEM = """You match a researcher's request to the recorded researches of AutoLab's demo. A request matches a recorded research only if it asks for the same thing in other words: the same kind of material, the same family of starting crystals (when the request names one), and the same objectives. A request that is narrower (specific elements or substitutions that the research did not set as its goal), broader, or about another material, another property or another objective does not match.
Answer with the JSON object only: {"match": "<the id of the matching research, or none>", "reason": "one sentence"}"""


def match_recorded(c, text: str, recorded: list[dict]) -> str | None:
    """The id of the recorded research that `text` asks for in other words, or None (Muse Spark decides; the code only
    accepts an id from `recorded`). recorded: [{"id", "request", "goal"}] of the request's domain."""
    import json

    if c is None or not recorded:
        return None
    messages = [{"role": "system", "content": MATCH_SYSTEM},
                {"role": "user", "content": json.dumps({"request": text, "recorded_researches": recorded})}]
    kwargs = {"max_output_tokens": 1500, **({"reasoning_effort": "low"} if c.provider == "meta" else {})}
    reply, _ = c.complete_json(messages, "recorded_match", **kwargs)
    ids = {r["id"] for r in recorded}
    return reply["match"] if reply.get("match") in ids else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _Log:
    """Collects the events a stage function emits (Campaign.emit), to send them at the right place."""

    def __init__(self):
        self.events: list[dict] = []

    def emit(self, type: str, step: str, data: dict | None = None, candidate_id: str | None = None) -> dict:
        e = {"type": type, "candidate_id": candidate_id, "step": step, "data": data or {}, "timestamp": _now()}
        self.events.append(e)
        return e


def _ask(c, messages: list[dict], schema: str, step: str) -> tuple[dict, dict]:
    """A JSON reply as Agent.ask gets it; returns (stored info, event data)."""
    kwargs = {"max_output_tokens": config.AGENT_MAX_OUTPUT_TOKENS}
    if c.provider == "meta":
        kwargs["reasoning_effort"] = config.AGENT_REASONING_EFFORT
    obj, replies = c.complete_json(messages, schema, **kwargs)
    info = {"provider": c.provider, "attempts": len(replies),
            "reasoning": "\n\n".join(r.reasoning for r in replies if r.reasoning),
            "input_tokens": sum(r.input_tokens for r in replies), "output_tokens": sum(r.output_tokens for r in replies),
            "cost_usd": round(sum(r.cost_usd for r in replies), 5), "seconds": round(sum(r.seconds for r in replies), 1),
            "cached": all(getattr(r, "cached", False) for r in replies), "hybrid": True}
    data = {**{k: v for k, v in info.items() if k != "reasoning"}, "reply": obj,
            "reasoning_summary": info["reasoning"][:config.EVENT_REASONING_CHARS]}
    return {"reply": obj, **info}, data


def _summary(m: dict, kind: str, label: str, data: dict) -> dict:
    """A plain-language summary: Muse Glimmer when its deployment answers in time, else the writer (Muse Spark)."""
    from autolab.agent.summaries import summary_messages
    from autolab.llm.client import LLMError

    messages = summary_messages(kind, data)
    reply = None
    if m.get("summarizer") is not None:
        waited = 0.0
        while reply is None:
            try:
                reply = m["summarizer"].chat(messages, max_output_tokens=config.GLIMMER_MAX_OUTPUT_TOKENS,
                                             reasoning_effort=config.GLIMMER_REASONING_EFFORT)
            except LLMError as e:
                if "HTTP 503" not in str(e) or waited >= GLIMMER_WAIT_S:
                    break
                time.sleep(10); waited += 10
    if reply is None or not reply.text.strip():
        w = m["writer"]
        kwargs = {"max_output_tokens": 3000, **({"reasoning_effort": "low"} if w.provider == "meta" else {})}
        reply = w.chat(messages, **kwargs)
    return {"kind": kind, "label": label, "text": reply.text.strip() or None, "provider": reply.provider,
            "cached": reply.cached, "output_tokens": reply.output_tokens, "hybrid": True}


def _for_model(d, cands: list[dict]) -> list[dict]:
    return [{k: c.get(k) for k in d.for_model if k in c} for c in cands]


def _iteration_data(d, rec: dict, analysis: dict) -> dict:
    """What the loop gives the summarizer for one round (agent/loop.py)."""
    return {"iteration": rec["iteration"], "hypothesis": (rec.get("proposal") or {}).get("reply", {}).get("hypothesis"),
            "domain": d.name,
            "candidates": [{k: c.get(k) for k in ("formula", "status", "rejected_at", "reason", "e_hull", "gap_optb88",
                                                  "voltage_V", "capacity_mAh_g", "energy_density_Wh_kg")
                            if c.get(k) is not None} for c in rec.get("candidates") or []],
            "slow_tests": [{k: f.get(k) for k in ("formula", "test", "outcome", "reason")} for f in rec.get("feedback") or []],
            "failure_analysis": analysis.get("failure_analysis") or [], "lessons": analysis.get("lessons"),
            "next_direction": analysis.get("next_direction")}


def _run_data(d, result: dict) -> dict:
    pool = {c["id"]: c for c in (result.get("prior") or []) + [c for r in result["iterations"] for c in r["candidates"]]}
    rk = result.get("stages", {}).get("ranking", {})
    return {"goal": result.get("goal"), "stop_reason": result.get("stop_reason"), "domain": d.name,
            "finalists": [{k: pool[i].get(k) for k in ("formula", "e_hull", "gap_optb88", "md_verdict", "D_ratio_to_parent",
                                                       "voltage_V", "capacity_mAh_g", "energy_density_Wh_kg", "novelty")
                           if pool[i].get(k) is not None} for i in rk.get("finalists", []) if i in pool],
            "excluded": rk.get("excluded", {}),
            "new_candidates": sum(len(r["candidates"]) for r in result["iterations"]),
            "passed_funnel": len(result.get("funnel_ranking") or [])}


def replay(store, cid: str, src: str, m: dict, finish, pace: float = PACE_S, quick: float = QUICK_S,
           sleep=time.sleep) -> dict:
    """Play the recorded research `src` into conversation `cid`, the agents above working live. `finish(cid, result,
    domain)` writes the summary, report and review messages. Returns the result, with the live texts."""
    from autolab.agent import review
    from autolab.llm.client import LLMError

    result = copy.deepcopy(store.result(src))
    recorded = store.events(src)
    d = get_domain(result.get("domain") or config.AGENT_DOMAIN)
    pool = {c["id"]: c for c in (result.get("prior") or []) + [c for r in result["iterations"] for c in r["candidates"]]}
    history = ([{"iteration": "earlier runs", "results": _for_model(d, result["prior"])}] if result.get("prior") else [])
    reviews = next((s.run for s in (*d.iteration_stages, *d.stages) if s.name == "candidate_analyses"), None)
    state = {"seq": len(store.events(cid)), "round": 0, "failed": []}
    live_summaries: list[dict] = []

    def push(e: dict, wait: float) -> None:  # the time spent writing to the store counts in the pace
        t = time.monotonic()
        store.append_event(cid, state["seq"], {**{k: v for k, v in e.items() if k != "seq"}, "timestamp": _now()})
        state["seq"] += 1
        sleep(max(0.0, wait - (time.monotonic() - t)))

    def stopped() -> bool:  # read from the store at most every few seconds (a database round trip)
        if time.monotonic() - state.get("checked", -1e9) < config.STOP_POLL_S:
            return state.get("stop", False)
        c = store.get(cid)
        state["checked"], state["stop"] = time.monotonic(), bool(c and c.get("cancel_requested_at"))
        return state["stop"]

    i = 0
    while i < len(recorded):
        if stopped():
            result["stop_reason"] = "interrupted by the user"
            break
        e = recorded[i]
        key = f"{e['type']}/{e['step']}"
        data = e.get("data") or {}
        try:
            if key == "llm/analysis" and state["round"] < len(result["iterations"]):
                rec = result["iterations"][state["round"]]
                hypothesis = (rec.get("proposal") or {}).get("reply", {}).get("hypothesis")
                args = (result["goal"], rec["iteration"], hypothesis, _for_model(d, rec["candidates"]), history,
                        rec.get("comparisons") or [])
                messages = d.analysis_messages(*args, rec.get("feedback") or []) if d.feedback else d.analysis_messages(*args)
                info, ev = _ask(m["brain"], messages, "analysis", "analysis")
                rec["analysis"] = info
                a = info["reply"]
                history.append({"iteration": rec["iteration"], "hypothesis": hypothesis, "results": _for_model(d, rec["candidates"]),
                                **({"slow_tests": rec.get("feedback") or [], "failure_analysis": a.get("failure_analysis") or []}
                                   if d.feedback else {}),
                                "lessons": a.get("lessons"), "next_direction": a.get("next_direction")})
                state["round"] += 1
                push({**e, "data": ev}, pace)
            elif key == "llm/summary":
                label = data.get("label") or ""
                if data.get("kind") == "iteration" and label.split()[-1:] and label.split()[-1].isdigit():
                    rec = result["iterations"][int(label.split()[-1]) - 1]
                    s = _summary(m, "iteration", label, _iteration_data(d, rec, (rec.get("analysis") or {}).get("reply") or {}))
                else:
                    s = _summary(m, "whole run", "run", _run_data(d, result))
                live_summaries.append(s)
                push({**e, "data": s}, pace)
            elif key == "stage/candidate_analyses" and data.get("status") == "start" and reviews is not None:
                j = i + 1  # the recorded block: its reviewed candidates, up to the stage's end
                while j < len(recorded) and not (recorded[j]["type"] == "stage" and recorded[j]["step"] == "candidate_analyses"
                                                 and recorded[j]["data"].get("status") != "start"):
                    j += 1
                block = recorded[i + 1:j]
                ids = [x["candidate_id"] for x in block if x["step"] == "candidate_analyses:done" and x["candidate_id"] in pool]
                push(e, quick)
                if ids:
                    cands = []
                    for cid_ in ids:
                        c = copy.deepcopy(pool[cid_])
                        for k in ("analysis", "excluded_at", "exclusion_reason"):
                            c.pop(k, None)
                        cands.append({**c, "status": "passed"})
                    log = _Log()
                    camp = Campaign(SimpleNamespace(analyst=m["reviewer"], events=log), result["goal"], cands,
                                    iteration=data.get("iteration"), settings=dict(d.settings))
                    out = reviews(camp)
                    for c in cands:
                        if c.get("analysis"):
                            pool[c["id"]]["analysis"] = c["analysis"]
                    for x in log.events:
                        push(x, pace)
                    if out.get("failed"):
                        state["failed"].append("candidate reviews")
                    end = recorded[j] if j < len(recorded) else None
                    if end is not None:
                        push({**end, "data": {**end["data"], **(out.get("summary") or {}), "hybrid": True}}, quick)
                    i = j + 1
                    continue
                for x in block:
                    push(x, pace)
                i = j
                continue
            elif key == "llm/campaign_review":
                log = _Log()
                out = review.campaign_review(SimpleNamespace(agent=SimpleNamespace(director=m["director"], result=result,
                                                                                    events=log)))
                result.setdefault("stages", {})["campaign_review"] = {"status": "done", **out}
                for x in log.events:
                    push(x, pace)
                nxt = recorded[i + 1] if i + 1 < len(recorded) else None
                if nxt and nxt["type"] == "stage" and nxt["step"] == "campaign_review":
                    push({**nxt, "data": {**nxt["data"], **out.get("summary", {})}}, quick)
                    i += 2
                    continue
            else:
                card = e["type"] in ("llm", "candidate") or (e["type"] == "loop" and e["step"] in ("iteration", "feedback", "start"))
                push(e, pace if card else quick)
        except LLMError as err:  # that step keeps its recorded answer; said at the end
            state["failed"].append(f"{key}: {type(err).__name__}: {err}"[:300])
            print(f"hybrid: {key} kept its recorded answer ({type(err).__name__}: {err})"[:400], flush=True)
            push(e, pace)
        i += 1

    if live_summaries:
        result["summaries"] = live_summaries
    result["hybrid"] = {"live": ["analyses", "candidate reviews", "summaries", "campaign review"], "failed": state["failed"],
                        "providers": {k: getattr(v, "provider", None) for k, v in m.items() if v is not None}}
    store.save_result(cid, result)
    finish(cid, result, d)
    if state["failed"]:
        store.add_message(cid, "assistant", "notice", "Some agents could not be reached; their recorded answers are "
                          "shown for those steps.")
    store.update(cid, status="interrupted" if result.get("stop_reason") == "interrupted by the user" else "done")
    return result
