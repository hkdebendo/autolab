"""Solid electrolytes for Li-metal batteries: the funnel and the stages after the iterations (SPEC 6.1).

Iterations: proposal (model) -> Materials Project check -> UMA relaxation -> E_hull (UMA + MP2020, per
substitution) -> band gap (GapModel) -> S-S flag (agent/pipeline.py).
Error-driven loop (config.FEEDBACK_LOOP): steps 1-4 below also run inside each iteration on its own candidates
(ITERATION_MD_SELECT_MAX candidate to MD), and their results (failures with their measurements: Li-metal contact,
slower than the parent, framework moving) go back to the model before it analyses the iteration (feedback()).
After the iterations, on the passed candidates (what was already computed in an iteration is reused):
1. electrodes: window, passivation against Li metal, interfaces with config.AGENT_CATHODES (top ELECTRODES_TOP);
   non-passivating -> excluded; polysulfide products -> reduced confidence of the electrode results;
2. candidate_analyses: Muse Spark Open (Baseten) reviews each eligible candidate, in parallel;
3. md_selection: the model picks at most MD_SELECT_MAX candidates from code-computed comparisons and the reviews
   (rule fallback: best E_hull per substitution, when no model answers);
4. molecular_dynamics: Li diffusion at the validated screening settings on Modal, next to the parents;
   "lower" than the parent -> excluded for conduction (MD_EXCLUDED_VERDICTS); not launched above MD_MAX_USD_PER_RUN;
5. ranking: FINAL_RANK_MD_ORDER, then E_hull per substitution; excluded candidates last; FINALISTS_MAX finalists;
6. novelty: LGPS control first, then the finalists (web search, cap NOVELTY_COST_CAP_USD, answers cached).
Every step reads the caches (relaxations, MD, MP, band gaps, novelty answers) before computing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from autolab import config
from autolab.agent.compare import comparisons
from autolab.agent.pipeline import Tools, evaluate_candidate
from autolab.domains import Campaign, Domain, Stage, register
from autolab.llm import prompts

FOR_MODEL = ("id", "parent", "substitution", "formula", "status", "rejected_at", "reason", "arrangements",
             "converged", "energy_spread_meV", "n_atoms", "n_modified", "e_hull", "e_hull_per_substitution",
             "decomposition", "decomposition_polysulfides", "reduced_confidence", "known_in_mp", "gap_optb88",
             "gap_mbj", "gap_low_confidence", "ss_bonds", "passivation", "md_verdict", "D_ratio_to_parent",
             "D_ratio_err", "excluded_at", "exclusion_reason")

FOR_SELECTION = ("id", "parent", "parent_formula", "substitution", "formula", "e_hull", "e_hull_per_substitution",
                 "reduced_confidence", "decomposition_polysulfides", "gap_optb88", "ss_bonds", "window", "passivation",
                 "passivation_reaction_energy", "interface_reaction_energy", "electrodes_reduced_confidence",
                 "electrodes_polysulfides", "md_cached", "analysis")

THRESHOLDS = ("CANDIDATE_ANALYSIS_PROVIDER", "CANDIDATE_ANALYSIS_MAX", "EHULL_SYNTHESIZABLE", "BANDGAP_MIN", "ELECTRODES_TOP", "AGENT_CATHODES", "ELECTRODE_EXCLUDED_PASSIVATION",
              "MD_SELECT_MAX", "MD_SCREEN_TEMPERATURE_K", "MD_SCREEN_PS", "MD_SCREEN_SEEDS", "MD_TIE_SIGMA",
              "MD_EXCLUDED_VERDICTS", "MD_MAX_USD_PER_RUN", "FINAL_RANK_MD_ORDER", "FINALISTS_MAX",
              "NOVELTY_COST_CAP_USD", "FEEDBACK_LOOP", "ITERATION_MD_SELECT_MAX", "MD_FRAMEWORK_D_RATIO_MAX")


# --- default tools (expensive or networked; tests replace them) ---------------

def _window_passivation(c: dict, budget) -> dict:
    from autolab.agent.electrochem import window_and_passivation

    return window_and_passivation(c, budget=budget)


def _interface(c: dict, cathode: str, budget) -> dict:
    from autolab.agent.electrochem import uma_interface

    return uma_interface(c, cathode, budget=budget)


def _interface_calibration(cathode: str, budget) -> dict:
    from autolab.agent.electrochem import interface_calibration

    return interface_calibration(cathode, budget=budget)


def _md_jobs(cands: list[dict]) -> list[dict]:
    """Parents then candidates, each with the GPU of its runs: those cached on the legacy A10G are read from it, the
    others run on config.MODAL_MD_GPU (same D on both: dynamics.with_md_gpu)."""
    from autolab.agent.dynamics import candidate_job, parent_job, with_md_gpu

    return with_md_gpu([parent_job(p) for p in sorted({c["parent"] for c in cands})] + [candidate_job(c) for c in cands])


def _md_cached(c: dict) -> bool:
    from autolab.agent.dynamics import candidate_job, md_runs_to_compute, with_md_gpu

    return not md_runs_to_compute(with_md_gpu([candidate_job(c)]))


def _md_plan(cands: list[dict]) -> dict:
    """Runs missing from the MD cache (candidates and their parents) and their estimated Modal cost."""
    from autolab.agent.dynamics import md_runs_to_compute, modal_md_plan

    jobs = _md_jobs(cands)
    todo = md_runs_to_compute(jobs)
    plan = modal_md_plan(todo) if todo else {"gpu": config.MODAL_MD_GPU, "runs": 0, "seconds": [], "timeout_s": 0,
                                             "wall_s": 0, "usd": 0.0, "usd_max": 0.0}
    return {**plan, "total_runs": len(jobs) * config.MD_SCREEN_SEEDS}


def _md_screen(cands: list[dict], plan: dict) -> list[dict]:
    """Screening at the validated settings, all missing runs in parallel on Modal, each cached when it ends."""
    from autolab.agent.dynamics import md_screen, md_verdicts
    from autolab.sim.backend import ModalBackend

    backend = None
    if config.SIM_BACKEND == "modal" and plan["runs"]:
        backend = ModalBackend(md_timeout_s=plan["timeout_s"])
    jobs = _md_jobs(cands)  # the limit applies to the runs to compute (plan), cached runs are free
    return md_verdicts(md_screen(jobs, backend=backend, max_runs=len(jobs) * config.MD_SCREEN_SEEDS))


def _conductivity(cands: list[dict]) -> dict:
    from autolab.agent.conductivity import candidates_conductivity

    return candidates_conductivity(cands)


def _ehull_error(formula: str) -> dict | None:
    from autolab.analysis.uma_errors import ehull_uncertainty

    return ehull_uncertainty(formula)


def _novelty(cands: list[dict], client) -> dict:
    from autolab.agent.novelty import novelty_check
    from autolab.store.cache import JsonCache

    return novelty_check(cands, client, cache=JsonCache(config.CACHE_DIR / "novelty"))


@dataclass
class ElectrolyteTools(Tools):
    """Funnel tools plus those of the stages after the iterations."""

    window_passivation: Callable = _window_passivation  # (candidate, budget) -> window_and_passivation dict
    interface: Callable = _interface  # (candidate, cathode, budget) -> uma_interface dict
    interface_calibration: Callable = _interface_calibration  # (cathode, budget) -> interface_calibration dict
    md_cached: Callable = _md_cached  # (candidate) -> True if all its MD runs are cached
    md_plan: Callable = _md_plan  # (candidates) -> runs to compute and estimated cost
    md_screen: Callable = _md_screen  # (candidates, plan) -> md_verdicts rows (parents included)
    novelty: Callable = _novelty  # (candidates, client) -> novelty_check dict
    ehull_error: Callable = _ehull_error  # (formula) -> UMA-vs-DFT error bar of its system (analysis.uma_errors)
    conductivity: Callable = _conductivity  # (candidates) -> conductivity at 300 K from the cached MD (no computation)


# --- stages -------------------------------------------------------------------

def rank_key(c: dict):
    return (c["e_hull_per_substitution"], c["e_hull"])


def exclude(c: dict, step: str, reason: str) -> None:
    """A passed candidate excluded by a later stage stays in the pool and in the report, with its reason."""
    c["excluded_at"], c["exclusion_reason"] = step, reason


def electrodes(camp: Campaign) -> dict:
    """Window and passivation, then the cathode interfaces of the candidates still kept. A computation that would
    exceed the relaxation budget is skipped (reported) and the stage goes on with the next candidate."""
    from autolab.sim.backend import BudgetExceeded

    t = camp.tools
    top = sorted(camp.passed(), key=rank_key)[:config.ELECTRODES_TOP]
    out = {"cathodes": list(config.AGENT_CATHODES), "calibrations": {}, "candidates": [], "excluded": [],
           "not_computed": {}, "stopped": None}
    memo = getattr(camp.agent, "electrode_calibrations", None)  # computed once per research, reused by each iteration
    if memo is None:
        memo = {}
        try:
            camp.agent.electrode_calibrations = memo
        except AttributeError:
            pass
    try:
        for cathode in config.AGENT_CATHODES:
            if cathode in memo:
                out["calibrations"][cathode] = memo[cathode]
                continue
            cal = t.interface_calibration(cathode, camp.budget)
            out["calibrations"][cathode] = {k: cal.get(k) for k in ("electrolyte", "cathode", "diff", "ok", "tolerance")}
            out["calibrations"][cathode].update(uma=cal["uma"]["min_reaction_energy"], mp=cal["mp"]["min_reaction_energy"])
            memo[cathode] = out["calibrations"][cathode]
            camp.emit("electrodes", "calibration", **out["calibrations"][cathode])
    except BudgetExceeded as e:
        out["stopped"] = f"relaxation budget (calibration): {e}"
        out["summary"] = {"computed": 0, "stopped": out["stopped"]}
        return out
    for c in top:
        if c.get("electrodes_done"):  # computed in an iteration of this research: reused as is
            out["candidates"].append(c["id"])
            if c.get("excluded_at") == "electrodes":
                out["excluded"].append(c["id"])
            continue
        try:
            wp = t.window_passivation(c, camp.budget)
        except BudgetExceeded as e:
            out["not_computed"][c["id"]] = f"window and passivation: {e}"
            continue
        w, p = wp["window"], wp["passivation"]
        # reduced confidence: polysulfides in the decomposition of the electrolyte only (window, Li metal), and for
        # the window only when its limits move by more than WINDOW_SENSITIVITY_MAX_V once the polysulfide energies are
        # shifted by their measured UMA error (window_sensitivity); those of the cathode reaction (FeS2 for almost
        # every sulfide) are information
        sens = w.get("sensitivity")
        window_polys = set(w.get("polysulfide_products") or [])
        robust = bool(window_polys) and sens is not None and sens["robust"]
        polys = (set() if robust else window_polys) | set(p.get("polysulfide_products") or [])
        c.update(window={k: w.get(k) for k in ("v_low", "v_high", "stable", "reduction_products",
                                               "oxidation_products", "sensitivity")},
                 window_polysulfides=sorted(window_polys), window_robust=robust if window_polys else None,
                 passivation=p["verdict"],
                 passivation_reaction_energy=p["reaction_energy"], passivation_products=p["products"],
                 metallic_products=p["metallic_products"])
        if p["verdict"] in config.ELECTRODE_EXCLUDED_PASSIVATION:  # excluded: no interface computed
            exclude(c, "electrodes", f"{p['verdict']} against Li metal (metallic products "
                                     f"{', '.join(p['metallic_products']) or 'none'}, reaction "
                                     f"{p['reaction_energy']:.3f} eV/atom)")
            out["excluded"].append(c["id"])
        interfaces = {}
        for cathode in config.AGENT_CATHODES:
            if c.get("excluded_at") or not out["calibrations"][cathode]["ok"]:
                interfaces[cathode] = None  # excluded, or UMA not trusted for this cathode
                continue
            try:
                r = t.interface(c, cathode, camp.budget)
            except BudgetExceeded as e:
                interfaces[cathode] = None
                out["not_computed"][c["id"]] = f"interface with {cathode}: {e}"
                continue
            interfaces[cathode] = {k: r.get(k) for k in ("min_reaction_energy", "mixing_ratio", "reaction",
                                                         "polysulfide_products")}
        energies = [r["min_reaction_energy"] for r in interfaces.values() if r]
        c.update(interfaces=interfaces, interface_reaction_energy=min(energies) if energies else None,
                 interface_polysulfides=sorted({x for r in interfaces.values() if r
                                                for x in r.get("polysulfide_products") or []}),
                 electrodes_polysulfides=sorted(polys), electrodes_reduced_confidence=bool(polys),
                 electrodes_done=True)
        out["candidates"].append(c["id"])
        camp.emit("electrodes", "done", c["id"], formula=c["formula"], window=c["window"], passivation=p["verdict"],
                  interface_reaction_energy=c["interface_reaction_energy"],
                  reduced_confidence=c["electrodes_reduced_confidence"], excluded=c.get("excluded_at") == "electrodes")
    if out["not_computed"]:
        out["stopped"] = f"relaxation budget: {len(out['not_computed'])} computation(s) skipped"
    out["summary"] = {"computed": len(out["candidates"]), "excluded": out["excluded"],
                      "not_computed": list(out["not_computed"]), "stopped": out["stopped"]}
    return out


ANALYSIS_FIELDS = tuple(k for k in FOR_SELECTION if k not in ("md_cached", "analysis"))


def candidate_analyses(camp: Campaign) -> dict:
    """Muse Spark Open (Baseten) reviews each eligible candidate, all in parallel: strengths, risks, MD priority.
    A failed or over-budget call only leaves that candidate without a review."""
    from concurrent.futures import ThreadPoolExecutor

    from autolab.llm.client import BudgetExceeded, LLMError

    client = getattr(camp.agent, "analyst", None)
    eligible = sorted((c for c in camp.passed() if not c.get("excluded_at")), key=rank_key)
    reused = [c["id"] for c in eligible if c.get("analysis")]  # reviewed in an earlier run: not paid twice
    todo = [c for c in eligible if not c.get("analysis")][:config.CANDIDATE_ANALYSIS_MAX]
    out = {"provider": getattr(client, "provider", None), "analysed": [], "reused": reused, "failed": {},
           "skipped": None}
    if client is None or not todo:
        out["skipped"] = "no analyst model" if client is None else "no new eligible candidate"
        out["summary"] = {"skipped": out["skipped"]}
        return out
    comps = comparisons(eligible)

    def review(c: dict):
        mine = [s for s in comps if c["id"] in json.dumps(s)]
        view = {k: c.get(k) for k in ANALYSIS_FIELDS if k in c}
        try:
            obj, replies = client.complete_json(prompts.candidate_analysis_messages(camp.goal, view, mine),
                                                "candidate_analysis",
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
        out["stopped"] = f"{len(out['failed'])} analysis call(s) failed (no retry)"
    out["summary"] = {"provider": client.provider, "analysed": len(out["analysed"]), "reused": len(reused),
                      "failed": list(out["failed"])}
    return out


def md_selection(camp: Campaign) -> dict:
    """The model chooses among the eligible candidates not simulated yet: those already in the MD cache get their
    verdict anyway (molecular_dynamics stage), so choosing them would waste the choice."""
    from autolab.agent.loop import LoopStopped

    eligible = sorted((c for c in camp.passed() if not c.get("excluded_at")), key=rank_key)
    n = camp.settings.get("md_select_max", config.MD_SELECT_MAX)
    out = {"eligible": [c["id"] for c in eligible], "choices": [], "selected": [], "ignored": [], "chosen_by": None,
           "rationale": None, "llm": None}
    for c in eligible:
        c["md_cached"] = bool(camp.tools.md_cached(c))
    choices = [c for c in eligible if not c["md_cached"]]
    out["choices"] = [c["id"] for c in choices]
    if not choices or n <= 0:
        reason = ("no eligible candidate" if not eligible else "every eligible candidate is already simulated"
                  if not choices else "candidates were chosen for molecular dynamics in each iteration")
        out["summary"] = {"selected": [], "reason": reason}
        return out
    view = [{k: c.get(k) for k in FOR_SELECTION if k in c and k != "md_cached"} for c in choices]
    ids = [c["id"] for c in choices]
    try:
        info = camp.ask(prompts.md_selection_messages(camp.goal, view, comparisons(eligible), n),
                        "md_selection", "md_selection")
        reply = info["reply"]
        out["llm"] = {k: v for k, v in info.items() if k != "reply"}
        out["selected"] = list(dict.fromkeys(i for i in reply["selected"] if i in ids))[:n]
        out["ignored"] = [i for i in reply["selected"] if i not in ids]
        out["chosen_by"], out["rationale"] = info["provider"], reply["rationale"]
    except LoopStopped as e:
        out["rationale"] = f"language model unavailable ({e})"
    if not out["selected"]:  # rule: best E_hull per substitution
        out["selected"], out["chosen_by"] = ids[:n], "rule (lowest E_hull per substitution)"
    for c in eligible:
        c["md_selected"] = c["id"] in out["selected"]
    out["summary"] = {"selected": out["selected"], "chosen_by": out["chosen_by"], "ignored": out["ignored"]}
    return out


def molecular_dynamics(camp: Campaign) -> dict:
    """The selected candidates, plus every eligible candidate whose MD is already in the cache (free: its verdict
    is known, e.g. a framework that moves). Only the selected ones can cost GPU time."""
    choice = camp.outputs.get("md_selection", {})
    sel = choice.get("selected") or []
    by_id = camp.by_id
    from_cache = [i for i in choice.get("eligible") or [] if i not in sel and by_id[i].get("md_cached")]
    out = {"rows": [], "plan": None, "excluded": [], "from_cache": from_cache, "stopped": None}
    if not sel and not from_cache:
        out["summary"] = {"reason": "no candidate selected"}
        return out
    cands = [by_id[i] for i in sel + from_cache]
    plan = camp.tools.md_plan(cands)
    out["plan"] = {k: plan.get(k) for k in ("gpu", "runs", "total_runs", "wall_s", "usd", "usd_max", "timeout_s")}
    camp.emit("molecular_dynamics", "plan", **out["plan"])
    spent = getattr(camp.agent, "md_usd", 0.0)  # MD already launched in this research (earlier iterations)
    if spent + plan["usd"] > config.MD_MAX_USD_PER_RUN:
        out["stopped"] = (f"estimated Modal cost {plan['usd']:.2f} $ (plus {spent:.2f} $ already launched in this "
                          f"research) above MD_MAX_USD_PER_RUN ({config.MD_MAX_USD_PER_RUN:g} $): not launched")
    elif plan["runs"] > config.MD_SCREEN_MAX_RUNS:
        out["stopped"] = f"{plan['runs']} MD runs to compute, above MD_SCREEN_MAX_RUNS ({config.MD_SCREEN_MAX_RUNS}): not launched"
    if out["stopped"]:
        out["summary"] = {"stopped": out["stopped"]}
        return out
    if plan["usd"] and hasattr(camp.agent, "md_usd"):
        camp.agent.md_usd = spent + plan["usd"]
    rows = camp.tools.md_screen(cands, plan)
    out["rows"] = [{k: v for k, v in r.items() if k not in ("D_blocks_cm2_per_s",)} for r in rows]
    for r in rows:
        c = by_id.get(r["id"]) if r.get("kind") == "candidate" else None
        if c is None:
            continue
        v = r.get("vs_parent")
        c.update(D_cm2_per_s=r["D_cm2_per_s"], D_sem_cm2_per_s=r["D_sem_cm2_per_s"],
                 D_ratio_to_parent=v["ratio"] if v else None, D_ratio_err=v["ratio_err"] if v else None,
                 md_verdict=v["verdict"] if v else "undetermined", conduction=r["conduction"],
                 md_framework_intact=(r.get("framework") or {}).get("intact"),
                 md_framework=framework_view(r.get("framework")), md_gpu=r.get("md_gpu"))
        if r["conduction"] == "excluded":
            exclude(c, "molecular_dynamics", r["conduction_reason"])
            out["excluded"].append(c["id"])
        camp.emit("molecular_dynamics", "done", c["id"], formula=c["formula"], D_cm2_per_s=c["D_cm2_per_s"],
                  ratio=c["D_ratio_to_parent"], verdict=c["md_verdict"], conduction=c["conduction"])
    out["summary"] = {"verdicts": {r["id"]: (r.get("vs_parent") or {}).get("verdict") for r in rows
                                   if r.get("kind") == "candidate"}, "excluded": out["excluded"],
                      "from_cache": from_cache}
    return out


def ranking(camp: Campaign) -> dict:
    order = {v: i for i, v in enumerate(config.FINAL_RANK_MD_ORDER)}

    def key(c):
        return (bool(c.get("excluded_at")), order.get(c.get("md_verdict") or "not_run", len(order)), *rank_key(c))

    ranked = sorted(camp.passed(), key=key)
    errors = {}
    error_bar = getattr(camp.tools, "ehull_error", None)  # funnel-only tools (other domains, tests) have none
    for c in ranked:  # error bar of the E_hull: UMA vs DFT on the known compounds of its system (cached per system)
        f = c["formula"]
        if f not in errors:
            errors[f] = error_bar(f) if error_bar else None
        c["e_hull_error"] = errors[f] if errors[f] and errors[f].get("available", True) else None
    kept = [c["id"] for c in ranked if not c.get("excluded_at")]
    out = {"ranking": [c["id"] for c in ranked], "kept": kept, "finalists": kept[:config.FINALISTS_MAX],
           "excluded": {c["id"]: f"{c['excluded_at']}: {c['exclusion_reason']}" for c in ranked if c.get("excluded_at")}}
    out["summary"] = {"finalists": out["finalists"], "excluded": list(out["excluded"])}
    return out


def conductivity(camp: Campaign) -> dict:
    """Ionic conductivity at 300 K of the simulated candidates and their parents, from the MD runs in the cache:
    Arrhenius fit extrapolated to 300 K, then Nernst-Einstein (agent/conductivity.py). Never computes: candidates
    with one temperature get an estimate with their parent's activation energy, labelled so."""
    tool = getattr(camp.tools, "conductivity", None)
    simulated = [c for c in camp.passed() if c.get("md_verdict")]
    if tool is None or not simulated:
        reason = "no simulated candidate" if tool else "no conductivity tool"
        return {"skipped": reason, "summary": {"skipped": reason}}
    res = tool(simulated)
    for cid, r in res["candidates"].items():
        camp.by_id[cid]["conductivity"] = _rounded(r)
    out = {"parents": _rounded(res["parents"]), "candidates": list(res["candidates"]),
           "temperature_K": config.CONDUCTIVITY_T_K}
    out["summary"] = {"computed": len(res["candidates"]), "parents": {k: round(v["sigma_mS_cm"], 3)
                                                                       for k, v in res["parents"].items()}}
    return out


