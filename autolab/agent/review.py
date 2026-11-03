"""Campaign review by Muse Wonder (SPEC 5.11): the research director reads the whole campaign at once.

Last stage of every domain. Muse Wonder, Meta's model for long multi-step work (1M-token context), receives a compact
dossier of the campaign: each round's hypothesis and proposals, the measurements of every candidate, the failures
with Muse Spark's hypotheses, the ranking, the literature check and the report. It returns what the campaign taught,
what worked, what failed and the next campaign to run. It decides nothing: thresholds, ranking and verdicts stay the
code's (config.py), and the review is shown as the model's reading of the data.
"""

from __future__ import annotations

import json

from autolab import config

SYSTEM = """You are Muse Wonder, the research director of AutoLab, an autonomous laboratory that discovers new materials for industry; this campaign is in the domain given by the data (battery materials). Other agents ran the campaign: Muse Spark proposed chemical substitutions in known crystals and interpreted each failure, UMA simulated the crystals, the code measured every property and decided every verdict from fixed rules. You read the whole campaign at once and write its review for the research team.
Write:
- headline: one sentence, the main result of the campaign.
- learned: 3 to 5 sentences on what the campaign taught across its rounds (how the proposals changed after each failure, which chemical ideas held, which did not), citing measured numbers and compounds by formula.
- worked: 2 to 4 sentences on what passed the tests and why, with the measured numbers.
- failed: 2 to 4 sentences on the failures that matter, each with its measured reason; a cause is a hypothesis and must be written as one.
- next_campaign: the next campaign to run with the same tools: goal (one sentence a researcher could type as a request), parents (known crystals by formula, from this campaign), directions (2 to 4 concrete substitutions or tests), why (two sentences tied to this campaign's results).
Rules: use only the numbers in the data, rounded, with their units; never invent a value; never claim a material is proven, synthesized or new to science (these are computational predictions); the thresholds, ranking and verdicts are fixed by the code, do not change or dispute them; name compounds by their chemical formula, never by a database id; name quantities in words (energy above the hull, band gap, diffusion against the parent, conductivity, voltage, capacity), never field names. gap_optb88 and gap_mbj are recorded predictions of the band gap; gap_dft is a band gap computed by DFT.
Answer with the JSON object only: {template}"""

_DROP = {"relaxed_atoms", "structure", "structures", "points", "protocol", "sources", "sensitivity", "windows", "rows",
         "message", "notes", "arrangements", "calibrations", "usage", "methods", "reasoning", "reasoning_summary"}
_EXTRA = ("rationale", "gap_dft", "window", "conductivity", "voltage_V", "capacity_mAh_g", "energy_density_Wh_kg")


def _slim(v, depth: int = 0):
    """A JSON value without bulky parts: no structures or raw series, lists cut to 6 items, strings to 400 chars."""
    if isinstance(v, dict):
        return {k: _slim(x, depth + 1) for k, x in v.items() if k not in _DROP and x is not None and depth < 4}
    if isinstance(v, list):
        return [_slim(x, depth + 1) for x in v[:6]]
    if isinstance(v, str):
        return v[:400]
    return round(v, 4) if isinstance(v, float) else v


def _candidate(c: dict, fields: tuple[str, ...]) -> dict:
    return _slim({k: c[k] for k in (*fields, *_EXTRA) if c.get(k) is not None})


def dossier(result: dict, earlier: bool = True) -> dict:
    """What Muse Wonder reads: the whole campaign, compact (`earlier`: with the candidates of earlier researches)."""
    from autolab.domains import get_domain

    d = get_domain(result.get("domain") or config.AGENT_DOMAIN)
    stages = result.get("stages") or {}
    pool = {c["id"]: c for c in (result.get("prior") or []) + [c for r in result.get("iterations") or []
                                                                  for c in r.get("candidates") or []]}
    rounds = []
    for r in result.get("iterations") or []:
        proposal = (r.get("proposal") or {}).get("reply") or {}
        analysis = (r.get("analysis") or {}).get("reply") or {}
        rounds.append({"round": r.get("iteration"), "hypothesis": proposal.get("hypothesis"),
                       "candidates": [_candidate(c, d.for_model) for c in r.get("candidates") or []],
                       "slow_tests": [_slim({k: f.get(k) for k in ("formula", "test", "outcome", "reason")})
                                      for f in r.get("feedback") or []],
                       "analysis": _slim({k: analysis.get(k) for k in ("failure_analysis", "lessons", "next_direction",
                                                                        "ranking")})})
    rk = stages.get("ranking") or {}
    report = stages.get("report") or {}
    narrative = report.get("narrative") or {}
    out = {
        "goal": result.get("goal"), "domain": d.name, "stop_reason": result.get("stop_reason"),
        "parents": [{"formula": p.get("formula"), "id": p.get("id")} for p in result.get("parents") or []],
        "thresholds": (result.get("settings") or {}).get("thresholds"),
        "rounds": rounds,
        "stages": {name: _slim({"status": s.get("status"), **(s.get("summary") or {})}) for name, s in stages.items()
                   if name != "campaign_review"},
        "finalists": [{"rank": i + 1, **_candidate(pool[f], d.for_model)} for i, f in
                      enumerate(rk.get("finalists") or []) if f in pool],
        "excluded": _slim(rk.get("excluded") or {}),
        "literature": [_slim({k: n.get(k) for k in ("formula", "label", "level")})
                       for n in (stages.get("novelty") or {}).get("candidates") or []],
        "report": _slim({"champion": report.get("champion"), "completeness": report.get("completeness"),
                         **{k: narrative.get(k) for k in ("executive_summary", "champion_reasons", "limitations")}}),
    }
    if earlier and result.get("prior"):
        out["earlier_candidates"] = [_candidate(c, d.for_model) for c in result["prior"]]
    return out


