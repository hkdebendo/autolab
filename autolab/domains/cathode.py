"""Cobalt-free cathodes for lithium-ion batteries: the second domain of the agent (owner, 2026-11-02).

Funnel of one candidate (a substitution in a known cobalt-free cathode, config.CATHODE_PARENTS):
1. generate: the substitution applied to the parent cell, cobalt refused, charge neutrality with mixed valence
   (config.CATHODE_OXIDATION_RANGES), config.CATHODE_N_ARRANGEMENTS random placements;
2. known: a composition already in Materials Project is reported, not computed;
3. relax: every arrangement relaxed with UMA (atoms and cell), the lowest in energy kept;
4. hull: E_hull against the stable MP phases of its system, all relaxed with UMA (config.CATHODE_HULL_REF_EHULL_MAX),
   kept if <= config.CATHODE_EHULL_MAX;
5. voltage: the Li that neutrality allows is removed (analysis.cathode.removable_li), the delithiated cell relaxed
   with UMA: average voltage, theoretical capacity, energy density and volume change, each kept within config, and
   compared with the parent computed the same way.
Error-driven loop: every failure of the funnel, with its numbers, goes back to the model before it analyses the
iteration (hypothesis on the cause, correction). After the iterations: independent reviews (Muse Spark Open),
ranking by energy density, final report (Muse Spark). Every threshold comes from config.py.
"""

from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Callable

from pymatgen.core import Composition, Structure

from autolab import config
from autolab.agent.compare import comparisons as _comparisons
from autolab.agent.pipeline import Tools, _default_known, _default_relax, _relaxed_structure, live_structure, n_modified
from autolab.analysis.cathode import (average_voltage, capacity_mAh_g, cathode_charge_check, energy_density_Wh_kg,
                                      removable_li, volume_change_pct)
from autolab.domains import Campaign, Domain, Stage, register
from autolab.llm.schemas import template

METRICS = (  # what the code compares between candidates (agent.compare), best first
    ("energy_density_Wh_kg", "energy density", "Wh/kg", "high"),
    ("voltage_V", "average voltage", "V", "high"),
    ("capacity_mAh_g", "theoretical capacity", "mAh/g", "high"),
    ("e_hull", "E_hull per atom", "eV/atom", "low"),
    ("e_hull_per_substitution", "E_hull per substitution", "eV per modified site", "low"),
    ("volume_change_pct", "volume change on charge", "%", "low"),
)
FOR_MODEL = ("id", "parent", "substitution", "formula", "status", "rejected_at", "reason", "arrangements", "converged",
             "known_in_mp", "e_hull", "e_hull_per_substitution", "decomposition", "n_atoms", "n_modified",
             "li_removed", "li_total", "voltage_V", "capacity_mAh_g", "energy_density_Wh_kg", "volume_change_pct",
             "parent_voltage_V", "parent_capacity_mAh_g", "parent_energy_density_Wh_kg", "parent_volume_change_pct")
THRESHOLDS = ("CATHODE_VOLTAGE_SIGNIFICANT_V", "CATHODE_EHULL_MAX", "CATHODE_HULL_REF_EHULL_MAX", "CATHODE_VOLTAGE_MIN", "CATHODE_VOLTAGE_MAX",
              "CATHODE_CAPACITY_MIN", "CATHODE_VOLUME_CHANGE_MAX", "CATHODE_N_ARRANGEMENTS", "CATHODE_FORBIDDEN",
              "CATHODE_REVIEW_MAX", "CATHODE_FINALISTS_MAX", "CANDIDATE_ANALYSIS_PROVIDER")
STEP_NAMES = {"generate": "charge neutrality", "known": "novelty (already in Materials Project)",
              "relax": "relaxation", "hull": "thermodynamic stability", "voltage": "average voltage",
              "capacity": "theoretical capacity", "volume": "volume change on charge"}


# --- default tools (expensive or networked; tests replace them) -----------------------------------------------------

def _default_hull_entries(elements, budget):
    from autolab.analysis.stability import uma_reference_entries

    return uma_reference_entries(elements, budget=budget, ehull_max=config.CATHODE_HULL_REF_EHULL_MAX)


def _default_ehull_error(formula: str) -> dict | None:
    from autolab.analysis.uma_errors import cached_system_errors, ehull_uncertainty

    return ehull_uncertainty(formula, errors=lambda els: cached_system_errors(els, ehull_max=config.CATHODE_HULL_REF_EHULL_MAX))


def _default_li_energy(budget) -> float:
    """Energy of one Li atom in bcc Li metal, relaxed with UMA (cached)."""
    from autolab.data.mp import get_structure

    s = get_structure(config.CATHODE_LI_METAL)
    res = _default_relax([s], budget)[0]
    return res["energy"] / len(s)


_PARENTS: dict[str, dict] = {}  # parent id -> its own metrics (computed once per process, relaxations cached on disk)


