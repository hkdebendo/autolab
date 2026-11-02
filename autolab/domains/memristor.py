"""Oxide memristors (valence-change memories for neuromorphic chips): the fourth domain of the agent (owner, 2026-11-02).

Funnel of one candidate (an isovalent substitution in a known switching oxide, config.MEMRISTOR_PARENTS):
1. generate: the substitution applied to the parent cell, charge neutrality with fixed oxidation states
   (config.MEMRISTOR_OXIDATION_STATES); a substitution with vacancies is refused (the moving vacancy is the one the
   code adds);
2. known: a composition already in Materials Project is reported, not computed;
3. relax, 4. hull (stable MP phases relaxed with UMA, <= config.MEMRISTOR_EHULL_MAX), 5. GapModel band gap
   (>= config.MEMRISTOR_BANDGAP_MIN): the shared funnel of agent.pipeline.
In each round (slow test): the migration barrier of a neutral O vacancy (NEB with UMA, analysis.migration) on the
hops next to the dopant, against the parent's lowest hop computed the same way; the verdict (lower / comparable /
higher, config.MEMRISTOR_EA_SIGNIFICANT_EV) is decided by the code and fed back to the model with every failure.
After the rounds: independent reviews, ranking by verdict then barrier then stability, literature check, report.
A lower barrier suggests easier switching at a possible cost in retention; neither is computed (config.MEMRISTOR_NOT_COMPUTED).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import partial
from typing import Callable

from pymatgen.core import Structure

from autolab import config
from autolab.agent.compare import comparisons as _comparisons
from autolab.agent.pipeline import Tools, _relaxed_structure
from autolab.analysis.migration import hop_items, lowest_barrier, vs_parent
from autolab.domains import Campaign, Domain, Stage, register
from autolab.llm.schemas import template

METRICS = (  # what the code compares between candidates (agent.compare), best first
    ("barrier_eV", "O-vacancy migration barrier", "eV", "low"),
    ("e_hull", "E_hull per atom", "eV/atom", "low"),
    ("e_hull_per_substitution", "E_hull per substitution", "eV per modified site", "low"),
    ("gap_optb88", "band gap", "eV", "high"),
)
FOR_MODEL = ("id", "parent", "substitution", "formula", "status", "rejected_at", "reason", "arrangements", "converged",
             "known_in_mp", "e_hull", "e_hull_per_substitution", "decomposition", "n_atoms", "n_modified",
             "gap_optb88", "gap_mbj", "barrier_eV", "parent_barrier_eV", "barrier_vs_parent", "barrier_hops")
THRESHOLDS = ("MEMRISTOR_EHULL_MAX", "MEMRISTOR_HULL_REF_EHULL_MAX", "MEMRISTOR_BANDGAP_MIN",
              "MEMRISTOR_EA_SIGNIFICANT_EV", "MEMRISTOR_NEB_MAX_USD", "MEMRISTOR_MOBILE_ION", "NEB_MAX_HOPS",
              "NEB_IMAGES", "NEB_FMAX", "NEB_MIN_LENGTH", "CANDIDATE_ANALYSIS_PROVIDER")
STEP_NAMES = {"generate": "charge neutrality", "known": "novelty (already in Materials Project)",
              "relax": "relaxation", "hull": "thermodynamic stability", "bandgap": "band gap"}
NO_VACANCY = ("a substitution may not remove atoms in this domain: the moving oxygen vacancy is added by the code "
              "(isovalent substitutions only)")


# --- default tools (expensive or networked; tests replace them) -----------------------------------------------------

def _default_hull_entries(elements, budget):
    from autolab.analysis.stability import uma_reference_entries

    return uma_reference_entries(elements, budget=budget, ehull_max=config.MEMRISTOR_HULL_REF_EHULL_MAX)


def _default_ehull_error(formula: str) -> dict | None:
    from autolab.analysis.uma_errors import cached_system_errors, ehull_uncertainty

    return ehull_uncertainty(formula, errors=lambda els: cached_system_errors(els, ehull_max=config.MEMRISTOR_HULL_REF_EHULL_MAX))


def _default_nebs(items: list[dict]) -> list[dict | None]:
    from autolab.sim.backend import run_nebs

    return run_nebs(items)


def _default_neb_cost(items: list[dict]) -> float:
    from autolab.sim.backend import neb_missing, neb_plan

    return neb_plan(neb_missing(items))["usd"]


def _default_parent_structure(material_id: str) -> Structure:
    from autolab.data.mp import get_structure

    return get_structure(material_id)


@dataclass
class MemristorTools(Tools):
    hull_entries: Callable = _default_hull_entries
    ehull_error: Callable = _default_ehull_error
    nebs: Callable = _default_nebs  # (items) -> NEB results (sim.backend.run_nebs), None for a failed hop
    neb_cost: Callable = _default_neb_cost  # (items) -> estimated Modal cost of the hops not in the cache
    parent_structure: Callable = _default_parent_structure


def evaluate(candidate_id, parent_id, parent, substitution, tools, events, budget=None) -> dict:
    from autolab.agent.pipeline import evaluate_candidate
    from autolab.chem.generator import vacancies_of
    from autolab.chem.oxidation import check_charge

    check = partial(check_charge, table=config.MEMRISTOR_OXIDATION_STATES)
    clean = {k: v for k, v in substitution.items() if k not in ("li_vacancies", "vacancies")}
    if vacancies_of(substitution):
        check = lambda s: {"ok": False, "charge": None, "unsupported": [], "reason": NO_VACANCY}  # noqa: E731
    out = evaluate_candidate(candidate_id, parent_id, parent, clean, tools, events, budget, charge_check=check,
                             ehull_max=config.MEMRISTOR_EHULL_MAX, gap_min=config.MEMRISTOR_BANDGAP_MIN)
    out["substitution"] = substitution
    return out


def rank_key(c: dict):
    return (c.get("e_hull_per_substitution") or 0.0, c.get("e_hull") or 0.0)


def comparisons(candidates: list[dict]) -> list[dict]:
    return _comparisons(candidates, METRICS)


# --- what the model reads and writes --------------------------------------------------------------------------------

def _oxidation_table() -> str:
    return ", ".join(f"{e}{'+' if q > 0 else ''}{q}" for e, q in config.MEMRISTOR_OXIDATION_STATES.items())


def proposal_system(max_proposals: int) -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new doped oxides for valence-change memristors, the resistive memories of neuromorphic chips: their resistance changes when oxygen vacancies move through the oxide under an electric field.
Each proposal is a chemical substitution applied to a parent switching oxide from Materials Project. The code builds the structures, relaxes them with the UMA machine-learned potential (Meta FAIR), filters them, and computes the migration barrier of an oxygen vacancy next to the dopant by the nudged elastic band method.

Substitution format:
- partial: {{"remove": "Hf", "add": "Zr", "count": 1}} replaces `count` randomly chosen `remove` sites of the parent cell by `add`. Several random arrangements are relaxed and the lowest in energy is kept.
- total: {{"remove": "Ti", "add": "Zr", "count": "all"}} replaces every `remove` site.

Rules checked by the code (a proposal breaking one is rejected before any simulation):
- Only these elements, with fixed oxidation states: {_oxidation_table()}. Substitutions must be isovalent (same charge) so that the cell stays neutral: no vacancies in a proposal (the code adds the moving oxygen vacancy itself).
- `count` is at most the number of `remove` sites in the parent cell (its cell formula is given); `parent` must be one of the given material ids.
A composition already present in Materials Project is reported and not computed: aim for new compositions.

Filters, with thresholds fixed by the code:
- E_hull (energy above the convex hull of the stable known phases, all relaxed with UMA) <= {config.MEMRISTOR_EHULL_MAX} eV/atom.
- Band gap (GapModel, optB88 scale) >= {config.MEMRISTOR_BANDGAP_MIN} eV: the high-resistance state needs an insulator.
- In each round, the slow test: the barrier of a neutral oxygen vacancy hopping next to the dopant, against the lowest hop of the parent computed the same way; "lower" or "higher" only beyond {config.MEMRISTOR_EA_SIGNIFICANT_EV} eV, else "comparable".
Candidates are ranked by that verdict (lower first: easier switching, lower forming and switching voltages), then by barrier, then E_hull per substitution. A lower barrier may cost retention; retention is not computed.

The history holds the results of earlier rounds, failures included with their measurements (slow_tests), and your failure_analysis of them. Treat every failure as data: do not repeat a strategy that failed; when a proposal corrects an earlier failure, say in the hypothesis which one and how (the cause you give is a hypothesis: the code measured only the numbers).

Propose at most {max_proposals} substitutions, diverse and chemically motivated (ionic radius and bond strength of the dopant, known dopants of HfO2, TiO2 or SrTiO3 memristors such as Zr, Si, Al-free isovalent ions, Sr/Ba/Ca exchange), each with a one-sentence rationale. Never repeat a substitution already evaluated.
Reply with JSON only, exactly this shape: {template("proposal")}"""


