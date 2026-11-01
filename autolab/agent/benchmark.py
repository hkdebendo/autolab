"""Validation benchmark (roadmap step 2): known compounds through the same funnel, judged blind.

Each compound comes from Materials Project and goes through the funnel steps of a candidate
(pipeline.evaluate_structures): UMA relaxation, E_hull against UMA references of its system with every phase
of its own composition removed (as if it were new), GapModel band gap; then window and passivation against Li
metal as in the electrodes stage, then (md_check) Li diffusion by MD at the screening settings against beta-Li3PS4.
The language model never sees them. Good electrolytes should pass, bad compounds (electronic conductors, unstable
phases) and hard negatives (stable insulators that conduct Li poorly: only the diffusion test can reject them) should
be rejected; the result is reported as it is.
"""

from __future__ import annotations

import time
from typing import Callable

from autolab import config
from autolab.agent.events import EventLog


def evaluate_known(material_id: str, expected: str, note: str, tools, get_structure: Callable,
                   events: EventLog | None = None, budget=None, group: str | None = None) -> dict:
    """One known compound through the funnel and the Li-metal check. expected: "pass" or "reject"; group: "good",
    "bad" or "hard" (default from expected)."""
    from autolab.agent.pipeline import evaluate_structures
    from autolab.sim.backend import BudgetExceeded

    events = events or EventLog()
    s = get_structure(material_id)
    formula = s.composition.reduced_formula
    cid = f"bench-{material_id}"
    t0 = time.perf_counter()
    out = {"id": cid, "material_id": material_id, "formula": formula, "expected": expected, "note": note,
           "group": group or ("good" if expected == "pass" else "bad"),
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
    _outcome(out)
    out["funnel_outcome"] = "pass" if out["funnel_status"] == "passed" else "reject"
    return out


def _outcome(out: dict) -> None:
    out["outcome"] = "pass" if out["status"] == "passed" else "reject"
    out["correct"] = out["outcome"] == out["expected"]


def md_jobs(rows: list[dict], reference_job: dict) -> list[dict]:
    """The reference (beta-Li3PS4) then every compound still passing, compared with it (dynamics.md_verdicts)."""
    from autolab.agent.dynamics import with_md_gpu

    jobs = [{**reference_job, "kind": "parent"}]
    jobs += [{"id": r["id"], "formula": r["formula"], "kind": "candidate", "parent": reference_job["id"],
              "atoms": r["relaxed_atoms"]} for r in rows if r["status"] == "passed"]
    return with_md_gpu(jobs)


def md_check(rows: list[dict], md_rows: list[dict], reference_formula: str = "Li3PS4") -> None:
    """Apply the diffusion verdicts (md_verdicts rows of md_jobs) to the benchmark rows: a compound slower than the
    reference by more than MD_TIE_SIGMA combined errors, without Li hop, or whose framework moves is rejected."""
    by_id = {r["id"]: r for r in rows}
    for m in md_rows:
        r = by_id.get(m["id"]) if m.get("kind") == "candidate" else None
        if r is None:
            continue
        v = m.get("vs_parent") or {}
        r.update(D_cm2_per_s=m["D_cm2_per_s"], D_sem_cm2_per_s=m["D_sem_cm2_per_s"], D_ratio_to_reference=v.get("ratio"),
                 D_ratio_err=v.get("ratio_err"), md_verdict=v.get("verdict") or "undetermined",
                 md_framework_intact=(m.get("framework") or {}).get("intact"))
        if m["conduction"] == "excluded":
            reason = m["conduction_reason"].replace("its parent", reference_formula)
            r.update(status="rejected", rejected_at="molecular_dynamics", reason=reason)
        _outcome(r)


def summarize(rows: list[dict]) -> dict:
    """Good compounds passing and bad ones rejected, after the funnel and after the Li-metal check."""
    good = [r for r in rows if r["expected"] == "pass"]
    bad = [r for r in rows if r["expected"] == "reject" and r.get("group", "bad") == "bad"]
    hard = [r for r in rows if r.get("group") == "hard"]
    by_step = lambda group: {s: sum(r.get("rejected_at") == s for r in group if r["outcome"] == "reject")
                             for s in sorted({r.get("rejected_at") for r in group if r["outcome"] == "reject"})}
    return {
        "good": len(good), "bad": len(bad), "hard": len(hard),
        "good_pass_funnel": sum(r["funnel_outcome"] == "pass" for r in good),
        "good_pass_all": sum(r["outcome"] == "pass" for r in good),
        "bad_rejected_funnel": sum(r["funnel_outcome"] == "reject" for r in bad),
        "bad_rejected_all": sum(r["outcome"] == "reject" for r in bad),
        "hard_rejected_funnel": sum(r["funnel_outcome"] == "reject" for r in hard),
        "hard_rejected_all": sum(r["outcome"] == "reject" for r in hard),
        "rejected_by": {"bad": by_step(bad), "hard": by_step(hard)},
    }


def render(rows: list[dict], summary: dict) -> str:
    v = lambda x, f=".3f": "—" if x is None else format(x, f)
    s = summary
    lines = ["# Validation benchmark: known compounds through the funnel, judged blind", "",
             "Each compound is relaxed by UMA and judged exactly like a candidate: E_hull against UMA + MP2020 "
             "references of its system with its own composition removed (as if it were new), GapModel band gap, then "
             "window and passivation against Li metal. The language model never sees them.", "",
             f"- Good electrolytes passing the funnel (E_hull <= {config.EHULL_SYNTHESIZABLE} eV/atom, gap >= "
             f"{config.BANDGAP_MIN} eV): **{s['good_pass_funnel']} / {s['good']}**; also passing the Li-metal check: "
             f"**{s['good_pass_all']} / {s['good']}**",
             f"- Bad compounds rejected by the funnel: **{s['bad_rejected_funnel']} / {s['bad']}**; after the Li-metal "
             f"check: **{s['bad_rejected_all']} / {s['bad']}**",
             *([f"- Hard negatives (stable insulators, poor Li conductors) rejected by the funnel: "
                f"**{s['hard_rejected_funnel']} / {s['hard']}**; after the Li-metal check and the diffusion test "
                f"against beta-Li3PS4: **{s['hard_rejected_all']} / {s['hard']}**"] if s.get("hard") else []),
             *([f"- Rejected by step: bad {s['rejected_by']['bad']}; hard {s['rejected_by']['hard']}"]
               if s.get("rejected_by") else []), "",
             "| Compound | Group | MP id | Expected | E_hull (eV/atom) | Gap optB88 / mBJ (eV) | Against Li metal | "
             "Window (V) | D at 600 K / D(beta-Li3PS4) | Result | Correct |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        w = r.get("window")
        window = "—" if not w else (f"{v(w['v_low'], '.2f')}–{v(w['v_high'], '.2f')}" if w["stable"] else "zero width")
        gap = "—" if r["gap_optb88"] is None else f"{r['gap_optb88']:.2f} / {r['gap_mbj']:.2f}"
        result = "pass" if r["outcome"] == "pass" else f"rejected at {r['rejected_at']}: {r['reason']}"
        ratio = ("—" if r.get("D_ratio_to_reference") is None else
                 f"{r['D_ratio_to_reference']:.2f} ± {r['D_ratio_err']:.2f} ({r['md_verdict']})")
        if r.get("md_verdict") == "undetermined":
            ratio = "no Li hop" if (r.get("D_cm2_per_s") or 0) <= 0 else "undetermined"
        lines.append(f"| {r['note']} | {r.get('group', '—')} | {r['material_id']} | {r['expected']} | {v(r['e_hull'])} | "
                     f"{gap} | {r.get('passivation') or '—'} | {window} | {ratio} | {result} | "
                     f"{'yes' if r['correct'] else '**no**'} |")
    return "\n".join(lines)