def render_conductivity(out: dict, result: dict) -> list[str]:
    lines = [f"## Ionic conductivity at {config.CONDUCTIVITY_T_K} K (estimate)", ""]
    if out.get("skipped"):
        return lines + [f"Not computed: {out['skipped']}.", ""]
    by_id = _pool(result)
    lines += ["Arrhenius fit of the diffusion coefficients of the molecular dynamics (runs up to "
              f"{config.CONDUCTIVITY_FIT_T_MAX_K} K), extrapolated to {config.CONDUCTIVITY_T_K} K, then the "
              "Nernst-Einstein relation (tracer diffusion, Haven ratio 1). The range is one standard error of the "
              "extrapolation: an order of magnitude, not a measurement.", "",
              "| Structure | σ at 300 K (mS/cm) | Range (mS/cm) | Activation energy (eV) | Method |", "|---|---|---|---|---|"]
    rows = [(f"parent {pid}", r) for pid, r in out["parents"].items()]
    rows += [(f"{cid} {by_id[cid]['formula']}", by_id[cid]["conductivity"]) for cid in out["candidates"]]
    for name, r in rows:
        lines.append(f"| {name} | {r['sigma_mS_cm']:.3g} | {r['sigma_low_mS_cm']:.2g}–{r['sigma_high_mS_cm']:.2g} | "
                     f"{r['Ea_eV']:.2f} ± {r['Ea_err_eV']:.2f} | {r['method']} |")
    return lines + [""]