@dataclass
class CathodeTools(Tools):
    hull_entries: Callable = _default_hull_entries  # (elements, budget) -> (UMA entries of the stable phases, skipped)
    li_energy: Callable = _default_li_energy  # (budget) -> eV per Li in Li metal
    ehull_error: Callable = _default_ehull_error  # (formula) -> UMA-vs-DFT error bar of its system (stable phases)

    def parent_metrics(self, parent_id: str, parent: Structure, budget) -> dict:
        """The parent cathode through the same relaxation and delithiation as a candidate (cached per parent)."""
        if parent_id not in _PARENTS:
            res = self.relax([parent], budget)[0]
            _PARENTS[parent_id] = delithiation(res, _relaxed_structure(res), self, budget) if res["converged"] else {}
        return _PARENTS[parent_id]


def delithiation(best: dict, lith: Structure, tools, budget, seed: int = config.GENERATOR_SEED) -> dict:
    """Remove the Li that neutrality allows from the relaxed lithiated cell, relax the delithiated cell, and compute
    voltage, capacity, energy density and volume change. Returns {"li_removed": 0} when no Li can leave, or an
    "error" when the delithiated cell does not converge."""
    import numpy as np

    li_sites = [i for i, site in enumerate(lith) if site.specie.symbol == "Li"]
    k = removable_li(lith)
    out = {"li_total": len(li_sites), "li_removed": k}
    if k == 0:
        return out
    removed = li_sites if k == len(li_sites) else sorted(random.Random(seed).sample(li_sites, k))
    delith = lith.copy()
    delith.remove_sites(removed)
    res = tools.relax([delith], budget)[0]
    if not res["converged"]:
        return {**out, "error": "the delithiated cell did not converge"}
    e_li = tools.li_energy(budget)
    voltage = average_voltage(best["energy"], res["energy"], k, e_li)
    capacity = capacity_mAh_g(lith, k)
    v_delith = abs(float(np.linalg.det(np.asarray(res["atoms"]["cell"], dtype=float))))
    out.update(voltage_V=round(voltage, 3), capacity_mAh_g=round(capacity, 1),
               energy_density_Wh_kg=round(energy_density_Wh_kg(voltage, capacity), 0),
               volume_change_pct=round(volume_change_pct(lith.volume, v_delith), 2),
               lithiated_volume_A3=round(lith.volume, 2), delithiated_volume_A3=round(v_delith, 2),
               delithiated_formula=delith.composition.reduced_formula, removed_sites=removed,
               delithiated_energy=res["energy"], li_metal_energy=e_li, delithiated_atoms=res["atoms"])
    return out


def delithiation_view(lith: Structure, m: dict) -> dict:
    """What the interface shows of the charge: the lithiated cell, the Li that leave (indices), the relaxed
    delithiated cell drawn next to it (same order without the removed Li). Display only."""
    import numpy as np

    from autolab.agent.pipeline import lattice

    d = m["delithiated_atoms"]
    keep = [i for i in range(len(lith)) if i not in set(m["removed_sites"])]
    cell = np.asarray(d["cell"], dtype=float)
    frac = np.asarray(d["positions"], dtype=float) @ np.linalg.inv(cell)
    frac -= np.round(frac - lith.frac_coords[keep])
    rnd = lambda rows, k: [[round(float(x), k) for x in r] for r in rows]
    return {"symbols": [s.specie.symbol for s in lith], "removed": m["removed_sites"],
            "lithiated": {"positions": rnd(lith.cart_coords, 3), "cell": rnd(lith.lattice.matrix, 4),
                          "lattice": lattice(lith.lattice.matrix)},
            "delithiated": {"positions": rnd(frac @ cell, 3), "cell": rnd(cell, 4), "lattice": lattice(cell)}}


# --- the funnel of one candidate ------------------------------------------------------------------------------------

def evaluate(candidate_id: str, parent_id: str, parent: Structure, substitution: dict, tools, events, budget=None) -> dict:
    from autolab.chem.generator import generate_candidates

    t0 = time.perf_counter()
    used0 = budget.used if budget else 0
    out = {"id": candidate_id, "parent": parent_id, "parent_formula": parent.composition.reduced_formula,
           "substitution": substitution, "formula": None, "status": "rejected", "rejected_at": None, "reason": None,
           "e_hull": None, "e_hull_per_substitution": None, "decomposition": None, "known_in_mp": [],
           "voltage_V": None, "capacity_mAh_g": None, "energy_density_Wh_kg": None, "volume_change_pct": None}

    def emit(step, **data):
        events.emit("candidate", step, data, candidate_id)

    def finish(status="rejected", step=None, reason=None):
        out.update(status=status, rejected_at=step, reason=reason,
                   new_relaxations=(budget.used - used0) if budget else None, seconds=round(time.perf_counter() - t0, 1))
        emit("done", status=status, rejected_at=step, reason=reason)
        return out

    # 1. cobalt refused, substitution applied, charge neutrality with mixed valence: before any simulation
    gen = generate_candidates(parent, substitution, parent_id, n_arrangements=config.CATHODE_N_ARRANGEMENTS,
                              charge_check=cathode_charge_check)
    out["formula"] = gen["formula"]
    emit("generate", accepted=gen["accepted"], formula=gen["formula"], charge=gen["charge"],
         arrangements=len(gen["candidates"]), reason=gen["reason"])
    if not gen["accepted"]:
        return finish(step="generate", reason=gen["reason"])
    if removable_li(Structure.from_dict(gen["candidates"][0]["structure"])) == 0:  # known from the composition alone
        return finish(step="voltage", reason=NO_LI)
    out["n_modified"] = n_modified(parent, substitution)

    # 2. a composition already in Materials Project is reported, not recomputed
    try:
        known = tools.known(gen["formula"])
    except Exception as e:  # MP unreachable: compute anyway, but say so
        known = []
        emit("known_check", error=f"{type(e).__name__}: {e}")
    else:
        emit("known_check", known=known)
    if known:
        out["known_in_mp"] = [k["material_id"] for k in known]
        return finish(step="known", reason=f"composition already in Materials Project: {', '.join(out['known_in_mp'])}")

    structures = [Structure.from_dict(c["structure"]) for c in gen["candidates"]]
    return evaluate_structures(out, structures, substitution, tools, emit, finish, budget, parent=(parent_id, parent))


