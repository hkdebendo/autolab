"""Validation benchmark (roadmap step 2): known compounds through the same funnel, judged blind.

Each compound comes from Materials Project and goes through the funnel steps of a candidate
(pipeline.evaluate_structures): UMA relaxation, E_hull against UMA references of its system with every phase
of its own composition removed (as if it were new), ALIGNN band gap; then window and passivation against Li
metal as in the electrodes stage. The language model never sees them. Good electrolytes should pass, bad
compounds (electronic conductors, unstable phases) should be rejected; the result is reported as it is.
"""

from __future__ import annotations

import time
from typing import Callable

from autolab import config
from autolab.agent.events import EventLog


def evaluate_known(material_id: str, expected: str, note: str, tools, get_structure: Callable,
                   events: EventLog | None = None, budget=None) -> dict:
    """One known compound through the funnel and the Li-metal check. expected: "pass" or "reject"."""
    from autolab.agent.pipeline import evaluate_structures
    from autolab.sim.backend import BudgetExceeded

    events = events or EventLog()
    s = get_structure(material_id)
    formula = s.composition.reduced_formula
    cid = f"bench-{material_id}"
    t0 = time.perf_counter()
    out = {"id": cid, "material_id": material_id, "formula": formula, "expected": expected, "note": note,
           "parent": None, "substitution": None, "status": "rejected", "rejected_at": None, "reason": None,
           "arrangements": 0, "converged": 0, "energy_spread_meV": None, "n_atoms": None,
           "n_modified": len(s),  # E_hull per substitution = E_hull per atom here (nothing substituted)
           "e_hull": None, "e_hull_per_substitution": None, "decomposition": None, "skipped_references": [],
           "energy": None, "relaxed_atoms": None, "gap_optb88": None, "gap_mbj": None, "gap_low_confidence": None,
           "ss_bonds": None, "passivation": None, "window": None}

    def emit(step, **data):
        events.emit("benchmark", step, data, cid)

    def finish(status="rejected", step=None, reason=None):
        out.update(status=status, rejected_at=step, reason=reason, seconds=round(time.perf_counter() - t0, 1))
        emit("done", status=status, rejected_at=step, reason=reason)
        return out

    emit("start", material_id=material_id, formula=formula, expected=expected)
    evaluate_structures(out, [s], tools, emit, finish, budget, hidden_formulas=frozenset({formula}))
    out["funnel_status"] = out["status"]
    if out["status"] == "passed":
        try:
            wp = tools.window_passivation(out, budget)
        except BudgetExceeded as e:
            out["electrodes"] = f"not computed: {e}"
        else:
            p, w = wp["passivation"], wp["window"]
            out.update(passivation=p["verdict"], passivation_reaction_energy=p["reaction_energy"],
                       metallic_products=p["metallic_products"],
                       window={k: w.get(k) for k in ("v_low", "v_high", "stable")})
            emit("electrodes", passivation=p["verdict"], window=out["window"])
            if p["verdict"] in config.ELECTRODE_EXCLUDED_PASSIVATION:
                out.update(status="rejected", rejected_at="electrodes",
                           reason=f"{p['verdict']} against Li metal (metallic products "
                                  f"{', '.join(p['metallic_products']) or 'none'})")
    out["outcome"] = "pass" if out["status"] == "passed" else "reject"
    out["funnel_outcome"] = "pass" if out["funnel_status"] == "passed" else "reject"
    out["correct"] = out["outcome"] == expected
    return out


def summarize(rows: list[dict]) -> dict:
    """Good compounds passing and bad ones rejected, after the funnel and after the Li-metal check."""
    good = [r for r in rows if r["expected"] == "pass"]
    bad = [r for r in rows if r["expected"] == "reject"]
    return {
        "good": len(good), "bad": len(bad),
        "good_pass_funnel": sum(r["funnel_outcome"] == "pass" for r in good),
        "good_pass_all": sum(r["outcome"] == "pass" for r in good),
        "bad_rejected_funnel": sum(r["funnel_outcome"] == "reject" for r in bad),
        "bad_rejected_all": sum(r["outcome"] == "reject" for r in bad),
    }


def render(rows: list[dict], summary: dict) -> str:
    v = lambda x, f=".3f": "—" if x is None else format(x, f)
    s = summary
    lines = ["# Validation benchmark: known compounds through the funnel, judged blind", "",
             "Each compound is relaxed by UMA and judged exactly like a candidate: E_hull against UMA + MP2020 "
             "references of its system with its own composition removed (as if it were new), ALIGNN band gap, then "
             "window and passivation against Li metal. The language model never sees them.", "",
             f"- Good electrolytes passing the funnel (E_hull <= {config.EHULL_SYNTHESIZABLE} eV/atom, gap >= "
             f"{config.BANDGAP_MIN} eV): **{s['good_pass_funnel']} / {s['good']}**; also passing the Li-metal check: "
             f"**{s['good_pass_all']} / {s['good']}**",
             f"- Bad compounds rejected by the funnel: **{s['bad_rejected_funnel']} / {s['bad']}**; after the Li-metal "
             f"check: **{s['bad_rejected_all']} / {s['bad']}**", "",
             "| Compound | MP id | Expected | E_hull (eV/atom) | Gap optB88 / mBJ (eV) | Against Li metal | Window (V) | "
             "Result | Correct |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        w = r.get("window")
        window = "—" if not w else (f"{v(w['v_low'], '.2f')}–{v(w['v_high'], '.2f')}" if w["stable"] else "zero width")
        gap = "—" if r["gap_optb88"] is None else f"{r['gap_optb88']:.2f} / {r['gap_mbj']:.2f}"
        result = "pass" if r["outcome"] == "pass" else f"rejected at {r['rejected_at']}: {r['reason']}"
        lines.append(f"| {r['note']} | {r['material_id']} | {r['expected']} | {v(r['e_hull'])} | {gap} | "
                     f"{r.get('passivation') or '—'} | {window} | {result} | {'yes' if r['correct'] else '**no**'} |")
    return "\n".join(lines)