def novelty(camp: Campaign) -> dict:
    finalists = camp.outputs.get("ranking", {}).get("finalists") or []
    client = getattr(camp.agent, "novelty_client", None)
    if not finalists or client is None:
        reason = "no finalist" if not finalists else "no web-search client (novelty check disabled)"
        return {"control": None, "candidates": [], "stopped": None, "skipped": reason, "summary": {"skipped": reason}}
    by_id = camp.by_id
    res = camp.tools.novelty([by_id[i] for i in finalists], client)
    for r in res["candidates"]:
        by_id[r["id"]]["novelty"] = r["level"]
    res["summary"] = {"control_ok": (res.get("control") or {}).get("control_ok"),
                      "levels": {r["id"]: r["level"] for r in res["candidates"]}, "stopped": res.get("stopped")}
    return res


# --- feedback of the slow tests (error-driven loop) ------------------------------------------------------------

def framework_view(framework: dict | None) -> dict | None:
    """Per non-Li element, the largest D ratio to Li and final MSD over the seeds (the measurements behind
    "framework moved"), for the model and the report."""
    if not framework:
        return None
    els: dict[str, dict] = {}
    for check in framework.get("per_seed") or [framework]:
        for el, v in (check.get("elements") or {}).items():
            e = els.setdefault(el, {"D_ratio_to_Li": None, "msd_final_A2": None})
            for k in e:
                if v.get(k) is not None and (e[k] is None or v[k] > e[k]):
                    e[k] = round(v[k], 4)
    return {"intact": framework.get("intact"), "limit_D_ratio_to_Li": config.MD_FRAMEWORK_D_RATIO_MAX, "elements": els}