NO_LI = "no Li can be removed: no element can be oxidised further (oxygen fixed at -2)"


def evaluate_structures(out: dict, structures: list[Structure], substitution: dict | None, tools, emit: Callable,
                        finish: Callable, budget=None, hidden_formulas: frozenset[str] = frozenset(),
                        parent: tuple | None = None) -> dict:
    """Steps 3-5 of the funnel on ready structures (arrangements of one composition): relaxation, E_hull, charge.
    `hidden_formulas`: reduced formulas removed from the hull references (blind benchmark of a known cathode);
    `parent`: (id, structure) of the parent the candidate is compared with (none in the benchmark)."""
    from autolab.analysis.stability import e_hull, uma_entry

    # 3. UMA relaxation of every arrangement; the lowest converged one is kept
    out["arrangements"] = len(structures)
    results = tools.relax(structures, budget)
    converged = [r for r in results if r["converged"]]
    out["converged"] = len(converged)
    epa = [r["energy_per_atom"] for r in converged]
    out["energy_spread_meV"] = round(1000 * (max(epa) - min(epa)), 1) if epa else None
    best = min(converged, key=lambda r: r["energy_per_atom"]) if converged else None
    emit("relax", arrangements=len(results), converged=len(converged), energies_per_atom=[round(e, 4) for e in epa],
         spread_meV=out["energy_spread_meV"], cached=all(r.get("cached") for r in results),
         structure=live_structure(structures[results.index(best)], best, substitution) if best else None)
    if not converged:
        return finish(step="relax", reason="no arrangement converged")
    lith = _relaxed_structure(best)
    out.update(energy=best["energy"], relaxed_atoms=best["atoms"], n_atoms=len(lith))
    out.setdefault("n_modified", len(lith))  # a known compound (benchmark): its E_hull per site is its E_hull

    # 4. stability against the stable phases of the system, all relaxed with UMA (never MP energies)
    elements = sorted(el.symbol for el in lith.composition.elements)
    entries, skipped = tools.hull_entries(elements, budget)
    if hidden_formulas:
        entries = [e for e in entries if e.composition.reduced_formula not in hidden_formulas]
    out["skipped_references"] = skipped
    hull = e_hull(uma_entry(Composition(lith.composition), best["energy"], out["id"], structure=lith), entries)
    out.update(e_hull=hull["e_hull"], decomposition=hull["decomposition"][:4],
               e_hull_per_substitution=round(hull["e_hull"] * out["n_atoms"] / out["n_modified"], 4))
    emit("hull", e_hull=hull["e_hull"], e_hull_per_substitution=out["e_hull_per_substitution"],
         decomposition=out["decomposition"], references=len(entries), skipped_references=skipped,
         limit=config.CATHODE_EHULL_MAX)
    if hull["e_hull"] > config.CATHODE_EHULL_MAX:
        return finish(step="hull", reason=f"E_hull {hull['e_hull']:.3f} > {config.CATHODE_EHULL_MAX} eV/atom")

    # 5. charge: Li removed, delithiated cell relaxed; voltage, capacity, energy density, volume change
    m = delithiation(best, lith, tools, budget)
    pm = tools.parent_metrics(parent[0], parent[1], budget) if parent else {}
    for key in ("voltage_V", "capacity_mAh_g", "energy_density_Wh_kg", "volume_change_pct"):
        out[key] = m.get(key)
        out[f"parent_{key}"] = pm.get(key)
    out.update(li_removed=m["li_removed"], li_total=m["li_total"], delithiated_formula=m.get("delithiated_formula"),
               delithiated_atoms=m.get("delithiated_atoms"))
    emit("voltage", **{k: v for k, v in m.items() if k not in ("delithiated_atoms", "removed_sites", "delithiated_energy",
                                                                 "li_metal_energy")},
         parent={k: pm.get(k) for k in ("voltage_V", "capacity_mAh_g", "energy_density_Wh_kg", "volume_change_pct")},
         parent_formula=out["parent_formula"],
         limits={"voltage": [config.CATHODE_VOLTAGE_MIN, config.CATHODE_VOLTAGE_MAX],
                 "capacity_min": config.CATHODE_CAPACITY_MIN, "volume_change_max": config.CATHODE_VOLUME_CHANGE_MAX},
         structure=delithiation_view(lith, m) if m.get("delithiated_atoms") else None)
    if m["li_removed"] == 0:
        return finish(step="voltage", reason=NO_LI)
    if m.get("error"):
        return finish(step="voltage", reason=m["error"])
    v = m["voltage_V"]
    if not config.CATHODE_VOLTAGE_MIN <= v <= config.CATHODE_VOLTAGE_MAX:
        return finish(step="voltage", reason=f"average voltage {v:.2f} V outside {config.CATHODE_VOLTAGE_MIN}-"
                                             f"{config.CATHODE_VOLTAGE_MAX} V")
    if m["capacity_mAh_g"] < config.CATHODE_CAPACITY_MIN:
        return finish(step="capacity", reason=f"capacity {m['capacity_mAh_g']:.0f} mAh/g < "
                                              f"{config.CATHODE_CAPACITY_MIN:.0f} mAh/g")
    if abs(m["volume_change_pct"]) > config.CATHODE_VOLUME_CHANGE_MAX:
        return finish(step="volume", reason=f"volume change {m['volume_change_pct']:.1f} % > "
                                            f"{config.CATHODE_VOLUME_CHANGE_MAX:.0f} %")
    return finish(status="passed")