def analysis_system() -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new doped oxides for valence-change memristors.
You receive the candidates evaluated in this round. Fields:
- status: "passed" (every filter passed), "rejected", "error" or "budget" (not evaluated: simulation budget reached).
- rejected_at: "generate" (unknown parent, element outside the table, impossible count, not charge-neutral, or vacancies asked), "known" (already in Materials Project), "relax" (no arrangement converged), "hull" (E_hull above {config.MEMRISTOR_EHULL_MAX} eV/atom), "bandgap" (gap below {config.MEMRISTOR_BANDGAP_MIN} eV).
- e_hull (eV/atom, UMA energies with the MP2020 corrections, against the stable MP phases relaxed with UMA) and decomposition; e_hull_per_substitution = e_hull x n_atoms / n_modified.
- gap_optb88 / gap_mbj (eV).
- barrier_eV: the lowest migration barrier of a neutral oxygen vacancy among the hops next to the dopant (NEB, UMA); parent_barrier_eV: the lowest hop of the parent; barrier_vs_parent: verdict decided by the code ("lower", "comparable" within {config.MEMRISTOR_EA_SIGNIFICANT_EV} eV, "higher", "undetermined" when a band did not converge).
- comparisons: statements computed by the code over all candidates so far. Base every comparison only on them and quote their numbers; never compare values yourself.
- slow_tests: the outcome of each candidate with its measurements; "failed" is a negative result.
- failure_analysis: for EACH failed candidate, its id, a hypothesis on the cause (dopant radius, bond strength, local distortion, a stronger metal-oxygen bond holding the oxygen), explicitly a hypothesis since the code measured only the numbers, and a correction for the next proposals. Empty list when nothing failed.
Only single hops of a neutral vacancy are computed: no electric field, no charged vacancy, no filament, no retention. Do not claim them.