def feedback(cands: list[dict]) -> list[dict]:
    """Results of the slow tests of one iteration, measured by the code: contact with Li metal (failures only) and
    Li diffusion (every simulated candidate). Each item: what was tested, outcome, the measurements and a factual
    message; the cause of a failure is left to the model, as a hypothesis."""
    out = []
    for c in cands:
        if c.get("status") != "passed":
            continue
        base = {"id": c["id"], "formula": c["formula"], "parent": c.get("parent"), "substitution": c.get("substitution")}
        if c.get("excluded_at") == "electrodes":
            out.append({**base, "test": "contact with Li metal", "outcome": "failed", "reason": c["exclusion_reason"],
                        "measured": {"passivation": c.get("passivation"),
                                     "reaction_energy_eV_per_atom": c.get("passivation_reaction_energy"),
                                     "products_with_Li": c.get("passivation_products"),
                                     "metallic_products": c.get("metallic_products")},
                        "message": f"Negative result: {c['formula']} ({c['id']}) failed the contact test with Li metal: "
                                   f"{c['exclusion_reason']}."})
        if c.get("md_verdict") is None:
            continue
        failed = c.get("excluded_at") == "molecular_dynamics"
        ratio = (f"D/D(parent) = {c['D_ratio_to_parent']:.2f} ± {c['D_ratio_err']:.2f}"
                 if c.get("D_ratio_to_parent") is not None else "D/D(parent) undetermined")
        reason = c["exclusion_reason"] if failed else f"{c['md_verdict']} with its parent ({ratio})"
        test = f"Li diffusion at {config.MD_SCREEN_TEMPERATURE_K} K (molecular dynamics, against its parent)"
        out.append({**base, "test": test, "outcome": "failed" if failed else "passed", "reason": reason,
                    "measured": {"D_cm2_per_s": c.get("D_cm2_per_s"), "D_error_cm2_per_s": c.get("D_sem_cm2_per_s"),
                                 "D_ratio_to_parent": c.get("D_ratio_to_parent"), "D_ratio_error": c.get("D_ratio_err"),
                                 "verdict": c.get("md_verdict"), "framework": c.get("md_framework")},
                    "message": (f"Negative result: {c['formula']} ({c['id']}) failed the {test}: {reason}." if failed
                                else f"Result: {c['formula']} ({c['id']}) passed the {test}: {reason}.")})
    return out


