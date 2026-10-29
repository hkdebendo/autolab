"""Markdown report of one loop run (proposals, funnel results, reasoning, stages, ranking, usage)."""

from __future__ import annotations

REASONING_CHARS = 1200


def _sub(s: dict) -> str:
    if not isinstance(s, dict):
        return str(s)
    count = "all" if s.get("count") == "all" else f"x{s.get('count')}"
    vac = f", -{s['li_vacancies']} Li" if s.get("li_vacancies") else ""
    return f"{s.get('remove')}->{s.get('add')} {count}{vac}"


def _num(x, fmt=".3f") -> str:
    return "—" if x is None else format(x, fmt)


def _short(text: str, n: int = REASONING_CHARS) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + " [...]"


def _llm_line(info: dict) -> str:
    return (f"_{info['provider']}, {info['attempts']} attempt(s), {info['input_tokens']} in / "
            f"{info['output_tokens']} out tokens, ~${info['cost_usd']:.4f}, {info['seconds']} s_")


def _reduced(c: dict) -> str:
    if not c.get("reduced_confidence"):
        return ""
    return (f", reduced confidence (decomposes via the polysulfide {', '.join(c['decomposition_polysulfides'])}, "
            "where UMA is least reliable)")


def _candidate_row(c: dict) -> str:
    gap = "—" if c.get("gap_optb88") is None else f"{c['gap_optb88']:.2f} / {c['gap_mbj']:.2f}"
    verdict = c["status"] if c["status"] == "passed" else f"{c['status']} at {c.get('rejected_at') or '—'}"
    if c.get("reason") and c["status"] != "passed":
        verdict += f": {c['reason']}"
    ss = {True: "yes", False: "no"}.get(c.get("ss_bonds"), "—")
    if c.get("reduced_confidence"):
        ss += f" (reduced confidence: decomposes via {', '.join(c['decomposition_polysulfides'])})"
    known = ", ".join(c.get("known_in_mp") or []) or "—"
    return (f"| {c['id']} | {c.get('formula') or '—'} | {c.get('arrangements', '—')}/{c.get('converged', '—')} | "
            f"{_num(c.get('energy_spread_meV'), '.1f')} | {_num(c.get('e_hull'))} | "
            f"{_num(c.get('e_hull_per_substitution'))} | {gap} | {ss} | {known} | {verdict} |")


