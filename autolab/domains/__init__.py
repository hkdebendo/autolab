"""Research domains of the agent loop (SPEC 6): the loop is generic, a domain says what it does.

A domain gives:
- the funnel of one candidate (`evaluate`), run during the iterations, and the tools it calls;
- the prompts (proposal, analysis) and the candidate fields the model sees, with the code-computed comparisons;
- the stages run once after the iterations, in order, on the whole pool (e.g. electrodes, molecular dynamics,
  final ranking, novelty check), each deciding from the rules of config.py;
- the slow tests run inside each iteration on its own candidates (config.FEEDBACK_LOOP), and the feedback built
  from their results (failures with their measurements), given to the model before it analyses the iteration and
  proposes the next one (error-driven design);
- the config thresholds it decides with (listed in the report).

Two domains: "electrolyte" (solid electrolytes for Li-metal batteries) and "cathode" (cobalt-free cathodes for Li-ion
batteries). A domain is a module of this package that builds its Domain and calls register(); the loop does not change.
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
    analysis_messages: Callable  # (goal, iteration, hypothesis, results, history, comparisons, feedback) -> messages
    comparisons: Callable[[list[dict]], list[dict]]
    for_model: tuple[str, ...]  # candidate fields sent to the model
    rank_key: Callable[[dict], Any]  # order of the passed candidates after the funnel (best first)
    stages: tuple[Stage, ...] = ()
    thresholds: tuple[str, ...] = ()  # config names the domain decides with
    render_candidates: Callable[[list[dict]], list[str]] | None = None  # report table of one iteration
    iteration_stages: tuple[Stage, ...] = ()  # slow tests run in each iteration on its candidates (FEEDBACK_LOOP)
    feedback: Callable[[list[dict]], list[dict]] | None = None  # iteration candidates -> results of the slow tests
    render_feedback: Callable[[dict], list[str]] | None = None  # iteration record -> report lines of its feedback


@dataclass
class Campaign:
    """What the stages share: the agent (models, events, budgets, tools), the pool of evaluated candidates
    (this run and earlier ones) and the outputs of the stages already run."""

    agent: Any
    goal: str
    candidates: list[dict]
    outputs: dict[str, dict] = field(default_factory=dict)
    iteration: int | None = None  # set when the stages run inside one iteration, on its candidates only
    settings: dict = field(default_factory=dict)  # per-campaign limits (e.g. md_select_max)

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
        if self.iteration is not None:
            data = {**data, "iteration": self.iteration}
        self.agent.events.emit("candidate" if candidate_id else "stage", f"{stage}:{step}", data, candidate_id)

    def ask(self, messages: list[dict], schema: str, step: str) -> dict:
        return self.agent.ask(messages, schema, step)


_DOMAINS: dict[str, Callable[[], Domain]] = {}


def register(name: str, factory: Callable[[], Domain]) -> None:
    _DOMAINS[name] = factory


def get_domain(name: str) -> Domain:
    if name == "electrolyte" and name not in _DOMAINS:
        from autolab.domains import electrolyte  # noqa: F401  (registers itself)
    if name == "cathode" and name not in _DOMAINS:
        from autolab.domains import cathode  # noqa: F401  (registers itself)
    if name not in _DOMAINS:
        raise ValueError(f"unknown domain {name!r} (known: electrolyte, cathode)")
    return _DOMAINS[name]()