def render_feedback(record: dict) -> list[str]:
    """Report lines of the slow tests of one iteration and of the model's reading of the failures."""
    fb = record.get("feedback") or []
    fa = ((record.get("analysis") or {}).get("reply") or {}).get("failure_analysis") or []
    if not fb and not fa:
        return []
    lines = ["**Slow tests of this iteration (fed back to the model):**", ""]
    lines += [f"- {f['message']}" for f in fb] or ["- none"]
    if fa:
        lines += ["", "**The model's reading of the failures (hypotheses, not measurements):**", ""]
        lines += [f"- {x.get('id')}: hypothesis: {x.get('hypothesis')} — correction: {x.get('correction')}" for x in fa]
    return lines + [""]


# --- report sections -----------------------------------------------------------

def _v(x, fmt=".2f") -> str:
    return "—" if x is None else format(x, fmt)


def render_electrodes(out: dict, result: dict) -> list[str]:
    by_id = _pool(result)
    lines = ["## Electrodes (UMA + MP2020 energies)", ""]
    for cal in out["calibrations"].values():
        lines.append(f"- Calibration Li3PS4 / {cal['cathode']}: UMA {cal['uma']:.3f} vs MP {cal['mp']:.3f} eV/atom "
                     f"(diff {cal['diff']:+.3f}, tolerance {cal['tolerance']}) → "
                     f"{'trusted' if cal['ok'] else 'NOT trusted: interfaces not computed'}")
    if out["candidates"]:
        lines += ["", f"| Candidate | Formula | Window (V) | Against Li metal | Worst reaction with "
                      f"{', '.join(out['cathodes'])} (eV/atom) | Confidence | Decision |", "|---|---|---|---|---|---|---|"]
        for cid in out["candidates"]:
            c = by_id[cid]
            w = c["window"]
            window = f"{_v(w['v_low'])}–{_v(w['v_high'])}" if w["stable"] else "zero width (not a rejection)"
            sens = (w.get("sensitivity") or {}) if isinstance(w, dict) else {}
            conf = (f"reduced (electrolyte decomposes via {', '.join(c['electrodes_polysulfides'])}"
                    + (f"; window limits move by {_v(sens.get('max_shift_V'))} V when the polysulfide energies shift "
                       f"by ±{sens.get('delta_eV_per_atom')} eV/atom" if sens.get("windows") else "") + ")"
                    if c["electrodes_reduced_confidence"] else "normal")
            if c.get("window_robust"):
                conf += (f" (window via {', '.join(c['window_polysulfides'])}, robust: limits move by "
                         f"{_v(sens.get('max_shift_V'))} V for ±{sens.get('delta_eV_per_atom')} eV/atom on the "
                         f"polysulfides)")
            if c.get("interface_polysulfides"):
                conf += f"; cathode reaction forms {', '.join(c['interface_polysulfides'])} (information)"
            if c.get("interfaces") and all(v is None for v in c["interfaces"].values()) and not c.get("excluded_at"):
                conf += "; interface not computed"
            decision = f"excluded: {c['exclusion_reason']}" if c.get("excluded_at") == "electrodes" else "kept"
            lines.append(f"| {cid} | {c['formula']} | {window} | {c['passivation']} ({c['passivation_reaction_energy']:.3f}) | "
                         f"{_v(c['interface_reaction_energy'], '.3f')} | {conf} | {decision} |")
    for cid, why in out.get("not_computed", {}).items():
        lines.append(f"- {cid}: not computed ({why})")
    if out.get("stopped"):
        lines += ["", f"**Stopped:** {out['stopped']}"]
    lines += ["", "Reduced confidence: the decomposition of the electrolyte (window limits, Li metal) goes through a "
                  "polysulfide, where UMA is least reliable, and the window limits move by more than "
                  f"{config.WINDOW_SENSITIVITY_MAX_V} V when every polysulfide energy is shifted by "
                  f"±{config.POLYSULFIDE_ENERGY_ERROR_EV} eV/atom (twice the largest UMA-vs-DFT difference measured on "
                  "known polysulfides). Interfaces are informative (no threshold); a polysulfide "
                  "formed with the cathode (FeS2 for almost every sulfide against LiFePO4) is shown as information only."]
    return lines + [""]


def render_candidate_analyses(out: dict, result: dict) -> list[str]:
    lines = ["## Candidate analyses (Muse Spark Open, in parallel)", ""]
    if out.get("skipped"):
        return lines + [f"Not run: {out['skipped']}.", ""]
    by_id = _pool(result)
    if out.get("reused"):
        lines += [f"Reviews kept from earlier runs: {', '.join(out['reused'])}.", ""]
    for cid in out["analysed"]:
        a = by_id[cid].get("analysis") or {}
        lines += [f"**{cid} {by_id[cid]['formula']}** (MD priority: {a.get('md_priority')}): {a.get('summary')}",
                  *[f"- strength: {s}" for s in a.get("strengths", [])], *[f"- risk: {s}" for s in a.get("risks", [])], ""]
    for cid, err in out.get("failed", {}).items():
        lines.append(f"- {cid}: no analysis ({err})")
    return lines + [""]


def render_md_selection(out: dict, result: dict) -> list[str]:
    lines = ["## Choice of the candidates for molecular dynamics", ""]
    if not out["eligible"]:
        return lines + ["No eligible candidate.", ""]
    lines += [f"Not simulated yet (the choice): {', '.join(out.get('choices') or []) or 'none'}. Selected by "
              f"{out['chosen_by']}: {', '.join(out['selected']) or 'none'}.", "", f"Rationale: {out['rationale'] or '—'}"]
    if out["ignored"]:
        lines += ["", f"Ids proposed by the model but not eligible (ignored): {', '.join(out['ignored'])}"]
    return lines + [""]


