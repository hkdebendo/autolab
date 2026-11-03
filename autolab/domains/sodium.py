"""Sodium solid electrolytes for sodium-metal batteries: the third domain of the agent (owner, 2026-11-02).

The lithium electrolyte funnel and slow tests with Na+ as the mobile ion (config.MOBILE_IONS): substitutions in known
sodium conductors (config.SODIUM_PARENTS), charge neutrality with fixed oxidation states (SODIUM_OXIDATION_STATES),
stability against the stable MP phases relaxed with UMA, closed-shell ions, then in each round the
window and the reaction with sodium metal, an independent review, the model's choice of one candidate and its Na
diffusion by molecular dynamics against its parent (calibrated on Na vacancies in Na3SbS4: config.SODIUM_MD_CAN_EXCLUDE). The stages are those of the
electrolyte domain, given this domain's settings (ion, no cathode, prompts, MD cap). After the iterations: ranking by
stability cost, literature check (a known sodium electrolyte as a control), final report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import partial
from typing import Callable

from autolab import config
from autolab.agent import review
from autolab.chem.oxidation import check_charge
from autolab.domains import Campaign, Domain, Stage, register
from autolab.domains import electrolyte as el
from autolab.llm.schemas import template


# --- tools: the electrolyte ones with Na metal, the stable phases as hull references, a sodium control ---------------

def _entries(elements, budget):
    from autolab.analysis.stability import uma_reference_entries

    return uma_reference_entries(elements, budget=budget, ehull_max=config.SODIUM_HULL_REF_EHULL_MAX)


def _window_passivation(c: dict, budget) -> dict:
    from autolab.agent.electrochem import window_and_passivation

    return window_and_passivation(c, entries_fn=_entries, budget=budget, ion="Na")


def _ehull_error(formula: str) -> dict | None:
    from autolab.analysis.uma_errors import cached_system_errors, ehull_uncertainty

    return ehull_uncertainty(formula, errors=lambda els: cached_system_errors(els, ehull_max=config.SODIUM_HULL_REF_EHULL_MAX))


def _novelty(cands: list[dict], client) -> dict:
    from autolab.agent.novelty import novelty_check
    from autolab.store.cache import JsonCache

    return novelty_check([{**c, "kind": "sodium"} for c in cands], client, control=config.SODIUM_NOVELTY_CONTROL,
                         cache=JsonCache(config.CACHE_DIR / "novelty"))


@dataclass
class SodiumTools(el.ElectrolyteTools):
    hull_entries: Callable = _entries
    window_passivation: Callable = _window_passivation
    ehull_error: Callable = _ehull_error
    novelty: Callable = _novelty


def evaluate(candidate_id, parent_id, parent, substitution, tools, events, budget=None) -> dict:
    from autolab.agent.pipeline import evaluate_candidate

    return evaluate_candidate(candidate_id, parent_id, parent, substitution, tools, events, budget,
                              charge_check=partial(check_charge, table=config.SODIUM_OXIDATION_STATES),
                              ehull_max=config.SODIUM_EHULL_MAX)


# --- what the model reads and writes --------------------------------------------------------------------------------

def _oxidation_table() -> str:
    return ", ".join(f"{e}{'+' if q > 0 else ''}{q}" for e, q in config.SODIUM_OXIDATION_STATES.items())


_MD_NOTE = ("" if config.SODIUM_MD_CAN_EXCLUDE else
            " — information only: the calibration of the sodium MD failed (ordered Na3SbS4 came out slower than "
            "Na3PS4, the reverse of experiment), so never conclude from it that a candidate conducts better or worse")


def proposal_system(max_proposals: int) -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new sodium solid electrolytes (superionic Na+ conductors) for sodium-metal batteries, the post-lithium option for the stationary storage of renewable energy.
Each proposal is a chemical substitution applied to a parent sodium conductor from Materials Project. The code builds the structures, relaxes them with the UMA machine-learned potential (Meta FAIR) and filters them.

Substitution format:
- partial: {{"remove": "S", "add": "Se", "count": 2, "li_vacancies": 0}} replaces `count` randomly chosen `remove` sites of the parent cell by `add`; the field li_vacancies removes that many Na atoms (the mobile ion of this domain) for charge balance. Several random arrangements are relaxed and the lowest in energy is kept.
- total: {{"remove": "Sb", "add": "P", "count": "all"}} replaces every `remove` site.

Rules checked by the code (a proposal breaking one is rejected before any simulation):
- Only these elements, with fixed oxidation states: {_oxidation_table()}. No redox-active transition metals.
- The cell must stay charge-neutral. Counts refer to the parent cell (its cell formula is given). Example: in Na6P2S8 (Na3PS4), replacing one S(-2) by Cl(-1) adds +1, so one Na vacancy is needed (li_vacancies: 1).
- `count` is at most the number of `remove` sites in the parent cell; `parent` must be one of the given material ids.
A composition already present in Materials Project is reported and not computed: aim for new compositions.

Filters, with thresholds fixed by the code:
- E_hull (energy above the convex hull of the stable known phases, all relaxed with UMA) <= {config.SODIUM_EHULL_MAX} eV/atom; candidates that pass are ranked by E_hull per substitution (E_hull x atoms / modified sites).
- Every ion with a closed electron shell (no easy electron hopping): the electrolyte must be an electronic insulator; the champion's band gap is then computed by DFT and must be >= {config.SODIUM_BANDGAP_MIN} eV.
- In each round, the slow tests: window and reaction with sodium metal (a candidate forming a metal with Na is excluded) and Na diffusion by molecular dynamics at {config.MD_SCREEN_TEMPERATURE_K} K against the parent for one chosen candidate{_MD_NOTE}.

The history holds slow_tests (results measured by the code, failures included) and your failure_analysis of them. Treat every failure as data: do not repeat a strategy that failed; when a proposal corrects an earlier failure, say in the hypothesis which one and how (the cause you give is a hypothesis: the code measured only the numbers). Keep every proposal charge-neutral.

Propose at most {max_proposals} substitutions, diverse and chemically motivated (Na vacancies, softer or larger anions that widen the Na pathways, aliovalent dopants known in sodium conductors), each with a one-sentence rationale. Never repeat a substitution already evaluated.
Reply with JSON only, exactly this shape: {template("proposal")}"""


