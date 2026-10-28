"""Agent loop: hypothesis -> evaluation -> analysis (SPEC 6.2), minimal version.

The model proposes substitutions (JSON), the funnel evaluates them, the model
reads the numbers and sets the next direction. Stops after n iterations, when a
budget is reached, or when the model returns stop=true. No retry loops: the
fallback provider is tried once when the main one fails.
"""

from __future__ import annotations

import json
import time

from pymatgen.core import Structure

from autolab import config
from autolab.agent.compare import comparisons
from autolab.agent.events import EventLog
from autolab.agent.pipeline import Tools, evaluate_candidate
from autolab.llm import prompts
from autolab.llm.client import BudgetExceeded as LLMBudgetExceeded
from autolab.llm.client import LLMError
from autolab.sim.backend import BudgetExceeded as SimBudgetExceeded
from autolab.sim.backend import RelaxBudget

# Result fields sent back to the model (the rest stays in the report).
_FOR_MODEL = ("id", "parent", "substitution", "formula", "status", "rejected_at", "reason", "arrangements",
              "converged", "energy_spread_meV", "n_atoms", "n_modified", "e_hull", "e_hull_per_substitution",
              "decomposition", "known_in_mp", "gap_optb88", "gap_mbj", "gap_low_confidence", "ss_bonds")


class LoopStopped(RuntimeError):
    """The language models cannot continue (budget, or main and fallback both failed)."""


def _parent_info(pid: str, s: Structure) -> dict:
    return {"id": pid, "formula": s.composition.reduced_formula,
            "cell_formula": s.composition.formula.replace(" ", ""), "nsites": len(s)}


def _substitution_key(parent: str, sub: dict) -> str:
    return json.dumps([parent, sub], sort_keys=True)