def rank_key(c: dict):
    return (-(c.get("energy_density_Wh_kg") or 0.0), c.get("e_hull_per_substitution") or 0.0)


def comparisons(candidates: list[dict]) -> list[dict]:
    return _comparisons(candidates, METRICS)


# --- what the model reads and writes --------------------------------------------------------------------------------

def _oxidation_table() -> str:
    return ", ".join(f"{el} {lo:+d}" + (f" to {hi:+d}" if hi != lo else "")
                     for el, (lo, hi) in config.CATHODE_OXIDATION_RANGES.items())


def proposal_system(max_proposals: int) -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new cobalt-free cathode materials for lithium-ion batteries.
Each proposal is a chemical substitution applied to a parent cathode from Materials Project. The code builds the structures, relaxes them with the UMA machine-learned potential (Meta FAIR), measures their stability, removes the lithium that charge neutrality allows, relaxes the charged (delithiated) cell and computes the average voltage, the theoretical capacity, the energy density and the volume change.

Substitution format:
- partial: {{"remove": "Mn", "add": "Ni", "count": 1, "li_vacancies": 0}} replaces `count` randomly chosen `remove` sites of the parent cell by `add`, then removes `li_vacancies` Li atoms. Several random arrangements are relaxed and the lowest in energy is kept.
- total: {{"remove": "Fe", "add": "Mn", "count": "all"}} replaces every `remove` site.

Rules checked by the code (a proposal breaking one is rejected before any simulation):
- Cobalt is excluded. Only these elements, with these oxidation states (mixed valence allowed): {_oxidation_table()}.
- The cell must be able to stay charge-neutral. Counts refer to the parent cell (its cell formula is given).
- Lithium can only leave if another element can be oxidised further (oxygen stays -2): a substitution that leaves no redox-active element (Fe below +3, Mn below +4, Ni below +4, V below +5, Ti below +4, Mo below +6, Cu below +2) gives no capacity.
- `count` is at most the number of `remove` sites in the parent cell; `parent` must be one of the given material ids.
A composition already present in Materials Project is reported and not computed: aim for new compositions.

Filters, with thresholds fixed by the code:
- E_hull (energy above the convex hull of the stable known phases of the system, all relaxed with UMA) <= {config.CATHODE_EHULL_MAX} eV/atom.
- Average voltage between {config.CATHODE_VOLTAGE_MIN} and {config.CATHODE_VOLTAGE_MAX} V vs Li/Li+ (above, common electrolytes decompose).
- Theoretical capacity >= {config.CATHODE_CAPACITY_MIN:.0f} mAh/g; volume change on charge <= {config.CATHODE_VOLUME_CHANGE_MAX:.0f} %.
Candidates that pass are ranked by energy density (voltage x capacity, Wh/kg), then E_hull per substitution. Each candidate is compared with its parent computed the same way.

The history holds the results of earlier iterations, failures included with their measurements (slow_tests), and your failure_analysis of them. Treat every failure as data: do not repeat a strategy that failed; when a proposal corrects an earlier failure, say in the hypothesis which one and how (the cause you give is a hypothesis: the code measured only the numbers).

