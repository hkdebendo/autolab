"""Research domains of the agent loop (SPEC 6): the loop is generic, a domain says what it does.

A domain gives:
- the funnel of one candidate (`evaluate`), run during the iterations, and the tools it calls;
- the prompts (proposal, analysis) and the candidate fields the model sees, with the code-computed comparisons;
- the stages run once after the iterations, in order, on the whole pool (e.g. electrodes, molecular dynamics,
  final ranking, novelty check), each deciding from the rules of config.py;
- the config thresholds it decides with (listed in the report).

Only "electrolyte" exists (solid electrolytes for Li-metal batteries). A new domain (e.g. cobalt-free cathodes)
is a new module in this package that builds its Domain and calls register(); the loop does not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Stage:
    """One step after the iterations. `run(campaign)` returns a JSON-serialisable dict (with "summary" for the
    event, and "stopped" when a budget or rule stopped it); `render(output, result)` gives report lines."""

    name: str
    run: Callable[["Campaign"], dict]
    render: Callable[[dict, dict], list[str]] | None = None


@dataclass(frozen=True)
class Domain:
    name: str
    goal: str
    parents: tuple[str, ...]
    make_tools: Callable[[], Any]  # injectable expensive steps (tests replace them)
    evaluate: Callable  # (candidate_id, parent_id, parent_structure, substitution, tools, events, budget) -> dict
    proposal_messages: Callable  # (goal, parents, history, max_proposals) -> messages
    analysis_messages: Callable  # (goal, iteration, hypothesis, results, history, comparisons) -> messages
    comparisons: Callable[[list[dict]], list[dict]]
    for_model: tuple[str, ...]  # candidate fields sent to the model
    rank_key: Callable[[dict], Any]  # order of the passed candidates after the funnel (best first)
    stages: tuple[Stage, ...] = ()
    thresholds: tuple[str, ...] = ()  # config names the domain decides with
    render_candidates: Callable[[list[dict]], list[str]] | None = None  # report table of one iteration


@dataclass
class Campaign:
    """What the stages share: the agent (models, events, budgets, tools), the pool of evaluated candidates
    (this run and earlier ones) and the outputs of the stages already run."""

    agent: Any
    goal: str
    candidates: list[dict]
    outputs: dict[str, dict] = field(default_factory=dict)

    @property
    def tools(self):
        return self.agent.tools

    @property
    def budget(self):
        return self.agent.budget

    @property
    def by_id(self) -> dict[str, dict]:
        return {c["id"]: c for c in self.candidates}

    def passed(self) -> list[dict]:
        return [c for c in self.candidates if c.get("status") == "passed"]

    def emit(self, stage: str, step: str, candidate_id: str | None = None, **data) -> None:
        self.agent.events.emit("candidate" if candidate_id else "stage", f"{stage}:{step}", data, candidate_id)

    def ask(self, messages: list[dict], schema: str, step: str) -> dict:
        return self.agent.ask(messages, schema, step)


_DOMAINS: dict[str, Callable[[], Domain]] = {}


def register(name: str, factory: Callable[[], Domain]) -> None:
    _DOMAINS[name] = factory


def get_domain(name: str) -> Domain:
    if name == "electrolyte" and name not in _DOMAINS:
        from autolab.domains import electrolyte  # noqa: F401  (registers itself)
    if name not in _DOMAINS:
        raise ValueError(f"unknown domain {name!r} (known: {', '.join(sorted(_DOMAINS)) or 'electrolyte'})")
    return _DOMAINS[name]()
