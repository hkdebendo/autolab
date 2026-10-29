"""Steps of a research shown to the user, with their state, computed only from the events the backend emitted
(interface.md 7.2): pending, running, done, failed, skipped (not needed), interrupted. Nothing is marked done unless
an event says so; labels and explanations are scientific, never the names of the models behind them."""

from __future__ import annotations

from dataclasses import dataclass

PENDING, RUNNING, DONE, FAILED, SKIPPED, INTERRUPTED = "pending", "running", "done", "failed", "skipped", "interrupted"


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    why: str  # what the step measures and why it matters, in plain words
    events: tuple[str, ...] = ()  # "type/step" of the funnel events that belong to it
    stage: str | None = None  # name of the stage after the iterations, when it is one


# Solid electrolytes (the only domain implemented): the funnel steps repeat in each iteration, the stages run once.
ELECTROLYTE_STEPS = (
    Step("goal", "Understanding the research goal",
         "AutoLab reads the request, checks that it is within the supported research areas and sets the constraints.",
         ("loop/scope",)),
    Step("propose", "Proposing candidate materials",
         "New compositions are proposed by chemical substitution in known lithium thiophosphate crystals.",
         ("llm/proposal",)),
    Step("build", "Building and relaxing crystal structures",
         "Each composition is built in several atomic arrangements, checked for charge neutrality and relaxed with a "
         "machine-learned interatomic potential (UMA); compositions already known are not recomputed.",
         ("candidate/generate", "candidate/known_check", "candidate/relax")),
    Step("stability", "Thermodynamic stability",
         "The energy above the convex hull says whether a crystal would decompose into known phases; at most "
         "0.05 eV/atom is kept as possibly synthesizable.",
         ("candidate/hull",)),
    Step("bandgap", "Electronic band gap",
         "An electrolyte must not conduct electrons: the band gap is predicted with a graph neural network (ALIGNN) and "
         "must be at least 2 eV.", ("candidate/bandgap", "candidate/ss_check", "candidate/done")),
    Step("learn", "Interpreting the results",
         "The numbers of this round are compared and the next direction of the search is chosen.",
         ("llm/analysis", "llm/summary")),
    Step("electrodes", "Electrochemical window and electrode compatibility",
         "Stability window in volts, reaction with lithium metal (a candidate forming a metal is excluded) and "
         "reaction energy with a LiFePO4 cathode.", stage="electrodes"),
    Step("review", "Independent review of the candidates",
         "Each remaining candidate is reviewed separately: strengths, risks and interest for ion-transport simulation.",
         stage="candidate_analyses"),
    Step("md_choice", "Choosing candidates for ion-transport simulation",
         "Molecular dynamics is the most expensive step: the most informative candidates not yet simulated are chosen.",
         stage="md_selection"),
    Step("md", "Lithium-ion diffusion (molecular dynamics)",
         "Lithium motion is simulated at 600 K and compared with the parent crystal; a candidate clearly slower than its "
         "parent, or whose framework falls apart, is excluded.", stage="molecular_dynamics"),
    Step("ranking", "Ranking the candidates",
         "Candidates are ordered by their diffusion verdict, then by their stability cost per substitution.",
         stage="ranking"),
    Step("literature", "Literature check",
         "A web search tells whether each finalist, or its close family, is already published; a known electrolyte is "
         "checked first as a control.", stage="novelty"),
    Step("report", "Final scientific report",
         "The three finalists are compared and the best compromise is analysed in detail, with its limits and the "
         "validations still needed.", stage="report"),
)


def steps_from_events(events: list[dict], run_state: str, steps=ELECTROLYTE_STEPS) -> list[dict]:
    """State of each step. run_state: running, done, interrupted or error (the conversation's research state)."""
    seen: dict[str, list[dict]] = {s.key: [] for s in steps}
    stage_status: dict[str, str] = {}
    stage_summary: dict[str, dict] = {}
    stages_started = False
    last_index: dict[str, int] = {}
    for i, e in enumerate(events):
        k = f"{e['type']}/{e['step']}"
        for s in steps:
            if k in s.events:
                seen[s.key].append(e)
                last_index[s.key] = i
        if e["type"] == "stage" and ":" not in e["step"]:
            stages_started = True
            stage_status[e["step"]] = e["data"].get("status", "start")
            stage_summary[e["step"]] = e["data"]
    finished = run_state in ("done", "interrupted", "error")
    current = max(last_index, key=last_index.get) if last_index else None  # the funnel step being worked on
    out = []
    for s in steps:
        detail = None
        if s.stage:
            st = stage_status.get(s.stage)
            summary = stage_summary.get(s.stage, {})
            if st is None:
                state = INTERRUPTED if run_state == "interrupted" else SKIPPED if finished else PENDING
            elif st == "start":
                state = RUNNING if not finished else (INTERRUPTED if run_state == "interrupted" else FAILED)
            elif st == "interrupted":
                state = INTERRUPTED
            elif st == "error":
                state, detail = FAILED, summary.get("error")
            elif summary.get("skipped") or (summary.get("reason") and not summary.get("verdicts")):
                state, detail = SKIPPED, summary.get("skipped") or summary.get("reason")
            else:
                state, detail = DONE, summary.get("stopped")  # a stage stopped by a budget is done, partially
        else:
            if not seen[s.key]:
                if s.key == "goal" and events:
                    state = DONE  # the research started: the request was accepted
                else:
                    state = INTERRUPTED if run_state == "interrupted" else SKIPPED if finished else PENDING
            elif stages_started or finished or s.key != current:
                state = DONE
            else:
                state = RUNNING
            detail = _funnel_detail(s.key, seen[s.key])
        out.append({"key": s.key, "label": s.label, "why": s.why, "state": state, "detail": detail})
    return out


def _funnel_detail(key: str, evs: list[dict]) -> str | None:
    if not evs:
        return None
    if key == "propose":
        n = sum(len((e["data"].get("reply") or {}).get("proposals", [])) for e in evs)
        return f"{n} substitutions proposed in {len(evs)} round(s)"
    if key == "stability":
        ok = sum(1 for e in evs if (e["data"].get("e_hull") is not None and e["data"]["e_hull"] <= 0.05))
        return f"{ok} of {len(evs)} structures within 0.05 eV/atom of the hull"
    if key == "bandgap":
        gaps = [e for e in evs if e["step"] == "bandgap"]
        ok = sum(1 for e in gaps if e["data"].get("passes"))
        return f"{ok} of {len(gaps)} insulating (gap >= 2 eV)" if gaps else None
    if key == "build":
        relax = [e for e in evs if e["step"] == "relax"]
        return f"{len(relax)} compositions relaxed" if relax else None
    return None