Propose at most {max_proposals} substitutions, diverse and chemically motivated (redox couples, ionic radii, known dopants that stabilise or raise the voltage), each with a one-sentence rationale. Never repeat a substitution already evaluated.
Reply with JSON only, exactly this shape: {template("proposal")}"""


def analysis_system() -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new cobalt-free cathode materials for lithium-ion batteries.
You receive the candidates evaluated in this iteration. Fields:
- status: "passed" (every filter passed), "rejected", "error" or "budget" (not evaluated: simulation budget reached).
- rejected_at: the failed step: "generate" (unknown parent, cobalt, element outside the table, impossible count, or cannot be charge neutral), "known" (already in Materials Project), "relax" (no arrangement converged), "hull" (E_hull above {config.CATHODE_EHULL_MAX} eV/atom), "voltage" (no Li can be removed, or average voltage outside {config.CATHODE_VOLTAGE_MIN}-{config.CATHODE_VOLTAGE_MAX} V), "capacity" (below {config.CATHODE_CAPACITY_MIN:.0f} mAh/g), "volume" (volume change above {config.CATHODE_VOLUME_CHANGE_MAX:.0f} %).
- e_hull (eV/atom, UMA energies with the MP2020 corrections, against the stable MP phases relaxed with UMA) and decomposition; e_hull_per_substitution = e_hull x n_atoms / n_modified (eV per modification).
- li_removed / li_total: Li removed on charge (all that charge neutrality allows); voltage_V: average voltage of that charge vs Li/Li+; capacity_mAh_g: theoretical capacity; energy_density_Wh_kg = voltage x capacity; volume_change_pct: shrinkage of the cell on charge.
- parent_*: the same quantities for the parent, computed the same way.
- comparisons: statements computed by the code over all candidates so far. Whenever a lesson compares candidates, base it only on these statements and quote their numbers; never compare values yourself.
- slow_tests: the result of each candidate with its measurements; outcome "failed" is a negative result.
- failure_analysis: for EACH failed candidate, give its id, a hypothesis on the physical or chemical cause (redox couple exhausted, ionic radius mismatch, Jahn-Teller distortion, inactive dopant diluting the capacity...), explicitly a hypothesis since the code measured only the numbers, and a correction for the next proposals. Empty list when nothing failed.
Only the average voltage over the whole charge is computed (no voltage profile), lithium diffusion in the cathode and cycling are not computed: do not claim them.

Rank only candidates with status "passed", best first by energy density unless the comparisons give a reason otherwise (empty list if none). Give 1 to 3 short lessons, one sentence of next direction, and stop=true only if more iterations are unlikely to help.
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


def _numbers(c: dict) -> str:
    parts = []
    if c.get("voltage_V") is not None:
        parts.append(f"{c['voltage_V']:.2f} V")
    if c.get("capacity_mAh_g") is not None:
        parts.append(f"{c['capacity_mAh_g']:.0f} mAh/g")
    if c.get("energy_density_Wh_kg") is not None:
        parts.append(f"{c['energy_density_Wh_kg']:.0f} Wh/kg")
    if c.get("volume_change_pct") is not None:
        parts.append(f"volume change {c['volume_change_pct']:.1f} %")
    if c.get("e_hull") is not None:
        parts.append(f"E_hull {c['e_hull']:.3f} eV/atom")
    return ", ".join(parts)


def feedback(cands: list[dict]) -> list[dict]:
    """Every candidate's outcome with its numbers, for the model's analysis: failures are data (error-driven loop)."""
    out = []
    for c in cands:
        if c.get("status") not in ("passed", "rejected"):
            continue
        name = f"{c.get('formula') or c['id']} ({c['id']})"
        parent = (f"; parent {c['parent_formula']}: {c['parent_voltage_V']:.2f} V, {c['parent_capacity_mAh_g']:.0f} mAh/g,"
                  f" {c['parent_energy_density_Wh_kg']:.0f} Wh/kg" if c.get("parent_voltage_V") is not None else "")
        measured = {k: c.get(k) for k in ("e_hull", "decomposition", "li_removed", "li_total", "voltage_V",
                                          "capacity_mAh_g", "energy_density_Wh_kg", "volume_change_pct",
                                          "parent_voltage_V", "parent_capacity_mAh_g", "parent_energy_density_Wh_kg")
                    if c.get(k) is not None}
        base = {"id": c["id"], "formula": c.get("formula"), "parent": c.get("parent"),
                "substitution": c.get("substitution"), "measured": measured}
        if c["status"] == "passed":
            out.append({**base, "test": "every filter", "outcome": "passed", "reason": _numbers(c),
                        "message": f"Result: {name} passed every filter: {_numbers(c)}{parent}."})
        else:
            test = STEP_NAMES.get(c.get("rejected_at"), c.get("rejected_at") or "evaluation")
            nums = _numbers(c)
            out.append({**base, "test": test, "outcome": "failed", "reason": c.get("reason"),
                        "message": f"Negative result: {name} failed the {test}: {c.get('reason')}"
                                   f"{f' (measured: {nums})' if nums else ''}{parent}."})
    return out


def render_feedback(record: dict) -> list[str]:
    fb = record.get("feedback") or []
    fa = ((record.get("analysis") or {}).get("reply") or {}).get("failure_analysis") or []
    if not fb and not fa:
        return []
    lines = ["**Results of this iteration (fed back to the model):**", ""] + [f"- {f['message']}" for f in fb]
    if fa:
        lines += ["", "**The model's reading of the failures (hypotheses, not measurements):**", ""]
        lines += [f"- {x.get('id')}: {x.get('hypothesis')} Correction: {x.get('correction')}" for x in fa]
    return lines + [""]


def render_candidates(candidates: list[dict]) -> list[str]:
    lines = ["| Candidate | Parent | Substitution | Status | E_hull (eV/atom) | Voltage (V) | Capacity (mAh/g) | "
             "Energy density (Wh/kg) | Volume change (%) |", "|---|---|---|---|---|---|---|---|---|"]
    for c in candidates:
        s = c.get("substitution") or {}
        sub = f"{s.get('remove')}→{s.get('add')} ×{s.get('count')}" + (f", −{s['li_vacancies']} Li" if s.get("li_vacancies") else "")
        status = c["status"] if c["status"] != "rejected" else f"rejected ({c.get('rejected_at')})"
        lines.append(f"| {c.get('formula') or c['id']} ({c['id']}) | {c.get('parent_formula') or c.get('parent')} | {sub} | "
                     f"{status} | {_n(c.get('e_hull'), '.3f')} | {_n(c.get('voltage_V'), '.2f')} | "
                     f"{_n(c.get('capacity_mAh_g'), '.0f')} | {_n(c.get('energy_density_Wh_kg'), '.0f')} | "
                     f"{_n(c.get('volume_change_pct'), '.1f')} |")
    return lines + [""]


def _n(x, f):
    return "—" if x is None else format(x, f)


# --- stages after the iterations: reviews, ranking, report ----------------------------------------------------------

REVIEW_FIELDS = ("formula", "parent_formula", "substitution", "e_hull", "e_hull_per_substitution", "decomposition",
                 "li_removed", "li_total", "voltage_V", "capacity_mAh_g", "energy_density_Wh_kg", "volume_change_pct",
                 "parent_voltage_V", "parent_capacity_mAh_g", "parent_energy_density_Wh_kg", "parent_volume_change_pct")


def review_system() -> str:
    return f"""You are a materials scientist reviewing ONE candidate cobalt-free cathode for lithium-ion batteries, found by the AutoLab agent. It passed every filter computed by the code: E_hull <= {config.CATHODE_EHULL_MAX} eV/atom (UMA energies, stable MP phases relaxed with UMA), average voltage {config.CATHODE_VOLTAGE_MIN}-{config.CATHODE_VOLTAGE_MAX} V, theoretical capacity >= {config.CATHODE_CAPACITY_MIN:.0f} mAh/g, volume change <= {config.CATHODE_VOLUME_CHANGE_MAX:.0f} %.
