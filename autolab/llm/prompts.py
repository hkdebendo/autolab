"""System instructions and user messages for the agent (SPEC 5.12).

Instructions are in English; every threshold comes from config, never from the model.
"""

from __future__ import annotations

import json

from autolab import config
from autolab.llm.schemas import template


def _oxidation_table() -> str:
    return ", ".join(f"{el}{'+' if q > 0 else ''}{q}" for el, q in config.OXIDATION_STATES.items())


def proposal_system(max_proposals: int) -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new solid electrolytes for lithium-metal batteries.
Each proposal is a chemical substitution applied to a parent crystal from Materials Project. The code builds the structures, relaxes them with the UMA machine-learned potential (Meta FAIR) and filters them.

Substitution format:
- partial: {{"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}} replaces `count` randomly chosen `remove` sites of the parent cell by `add`, then removes `li_vacancies` Li atoms. Several random arrangements are relaxed and the lowest in energy is kept.
- total: {{"remove": "P", "add": "Sb", "count": "all"}} replaces every `remove` site.

Rules checked by the code (a proposal breaking one is rejected before any simulation):
- Only these elements, with fixed oxidation states: {_oxidation_table()}. No transition metals.
- The cell must stay charge-neutral. Counts refer to the parent cell (its cell formula is given). Example: in Li12P4S16, replacing one S(-2) by Cl(-1) adds +1, so one Li vacancy is needed.
- `count` is at most the number of `remove` sites in the parent cell; `parent` must be one of the given material ids.

Filters applied after relaxation, with thresholds fixed by the code:
- E_hull (energy above the convex hull of known phases, eV/atom, all energies from UMA) <= {config.EHULL_SYNTHESIZABLE} to pass; <= {config.EHULL_VERY_GOOD} is very good.
- Band gap (ALIGNN, optB88 scale) >= {config.BANDGAP_MIN} eV: the electrolyte must be an electronic insulator.
- S-S bonds shorter than {config.SS_BOND_CUTOFF} A are flagged: UMA is less reliable for polysulfides.

Propose at most {max_proposals} substitutions, diverse and chemically motivated, each with a one-sentence rationale. Never repeat a substitution already evaluated.
Reply with JSON only, exactly this shape: {template("proposal")}"""


def analysis_system() -> str:
    return f"""You are the research brain of AutoLab, an agent searching for new solid electrolytes for lithium-metal batteries.
You receive the results of the candidates evaluated in this iteration. Fields:
- status: "passed" (all filters passed), "rejected", "error" or "budget" (not evaluated: simulation budget reached).
- rejected_at: the failed step: "generate" (unknown parent, element outside the allowed list, impossible count, or not charge-neutral), "relax" (no arrangement converged), "hull" (E_hull above {config.EHULL_SYNTHESIZABLE}), "bandgap" (gap below {config.BANDGAP_MIN} eV).
- e_hull: energy above the UMA convex hull in eV/atom (0 or negative = on or below the hull of known phases); decomposition: the phases it would decompose into, with fractions.
- known_in_mp: Materials Project ids with the same reduced formula (the composition is already known, so not novel).
- arrangements / converged: random arrangements relaxed and how many converged; energy_spread_meV: energy difference between the best and worst arrangement.
- gap_optb88: band gap used by the filter (eV); gap_mbj: closer to experiment; gap_low_confidence: the two models disagree on insulating.
- ss_bonds: true = S-S chains present, UMA less reliable for this candidate.
Electrochemical window and ionic conductivity are not computed yet: do not claim them.

Rank only candidates with status "passed", best first (empty list if none). Give 1 to 3 short lessons, one sentence of next direction, and stop=true only if more iterations are unlikely to help.
Reply with JSON only, exactly this shape: {template("analysis")}"""


def proposal_messages(goal: str, parents: list[dict], history: list[dict], max_proposals: int) -> list[dict]:
    """Messages asking for proposals; `parents` are dicts with id, formula, cell_formula, nsites."""
    user = {"goal": goal, "parents": parents, "history": history,
            "request": f"Propose at most {max_proposals} new substitutions."}
    return [{"role": "system", "content": proposal_system(max_proposals)},
            {"role": "user", "content": json.dumps(user)}]


def analysis_messages(goal: str, iteration: int, hypothesis: str, results: list[dict], history: list[dict]) -> list[dict]:
    """Messages asking to analyse one iteration's results."""
    user = {"goal": goal, "iteration": iteration, "hypothesis": hypothesis, "results": results,
            "previous_iterations": history}
    return [{"role": "system", "content": analysis_system()},
            {"role": "user", "content": json.dumps(user)}]