def analysis_system() -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new sodium solid electrolytes (superionic Na+ conductors) for sodium-metal batteries.
You receive the results of the candidates evaluated in this iteration. Fields:
- status: "passed" (every filter passed), "rejected", "error" or "budget" (not evaluated: simulation budget reached).
- rejected_at: "generate" (unknown parent, element outside the table, impossible count, or not charge-neutral), "known" (already in Materials Project), "relax" (no arrangement converged), "hull" (E_hull above {config.SODIUM_EHULL_MAX} eV/atom), "bandgap" (an ion with an open electron shell).
- e_hull (eV/atom, UMA energies with the MP2020 corrections, against the stable MP phases relaxed with UMA) and decomposition; e_hull_per_substitution: the ranking criterion (eV per modified site, the li_vacancies count Na vacancies).
- closed_shell: every ion has a closed electron shell; ss_bonds: S-S chains present (UMA less reliable).
- comparisons: statements computed by the code over all candidates so far. Base every comparison only on them and quote their numbers; never compare values yourself.
- slow_tests, run by the code in this iteration: "contact with Na metal" (a candidate whose reaction with sodium metal gives a metallic product and releases at least 0.1 eV/atom is excluded) and "Na diffusion" (molecular dynamics at {config.MD_SCREEN_TEMPERATURE_K} K, {config.MD_SCREEN_SEEDS} runs of {config.MD_SCREEN_PS} ps, against the parent: D, D_ratio_to_parent with its error, verdict higher/tied/lower{_MD_NOTE}; framework: for each element its diffusion relative to Na — the framework "moved" when one exceeds {config.MD_FRAMEWORK_D_RATIO_MAX:.0%} of Na).
- failure_analysis: for EACH failed slow test, its id, a hypothesis on the physical or chemical cause, explicitly a hypothesis since the code measured only the numbers, and a correction for the next proposals that keeps charge neutrality. Empty list when nothing failed.
Ionic conductivity at room temperature is not computed in this domain: do not claim it.