Fields: formula, parent and substitution; e_hull and e_hull_per_substitution; decomposition; li_removed / li_total (Li removed on charge); voltage_V (average over that charge), capacity_mAh_g, energy_density_Wh_kg, volume_change_pct; parent_* (the parent computed the same way); comparisons computed by the code.
Write 1 to 3 strengths and 1 to 3 risks, each one short sentence grounded in these numbers or in well-known chemistry (redox couples, Jahn-Teller Mn3+, Mn dissolution, electronic conductivity of phosphates, cost or toxicity of an element). Quote numbers only from the fields or comparisons; never compute or compare values yourself. Give md_priority "high", "medium" or "low": the priority of this candidate for an experimental or DFT follow-up. Voltage profiles, Li diffusion and cycling were not computed: do not claim them.
Reply with JSON only, exactly this shape: {template("candidate_analysis")}"""


def candidate_analyses(camp: Campaign) -> dict:
    """Muse Spark Open reviews each passed candidate, in parallel (strengths, risks, priority); a failed call only
    leaves that candidate without a review."""
    from concurrent.futures import ThreadPoolExecutor

    from autolab.llm.client import BudgetExceeded, LLMError

    client = getattr(camp.agent, "analyst", None)
    eligible = sorted(camp.passed(), key=rank_key)
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


def ranking(camp: Campaign) -> dict:
    """Passed candidates by energy density (voltage x capacity), then E_hull per substitution."""
    ranked = sorted(camp.passed(), key=rank_key)
    errors, error_bar = {}, getattr(getattr(camp.agent, "tools", None), "ehull_error", None)
    for c in ranked:  # error bar of the E_hull: UMA vs DFT on the known compounds of its system (cached per system)
        f = c.get("formula")
        if f not in errors:
            try:
                errors[f] = error_bar(f) if error_bar and f else None
            except Exception:  # e.g. references not relaxed in the cache: the E_hull stays, without its error bar
                errors[f] = None
        e = errors[f]
        c["e_hull_error"] = e if e and e.get("available", True) else None
    out = {"ranking": [c["id"] for c in ranked], "finalists": [c["id"] for c in ranked[:config.CATHODE_FINALISTS_MAX]],
           "excluded": {}}
    out["summary"] = {"finalists": out["finalists"]}
    return out


def novelty(camp: Campaign) -> dict:
    """Literature check of the finalists (web search, Muse Spark), a known cathode first as a control."""
    from autolab.agent.novelty import novelty_check
    from autolab.store.cache import JsonCache

    finalists = camp.outputs.get("ranking", {}).get("finalists") or []
    client = getattr(camp.agent, "novelty_client", None)
    if not finalists or client is None:
        reason = "no finalist" if not finalists else "no web-search client (novelty check disabled)"
        return {"control": None, "candidates": [], "stopped": None, "skipped": reason, "summary": {"skipped": reason}}
    by_id = camp.by_id
    res = novelty_check([{**by_id[i], "kind": "cathode"} for i in finalists], client,
                        control=config.CATHODE_NOVELTY_CONTROL, cache=JsonCache(config.CACHE_DIR / "novelty"))
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


def vs_parent(c: dict) -> dict | None:
    """The candidate against its parent computed the same way: differences, and whether the voltage difference is
    beyond the model's error (config.CATHODE_VOLTAGE_SIGNIFICANT_V); decided by the code, not by the model."""
    if c.get("voltage_V") is None or c.get("parent_voltage_V") is None:
        return None
    dv = round(c["voltage_V"] - c["parent_voltage_V"], 3)
    beyond = abs(dv) > config.CATHODE_VOLTAGE_SIGNIFICANT_V
    return {"voltage_difference_V": dv, "voltage_difference_beyond_model_error": beyond,
            "model_voltage_error_V": config.CATHODE_VOLTAGE_SIGNIFICANT_V,
            "capacity_difference_mAh_g": round(c["capacity_mAh_g"] - c["parent_capacity_mAh_g"], 1),
            "energy_density_difference_Wh_kg": round(c["energy_density_Wh_kg"] - c["parent_energy_density_Wh_kg"], 0),
            "verdict": ("higher voltage than its parent" if beyond and dv > 0 else "lower voltage than its parent"
                        if beyond else "comparable to its parent within the model's voltage error")}


