"""Literature novelty check of the final candidates (last step), with Meta web search.

Three levels only, decided by the model but bounded by the code:
- "published": the composition itself is reported (needs at least one API citation);
- "related": a close family (same dopant family or same parent) is studied (needs a citation);
- "none_found": nothing found in this search. It never means "never discovered".
Links come only from the API's url_citation annotations: URLs typed by the model are removed,
and a "published"/"related" claim without any citation is downgraded to "none_found".
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from autolab import config

LEVELS = {
    "published": "already published",
    "related": "close family already studied",
    "none_found": "no publication found in this search",
}

_LEVEL = re.compile(r"^\s*LEVEL\s*:\s*(published|related|none_found)\b", re.I | re.M)
_URL = re.compile(r"\(?\s*(?:https?://|www\.)\S+\s*\)?")
_OVERCLAIM = re.compile(r"never (?:been )?(?:reported|discovered|published|synthesi[sz]ed|studied)|"
                        r"first (?:ever|time)|(?:entirely |completely )?new to (?:the|all) literature|"
                        r"novel in (?:the|all) literature|undiscovered", re.I)

SYSTEM = f"""You check whether a computationally predicted solid electrolyte has already been published.
Search the web (articles, patents, theses, and databases such as ICSD, OQMD, AFLOW, Materials Project, JARVIS)
for the exact composition and for close families: the same dopant in the same parent (other concentrations
included), or the same parent structure with chemically similar dopants.

Reply in plain text. First line exactly one of:
LEVEL: published   (the exact composition, or the same compound written differently, is reported)
LEVEL: related     (not the exact composition, but the same dopant family or the same parent doping is studied)
LEVEL: none_found  (this search found neither)
Then 2 to 4 short sentences saying what was found, each claim supported by a cited source.
Never write a URL yourself: sources are attached automatically from your search.
Never claim that something was never reported, never discovered or is new to the literature: a web search
cannot prove absence; "none_found" only means this search found nothing."""


def _describe(c: dict) -> str:
    if not c.get("substitution"):
        return f"Composition: {c['formula']} (known reference compound, used as a control)."
    s = c["substitution"]
    vac = f", with {s['li_vacancies']} Li vacancies for charge balance" if s.get("li_vacancies") else ""
    count = "all" if s["count"] == "all" else s["count"]
    return (f"Composition: {c['formula']}. Built from {c.get('parent_formula') or ''} ({c['parent']}) by replacing "
            f"{count} {s['remove']} by {s['add']}{vac}. Family: {s['add']}-substituted "
            f"{c.get('parent_formula') or c['parent']}.")


def messages_for(c: dict) -> list[dict]:
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": _describe(c)}]


def _clean(text: str) -> tuple[str, list[str]]:
    """Body without the LEVEL line, typed URLs and over-claiming sentences; notes on what was removed."""
    notes = []
    body = _LEVEL.sub("", text, count=1).strip()
    body, n_urls = _URL.subn("", body)
    if n_urls:
        notes.append(f"{n_urls} URL(s) written by the model removed (only API citations are kept)")
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    kept = [s for s in sentences if not _OVERCLAIM.search(s)]
    if len(kept) < len(sentences):
        notes.append(f"{len(sentences) - len(kept)} over-claiming sentence(s) removed")
    return " ".join(kept).strip(), notes


def check(c: dict, client, today: str | None = None) -> dict:
    """Novelty level of one candidate from one grounded web search."""
    reply = client.web_search(messages_for(c), reasoning_effort=config.NOVELTY_REASONING_EFFORT,
                              max_output_tokens=config.NOVELTY_MAX_OUTPUT_TOKENS)
    m = _LEVEL.search(reply.text)
    level = m.group(1).lower() if m else "none_found"
    summary, notes = _clean(reply.text)
    if not m:
        notes.append("the model gave no level: check manually")
    sources, seen = [], set()
    for cit in reply.citations:
        if cit.get("url") and cit["url"] not in seen:
            seen.add(cit["url"])
            sources.append({"title": cit.get("title") or cit["url"], "url": cit["url"]})
    if level in ("published", "related") and not sources:
        notes.append(f"'{level}' claimed without any citation from the API: unsourced claim discarded")
        level = "none_found"
    return {"id": c["id"], "formula": c["formula"], "level": level, "label": LEVELS[level], "summary": summary,
            "sources": sources, "sources_considered": len(reply.sources_considered), "web_searches": reply.web_searches,
            "cost_usd": round(reply.cost_usd, 5), "date": today or datetime.now(timezone.utc).date().isoformat(),
            "notes": notes}


def novelty_check(candidates: list[dict], client, control: dict | None = config.NOVELTY_CONTROL) -> dict:
    """Control first (a known electrolyte, expected 'published'), then each final candidate.

    Stops cleanly when the client's budget is reached; what was checked is kept.
    """
    from autolab.llm.client import BudgetExceeded, LLMError

    out = {"control": None, "candidates": [], "stopped": None}
    for c in ([control] if control else []) + list(candidates):
        try:
            res = check(c, client)
        except BudgetExceeded as e:
            out["stopped"] = f"budget: {e}"
            break
        except LLMError as e:
            out["stopped"] = f"language model: {e}"
            break
        if control and c is control:
            res["control_ok"] = res["level"] == "published"
            out["control"] = res
        else:
            out["candidates"].append(res)
    out["usage"] = client.tracker.summary()
    return out


def render(result: dict) -> str:
    """'Novelty check' section of the final report."""
    lines = ["## Novelty check (literature, web search)", ""]
    rows = ([result["control"]] if result.get("control") else []) + result["candidates"]
    if rows:
        lines += [f"Search date: {rows[0]['date']}. Links come only from the citations returned by the API. "
                  "\"No publication found in this search\" does not mean the material was never reported.", ""]
    for r in rows:
        tag = " (control, expected: already published)" if "control_ok" in r else ""
        lines += [f"### {r['id']} {r['formula']}{tag}: {r['label']}", "", r["summary"] or "(no summary)"]
        if r["sources"]:
            lines += ["", "Sources:"] + [f"- [{s['title']}]({s['url']})" for s in r["sources"]]
        if r["notes"]:
            lines += ["", "Notes: " + "; ".join(r["notes"])]
        lines += ["", f"_{r['web_searches']} web searches, {r['sources_considered']} sources considered, "
                      f"~${r['cost_usd']:.4f}, {r['date']}_", ""]
    if result.get("stopped"):
        lines.append(f"**Stopped:** {result['stopped']}")
    u = result.get("usage")
    if u:
        lines.append(f"Total: {u['calls']} calls, ~${u['cost_usd']:.4f}.")
    return "\n".join(lines)