Rank only candidates with status "passed", best first by the barrier verdict, then barrier, then e_hull_per_substitution (empty list if none). Give 1 to 3 short lessons, one sentence of next direction, and stop=true only if more rounds are unlikely to help.
Reply with JSON only, exactly this shape: {template("analysis")}"""


def proposal_messages(goal: str, parents: list[dict], history: list[dict], max_proposals: int) -> list[dict]:
    user = {"goal": goal, "parents": parents, "history": history,
            "request": f"Propose at most {max_proposals} new substitutions."}
    return [{"role": "system", "content": proposal_system(max_proposals)}, {"role": "user", "content": json.dumps(user)}]


def analysis_messages(goal: str, iteration: int, hypothesis: str, results: list[dict], history: list[dict],
                      comparisons: list[dict] | None = None, slow_tests: list[dict] | None = None) -> list[dict]:
    user = {"goal": goal, "iteration": iteration, "hypothesis": hypothesis, "results": results,
            "comparisons": comparisons or [], "slow_tests": slow_tests or [], "previous_iterations": history}
    return [{"role": "system", "content": analysis_system()}, {"role": "user", "content": json.dumps(user)}]


def _n(x, f):
    return "—" if x is None else format(x, f)


def _numbers(c: dict) -> str:
    parts = []
    if c.get("e_hull") is not None:
        parts.append(f"E_hull {c['e_hull']:.3f} eV/atom")
    if c.get("gap_optb88") is not None:
        parts.append(f"gap {c['gap_optb88']:.2f} eV")
    if c.get("barrier_eV") is not None:
        parts.append(f"O-vacancy barrier {c['barrier_eV']:.2f} eV (parent {_n(c.get('parent_barrier_eV'), '.2f')} eV, "
                     f"{c.get('barrier_vs_parent')})")
    return ", ".join(parts)


# --- slow test of each round: the oxygen-vacancy migration barrier ---------------------------------------------------

_PARENT_BARRIERS: dict[str, dict] = {}  # parent id -> lowest barrier (per process; the NEB results are cached on disk)


def _parent_barrier(camp: Campaign, parent_id: str) -> tuple[dict, list[dict], dict]:
    t = camp.tools
    res = t.relax([t.parent_structure(parent_id)], camp.budget)[0]
    items, info = hop_items(_relaxed_structure(res))
    return res, items, info


def migration(camp: Campaign) -> dict:
    """NEB barriers of the round's passed candidates (hops next to the dopant) and of their parents (lowest hop),
    in one batch; skipped beyond the research's cost cap (config.MEMRISTOR_NEB_MAX_USD), never retried."""
    t = camp.tools
    todo = [c for c in camp.passed() if c.get("barrier_eV") is None and not c.get("migration_done")]
    out = {"computed": [], "verdicts": {}, "parents": {}, "stopped": None, "skipped": None}
    if not todo:
        out["skipped"] = "no new passed candidate"
        out["summary"] = {"skipped": out["skipped"]}
        return out
    jobs = []  # (owner id, items, info)
    for pid in sorted({c["parent"] for c in todo} - set(_PARENT_BARRIERS)):
        _, items, info = _parent_barrier(camp, pid)
        jobs.append((pid, items, info))
    for c in todo:
        add = (c.get("substitution") or {}).get("add")
        items, info = hop_items(_relaxed_structure({"atoms": c["relaxed_atoms"]}), near=add)
        jobs.append((c["id"], items, info))
    items = [it for _, its, _ in jobs for it in its]
    usd = t.neb_cost(items)
    spent = getattr(camp.agent, "neb_usd", 0.0)
    cap = camp.settings.get("neb_max_usd", config.MEMRISTOR_NEB_MAX_USD)
    if spent + usd > cap:
        out["stopped"] = (f"estimated Modal cost {usd:.2f} $ (plus {spent:.2f} $ already launched in this research) above "
                          f"MEMRISTOR_NEB_MAX_USD ({cap:g} $): not launched")
        out["summary"] = {"stopped": out["stopped"]}
        return out
    camp.agent.neb_usd = spent + usd
    camp.emit("migration", "launched", None, candidates=[c["id"] for c in todo], hops=len(items), usd=round(usd, 3))
    results = t.nebs(items)
    k, lows = 0, {}
    for owner, its, info in jobs:
        lows[owner] = {**lowest_barrier(results[k:k + len(its)], info["hops"]), "n_atoms": info["n_atoms"]}
        k += len(its)
    for pid in {c["parent"] for c in todo}:
        if pid in lows:
            _PARENT_BARRIERS[pid] = lows[pid]
        out["parents"][pid] = _PARENT_BARRIERS.get(pid, {}).get("barrier_eV")
    for c in todo:
        low, parent = lows[c["id"]], _PARENT_BARRIERS.get(c["parent"], {})
        v = vs_parent(low["barrier_eV"], parent.get("barrier_eV"), parent_unconverged_min=parent.get("unconverged_min_eV"))
        c.update(barrier_eV=low["barrier_eV"], parent_barrier_eV=parent.get("barrier_eV"), barrier_vs_parent=v["verdict"],
                 barrier_difference_eV=v["difference_eV"], barrier_verdict_reason=v.get("reason"), barrier_hops=low["hops"], barrier_profile_eV=(low["best_hop"] or {}).get("profile_eV"),
                 parent_barrier_profile_eV=(parent.get("best_hop") or {}).get("profile_eV"), migration_done=True)
        out["computed"].append(c["id"])
        out["verdicts"][c["id"]] = v["verdict"]
        camp.emit("migration", "done", c["id"], formula=c["formula"], barrier_eV=c["barrier_eV"],
                  parent_barrier_eV=c["parent_barrier_eV"], verdict=v["verdict"], difference_eV=v["difference_eV"],
                  profile_eV=c["barrier_profile_eV"], parent_profile_eV=c["parent_barrier_profile_eV"],
                  parent=c.get("parent_formula"), hops=len(low["hops"]), converged_hops=low["converged_hops"],
                  n_atoms=low["n_atoms"])
    out["usd"] = round(usd, 3)
    out["summary"] = {"computed": len(out["computed"]), "verdicts": out["verdicts"], "parents": out["parents"]}
    return out