def candidate_table(candidates: list[dict]) -> list[str]:
    """Funnel results of one iteration (electrolyte domain)."""
    lines = ["| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | "
             "E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [_candidate_row(c) for c in candidates]
    for c in candidates:
        if c.get("decomposition"):
            products = ", ".join(f"{d['formula']} {d['fraction']:.2f}" for d in c["decomposition"])
            lines.append(f"- {c['id']} decomposes into: {products}")
    return lines


def render(result: dict, domain=None) -> str:
    """Report of a run; the domain gives the iteration table and the sections of its stages."""
    from autolab.domains import get_domain

    domain = domain or get_domain(result.get("domain", "electrolyte"))
    table = domain.render_candidates or candidate_table
    lines = ["# AutoLab loop report", "", f"**Domain.** {domain.name}. **Goal.** {result['goal']}", ""]
    lines.append("**Parents.** " + "; ".join(f"{p['formula']} {p['id']} ({p['cell_formula']}, {p['nsites']} atoms)"
                                             for p in result["parents"]))
    s = result["settings"]
    lines += [f"**Settings.** {s['n_iterations']} iterations max, {s['max_candidates']} candidates max, "
              f"{s['max_relaxations']} new UMA relaxations max; brain {s['brain']}, fallback {s['fallback']}.",
              f"**Stop reason.** {result['stop_reason']}", ""]

    for r in result["iterations"]:
        lines += [f"## Iteration {r['iteration']}", ""]
        if not r["proposal"]:
            lines += ["No proposal (language model unavailable).", ""]
            continue
        p = r["proposal"]
        lines += [f"**Hypothesis.** {p['reply']['hypothesis']}", "", _llm_line(p), "",
                  "| Proposal | Parent | Substitution | Rationale |", "|---|---|---|---|"]
        for c in r["candidates"]:
            lines.append(f"| {c['id']} | {c['parent']} | {_sub(c['substitution'])} | {c.get('rationale') or ''} |")
        if p["reasoning"]:
            lines += ["", "<details><summary>Reasoning summary (proposals)</summary>", "",
                      _short(p["reasoning"]), "", "</details>"]
        lines += [""] + table(r["candidates"])
        if r.get("comparisons"):
            lines += ["", "<details><summary>Comparisons computed by the code (given to the model)</summary>", ""]
            for comp in r["comparisons"]:
                lines.append(f"- **{comp['kind']}**, {comp['about']}: " + "; ".join(comp["statements"]))
            lines += ["", "</details>"]
        a = r["analysis"]
        if a:
            reply = a["reply"]
            lines += ["", f"**Analysis.** ranking {reply['ranking'] or '[]'}; stop={reply['stop']}", ""]
            lines += [f"- {lesson}" for lesson in reply["lessons"]]
            lines += ["", f"**Next direction.** {reply['next_direction']}", "", _llm_line(a)]
            if a["reasoning"]:
                lines += ["", "<details><summary>Reasoning summary (analysis)</summary>", "",
                          _short(a["reasoning"]), "", "</details>"]
        lines.append("")

    if result.get("summaries"):
        lines += ["## Summaries (Muse Glimmer)", ""]
        for s in result["summaries"]:
            lines += [f"**{s.get('label') or 'summary'}.** " + (s["text"] or f"not written ({s.get('error')})"), ""]
    if result.get("prior"):
        lines += [f"**Earlier runs.** {len(result['prior'])} candidates given to the model and to the stages: "
                  f"{', '.join(c['id'] for c in result['prior'])}.", ""]
    stages = {s.name: s for s in domain.stages}
    for name, out in result.get("stages", {}).items():
        stage = stages.get(name)
        if out["status"] == "error":
            lines += [f"## {name}", "", f"**Error:** {out['error']}", ""]
        elif stage and stage.render:
            lines += stage.render(out, result)
    if not result.get("stages"):
        by_id = {c["id"]: c for r in result["iterations"] for c in r["candidates"]}
        lines += ["## Ranking after the funnel (passed candidates, lowest E_hull per substitution first)", ""]
        if result["final_ranking"]:
            for i, cid in enumerate(result["final_ranking"], 1):
                c = by_id[cid]
                lines.append(f"{i}. {cid} {c['formula']} ({_sub(c['substitution'])} in {c['parent']}): "
                             f"E_hull per substitution {_num(c.get('e_hull_per_substitution'))} eV per modified site, "
                             f"E_hull per atom {_num(c['e_hull'])} eV/atom, gap {_num(c['gap_optb88'], '.2f')} eV"
                             f"{', S-S bonds (reduced reliability)' if c.get('ss_bonds') else ''}"
                             f"{_reduced(c)}")
        else:
            lines.append("No candidate passed all filters.")
        lines += ["", "Stages after the funnel not run. Candidates are computational predictions, not proven materials."]
    lines += ["", f"Model ranking (last analysis): {result['model_ranking'] or '[]'}", "", "## Usage", ""]
    u = result["usage"]
    for provider, t in u["llm"].items():
        lines.append(f"- {provider}: {t['calls']} calls, {t['input_tokens']} in / {t['output_tokens']} out tokens, "
                     f"~${t['cost_usd']:.4f}")
    if u.get("analyst"):
        lines.append(f"- candidate analyses ({', '.join(u['analyst']['by_provider']) or 'analyst'}): "
                     f"{u['analyst']['calls']} calls, ~${u['analyst']['cost_usd']:.4f}")
    if u.get("novelty"):
        lines.append(f"- novelty web search: {u['novelty']['calls']} calls, ~${u['novelty']['cost_usd']:.4f}")
    if u.get("md"):
        lines.append(f"- molecular dynamics: {u['md']['runs']} new runs of {u['md']['total_runs']} on Modal "
                     f"{u['md']['gpu']}, estimate {u['md']['usd']:.2f} $")
    lines += [f"- UMA relaxations: {u['relaxations']['new']} new / {u['relaxations']['limit']} allowed",
              f"- events: {u['events']}; duration {u['seconds'] / 60:.1f} min"]
    return "\n".join(lines)