def render_md(out: dict, result: dict) -> list[str]:
    from autolab.sim.backend import gpu_type

    gpus = sorted({g for g in (gpu_type(r.get("gpu")) for r in out.get("rows") or []) if g}) or [config.MODAL_MD_GPU]
    lines = [f"## Li diffusion ({config.MD_SCREEN_TEMPERATURE_K} K, {config.MD_SCREEN_SEEDS} seeds of "
             f"{config.MD_SCREEN_PS} ps pooled, Modal {' + '.join(gpus)})", ""]
    p = out.get("plan")
    if p:
        lines.append(f"Runs computed: {p['runs']} of {p['total_runs']} (others from the cache); estimate "
                     f"{p['usd']:.2f} $, about {p['wall_s'] / 60:.0f} min in parallel.")
    if out.get("from_cache"):
        lines.append(f"Not selected but already simulated (verdict from the cache, no cost): "
                     f"{', '.join(out['from_cache'])}.")
    if out.get("stopped"):
        return lines + ["", f"**Not launched:** {out['stopped']}", ""]
    if out["rows"]:
        lines += ["", "| Structure | Kind | D ± s.e. (cm²/s) | D / D(parent) | Verdict | Conduction | Framework |",
                  "|---|---|---|---|---|---|---|"]
        for r in out["rows"]:
            v = r.get("vs_parent")
            fw = r.get("framework")
            lines.append(f"| {r['formula']} ({r['id']}) | {r['kind']} | {r['D_cm2_per_s']:.2e} ± "
                         f"{_v(r['D_sem_cm2_per_s'], '.1e')} | "
                         f"{'—' if not v else format(v['ratio'], '.2f') + ' ± ' + format(v['ratio_err'], '.2f')} | "
                         f"{(v or {}).get('verdict', '—')} | {r.get('conduction', '—')} | "
                         f"{'—' if not fw else ('intact' if fw['intact'] else 'MOVED')} |")
    return lines + [""]


def render_ranking(out: dict, result: dict) -> list[str]:
    by_id = _pool(result)
    lines = ["## Final ranking", "",
             f"Order: MD verdict ({' > '.join(config.FINAL_RANK_MD_ORDER)}), then lowest E_hull per substitution; "
             "excluded candidates last, with their reason. Candidates are computational predictions, not proven "
             "materials. E_hull ± its error bar: mean absolute UMA-vs-DFT (Materials Project) difference on the known "
             "compounds of the same chemical system.", ""]
    if not out["ranking"]:
        return lines + ["No candidate passed all filters.", ""]
    for i, cid in enumerate(out["ranking"], 1):
        c = by_id[cid]
        md = c.get("md_verdict") or "not run"
        ratio = f" (D/D(parent) {c['D_ratio_to_parent']:.2f} ± {c['D_ratio_err']:.2f})" if c.get("D_ratio_to_parent") else ""
        flags = [f"reduced confidence (E_hull via {', '.join(c['decomposition_polysulfides'])})"] if c.get("reduced_confidence") else []
        if c.get("electrodes_reduced_confidence"):
            flags.append(f"reduced confidence of the window (decomposes via {', '.join(c['electrodes_polysulfides'])})")
        tail = f" — EXCLUDED at {c['excluded_at']}: {c['exclusion_reason']}" if c.get("excluded_at") else ""
        star = " **finalist**" if cid in out["finalists"] else ""
        err = c.get("e_hull_error")
        pm = f" ± {err['mae_eV_per_atom']:.3f}" if err else ""
        lines.append(f"{i}. {cid} {c['formula']}{star}: E_hull per substitution {c['e_hull_per_substitution']:.3f} eV, "
                     f"E_hull {c['e_hull']:.3f}{pm} eV/atom, gap {_v(c.get('gap_optb88'))} eV, MD {md}{ratio}"
                     f"{'; ' + '; '.join(flags) if flags else ''}{tail}")
    return lines + [""]


# --- final report (interface.md 12): numbers from the code, narrative from the model, methods named ---------------

METHODS = [
    ("Candidate proposals and decisions", "Meta Muse Spark (reasoning model), with comparisons computed by the code"),
    ("Structure relaxation and energies", "Meta FAIR UMA (uma-s-1p2, OMat head), MP2020 corrections; references from "
                                         "Materials Project, all relaxed with UMA (no mixing of energy sources)"),
    ("Thermodynamic stability", "energy above the convex hull of the chemical system; kept if <= 0.05 eV/atom; error "
                                "bar measured against DFT (Materials Project) on the known compounds of the same system"),
    ("Electronic band gap", "recorded prediction (optB88vdW scale for the filter, mBJ shown); kept if >= 2 eV"),
    ("Electrochemical window and electrodes", "grand-potential phase diagrams (window, reaction with Li metal), "
                                              "interface reactivity with LiFePO4 (calibrated against MP)"),
    ("Independent reviews", "Meta Muse Spark Open, one review per candidate, in parallel"),
    ("Lithium diffusion", "Langevin molecular dynamics with UMA at 600 K, 2 x 40 ps per structure, diffusion "
                          "coefficient by blocks, compared with the parent crystal (calibrated: Li7P3S11 2.0x faster "
                          "than beta-Li3PS4)"),
    ("Error-driven loop", "the slow tests (reaction with lithium metal, lithium diffusion) run in each round; their "
                          "failures, with the measured numbers, go back to the proposing model, which explains them "
                          "as hypotheses and corrects its next proposals"),
    ("Ionic conductivity at 300 K", "Arrhenius fit of the diffusion coefficients (molecular dynamics at several "
                                    "temperatures), extrapolated to 300 K, Nernst-Einstein relation; an estimate with "
                                    "its range (calibrated: Li7P3S11 and beta-Li3PS4 against experiment)"),
    ("Literature check", "Meta Muse Spark with web search; a known electrolyte (LGPS) checked first as a control"),
    ("Plain-language summaries", "Meta Muse Glimmer"),
]