Rank only candidates with status "passed" and not excluded, best first by e_hull_per_substitution unless the comparisons or the slow tests give a reason otherwise (empty list if none). Give 1 to 3 short lessons, one sentence of next direction, and stop=true only if more iterations are unlikely to help.
Reply with JSON only, exactly this shape: {template("analysis")}"""


def md_selection_messages(goal: str, candidates: list[dict], comparisons: list[dict], max_selected: int) -> list[dict]:
    system = f"""You are the research brain of AutoLab, an agent searching for new sodium solid electrolytes for sodium-metal batteries.
The candidates below passed every filter (E_hull <= {config.SODIUM_EHULL_MAX} eV/atom, closed-shell ions) and were not excluded at the electrodes. Choose which ones go to molecular dynamics, the most expensive step: Na diffusion at {config.MD_SCREEN_TEMPERATURE_K} K on a GPU, {config.MD_SCREEN_SEEDS} runs of {config.MD_SCREEN_PS} ps each, compared with the candidate's own parent.
Fields: e_hull and e_hull_per_substitution (lower is better); window (electrochemical stability window in V vs Na/Na+; stable=false means zero width, not a rejection); passivation against sodium metal; analysis: a short review written by another model (an opinion, the numbers come first); comparisons: statements computed by the code (base every comparison only on them).
Select at most {max_selected} candidate ids, the most promising and diverse for Na conduction (Na vacancies, larger or softer anions, dopants known to open Na pathways), and give a one-sentence rationale. Only ids from the list are accepted.
Reply with JSON only, exactly this shape: {template("md_selection")}"""
    user = {"goal": goal, "candidates": candidates, "comparisons": comparisons,
            "request": f"Select at most {max_selected} candidates for molecular dynamics."}
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}]


def review_messages(goal: str, candidate: dict, comparisons: list[dict]) -> list[dict]:
    system = f"""You are a materials scientist reviewing ONE candidate sodium solid electrolyte (Na+ conductor) for sodium-metal batteries, found by the AutoLab agent. It passed every filter computed by the code (E_hull <= {config.SODIUM_EHULL_MAX} eV/atom with UMA energies, closed-shell ions) and was not excluded at the electrodes.