def render_ranking(out: dict, result: dict) -> list[str]:
    pool = _pool(result)
    lines = ["## Final ranking", "", "Order: energy density (voltage x theoretical capacity), then E_hull per "
             "substitution. Candidates are computational predictions, not proven materials.", ""]
    if not out["ranking"]:
        return lines + ["No candidate passed all filters.", ""]
    for i, cid in enumerate(out["ranking"], 1):
        c = pool[cid]
        star = " **finalist**" if cid in out["finalists"] else ""
        err = c.get("e_hull_error")
        pm = f" (E_hull error bar ± {err['mae_eV_per_atom']:.3f} eV/atom)" if err else ""
        lines.append(f"{i}. {cid} {c['formula']}{star}: {_numbers(c)}{pm} (parent {c.get('parent_formula')}: "
                     f"{_n(c.get('parent_voltage_V'), '.2f')} V, {_n(c.get('parent_energy_density_Wh_kg'), '.0f')} Wh/kg)")
    return lines + [""]


METHODS = [
    ("Candidate proposals and decisions", "Meta Muse Spark (reasoning model), with comparisons computed by the code"),
    ("Structure relaxation and energies", "Meta FAIR UMA (uma-s-1p2, OMat head), atoms and cell relaxed, MP2020 "
                                         "corrections for the hull; references from Materials Project relaxed with UMA"),
    ("Thermodynamic stability", "energy above the convex hull of the stable known phases of the system; kept if <= "
                                f"{config.CATHODE_EHULL_MAX} eV/atom; error bar measured against DFT (Materials Project) "
                                "on the known compounds of the same system"),
    ("Voltage, capacity, energy density", "the Li that charge neutrality allows removed, delithiated cell relaxed with "
                                          "UMA; average voltage from the UMA energies and Li metal; theoretical "
                                          "capacity from the Li removed (calibrated on four known cathodes)"),
    ("Volume change", "lithiated and delithiated cells, both relaxed with UMA"),
    ("Independent reviews", "Meta Muse Spark Open, one review per passed candidate, in parallel"),
    ("Literature check", "Meta Muse Spark with web search; a known cathode (LiNi0.5Mn1.5O4) checked first as a control"),
    ("Error-driven loop", "each iteration's failures, with their numbers, go back to the proposing model, which explains "
                          "them as hypotheses and corrects its next proposals"),
    ("Plain-language summaries", "Meta Muse Glimmer"),
]