class Agent:
    def __init__(self, brain, fallback=None, tools: Tools | None = None, events: EventLog | None = None,
                 budget: RelaxBudget | None = None, get_structure=None):
        self.brain, self.fallback = brain, fallback
        self.tools = tools or Tools()
        self.events = events or EventLog()
        self.budget = budget or RelaxBudget(config.MAX_RELAXATIONS_PER_RUN)
        if get_structure is None:
            from autolab.data.mp import get_structure
        self.get_structure = get_structure

    def ask(self, messages: list[dict], schema: str, step: str) -> dict:
        """JSON reply from the main model, or once from the fallback; returns reply info for the report."""
        clients = [c for c in (self.brain, self.fallback) if c is not None]
        errors = []
        for client in clients:
            kwargs = {"max_output_tokens": config.AGENT_MAX_OUTPUT_TOKENS}
            if client is self.brain:
                kwargs["reasoning_effort"] = config.AGENT_REASONING_EFFORT
            try:
                obj, replies = client.complete_json(messages, schema, **kwargs)
            except LLMBudgetExceeded as e:
                self.events.emit("llm", "budget", {"provider": client.provider, "error": str(e)})
                raise LoopStopped(str(e)) from e
            except LLMError as e:
                errors.append(f"{client.provider}: {e}")
                self.events.emit("llm", "error", {"provider": client.provider, "step": step, "error": str(e)})
                continue
            info = {
                "provider": client.provider, "attempts": len(replies),
                "reasoning": "\n\n".join(r.reasoning for r in replies if r.reasoning),
                "input_tokens": sum(r.input_tokens for r in replies),
                "output_tokens": sum(r.output_tokens for r in replies),
                "cost_usd": round(sum(r.cost_usd for r in replies), 5),
                "seconds": round(sum(r.seconds for r in replies), 1),
            }
            self.events.emit("llm", step, {k: v for k, v in info.items() if k != "reasoning"})
            return {"reply": obj, **info}
        raise LoopStopped("; ".join(errors) or "no language model configured")

    def run(self, goal: str = config.AGENT_GOAL, parents: list[str] | None = None,
            n_iterations: int = config.MAX_ITERATIONS,
            max_candidates: int = config.MAX_CANDIDATES_PER_ITERATION) -> dict:
        if not 1 <= n_iterations <= config.MAX_ITERATIONS:
            raise ValueError(f"n_iterations must be 1..{config.MAX_ITERATIONS} (MAX_ITERATIONS)")
        if not 1 <= max_candidates <= config.MAX_CANDIDATES_PER_ITERATION:
            raise ValueError(f"max_candidates must be 1..{config.MAX_CANDIDATES_PER_ITERATION}")
        t0 = time.perf_counter()
        parents = parents or list(config.AGENT_PARENTS)
        structures = {pid: self.get_structure(pid) for pid in parents}
        parent_info = [_parent_info(pid, s) for pid, s in structures.items()]
        result = {"goal": goal, "parents": parent_info, "settings": {
            "n_iterations": n_iterations, "max_candidates": max_candidates, "max_relaxations": self.budget.max_new,
            "brain": getattr(self.brain, "provider", None), "fallback": getattr(self.fallback, "provider", None)},
            "iterations": [], "stop_reason": "iterations done"}
        self.events.emit("loop", "start", {"goal": goal, "parents": parents, **result["settings"]})
        history: list[dict] = []
        seen: set[str] = set()

        for it in range(1, n_iterations + 1):
            record = {"iteration": it, "proposal": None, "candidates": [], "comparisons": [], "analysis": None}
            result["iterations"].append(record)
            self.events.emit("loop", "iteration", {"iteration": it})
            try:
                record["proposal"] = self.ask(prompts.proposal_messages(goal, parent_info, history, max_candidates),
                                              "proposal", "proposal")
            except LoopStopped as e:
                result["stop_reason"] = f"language model: {e}"
                break
            proposal = record["proposal"]["reply"]
            sim_stop = None
            for k, p in enumerate(proposal["proposals"][:max_candidates], 1):
                cid = f"it{it}-c{k}"
                key = _substitution_key(p["parent"], p["substitution"])
                if sim_stop:
                    res = {"id": cid, "parent": p["parent"], "substitution": p["substitution"], "status": "budget",
                           "reason": sim_stop}
                elif p["parent"] not in structures:
                    res = {"id": cid, "parent": p["parent"], "substitution": p["substitution"],
                           "status": "rejected", "rejected_at": "generate", "reason": "unknown parent"}
                elif key in seen:
                    res = {"id": cid, "parent": p["parent"], "substitution": p["substitution"],
                           "status": "rejected", "rejected_at": "generate", "reason": "already evaluated"}
                else:
                    seen.add(key)
                    try:
                        res = evaluate_candidate(cid, p["parent"], structures[p["parent"]], p["substitution"],
                                                 self.tools, self.events, self.budget)
                    except SimBudgetExceeded as e:
                        sim_stop = str(e)
                        res = {"id": cid, "parent": p["parent"], "substitution": p["substitution"],
                               "status": "budget", "reason": sim_stop}
                    except Exception as e:  # one broken candidate must not stop the run
                        res = {"id": cid, "parent": p["parent"], "substitution": p["substitution"],
                               "status": "error", "reason": f"{type(e).__name__}: {e}"}
                        self.events.emit("candidate", "error", {"error": res["reason"]}, cid)
                res["rationale"] = p.get("rationale")
                record["candidates"].append(res)

            for_model = [{k: c.get(k) for k in _FOR_MODEL if k in c} for c in record["candidates"]]
            # Comparisons over every candidate so far, so that the model never compares tables itself.
            record["comparisons"] = comparisons([c for r in result["iterations"] for c in r["candidates"]])
            try:
                record["analysis"] = self.ask(
                    prompts.analysis_messages(goal, it, proposal["hypothesis"], for_model, history,
                                              record["comparisons"]),
                    "analysis", "analysis")
            except LoopStopped as e:
                result["stop_reason"] = f"language model: {e}"
                break
            analysis = record["analysis"]["reply"]
            history.append({"iteration": it, "hypothesis": proposal["hypothesis"], "results": for_model,
                            "lessons": analysis["lessons"], "next_direction": analysis["next_direction"]})
            if sim_stop:
                result["stop_reason"] = f"relaxation budget: {sim_stop}"
                break
            if analysis["stop"]:
                result["stop_reason"] = "the model asked to stop"
                break

        candidates = [c for r in result["iterations"] for c in r["candidates"]]
        passed = sorted((c for c in candidates if c["status"] == "passed"),
                        key=lambda c: (c["e_hull_per_substitution"], c["e_hull"]))
        last = next((r["analysis"]["reply"] for r in reversed(result["iterations"]) if r["analysis"]), None)
        result["final_ranking"] = [c["id"] for c in passed]
        result["model_ranking"] = last["ranking"] if last else []
        result["usage"] = {
            "llm": {c.provider: c.tracker.summary() for c in (self.brain, self.fallback) if c is not None},
            "relaxations": {"new": self.budget.used, "limit": self.budget.max_new},
            "events": len(self.events.events),
            "seconds": round(time.perf_counter() - t0, 1),
        }
        self.events.emit("loop", "stop", {"reason": result["stop_reason"], "passed": result["final_ranking"]})
        return result