def review_messages(result: dict) -> list[dict]:
    """The request to Muse Wonder; the earlier researches' candidates are left out if the dossier is too large."""
    from autolab.llm.schemas import template

    for earlier in (True, False):
        text = json.dumps(dossier(result, earlier), default=str)
        if len(text) <= config.CAMPAIGN_REVIEW_MAX_INPUT_CHARS:
            break
    else:
        raise ValueError(f"campaign dossier of {len(text)} characters > CAMPAIGN_REVIEW_MAX_INPUT_CHARS")
    return [{"role": "system", "content": SYSTEM.replace("{template}", template("campaign_review"))},
            {"role": "user", "content": f"Review this campaign.\n{text}"}]


def campaign_review(camp) -> dict:
    """Stage: one call to Muse Wonder on the whole campaign (the agent's `director`), its reply in an event."""
    from autolab.llm.client import LLMError

    director, result = getattr(camp.agent, "director", None), getattr(camp.agent, "result", None)
    if director is None or result is None:
        why = "no campaign reviewer configured" if director is None else "no campaign to review"
        return {"skipped": why, "summary": {"skipped": why}}
    messages = review_messages(result)
    try:
        reply, replies = director.complete_json(messages, "campaign_review",
                                                max_output_tokens=config.CAMPAIGN_REVIEW_MAX_OUTPUT_TOKENS,
                                                reasoning_effort=config.CAMPAIGN_REVIEW_REASONING_EFFORT)
    except LLMError as e:  # reported, never retried
        camp.agent.events.emit("llm", "error", {"provider": director.provider, "step": "campaign_review",
                                                "error": str(e)})
        raise
    info = {"provider": director.provider, "model": getattr(director, "model", None), "attempts": len(replies),
            "input_tokens": sum(r.input_tokens for r in replies), "output_tokens": sum(r.output_tokens for r in replies),
            "cost_usd": round(sum(r.cost_usd for r in replies), 5), "seconds": round(sum(r.seconds for r in replies), 1),
            "cached": all(r.cached for r in replies), "dossier_chars": len(messages[1]["content"])}
    reasoning = "\n\n".join(r.reasoning for r in replies if r.reasoning)
    camp.agent.events.emit("llm", "campaign_review", {**info, "reply": reply,
                                                      "reasoning_summary": reasoning[:config.EVENT_REASONING_CHARS]})
    return {**info, "review": reply,
            "summary": {"headline": reply["headline"], "next_goal": reply["next_campaign"]["goal"]}}


def render(out: dict, result: dict) -> list[str]:
    """The review as Markdown (the conversation's last message)."""
    if out.get("skipped") or not out.get("review"):
        return ["## Campaign review", "", f"Not written: {out.get('skipped') or out.get('error') or 'no reply'}.", ""]
    r, nxt = out["review"], out["review"]["next_campaign"]
    lines = ["## Campaign review", "", f"**{r['headline']}**", ""]
    for title, key in (("What the campaign taught", "learned"), ("What worked", "worked"), ("What failed", "failed")):
        if r.get(key):
            lines += [f"### {title}", "", *[f"- {x}" for x in r[key]], ""]
    lines += ["### Next campaign", "", f"> {nxt['goal']}", ""]
    if nxt.get("parents"):
        lines += [f"Starting from: {', '.join(map(str, nxt['parents']))}.", ""]
    lines += [*[f"- {x}" for x in nxt.get("directions") or []], "", nxt.get("why") or "", ""]
    return lines