REPORT_SYSTEM = """You write the final report of a computational search for cobalt-free cathode materials, for scientists and for readers who are not specialists. The code gives you the comparison table of the finalists (the first one is the champion: the highest energy density among those that passed every filter), the candidates rejected with their reasons, and what was not computed.
Rules:
- Use only the numbers of the table, quoted exactly with their units; never invent or estimate a value. A missing value was not computed: say so.
- The energy above the hull comes with its error bar when given (e_hull_error_eV_per_atom: mean UMA-vs-DFT difference on the known compounds of its system): quote it with the value.
- champion_reasons: why the champion is preferred, each reason tied to numbers of the table, including the comparison with its parent computed the same way.
- Compare a finalist with its parent only through vs_parent: when voltage_difference_beyond_model_error is false, write that its voltage and energy density are comparable to the parent within the model's error (quote model_voltage_error_V), never that it improves on it; the capacity difference comes from the composition and may be stated as it is.
- novelty (when given): "published" (already reported), "related" (close family already studied) or "none_found" (this search found nothing; never "new to science").
- tradeoffs: its compromises and weaknesses. uncertainties: what limits the confidence (UMA energies instead of DFT, average voltage only, ordering of the substituted sites, magnetism not explicit).
- validation: experiments or calculations to confirm it (e.g. DFT+U voltages, synthesis and XRD, galvanostatic cycling), each with "basis": "documented" (standard practice) or "hypothesis".
- synthesis: possible routes, each with "basis": "documented" only for well-established routes of this family (e.g. solid-state reaction, sol-gel for spinels, carbon coating of phosphates), else "hypothesis".
- limitations: properties not studied. The candidates are computational predictions, not proven materials.
- Write readable prose, numbers as given, units written normally (V, mAh/g, Wh/kg, eV/atom). Do not name AI models or providers. Plain English, short sentences.
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
                "e_hull_error_basis": (f"mean absolute UMA-vs-DFT difference on {c['e_hull_error']['n']} known compounds "
                                       f"of {c['e_hull_error']['system']}" if c.get("e_hull_error") else None),
                "decomposition": c.get("decomposition"), "li_removed": c.get("li_removed"), "li_total": c.get("li_total"),
                "voltage_V": c.get("voltage_V"), "capacity_mAh_g": c.get("capacity_mAh_g"),
                "energy_density_Wh_kg": c.get("energy_density_Wh_kg"), "volume_change_pct": c.get("volume_change_pct"),
                "parent_voltage_V": c.get("parent_voltage_V"), "parent_capacity_mAh_g": c.get("parent_capacity_mAh_g"),
                "parent_energy_density_Wh_kg": c.get("parent_energy_density_Wh_kg"),
                "parent_volume_change_pct": c.get("parent_volume_change_pct"), "vs_parent": vs_parent(c),
                "novelty": c.get("novelty"), "review": c.get("analysis")}

    rows = [_rounded(row(by_id[i])) for i in finalists]
    rejected = {c["id"]: f"{c.get('formula')}: {c.get('rejected_at')}: {c.get('reason')}" for c in camp.candidates
                if c.get("status") == "rejected"}
    out = {"completeness": "complete", "missing_steps": [], "champion": rows[0]["id"], "finalists": rows,
           "excluded": rejected, "methods": [{"step": a, "method": b} for a, b in METHODS],
           "not_computed": config.CATHODE_NOT_COMPUTED, "narrative": None}
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
    champ = rows[0]
    lines = ["## Final scientific report", ""]
    if n.get("executive_summary"):
        lines += ["### Executive summary", "", n["executive_summary"], ""]
    lines += ["### Comparison of the finalists", "", "| | " + " | ".join(r["formula"] for r in rows) + " |",
              "|---|" + "---|" * len(rows)]
    sub = lambda s: f"{s.get('remove')}→{s.get('add')} ×{s.get('count')}" + (f", −{s['li_vacancies']} Li" if s.get("li_vacancies") else "")
    fields = [("Parent cathode", lambda r: r.get("parent") or "—"), ("Substitution", lambda r: sub(r.get("substitution") or {})),
              ("Space group", lambda r: r.get("space_group") or "—"),
              ("E_hull (eV/atom)", lambda r: _n(r.get("e_hull_eV_per_atom"), ".3f") + (
                  f" ± {r['e_hull_error_eV_per_atom']:.3f}" if r.get("e_hull_error_eV_per_atom") is not None else "")),
              ("Li removed on charge", lambda r: f"{r.get('li_removed')} of {r.get('li_total')}"),
              ("Average voltage (V)", lambda r: f"{_n(r.get('voltage_V'), '.2f')} (parent {_n(r.get('parent_voltage_V'), '.2f')})"),
              ("Theoretical capacity (mAh/g)", lambda r: f"{_n(r.get('capacity_mAh_g'), '.0f')} (parent {_n(r.get('parent_capacity_mAh_g'), '.0f')})"),
              ("Energy density (Wh/kg)", lambda r: f"{_n(r.get('energy_density_Wh_kg'), '.0f')} (parent {_n(r.get('parent_energy_density_Wh_kg'), '.0f')})"),
              ("Volume change on charge (%)", lambda r: f"{_n(r.get('volume_change_pct'), '.1f')} (parent {_n(r.get('parent_volume_change_pct'), '.1f')})"),
              ("Against its parent", lambda r: (r.get("vs_parent") or {}).get("verdict") or "—"),
              ("Literature", lambda r: r.get("novelty") or "not checked")]
    for label, f in fields:
        lines.append(f"| {label} | " + " | ".join(str(f(r)) for r in rows) + " |")
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


def _pool(result: dict) -> dict[str, dict]:
    pool = {c["id"]: c for c in result.get("prior", [])}
    pool.update({c["id"]: c for r in result["iterations"] for c in r["candidates"]})
    return pool


def make_domain() -> Domain:
    return Domain(
        name="cathode", goal=config.CATHODE_GOAL, parents=tuple(config.CATHODE_PARENTS),
        make_tools=lambda: CathodeTools(not_run=[]), evaluate=evaluate, proposal_messages=proposal_messages,
        analysis_messages=analysis_messages, comparisons=comparisons, for_model=FOR_MODEL, rank_key=rank_key,
        feedback=feedback, render_feedback=render_feedback,
        stages=(Stage("candidate_analyses", candidate_analyses, render_candidate_analyses),
                Stage("ranking", ranking, render_ranking),
                Stage("novelty", novelty, render_novelty),
                Stage("report", report, render_report)),
        thresholds=THRESHOLDS, render_candidates=render_candidates)


register("cathode", make_domain)