def render_migration(out: dict, result: dict) -> list[str]:
    lines = ["## Oxygen-vacancy migration barriers (NEB with UMA)", ""]
    if out.get("skipped") or out.get("stopped"):
        return lines + [f"Not run: {out.get('skipped') or out.get('stopped')}.", ""]
    pool = _pool(result)
    for cid in out["computed"]:
        c = pool[cid]
        lines.append(f"- {c['formula']} ({cid}): {_n(c.get('barrier_eV'), '.2f')} eV against "
                     f"{_n(c.get('parent_barrier_eV'), '.2f')} eV for {c.get('parent_formula')}: {c.get('barrier_vs_parent')}")
    return lines + [""]


def feedback(cands: list[dict]) -> list[dict]:
    """Every candidate's outcome with its numbers, for the model's analysis: failures are data (error-driven loop)."""
    out = []
    for c in cands:
        if c.get("status") not in ("passed", "rejected"):
            continue
        name = f"{c.get('formula') or c['id']} ({c['id']})"
        measured = {k: c.get(k) for k in ("e_hull", "decomposition", "gap_optb88", "barrier_eV", "parent_barrier_eV",
                                          "barrier_vs_parent", "barrier_difference_eV") if c.get(k) is not None}
        base = {"id": c["id"], "formula": c.get("formula"), "parent": c.get("parent"),
                "substitution": c.get("substitution"), "measured": measured}
        if c["status"] == "rejected":
            test = STEP_NAMES.get(c.get("rejected_at"), c.get("rejected_at") or "evaluation")
            out.append({**base, "test": test, "outcome": "failed", "reason": c.get("reason"),
                        "message": f"Negative result: {name} failed the {test}: {c.get('reason')}."})
        elif c.get("barrier_vs_parent") is not None:
            failed = c["barrier_vs_parent"] in ("higher", "undetermined")
            test = "oxygen-vacancy migration barrier against the parent (NEB)"
            out.append({**base, "test": test, "outcome": "failed" if failed else "passed", "reason": _numbers(c),
                        "message": f"{'Negative result' if failed else 'Result'}: {name}: {_numbers(c)}."})
    return out