REPORT_SYSTEM = """You write the final report of a computational materials-discovery research, for scientists and for readers who are not specialists. The code gives you the comparison table of the three finalists (the first one is the champion: the best compromise by the criteria of the research), the excluded candidates with their reasons, the literature check and what was not computed.
Rules:
- Use only the numbers of the table, quoted exactly with their units; never invent or estimate a value. A missing value was not computed: say so.
- The energy above the hull comes with its error bar (e_hull_error_eV_per_atom: mean UMA-vs-DFT difference on known compounds of the same system): quote it with the value when given.
- champion_reasons: why the champion is preferred to the two others, each reason tied to numbers of the table.
- tradeoffs: its compromises and weaknesses. uncertainties: what limits the confidence (methods, temperature of the diffusion, reduced-confidence flags, statistics).
- validation: experiments or calculations to confirm it (e.g. XRD, impedance spectroscopy, DFT checks, cycling against Li metal), each with "basis": "documented" (standard practice) or "hypothesis".
- synthesis: possible routes, each with "basis": "documented" only for well-established routes for this family of sulfide electrolytes (e.g. ball milling then annealing under inert atmosphere), else "hypothesis"; never present a route as guaranteed.
- limitations: properties not studied and validations still needed. The candidates are computational predictions, not proven materials.
- The ionic conductivity at 300 K is an extrapolated estimate with a range and a method (own fit, or the parent's activation energy assumed): give it as an order of magnitude with its range, never as a measurement.
- Write readable prose: name quantities in words (energy above the hull, band gap, diffusion coefficient), never field names such as e_hull or gap_optb88; numbers as given (already rounded), with units written normally (eV/atom, cm²/s).
- Do not name AI models or providers. Plain English, short sentences.
Reply with JSON only, exactly this shape: {template}"""


def _structure_info(c: dict) -> dict:
    """Space group and cell of the relaxed structure (pymatgen), or {} when it cannot be read."""
    try:
        from pymatgen.io.ase import AseAtomsAdaptor
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        from autolab.sim.serialize import atoms_from_dict

        s = AseAtomsAdaptor.get_structure(atoms_from_dict(c["relaxed_atoms"]))
        lat = s.lattice
        try:
            sg = SpacegroupAnalyzer(s, symprec=0.1).get_space_group_symbol()
        except Exception:
            sg = None
        return {"space_group": sg, "a_A": round(lat.a, 3), "b_A": round(lat.b, 3), "c_A": round(lat.c, 3),
                "alpha": round(lat.alpha, 1), "beta": round(lat.beta, 1), "gamma": round(lat.gamma, 1),
                "volume_A3": round(lat.volume, 1), "atoms_in_cell": len(s)}
    except Exception:
        return {}


def _finalist_row(c: dict, novelty_by_id: dict) -> dict:
    nv = novelty_by_id.get(c["id"], {})
    return {"id": c["id"], "formula": c["formula"], "parent": c.get("parent_formula") or c.get("parent"),
            "substitution": c.get("substitution"), **_structure_info(c),
            "e_hull_eV_per_atom": c.get("e_hull"), "e_hull_per_substitution_eV": c.get("e_hull_per_substitution"),
            "e_hull_error_eV_per_atom": (c.get("e_hull_error") or {}).get("mae_eV_per_atom"),
            "e_hull_error_basis": (f"mean absolute UMA-vs-DFT difference on {c['e_hull_error']['n']} known compounds of "
                                   f"{c['e_hull_error']['system']}" if c.get("e_hull_error") else None),
            "decomposition": c.get("decomposition"), "gap_optb88_eV": c.get("gap_optb88"), "gap_mbj_eV": c.get("gap_mbj"),
            "window_V": c.get("window"), "against_li_metal": c.get("passivation"),
            "reaction_with_LiFePO4_eV_per_atom": c.get("interface_reaction_energy"),
            "D_600K_cm2_per_s": c.get("D_cm2_per_s"), "D_error_cm2_per_s": c.get("D_sem_cm2_per_s"),
            "D_ratio_to_parent": c.get("D_ratio_to_parent"), "D_ratio_error": c.get("D_ratio_err"),
            "diffusion_verdict": c.get("md_verdict") or "not simulated",
            "ionic_conductivity_300K_mS_cm": (c.get("conductivity") or {}).get("sigma_mS_cm"),
            "ionic_conductivity_range_mS_cm": ([c["conductivity"]["sigma_low_mS_cm"], c["conductivity"]["sigma_high_mS_cm"]]
                                               if c.get("conductivity") else None),
            "ionic_conductivity_method": ((c.get("conductivity") or {}).get("method") or "not computed"),
            "activation_energy_eV": (c.get("conductivity") or {}).get("Ea_eV"),
            "confidence_flags": [f for f, on in (("stability via a polysulfide", c.get("reduced_confidence")),
                                                 ("window via a polysulfide", c.get("electrodes_reduced_confidence")),
                                                 ("S-S bonds", c.get("ss_bonds"))) if on],
            "novelty": nv.get("label"), "novelty_summary": nv.get("summary"),
            "novelty_sources": [s.get("url") for s in nv.get("sources", [])][:3],
            "review": c.get("analysis")}


def _rounded(x, digits: int = 3):
    """Numbers for the report: fixed decimals, or 3 significant digits for small values such as D."""
    if isinstance(x, float):
        return float(f"{x:.3g}") if x and abs(x) < 1e-3 else round(x, digits)
    if isinstance(x, dict):
        return {k: _rounded(v, digits) for k, v in x.items()}
    if isinstance(x, list):
        return [_rounded(v, digits) for v in x]
    return x


def report(camp: Campaign) -> dict:
    from autolab.agent.loop import LoopStopped
    from autolab.llm.schemas import template

    rk = camp.outputs.get("ranking", {})
    finalists = rk.get("finalists") or []
    if not finalists:
        return {"skipped": "no finalist", "summary": {"skipped": "no finalist"}}
    by_id = camp.by_id
    novelty_by_id = {r["id"]: r for r in (camp.outputs.get("novelty", {}).get("candidates") or [])}
    rows = [_rounded(_finalist_row(by_id[i], novelty_by_id)) for i in finalists]
    needed = ("electrodes", "molecular_dynamics", "ranking", "novelty")
    missing = [n for n in needed if (camp.outputs.get(n) or {}).get("skipped") or n not in camp.outputs
               or (camp.outputs.get(n) or {}).get("error")]
    status = "complete" if not missing and len(rows) == config.FINALISTS_MAX else "partial"
    out = {"completeness": status, "missing_steps": missing, "champion": rows[0]["id"], "finalists": rows,
           "excluded": rk.get("excluded", {}), "methods": [{"step": a, "method": b} for a, b in METHODS],
           "not_computed": config.CAPABILITIES["not_computed"], "narrative": None}
    facts = {"goal": camp.goal, "status": status, "finalists": rows, "excluded": out["excluded"],
             "not_computed": out["not_computed"]}
    try:
        info = camp.ask([{"role": "system", "content": REPORT_SYSTEM.replace("{template}", template("report"))},
                         {"role": "user", "content": json.dumps(facts, default=str)}], "report", "report")
        n = info["reply"]
        for key in ("validation", "synthesis"):  # each item: documented practice or hypothesis, never unlabelled
            n[key] = [{"text": str(x.get("text", x)) if isinstance(x, dict) else str(x),
                       "basis": x.get("basis") if isinstance(x, dict) and x.get("basis") in ("documented", "hypothesis")
                       else "hypothesis"} for x in n.get(key, [])]
        out["narrative"] = n
    except LoopStopped as e:
        out["narrative_error"] = f"the narrative could not be written ({e}); the numbers above are complete"
    out["summary"] = {"champion": out["champion"], "completeness": status, "narrative": out["narrative"] is not None}
    return out


