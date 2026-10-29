"""Agent loop: hypothesis -> evaluation -> analysis (SPEC 6.2), then the stages of the domain.

The model proposes substitutions (JSON), the domain's funnel evaluates them, the model
reads the numbers and sets the next direction. Iterations stop after n, when a
budget is reached, or when the model returns stop=true. Then the domain's stages run in
order on the whole pool (this run plus earlier runs given as `prior`), each emitting its
events and deciding from config.py. No retry loops: the fallback provider is tried once
when the main one fails. The loop knows nothing of electrolytes: see autolab/domains.
"""

from __future__ import annotations

import json
import time

from pymatgen.core import Structure

from autolab import config
from autolab.agent.events import EventLog
from autolab.domains import Campaign, Domain, get_domain
from autolab.llm.client import BudgetExceeded as LLMBudgetExceeded
from autolab.llm.client import LLMError
from autolab.sim.backend import BudgetExceeded as SimBudgetExceeded
from autolab.sim.backend import RelaxBudget


class LoopStopped(RuntimeError):
    """The language models cannot continue (budget, or main and fallback both failed)."""


def _parent_info(pid: str, s: Structure) -> dict:
    return {"id": pid, "formula": s.composition.reduced_formula,
            "cell_formula": s.composition.formula.replace(" ", ""), "nsites": len(s)}


def _substitution_key(parent: str, sub: dict) -> str:
    return json.dumps([parent, sub], sort_keys=True)


class Agent:
    def __init__(self, brain, fallback=None, tools=None, events: EventLog | None = None,
                 budget: RelaxBudget | None = None, get_structure=None, domain: Domain | str | None = None,
                 novelty_client=None):
        self.domain = domain if isinstance(domain, Domain) else get_domain(domain or config.AGENT_DOMAIN)
        self.brain, self.fallback = brain, fallback
        self.novelty_client = novelty_client  # web search of the novelty stage, with its own cost cap
        self.tools = tools or self.domain.make_tools()
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
            # the reply and a reasoning summary go into the event, so that events.jsonl alone replays the run
            self.events.emit("llm", step, {**{k: v for k, v in info.items() if k != "reasoning"}, "reply": obj,
                                           "reasoning_summary": info["reasoning"][:config.EVENT_REASONING_CHARS]})
            return {"reply": obj, **info}
        raise LoopStopped("; ".join(errors) or "no language model configured")

    def run(self, goal: str | None = None, parents: list[str] | None = None,
            n_iterations: int = config.MAX_ITERATIONS,
            max_candidates: int = config.MAX_CANDIDATES_PER_ITERATION, prior: list[dict] | None = None,
            stages: bool = True) -> dict:
        """Iterations, then the domain's stages. `prior`: candidates evaluated in earlier runs (ids unique): never
        proposed again, shown to the model, and part of the pool of the stages (their computations are cached)."""
        if not 1 <= n_iterations <= config.MAX_ITERATIONS:
            raise ValueError(f"n_iterations must be 1..{config.MAX_ITERATIONS} (MAX_ITERATIONS)")
        if not 1 <= max_candidates <= config.MAX_CANDIDATES_PER_ITERATION:
            raise ValueError(f"max_candidates must be 1..{config.MAX_CANDIDATES_PER_ITERATION}")
        t0 = time.perf_counter()
        d = self.domain
        goal = goal or d.goal
        prior = list(prior or [])
        parents = parents or list(d.parents)
        structures = {pid: self.get_structure(pid) for pid in parents}
        parent_info = [_parent_info(pid, s) for pid, s in structures.items()]
        result = {"domain": d.name, "goal": goal, "parents": parent_info, "settings": {
            "n_iterations": n_iterations, "max_candidates": max_candidates, "max_relaxations": self.budget.max_new,
            "brain": getattr(self.brain, "provider", None), "fallback": getattr(self.fallback, "provider", None),
            "thresholds": {name: getattr(config, name) for name in d.thresholds}},
            "prior": prior, "iterations": [], "stages": {}, "stop_reason": "iterations done"}
        self.events.emit("loop", "start", {"goal": goal, "domain": d.name, "parents": parent_info,
                                           "prior": [c["id"] for c in prior], **result["settings"]})
        seen: set[str] = {_substitution_key(c["parent"], c["substitution"]) for c in prior if c.get("substitution")}
        history: list[dict] = []
        if prior:
            history.append({"iteration": "earlier runs",
                            "results": [{k: c.get(k) for k in d.for_model if k in c} for c in prior]})

        for it in range(1, n_iterations + 1):
            record = {"iteration": it, "proposal": None, "candidates": [], "comparisons": [], "analysis": None}
            result["iterations"].append(record)
            self.events.emit("loop", "iteration", {"iteration": it})
            try:
                record["proposal"] = self.ask(d.proposal_messages(goal, parent_info, history, max_candidates),
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
                        res = d.evaluate(cid, p["parent"], structures[p["parent"]], p["substitution"],
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

            for_model = [{k: c.get(k) for k in d.for_model if k in c} for c in record["candidates"]]
            # Comparisons over every candidate so far, so that the model never compares tables itself.
            record["comparisons"] = d.comparisons(prior + [c for r in result["iterations"] for c in r["candidates"]])
            try:
                record["analysis"] = self.ask(
                    d.analysis_messages(goal, it, proposal["hypothesis"], for_model, history, record["comparisons"]),
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
        passed = sorted((c for c in candidates if c["status"] == "passed"), key=d.rank_key)
        last = next((r["analysis"]["reply"] for r in reversed(result["iterations"]) if r["analysis"]), None)
        result["funnel_ranking"] = [c["id"] for c in passed]
        result["model_ranking"] = last["ranking"] if last else []
        if stages:
            self.run_stages(Campaign(self, goal, prior + candidates), result)
        result["final_ranking"] = result["stages"].get("ranking", {}).get("ranking", result["funnel_ranking"])
        result["usage"] = {
            "llm": {c.provider: c.tracker.summary() for c in (self.brain, self.fallback) if c is not None},
            "novelty": self.novelty_client.tracker.summary() if self.novelty_client is not None else None,
            "relaxations": {"new": self.budget.used, "limit": self.budget.max_new},
            "md": result["stages"].get("molecular_dynamics", {}).get("plan"),
            "events": len(self.events.events),
            "seconds": round(time.perf_counter() - t0, 1),
        }
        self.events.emit("loop", "stop", {"reason": result["stop_reason"], "passed": result["funnel_ranking"],
                                          "final_ranking": result["final_ranking"]})
        return result

    def run_stages(self, campaign: Campaign, result: dict) -> None:
        """The domain's stages in order. A stage that fails or is stopped by a budget does not stop the next
        ones: each reads what the previous ones left on the candidates."""
        for stage in self.domain.stages:
            self.events.emit("stage", stage.name, {"status": "start"})
            try:
                out = stage.run(campaign)
                status = "stopped" if out.get("stopped") else "done"
            except Exception as e:  # reported, never retried
                out, status = {"error": f"{type(e).__name__}: {e}"}, "error"
            campaign.outputs[stage.name] = out
            result["stages"][stage.name] = {"status": status, **out}
            self.events.emit("stage", stage.name, {"status": status, **out.get("summary", {}),
                                                   **({"error": out["error"]} if "error" in out else {})})