def render_feedback(record: dict) -> list[str]:
    fb = record.get("feedback") or []
    fa = ((record.get("analysis") or {}).get("reply") or {}).get("failure_analysis") or []
    if not fb and not fa:
        return []
    lines = ["**Results of this round (fed back to the model):**", ""] + [f"- {f['message']}" for f in fb]
    if fa:
        lines += ["", "**The model's reading of the failures (hypotheses, not measurements):**", ""]
        lines += [f"- {x.get('id')}: {x.get('hypothesis')} Correction: {x.get('correction')}" for x in fa]
    return lines + [""]


def render_candidates(candidates: list[dict]) -> list[str]:
    lines = ["| Candidate | Parent | Substitution | Status | E_hull (eV/atom) | Gap (eV) | O-vacancy barrier (eV) | "
             "Parent barrier (eV) | Verdict |", "|---|---|---|---|---|---|---|---|---|"]
    for c in candidates:
        s = c.get("substitution") or {}
        status = c["status"] if c["status"] != "rejected" else f"rejected ({c.get('rejected_at')})"
        lines.append(f"| {c.get('formula') or c['id']} ({c['id']}) | {c.get('parent_formula') or c.get('parent')} | "
                     f"{s.get('remove')}→{s.get('add')} ×{s.get('count')} | {status} | {_n(c.get('e_hull'), '.3f')} | "
                     f"{_n(c.get('gap_optb88'), '.2f')} | {_n(c.get('barrier_eV'), '.2f')} | "
                     f"{_n(c.get('parent_barrier_eV'), '.2f')} | {c.get('barrier_vs_parent') or '—'} |")
    return lines + [""]


# --- stages after the rounds: reviews, ranking, literature, report --------------------------------------------------

REVIEW_FIELDS = ("formula", "parent_formula", "substitution", "e_hull", "e_hull_per_substitution", "decomposition",
                 "gap_optb88", "gap_mbj", "barrier_eV", "parent_barrier_eV", "barrier_vs_parent", "barrier_difference_eV")


def review_system() -> str:
    return f"""You are a materials scientist reviewing ONE candidate doped oxide for valence-change memristors (resistive memories of neuromorphic chips), found by the AutoLab agent. It passed the filters computed by the code: E_hull <= {config.MEMRISTOR_EHULL_MAX} eV/atom (UMA energies, stable MP phases relaxed with UMA), GapModel band gap >= {config.MEMRISTOR_BANDGAP_MIN} eV.
Fields: formula, parent and substitution; e_hull and e_hull_per_substitution; decomposition; gap_optb88 and gap_mbj (eV); barrier_eV: lowest migration barrier of a neutral oxygen vacancy next to the dopant (NEB with UMA); parent_barrier_eV and barrier_vs_parent (decided by the code, "comparable" within {config.MEMRISTOR_EA_SIGNIFICANT_EV} eV); comparisons computed by the code.
Write 1 to 3 strengths and 1 to 3 risks, each one short sentence grounded in these numbers or in well-known chemistry (CMOS compatibility of the elements, dopants known in HfO2/TiO2/SrTiO3 memristors, phase stability of doped HfO2, retention against easier switching). Quote numbers only from the fields or comparisons; never compute or compare values yourself. Give md_priority "high", "medium" or "low": the priority of this candidate for a DFT or device follow-up. Fields, charged vacancies, filaments, retention and endurance were not computed: do not claim them.
Reply with JSON only, exactly this shape: {template("candidate_analysis")}"""