Fields: formula, parent and substitution; e_hull and e_hull_per_substitution (lower is better); decomposition; ss_bonds; window (electrochemical stability window in V vs Na/Na+); passivation against sodium metal and passivation_reaction_energy (eV/atom); comparisons: statements computed by the code about this candidate.
Write 1 to 3 strengths and 1 to 3 risks, each one short sentence grounded in these numbers or in well-known chemistry (Na vacancies, softer anions, moisture sensitivity of sulfides, cost or toxicity of an element, abundance of sodium). Quote numbers only from the fields or comparisons; never compute or compare values yourself. Give md_priority "high", "medium" or "low": how much a Na-diffusion simulation of this candidate would teach us. Ionic conductivity is not known: do not claim it.
Reply with JSON only, exactly this shape: {template("candidate_analysis")}"""
    user = {"goal": goal, "candidate": candidate, "comparisons": comparisons}
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user)}]


def proposal_messages(goal: str, parents: list[dict], history: list[dict], max_proposals: int) -> list[dict]:
    user = {"goal": goal, "parents": parents, "history": history,
            "request": f"Propose at most {max_proposals} new substitutions."}
    return [{"role": "system", "content": proposal_system(max_proposals)}, {"role": "user", "content": json.dumps(user)}]


def analysis_messages(goal: str, iteration: int, hypothesis: str, results: list[dict], history: list[dict],
                      comparisons: list[dict] | None = None, slow_tests: list[dict] | None = None) -> list[dict]:
    user = {"goal": goal, "iteration": iteration, "hypothesis": hypothesis, "results": results,
            "comparisons": comparisons or [], "slow_tests": slow_tests or [], "previous_iterations": history}
    return [{"role": "system", "content": analysis_system()}, {"role": "user", "content": json.dumps(user)}]


# --- stages after the iterations: ranking, literature, report -------------------------------------------------------

def render_ranking(out: dict, result: dict) -> list[str]:
    pool = el._pool(result)
    order = (f"diffusion verdict against the parent at {config.MD_SCREEN_TEMPERATURE_K} K "
             f"({' > '.join(config.FINAL_RANK_MD_ORDER)}), then lowest E_hull per substitution" if config.SODIUM_MD_CAN_EXCLUDE
             else "lowest E_hull per substitution (the Na diffusion verdict is shown as information: its calibration "
                  "failed, it does not rank)")
    lines = ["## Final ranking", "", f"Order: {order}; excluded candidates last, with their reason. Candidates are "
             "computational predictions, not proven materials.", ""]
    if not out["ranking"]:
        return lines + ["No candidate passed all filters.", ""]
    for i, cid in enumerate(out["ranking"], 1):
        c = pool[cid]
        err = c.get("e_hull_error")
        pm = f" ± {err['mae_eV_per_atom']:.3f}" if err else ""
        md = c.get("md_verdict") or "not simulated"
        ratio = f" (D/D(parent) {c['D_ratio_to_parent']:.2f} ± {c['D_ratio_err']:.2f})" if c.get("D_ratio_to_parent") else ""
        tail = f" — EXCLUDED at {c['excluded_at']}: {c['exclusion_reason']}" if c.get("excluded_at") else ""
        star = " **finalist**" if cid in out["finalists"] else ""
        lines.append(f"{i}. {cid} {c['formula']}{star}: E_hull {c['e_hull']:.3f}{pm} eV/atom, per substitution "
                     f"{c['e_hull_per_substitution']:.3f} eV, gap {el.gap_text(c)}, Na diffusion {md}{ratio}{tail}")
    return lines + [""]


METHODS = [
    ("Candidate proposals and decisions", "Meta Muse Spark (reasoning model), with comparisons computed by the code"),
    ("Structure relaxation and energies", "Meta FAIR UMA (uma-s-1p2, OMat head), MP2020 corrections; references from "
                                         "Materials Project (the stable phases), all relaxed with UMA"),
    ("Thermodynamic stability", f"energy above the convex hull of the system; kept if <= {config.SODIUM_EHULL_MAX} "
                                "eV/atom; error bar measured against DFT (Materials Project) on the known compounds of the "
                                "same system"),
    ("Electronic insulation", f"every ion with a closed electron shell (rule, no model); the champion's band gap by DFT "
                              f"(GPAW, PBE, plane waves, on Modal CPU), kept if >= {config.SODIUM_BANDGAP_MIN} eV"),
    ("Electrochemical window and sodium metal", "grand-potential phase diagrams open to sodium (window vs Na/Na+, "
                                                "reaction with sodium metal)"),
    ("Independent reviews", "Meta Muse Spark Open, one review per candidate, in parallel"),
    ("Sodium diffusion", f"Langevin molecular dynamics with UMA at {config.MD_SCREEN_TEMPERATURE_K} K, "
                         f"{config.MD_SCREEN_SEEDS} x {config.MD_SCREEN_PS} ps per structure, compared with the parent "
                         "crystal (difference within 2 combined errors = tied); "
                         + ("calibrated: Na vacancies made by W in Na3SbS4 speed Na up by 2.8 combined errors, as in "
                            "experiment; comparisons between different crystals are not trusted" if config.SODIUM_MD_CAN_EXCLUDE
                            else "information only, it neither excludes nor ranks: its calibration failed")),
    ("Error-driven loop", "the slow tests (reaction with sodium metal, sodium diffusion) run in each round; their "
                          "failures, with the measured numbers, go back to the proposing model, which explains them as "
                          "hypotheses and corrects its next proposals"),
    ("Literature check", "Meta Muse Spark with web search; a known sodium electrolyte (Na3PS4) checked first as a control"),
    ("Plain-language summaries", "Meta Muse Glimmer"),
    ("Campaign review", "Meta Muse Wonder reads the whole campaign at once and plans the next one; it decides nothing"),
]

REPORT_SYSTEM = el.REPORT_SYSTEM.replace(
    "computational materials-discovery research", "computational search for sodium solid electrolytes (Na+ conductors) "
    "for sodium-metal batteries").replace("cycling against Li metal", "cycling against Na metal")


def report(camp: Campaign) -> dict:
    """The electrolyte report with this domain's methods, rules and not-computed list (sodium metal, no cathode
    interface, no conductivity at 300 K)."""
    from autolab.agent.loop import LoopStopped

    rk = camp.outputs.get("ranking", {})
    finalists = rk.get("finalists") or []
    if not finalists:
        return {"skipped": "no finalist", "summary": {"skipped": "no finalist"}}
    by_id = camp.by_id
    novelty_by_id = {r["id"]: r for r in (camp.outputs.get("novelty", {}).get("candidates") or [])}
    rows = []
    for i in finalists:
        r = el._finalist_row(by_id[i], novelty_by_id)
        r["against_na_metal"] = r.pop("against_li_metal", None)
        for k in ("reaction_with_LiFePO4_eV_per_atom", "ionic_conductivity_300K_mS_cm", "ionic_conductivity_range_mS_cm",
                  "ionic_conductivity_method", "activation_energy_eV", "ionic_conductivity_vs_parent",
                  "parent_ionic_conductivity_range_mS_cm", "parent_activation_energy_eV", "activation_energy_error_eV",
                  "ranking_level"):
            r.pop(k, None)
        rows.append(el._rounded(r))
    out = {"completeness": "complete", "missing_steps": [], "champion": rows[0]["id"], "finalists": rows,
           "excluded": rk.get("excluded", {}), "methods": [{"step": a, "method": b} for a, b in METHODS],
           "not_computed": config.SODIUM_NOT_COMPUTED, "narrative": None}
    facts = {"goal": camp.goal, "finalists": rows, "excluded": out["excluded"], "not_computed": out["not_computed"],
             "tie_break_convention": "lowest E_hull per substitution"
             + ("" if config.SODIUM_MD_CAN_EXCLUDE else "; the Na diffusion verdict does not rank (uncalibrated)"),
             "md_calibration": ("passed for a candidate against its own parent (Na vacancies in Na3SbS4, +2.8 combined "
                                "errors); a tied verdict means no difference shown, not equal conduction"
                                if config.SODIUM_MD_CAN_EXCLUDE else
                                "FAILED: each Na diffusion verdict is information only and must never be presented as "
                                "faster or slower conduction")}
    try:
        info = camp.ask([{"role": "system", "content": REPORT_SYSTEM.replace("{template}", template("report"))},
                         {"role": "user", "content": json.dumps(facts, default=str)}], "report", "report")
        n = info["reply"]
        for key in ("validation", "synthesis"):
            n[key] = [{"text": str(x.get("text", x)) if isinstance(x, dict) else str(x),
                       "basis": x.get("basis") if isinstance(x, dict) and x.get("basis") in ("documented", "hypothesis")
                       else "hypothesis"} for x in n.get(key, [])]
        out["narrative"] = n
    except LoopStopped as e:
        out["narrative_error"] = f"the narrative could not be written ({e}); the numbers above are complete"
    out["summary"] = {"champion": out["champion"], "completeness": "complete", "narrative": out["narrative"] is not None}
    return out


def render_report(out: dict, result: dict) -> list[str]:
    if out.get("skipped"):
        return ["## Final scientific report", "", f"Not written: {out['skipped']}.", ""]
    n = out.get("narrative") or {}
    rows = out["finalists"]
    champ = rows[0]
    f = el._fmt
    lines = ["## Final scientific report", ""]
    if n.get("executive_summary"):
        lines += ["### Executive summary", "", n["executive_summary"], ""]
    lines += ["### Comparison of the finalists", "", "| | " + " | ".join(r["formula"] for r in rows) + " |",
              "|---|" + "---|" * len(rows)]
    fields = [("Parent crystal", lambda r: r.get("parent") or "—"), ("Space group", lambda r: r.get("space_group") or "—"),
              ("E_hull (eV/atom)", lambda r: f(r.get("e_hull_eV_per_atom"), ".3f") + (
                  f" ± {r['e_hull_error_eV_per_atom']:.3f}" if r.get("e_hull_error_eV_per_atom") is not None else "")),
              ("E_hull per substitution (eV)", lambda r: f(r.get("e_hull_per_substitution_eV"), ".3f")),
              ("Band gap", el.gap_text),
              ("Window (V vs Na/Na+)", lambda r: (f"{r['window_V']['v_low']:.2f}–{r['window_V']['v_high']:.2f}"
                                                  if r.get("window_V") and r["window_V"].get("stable") else
                                                  "zero width" if r.get("window_V") else "not computed")),
              ("Against Na metal", lambda r: r.get("against_na_metal") or "not computed"),
              ("D at 600 K (cm²/s)", lambda r: f(r.get("D_600K_cm2_per_s"), ".2e")),
              ("D / D(parent)", lambda r: (f"{r['D_ratio_to_parent']:.2f} ± {r['D_ratio_error']:.2f}"
                                           if r.get("D_ratio_to_parent") is not None else "not simulated")),
              ("Diffusion verdict", lambda r: r.get("diffusion_verdict") or "not simulated"),
              ("Literature", lambda r: r.get("novelty") or "not checked")]
    for label, fn in fields:
        lines.append(f"| {label} | " + " | ".join(str(fn(r)) for r in rows) + " |")
    lines += ["", f"### Champion: {champ['formula']}", ""]
    for title, key in (("Why it is preferred", "champion_reasons"), ("Trade-offs", "tradeoffs"), ("Uncertainties", "uncertainties")):
        if n.get(key):
            lines += [f"**{title}.**", ""] + [f"- {x}" for x in n[key]] + [""]
    for title, key in (("Validation to do", "validation"), ("Synthesis routes to consider", "synthesis")):
        if n.get(key):
            lines += [f"**{title}.**", ""] + [f"- {x['text']} *({x['basis']})*" for x in n[key]] + [""]
    lines += ["### Methods", ""] + [f"- **{m['step']}**: {m['method']}" for m in out["methods"]] + [""]
    lines += ["### Limitations", ""] + [f"- {x}" for x in n.get("limitations", [])]
    lines += [f"- Not computed: {out['not_computed']}.", "- The candidates are computational predictions, not proven materials.", ""]
    if out.get("narrative_error"):
        lines += [f"*{out['narrative_error']}*", ""]
    return lines


def make_domain() -> Domain:
    slow = (Stage("electrodes", el.electrodes, el.render_electrodes),
            Stage("candidate_analyses", el.candidate_analyses, el.render_candidate_analyses),
            Stage("md_selection", el.md_selection, el.render_md_selection),
            Stage("molecular_dynamics", el.molecular_dynamics, el.render_md))
    return Domain(
        name="sodium", goal=config.SODIUM_GOAL, parents=tuple(config.SODIUM_PARENTS),
        make_tools=lambda: SodiumTools(not_run=[]), evaluate=evaluate, proposal_messages=proposal_messages,
        analysis_messages=analysis_messages, comparisons=el.comparisons, for_model=el.FOR_MODEL, rank_key=el.rank_key,
        iteration_stages=slow, feedback=partial(el.feedback, ion="Na"), render_feedback=el.render_feedback,
        stages=slow + (Stage("ranking", el.ranking, render_ranking), Stage("dft_gap", el.dft_gap, el.render_dft_gap),
                       Stage("novelty", el.novelty, el.render_novelty),
                       Stage("report", report, render_report),
                       Stage("campaign_review", review.campaign_review, review.render)),
        thresholds=("SODIUM_EHULL_MAX", "SODIUM_BANDGAP_MIN", "SODIUM_HULL_REF_EHULL_MAX", "SODIUM_MD_MAX_USD",
                    "SODIUM_MD_CAN_EXCLUDE", "MD_SCREEN_TEMPERATURE_K", "MD_SCREEN_SEEDS", "MD_SCREEN_PS",
                    "MD_TIE_SIGMA", "MD_FRAMEWORK_D_RATIO_MAX", "ELECTRODES_TOP", "ELECTRODE_EXCLUDED_PASSIVATION",
                    "ITERATION_MD_SELECT_MAX", "FINALISTS_MAX"),
        render_candidates=None,
        settings={"ion": "Na", "cathodes": config.SODIUM_CATHODES, "review_messages": review_messages,
                  "md_selection_messages": md_selection_messages, "md_max_usd": config.SODIUM_MD_MAX_USD,
                  "md_max_usd_name": "SODIUM_MD_MAX_USD", "md_can_exclude": config.SODIUM_MD_CAN_EXCLUDE,
                  "md_ranks": config.SODIUM_MD_CAN_EXCLUDE, "gap_min": config.SODIUM_BANDGAP_MIN})


register("sodium", make_domain)
