"""Follow-up questions on a finished research (interface.md 10): the context is built by the code from the stored
result (no model call to summarize it), then the main model answers from those facts only. Answers are kept in the
reply cache, so the same question on the same research is answered again for free."""

from __future__ import annotations

import json

from autolab import config

CANDIDATE_FIELDS = ("formula", "parent_formula", "substitution", "e_hull", "e_hull_per_substitution", "decomposition",
                    "reduced_confidence", "gap_optb88", "gap_mbj", "window", "passivation", "interface_reaction_energy",
                    "electrodes_reduced_confidence", "D_cm2_per_s", "D_ratio_to_parent", "D_ratio_err", "md_verdict",
                    "conduction", "novelty", "analysis", "excluded_at", "exclusion_reason")


def context(result: dict) -> dict:
    """The facts of a research, compact, from its stored result."""
    pool = {c["id"]: c for c in result.get("prior", []) + [c for r in result.get("iterations", [])
                                                          for c in r["candidates"]]}
    st = result.get("stages", {})
    rk = st.get("ranking", {})
    pick = lambda c: {k: c.get(k) for k in CANDIDATE_FIELDS if c.get(k) is not None}
    report = st.get("report", {})
    return {
        "goal": result.get("goal"),
        "stopped_because": result.get("stop_reason"),
        "steps": {name: s.get("status") for name, s in st.items()},
        "candidates_evaluated": len(pool),
        "passed_funnel": len(result.get("funnel_ranking", [])),
        "finalists": [{"id": i, **pick(pool[i])} for i in rk.get("finalists", []) if i in pool],
        "other_ranked": [{"id": i, "formula": pool[i].get("formula"), "md_verdict": pool[i].get("md_verdict")}
                         for i in rk.get("kept", [])[3:12] if i in pool],
        "excluded": rk.get("excluded", {}),
        "report": {k: report.get(k) for k in ("champion", "narrative", "completeness") if report.get(k)},
        "literature": [{"formula": c.get("formula"), "level": c.get("label"), "summary": c.get("summary")}
                       for c in (st.get("novelty", {}).get("candidates") or [])],
        "summaries": [s.get("text") for s in result.get("summaries") or [] if s.get("text")],
        "methods": ("UMA machine-learned potential (relaxations, energies with MP2020 corrections, molecular dynamics "
                    "at 600 K, 2 x 40 ps), convex hull against Materials Project phases, ALIGNN band gaps, grand-potential "
                    "electrochemical window, interface reactivity with LiFePO4, web literature search"),
        "not_computed": config.CAPABILITIES["not_computed"],
    }


SYSTEM = """You are AutoLab, an AI research assistant for materials discovery, answering a follow-up question about a research you already carried out. The facts of that research are given as JSON.
Rules:
- Use only these facts and well-established textbook science. Quote numbers exactly as given, with their units.
- If something was not computed (see not_computed, or a missing field), say so plainly; never invent a value.
- When you suggest experiments or synthesis routes, say clearly which are standard, documented practice and which are hypotheses to verify.
- The candidates are computational predictions, not proven materials.
- Do not mention the names of AI models or providers; speak as AutoLab.
- Answer in the user's language, clearly and concisely, with short paragraphs or a short list when useful (Markdown allowed)."""


def followup_messages(question: str, facts: dict, history: list[dict] | None = None) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Facts of the research:\n" + json.dumps(facts, default=str)}]
    for h in (history or [])[-4:]:  # the last exchanges keep the thread of the discussion
        msgs += [{"role": "user", "content": h["question"]}, {"role": "assistant", "content": h["answer"]}]
    return msgs + [{"role": "user", "content": question}]


def answer(question: str, result: dict, client, history: list[dict] | None = None) -> dict:
    reply = client.chat(followup_messages(question, context(result), history),
                        max_output_tokens=config.FOLLOWUP_MAX_OUTPUT_TOKENS)
    return {"text": reply.text.strip(), "cached": reply.cached}