def candidate_analyses(camp: Campaign) -> dict:
    """Muse Spark Open reviews each passed candidate, in parallel; a failed call only leaves it without a review."""
    from concurrent.futures import ThreadPoolExecutor

    from autolab.llm.client import BudgetExceeded, LLMError

    client = getattr(camp.agent, "analyst", None)
    eligible = sorted(camp.passed(), key=ranking_key)
    todo = [c for c in eligible if not c.get("analysis")][:config.CATHODE_REVIEW_MAX]
    out = {"provider": getattr(client, "provider", None), "analysed": [], "failed": {}, "skipped": None}
    if client is None or not todo:
        out["skipped"] = "no analyst model" if client is None else "no passed candidate to review"
        out["summary"] = {"skipped": out["skipped"]}
        return out
    comps = comparisons(eligible)

    def review(c: dict):
        mine = [s for s in comps if c["id"] in json.dumps(s)]
        user = {"goal": camp.goal, "candidate": {k: c.get(k) for k in REVIEW_FIELDS if k in c}, "comparisons": mine}
        try:
            obj, replies = client.complete_json([{"role": "system", "content": review_system()},
                                                 {"role": "user", "content": json.dumps(user)}], "candidate_analysis",
                                                max_output_tokens=config.CANDIDATE_ANALYSIS_MAX_OUTPUT_TOKENS)
        except (BudgetExceeded, LLMError) as e:
            return c, None, f"{type(e).__name__}: {e}"
        return c, {**obj, "cost_usd": round(sum(r.cost_usd for r in replies), 5)}, None

    with ThreadPoolExecutor(max_workers=config.CANDIDATE_ANALYSIS_WORKERS) as pool:
        for c, analysis, error in pool.map(review, todo):
            if analysis is None:
                out["failed"][c["id"]] = error
                continue
            c["analysis"] = {k: analysis[k] for k in ("strengths", "risks", "md_priority", "summary")}
            out["analysed"].append(c["id"])
            camp.emit("candidate_analyses", "done", c["id"], formula=c["formula"], provider=client.provider, **analysis)
    if out["failed"]:
        out["stopped"] = f"{len(out['failed'])} review call(s) failed (no retry)"
    out["summary"] = {"provider": client.provider, "analysed": len(out["analysed"]), "failed": list(out["failed"])}
    return out


def render_candidate_analyses(out: dict, result: dict) -> list[str]:
    lines = ["## Independent reviews", ""]
    if out.get("skipped"):
        return lines + [f"Not run: {out['skipped']}.", ""]
    pool = _pool(result)
    for cid in out.get("analysed", []):
        a = pool[cid].get("analysis") or {}
        lines.append(f"- **{pool[cid].get('formula')}** (priority {a.get('md_priority')}): {a.get('summary')}")
    return lines + [""]


def ranking_key(c: dict):
    order = {v: i for i, v in enumerate(config.MEMRISTOR_RANK_ORDER)}
    return (order.get(c.get("barrier_vs_parent") or "not_computed", len(order)),
            c.get("barrier_eV") if c.get("barrier_eV") is not None else 99.0, *rank_key(c))


def ranking(camp: Campaign) -> dict:
    """Passed candidates by barrier verdict against the parent (config.MEMRISTOR_RANK_ORDER), then barrier, then
    E_hull per substitution; each E_hull with its UMA-vs-DFT error bar when the references are cached."""
    ranked = sorted(camp.passed(), key=ranking_key)
    errors, error_bar = {}, getattr(getattr(camp.agent, "tools", None), "ehull_error", None)
    for c in ranked:
        f = c.get("formula")
        if f not in errors:
            try:
                errors[f] = error_bar(f) if error_bar and f else None
            except Exception:  # references not in the cache: the E_hull stays, without its error bar
                errors[f] = None
        e = errors[f]
        c["e_hull_error"] = e if e and e.get("available", True) else None
    out = {"ranking": [c["id"] for c in ranked], "finalists": [c["id"] for c in ranked[:config.FINALISTS_MAX]],
           "excluded": {}, "order": list(config.MEMRISTOR_RANK_ORDER)}
    out["summary"] = {"finalists": out["finalists"],
                      "levels": [camp.by_id[i].get("barrier_vs_parent") or "not_computed" for i in out["finalists"]]}
    return out


def render_ranking(out: dict, result: dict) -> list[str]:
    pool = _pool(result)
    lines = ["## Final ranking", "", f"Order: oxygen-vacancy barrier against the parent ({' > '.join(out.get('order', []))}"
             "), then barrier, then E_hull per substitution. A lower barrier suggests easier switching, at a possible "
             "cost in retention (not computed). Candidates are computational predictions, not proven materials.", ""]
    if not out["ranking"]:
        return lines + ["No candidate passed all filters.", ""]
    for i, cid in enumerate(out["ranking"], 1):
        c = pool[cid]
        star = " **finalist**" if cid in out["finalists"] else ""
        err = c.get("e_hull_error")
        pm = f" (E_hull error bar ± {err['mae_eV_per_atom']:.3f} eV/atom)" if err else ""
        lines.append(f"{i}. {cid} {c['formula']}{star}: {_numbers(c)}{pm}")
    return lines + [""]


