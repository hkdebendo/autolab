"""Blind benchmark of the cathode funnel (config.CATHODE_BENCHMARK): known compounds go through the same steps as a
candidate (charge neutrality and cobalt, removable Li, UMA relaxation, E_hull with their own composition removed from
the hull, charge), never shown to the model; each outcome is compared with the one fixed before the runs."""

from __future__ import annotations

import time

from autolab import config
from autolab.analysis.cathode import cathode_charge_check, removable_li
from autolab.domains.cathode import NO_LI, evaluate_structures


def evaluate_known(entry: dict, structure, tools, events, budget=None) -> dict:
    """One known compound through the cathode funnel (no parent, no novelty step: it is known by design)."""
    t0 = time.perf_counter()
    formula = structure.composition.reduced_formula
    out = {"id": entry["id"], "parent": None, "parent_formula": None, "substitution": None, "formula": formula,
           "status": "rejected", "rejected_at": None, "reason": None, "e_hull": None, "voltage_V": None,
           "capacity_mAh_g": None, "energy_density_Wh_kg": None, "volume_change_pct": None}

    def emit(step, **data):
        events.emit("candidate", step, data, entry["id"])

    def finish(status="rejected", step=None, reason=None):
        out.update(status=status, rejected_at=step, reason=reason, seconds=round(time.perf_counter() - t0, 1))
        emit("done", status=status, rejected_at=step, reason=reason)
        return out

    verdict = cathode_charge_check(structure)
    emit("generate", accepted=verdict["ok"], formula=formula, charge=verdict["charge"], arrangements=1,
         reason=verdict["reason"])
    if not verdict["ok"]:
        return finish(step="generate", reason=verdict["reason"])
    if removable_li(structure) == 0:
        return finish(step="voltage", reason=NO_LI)
    return evaluate_structures(out, [structure], None, tools, emit, finish, budget, hidden_formulas=frozenset({formula}))


def outcome(res: dict) -> str:
    return "passed" if res["status"] == "passed" else res.get("rejected_at") or res["status"]


def summarize(rows: list[dict]) -> dict:
    """Agreement with the expected outcomes, per group."""
    groups: dict[str, dict] = {}
    for r in rows:
        g = groups.setdefault(r["group"], {"n": 0, "as_expected": 0})
        g["n"] += 1
        g["as_expected"] += r["outcome"] == r["expected"]
    return {"groups": groups, "as_expected": sum(r["outcome"] == r["expected"] for r in rows), "n": len(rows)}


def render(rows: list[dict], summary: dict) -> str:
    lines = ["# Blind benchmark of the cathode funnel", "",
             "Known compounds go through the same steps as a candidate (no cobalt, charge neutrality, removable Li, UMA "
             "relaxation, E_hull with their own composition removed from the hull, charge), never shown to the model. "
             "Expected outcomes fixed before the runs (config.CATHODE_BENCHMARK).", "",
             "| Compound | Group | Expected | Outcome | E_hull (eV/atom) | Voltage (V) | Capacity (mAh/g) | Volume change (%) | Why |",
             "|---|---|---|---|---|---|---|---|---|"]
    f = lambda x, d: "—" if x is None else format(x, d)
    for r in rows:
        mark = "✅" if r["outcome"] == r["expected"] else "❌"
        lines.append(f"| {r['formula']} ({r['id']}) | {r['group']} | {r['expected']} | {mark} {r['outcome']} | "
                     f"{f(r.get('e_hull'), '.3f')} | {f(r.get('voltage_V'), '.2f')} | {f(r.get('capacity_mAh_g'), '.0f')} | "
                     f"{f(r.get('volume_change_pct'), '.1f')} | {r['why']} |")
    lines += ["", "Agreement: " + ", ".join(f"{g} {v['as_expected']}/{v['n']}" for g, v in summary["groups"].items())
              + f"; total {summary['as_expected']}/{summary['n']}.", ""]
    return "\n".join(lines)