def _fmt(x, f=".3f", unit=""):
    return "not computed" if x is None else (f"{x:{f}}{unit}" if isinstance(x, (int, float)) else str(x))


def render_report(out: dict, result: dict) -> list[str]:
    if out.get("skipped"):
        return ["## Final scientific report", "", f"Not written: {out['skipped']}.", ""]
    n = out.get("narrative") or {}
    rows = out["finalists"]
    champ = rows[0]
    lines = ["## Final scientific report", "",
             f"*Ranking {out['completeness']}*" + (f" (steps missing: {', '.join(out['missing_steps'])})"
                                              if out["missing_steps"] else "") + ".", ""]
    if n.get("executive_summary"):
        lines += ["### Executive summary", "", n["executive_summary"], ""]
    lines += ["### Comparison of the three finalists", "",
              "| | " + " | ".join(r["formula"] for r in rows) + " |", "|---|" + "---|" * len(rows)]
    fields = [("Parent crystal", "parent", None), ("Space group", "space_group", None),
              ("Cell a / b / c (Å)", None, lambda r: " / ".join(_fmt(r.get(k), ".2f") for k in ("a_A", "b_A", "c_A"))),
              ("E_hull (eV/atom)", None, lambda r: _fmt(r.get("e_hull_eV_per_atom"), ".3f") + (
                  f" ± {r['e_hull_error_eV_per_atom']:.3f}" if r.get("e_hull_error_eV_per_atom") is not None else "")),
              ("E_hull per substitution (eV)", "e_hull_per_substitution_eV", ".3f"),
              ("Band gap optB88 / mBJ (eV)", None, lambda r: f"{_fmt(r['gap_optb88_eV'], '.2f')} / {_fmt(r['gap_mbj_eV'], '.2f')}"),
              ("Window (V)", None, lambda r: (f"{r['window_V']['v_low']:.2f}–{r['window_V']['v_high']:.2f}"
                                              if r.get("window_V") and r["window_V"].get("stable") else
                                              "zero width" if r.get("window_V") else "not computed")),
              ("Against Li metal", "against_li_metal", None),
              ("Reaction with LiFePO4 (eV/atom)", "reaction_with_LiFePO4_eV_per_atom", ".3f"),
              ("D at 600 K (cm²/s)", "D_600K_cm2_per_s", ".2e"),
              ("D / D(parent)", None, lambda r: (f"{r['D_ratio_to_parent']:.2f} ± {r['D_ratio_error']:.2f}"
                                                 if r.get("D_ratio_to_parent") is not None else "not simulated")),
              ("Diffusion verdict", "diffusion_verdict", None),
              ("Ionic conductivity at 300 K (mS/cm, estimate)", None, lambda r: (
                  f"{r['ionic_conductivity_300K_mS_cm']:.3g} (range {r['ionic_conductivity_range_mS_cm'][0]:.2g}–"
                  f"{r['ionic_conductivity_range_mS_cm'][1]:.2g}; {r['ionic_conductivity_method']})"
                  if r.get("ionic_conductivity_300K_mS_cm") is not None else "not computed")),
              ("Literature", "novelty", None),
              ("Confidence flags", None, lambda r: ", ".join(r["confidence_flags"]) or "none")]
    for label, key, f in fields:
        cells = [f(r) if callable(f) else _fmt(r.get(key), f) if f else (r.get(key) or "not computed") for r in rows]
        lines.append(f"| {label} | " + " | ".join(str(c) for c in cells) + " |")
    lines += ["", f"### Champion: {champ['formula']}", ""]
    for title, key in (("Why it is preferred", "champion_reasons"), ("Trade-offs", "tradeoffs"),
                       ("Uncertainties", "uncertainties")):
        if n.get(key):
            lines += [f"**{title}.**", *[f"- {x}" for x in n[key]], ""]
    for title, key in (("Validation", "validation"), ("Synthesis routes to consider", "synthesis")):
        if n.get(key):
            lines += [f"**{title}.**", *[f"- {x['text']} *({x['basis']})*" for x in n[key]], ""]
    if out.get("narrative_error"):
        lines += [f"*{out['narrative_error']}*", ""]
    lines += ["### Methods", "", *[f"- **{m['step']}**: {m['method']}" for m in out["methods"]], "",
              "### Limitations", "", *[f"- {x}" for x in n.get("limitations", [])],
              f"- Not computed: {out['not_computed']}.",
              "- The candidates are computational predictions, not proven materials.", ""]
    return lines


def render_novelty(out: dict, result: dict) -> list[str]:
    if out.get("skipped"):
        return ["## Novelty check", "", f"Not run: {out['skipped']}.", ""]
    from autolab.agent.novelty import render

    return [render(out), ""]


def _pool(result: dict) -> dict[str, dict]:
    pool = {c["id"]: c for c in result.get("prior", [])}
    pool.update({c["id"]: c for r in result["iterations"] for c in r["candidates"]})
    return pool


def _evaluate(cid, parent_id, parent, substitution, tools, events, budget):
    return evaluate_candidate(cid, parent_id, parent, substitution, tools, events, budget)


def make_domain() -> Domain:
    from autolab.agent.report import candidate_table

    return Domain(
        name="electrolyte", goal=config.AGENT_GOAL, parents=tuple(config.AGENT_PARENTS),
        make_tools=lambda: ElectrolyteTools(not_run=[]), evaluate=_evaluate,
        proposal_messages=prompts.proposal_messages, analysis_messages=prompts.analysis_messages,
        comparisons=comparisons, for_model=FOR_MODEL, rank_key=rank_key,
        iteration_stages=(Stage("electrodes", electrodes, render_electrodes),
                          Stage("candidate_analyses", candidate_analyses, render_candidate_analyses),
                          Stage("md_selection", md_selection, render_md_selection),
                          Stage("molecular_dynamics", molecular_dynamics, render_md)),
        feedback=feedback, render_feedback=render_feedback,
        stages=(Stage("electrodes", electrodes, render_electrodes),
                Stage("candidate_analyses", candidate_analyses, render_candidate_analyses),
                Stage("md_selection", md_selection, render_md_selection),
                Stage("molecular_dynamics", molecular_dynamics, render_md),
                Stage("ranking", ranking, render_ranking),
                Stage("conductivity", conductivity, render_conductivity),
                Stage("novelty", novelty, render_novelty),
                Stage("report", report, render_report)),
        thresholds=THRESHOLDS, render_candidates=candidate_table)


register("electrolyte", make_domain)