def novelty(camp: Campaign) -> dict:
    """Literature check of the finalists (web search, Muse Spark), a known memristor oxide first as a control."""
    from autolab.agent.novelty import novelty_check
    from autolab.store.cache import JsonCache

    finalists = camp.outputs.get("ranking", {}).get("finalists") or []
    client = getattr(camp.agent, "novelty_client", None)
    if not finalists or client is None:
        reason = "no finalist" if not finalists else "no web-search client (novelty check disabled)"
        return {"control": None, "candidates": [], "stopped": None, "skipped": reason, "summary": {"skipped": reason}}
    by_id = camp.by_id
    res = novelty_check([{**by_id[i], "kind": "memristor"} for i in finalists], client,
                        control=config.MEMRISTOR_NOVELTY_CONTROL, cache=JsonCache(config.CACHE_DIR / "novelty"))
    for r in res["candidates"]:
        by_id[r["id"]]["novelty"] = r["level"]
    res["summary"] = {"control_ok": (res.get("control") or {}).get("control_ok"),
                      "levels": {r["id"]: r["level"] for r in res["candidates"]}, "stopped": res.get("stopped")}
    return res


def render_novelty(out: dict, result: dict) -> list[str]:
    if out.get("skipped"):
        return ["## Novelty check", "", f"Not run: {out['skipped']}.", ""]
    from autolab.agent.novelty import render

    return [render(out), ""]


METHODS = [
    ("Candidate proposals and decisions", "Meta Muse Spark (reasoning model), with comparisons computed by the code"),
    ("Structure relaxation and energies", "Meta FAIR UMA (uma-s-1p2, OMat head), atoms and cell relaxed, MP2020 "
                                         "corrections for the hull; references from Materials Project relaxed with UMA"),
    ("Thermodynamic stability", "energy above the convex hull of the stable known phases of the system; kept if <= "
                                f"{config.MEMRISTOR_EHULL_MAX} eV/atom"),
    ("Electronic band gap", f"recorded prediction (optB88vdW scale); kept if >= {config.MEMRISTOR_BANDGAP_MIN} eV"),
    ("Oxygen-vacancy migration barrier", f"nudged elastic band with climbing image ({config.NEB_IMAGES} images, forces "
                                         f"below {config.NEB_FMAX} eV/A) with UMA, neutral vacancy in a supercell of at "
                                         f"least {config.NEB_MIN_LENGTH:g} A; the lowest of the {config.NEB_MAX_HOPS} "
                                         "distinct hops next to the dopant, against the parent's lowest hop; checked "
                                         "on CeO2 (fast) and MgO (slow) before use"),
    ("Independent reviews", "Meta Muse Spark Open, one review per passed candidate, in parallel"),
    ("Literature check", "Meta Muse Spark with web search; a known memristor oxide (Hf0.5Zr0.5O2) checked first as a control"),
    ("Error-driven loop", "each round's failures, with their numbers, go back to the proposing model, which explains "
                          "them as hypotheses and corrects its next proposals"),
    ("Plain-language summaries", "Meta Muse Glimmer"),
]

REPORT_SYSTEM = """You write the final report of a computational search for doped oxides for valence-change memristors (the resistive memories of neuromorphic chips), for scientists and for readers who are not specialists. The code gives you the comparison table of the finalists (the first one is the champion), the candidates rejected with their reasons, and what was not computed.
Rules:
- Use only the numbers of the table, quoted exactly with their units; never invent or estimate a value. A missing value was not computed: say so.
- The energy above the hull comes with its error bar when given (e_hull_error_eV_per_atom): quote it with the value.
- The migration barrier is that of a neutral oxygen vacancy on single hops next to the dopant (NEB with UMA), compared with the parent's lowest hop: use barrier_vs_parent as decided by the code; "comparable" means the difference is within barrier_tolerance_eV, never call it an improvement. A lower barrier suggests easier switching (lower forming and switching voltages) and may cost retention: say both, never claim better switching, retention or endurance as measured.
- champion_reasons: why the champion is preferred, each reason tied to numbers of the table.
- novelty (when given): "published", "related" or "none_found" (this search found nothing; never "new to science").
- tradeoffs and uncertainties: UMA instead of DFT, neutral vacancy only, single hops, no electric field, crystalline cells instead of amorphous films.
- validation: calculations or experiments to confirm it (e.g. DFT NEB with charged vacancies, device fabrication and switching tests), each with "basis": "documented" or "hypothesis". synthesis: routes, "documented" only for well-established ones (atomic layer deposition of doped HfO2, sputtering), else "hypothesis".
- limitations: properties not studied. The candidates are computational predictions, not proven materials.
- Write readable prose, units written normally (eV, eV/atom). Do not name AI models or providers. Plain English, short sentences.
Reply with JSON only, exactly this shape: {template}"""


def report(camp: Campaign) -> dict:
    from autolab.agent.loop import LoopStopped
    from autolab.domains.electrolyte import _rounded, _structure_info

    rk = camp.outputs.get("ranking", {})
    finalists = rk.get("finalists") or []
    if not finalists:
        return {"skipped": "no finalist", "summary": {"skipped": "no finalist"}}
    by_id = camp.by_id

    def row(c):
        return {"id": c["id"], "formula": c["formula"], "parent": c.get("parent_formula") or c.get("parent"),
                "substitution": c.get("substitution"), **_structure_info(c),
                "e_hull_eV_per_atom": c.get("e_hull"), "e_hull_per_substitution_eV": c.get("e_hull_per_substitution"),
                "e_hull_error_eV_per_atom": (c.get("e_hull_error") or {}).get("mae_eV_per_atom"),
                "decomposition": c.get("decomposition"), "gap_optb88_eV": c.get("gap_optb88"), "gap_mbj_eV": c.get("gap_mbj"),
                "barrier_eV": c.get("barrier_eV"), "parent_barrier_eV": c.get("parent_barrier_eV"),
                "barrier_vs_parent": c.get("barrier_vs_parent"), "barrier_difference_eV": c.get("barrier_difference_eV"),
                "barrier_tolerance_eV": config.MEMRISTOR_EA_SIGNIFICANT_EV,
                "barrier_profile_eV": c.get("barrier_profile_eV"), "parent_barrier_profile_eV": c.get("parent_barrier_profile_eV"),
                "novelty": c.get("novelty"), "review": c.get("analysis")}

    rows = [_rounded(row(by_id[i])) for i in finalists]
    rejected = {c["id"]: f"{c.get('formula')}: {c.get('rejected_at')}: {c.get('reason')}" for c in camp.candidates
                if c.get("status") == "rejected"}
    out = {"completeness": "complete", "missing_steps": [], "champion": rows[0]["id"], "finalists": rows,
           "excluded": rejected, "methods": [{"step": a, "method": b} for a, b in METHODS],
           "not_computed": config.MEMRISTOR_NOT_COMPUTED, "narrative": None}
    facts = {"goal": camp.goal, "finalists": rows, "rejected": rejected, "not_computed": out["not_computed"]}
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
    lines = ["## Final scientific report", ""]
    if n.get("executive_summary"):
        lines += ["### Executive summary", "", n["executive_summary"], ""]
    lines += ["### Comparison of the finalists", "", "| | " + " | ".join(r["formula"] for r in rows) + " |",
              "|---|" + "---|" * len(rows)]
    sub = lambda s: f"{s.get('remove')}→{s.get('add')} ×{s.get('count')}"  # noqa: E731
    fields = [("Parent oxide", lambda r: r.get("parent") or "—"), ("Substitution", lambda r: sub(r.get("substitution") or {})),
              ("Space group", lambda r: r.get("space_group") or "—"),
              ("E_hull (eV/atom)", lambda r: _n(r.get("e_hull_eV_per_atom"), ".3f") + (
                  f" ± {r['e_hull_error_eV_per_atom']:.3f}" if r.get("e_hull_error_eV_per_atom") is not None else "")),
              ("Band gap optB88 / mBJ (eV)", lambda r: f"{_n(r.get('gap_optb88_eV'), '.2f')} / {_n(r.get('gap_mbj_eV'), '.2f')}"),
              ("O-vacancy barrier (eV)", lambda r: f"{_n(r.get('barrier_eV'), '.2f')} (parent {_n(r.get('parent_barrier_eV'), '.2f')})"),
              ("Against its parent", lambda r: r.get("barrier_vs_parent") or "—"),
              ("Literature", lambda r: r.get("novelty") or "not checked")]
    for label, f in fields:
        lines.append(f"| {label} | " + " | ".join(str(f(r)) for r in rows) + " |")
    lines += ["", f"### Champion: {rows[0]['formula']}", ""]
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


def _pool(result: dict) -> dict[str, dict]:
    pool = {c["id"]: c for c in result.get("prior", [])}
    pool.update({c["id"]: c for r in result["iterations"] for c in r["candidates"]})
    return pool


def make_domain() -> Domain:
    return Domain(
        name="memristor", goal=config.MEMRISTOR_GOAL, parents=tuple(config.MEMRISTOR_PARENTS),
        make_tools=lambda: MemristorTools(not_run=[]), evaluate=evaluate, proposal_messages=proposal_messages,
        analysis_messages=analysis_messages, comparisons=comparisons, for_model=FOR_MODEL, rank_key=rank_key,
        feedback=feedback, render_feedback=render_feedback,
        iteration_stages=(Stage("migration", migration, render_migration),),
        stages=(Stage("candidate_analyses", candidate_analyses, render_candidate_analyses),
                Stage("ranking", ranking, render_ranking),
                Stage("novelty", novelty, render_novelty),
                Stage("report", report, render_report)),
        thresholds=THRESHOLDS, render_candidates=render_candidates,
        settings={"neb_max_usd": config.MEMRISTOR_NEB_MAX_USD})


register("memristor", make_domain)
