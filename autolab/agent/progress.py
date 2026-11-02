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


# Solid electrolytes (the only domain implemented): the funnel steps repeat in each iteration; with the error-driven
# loop the slow tests (electrodes to molecular dynamics) also run in each iteration, then once more on the whole pool.
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
         "An electrolyte must not conduct electrons: the band gap is predicted with a band-gap model and "
         "must be at least 2 eV.", ("candidate/bandgap", "candidate/ss_check", "candidate/done")),
    Step("learn", "Interpreting the results",
         "The numbers of this round are compared, the failures of the slow tests are explained as hypotheses, and the "
         "next direction of the search is chosen to correct them.", ("loop/feedback", "llm/analysis", "llm/summary")),
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
         "parent, or whose framework falls apart, is excluded, and the failure is sent back to guide the next round.",
         stage="molecular_dynamics"),
    Step("conductivity", "Ionic conductivity at room temperature (estimate)",
         "The diffusion coefficients measured at several temperatures are extrapolated to 300 K (Arrhenius law) and "
         "converted to a conductivity in mS/cm, with its range.", stage="conductivity"),
    Step("ranking", "Ranking the candidates",
         "Candidates are ordered by their room-temperature conductivity against their parent (when fitted), their "
         "diffusion verdict, then their stability cost per substitution.",
         stage="ranking"),
    Step("literature", "Literature check",
         "A web search tells whether each finalist, or its close family, is already published; a known electrolyte is "
         "checked first as a control.", stage="novelty"),
    Step("report", "Final scientific report",
         "The three finalists are compared and the best compromise is analysed in detail, with its limits and the "
         "validations still needed.", stage="report"),
)


CATHODE_STEPS = (
    Step("goal", "Understanding the research goal",
         "AutoLab reads the request, checks that it is within the supported research areas and sets the constraints.",
         ("loop/scope",)),
    Step("propose", "Proposing candidate cathodes",
         "New cobalt-free compositions are proposed by chemical substitution in known cathodes (LiFePO4, LiMnPO4, "
         "spinel LiMn2O4, LiNi0.5Mn1.5O4).", ("llm/proposal",)),
    Step("build", "Building and relaxing crystal structures",
         "Each composition is built in several atomic arrangements, checked for charge neutrality (mixed valence "
         "allowed, no cobalt) and relaxed with a machine-learned interatomic potential (UMA); known compositions are "
         "not recomputed.", ("candidate/generate", "candidate/known_check", "candidate/relax")),
    Step("stability", "Thermodynamic stability",
         "The energy above the convex hull of the stable known phases says whether the cathode would decompose.",
         ("candidate/hull",)),
    Step("voltage", "Charging: voltage, capacity, volume change",
         "The lithium that charge neutrality allows is removed and the charged cell relaxed: average voltage vs "
         "lithium, theoretical capacity, energy density and volume change, compared with the parent cathode.",
         ("candidate/voltage", "candidate/done")),
    Step("learn", "Interpreting the results",
         "The numbers of this round, failures included, go back to the agent, which explains them as hypotheses and "
         "corrects the next proposals.", ("loop/feedback", "llm/analysis", "llm/summary")),
    Step("review", "Independent review of the candidates",
         "Each candidate that passed is reviewed separately: strengths, risks, priority for a follow-up.",
         stage="candidate_analyses"),
    Step("ranking", "Ranking the candidates", "Candidates are ordered by energy density (voltage x capacity), then "
         "by their stability cost per substitution.", stage="ranking"),
    Step("literature", "Literature check", "A web search tells whether each finalist, or its close family, is "
         "already published; a known cathode is checked first as a control.", stage="novelty"),
    Step("report", "Final scientific report", "The finalists are compared with their parents and the best one "
         "analysed in detail, with its limits and the validations still needed.", stage="report"),
)
SODIUM_STEPS = (
    Step("goal", "Understanding the research goal",
         "AutoLab reads the request, checks that it is within the supported research areas and sets the constraints.",
         ("loop/scope",)),
    Step("propose", "Proposing candidate sodium conductors",
         "New compositions are proposed by chemical substitution in known sodium conductors (Na3PS4, Na3SbS4, NASICON).",
         ("llm/proposal",)),
    Step("build", "Building and relaxing crystal structures",
         "Each composition is built in several atomic arrangements, checked for charge neutrality and relaxed with a "
         "machine-learned interatomic potential (UMA); compositions already known are not recomputed.",
         ("candidate/generate", "candidate/known_check", "candidate/relax")),
    Step("stability", "Thermodynamic stability",
         "The energy above the convex hull of the stable known phases says whether a crystal would decompose.",
         ("candidate/hull",)),
    Step("bandgap", "Electronic band gap",
         "An electrolyte must not conduct electrons: the band gap is predicted with a band-gap model.",
         ("candidate/bandgap", "candidate/ss_check", "candidate/done")),
    Step("learn", "Interpreting the results",
         "The numbers of this round, failures included, go back to the agent, which explains them as hypotheses and "
         "corrects the next proposals.", ("loop/feedback", "llm/analysis", "llm/summary")),
    Step("electrodes", "Electrochemical window and contact with sodium metal",
         "Stability window in volts vs Na/Na+ and reaction with sodium metal (a candidate forming a metal is excluded).",
         stage="electrodes"),
    Step("review", "Independent review of the candidates",
         "Each remaining candidate is reviewed separately: strengths, risks and interest for ion-transport simulation.",
         stage="candidate_analyses"),
    Step("md_choice", "Choosing candidates for ion-transport simulation",
         "Molecular dynamics is the most expensive step: the most informative candidates not yet simulated are chosen.",
         stage="md_selection"),
    Step("md", "Sodium-ion diffusion (molecular dynamics)",
         "Sodium motion is simulated at 600 K and compared with the parent crystal; the failures are sent back to guide "
         "the next round.", stage="molecular_dynamics"),
    Step("ranking", "Ranking the candidates", "Candidates are ordered by their diffusion verdict against their parent, "
         "then by their stability cost per substitution.", stage="ranking"),
    Step("literature", "Literature check", "A web search tells whether each finalist, or its close family, is already "
         "published; a known sodium electrolyte is checked first as a control.", stage="novelty"),
    Step("report", "Final scientific report", "The finalists are compared and the best compromise analysed in detail, "
         "with its limits and the validations still needed.", stage="report"),
)
MEMRISTOR_STEPS = (
    Step("goal", "Understanding the research goal",
         "AutoLab reads the request, checks that it is within the supported research areas and sets the constraints.",
         ("loop/scope",)),
    Step("propose", "Proposing doped oxides",
         "New compositions are proposed by isovalent substitution in known switching oxides (HfO2, TiO2, SrTiO3).",
         ("llm/proposal",)),
    Step("build", "Building and relaxing crystal structures",
         "Each composition is built in several atomic arrangements, checked for charge neutrality and relaxed with a "
         "machine-learned interatomic potential (UMA); compositions already known are not recomputed.",
         ("candidate/generate", "candidate/known_check", "candidate/relax")),
    Step("stability", "Thermodynamic stability",
         "The energy above the convex hull of the stable known phases says whether a crystal would decompose.",
         ("candidate/hull",)),
    Step("bandgap", "Electronic band gap",
         "A memristor oxide must insulate in its high-resistance state: the band gap is predicted with GapModel.",
         ("candidate/bandgap", "candidate/ss_check", "candidate/done")),
    Step("migration", "Oxygen-vacancy migration barrier",
         "An oxygen vacancy is made to hop next to the dopant (nudged elastic band with UMA) and its barrier is "
         "compared with that of the parent oxide: a lower barrier suggests easier switching.", stage="migration"),
    Step("learn", "Interpreting the results",
         "The numbers of this round, failures included, go back to the agent, which explains them as hypotheses and "
         "corrects the next proposals.", ("loop/feedback", "llm/analysis", "llm/summary")),
    Step("review", "Independent review of the candidates",
         "Each candidate is reviewed separately: strengths, risks and interest for a follow-up.",
         stage="candidate_analyses"),
    Step("ranking", "Ranking the candidates", "Candidates are ordered by their barrier against the parent, then by the "
         "barrier itself and their stability cost per substitution.", stage="ranking"),
    Step("literature", "Literature check", "A web search tells whether each finalist, or its close family, is already "
         "published; a known memristor oxide is checked first as a control.", stage="novelty"),
    Step("report", "Final scientific report", "The finalists are compared and the best compromise analysed in detail, "
         "with its limits and the validations still needed.", stage="report"),
)
DOMAIN_STEPS = {"electrolyte": ELECTROLYTE_STEPS, "cathode": CATHODE_STEPS, "sodium": SODIUM_STEPS,
                "memristor": MEMRISTOR_STEPS}


def domain_of(events: list[dict]) -> str:
    """The domain a research runs in, from its start event (electrolyte when not said)."""
    for e in events:
        if e.get("type") == "loop" and e.get("step") == "start":
            return (e.get("data") or {}).get("domain") or "electrolyte"
    return "electrolyte"


def steps_from_events(events: list[dict], run_state: str, steps=None) -> list[dict]:
    """State of each step. run_state: running, done, interrupted or error (the conversation's research state);
    the steps are the domain's (read from the start event) unless given."""
    steps = steps or DOMAIN_STEPS.get(domain_of(events), ELECTROLYTE_STEPS)
    seen: dict[str, list[dict]] = {s.key: [] for s in steps}
    stage_status: dict[str, str] = {}
    stage_summary: dict[str, dict] = {}
    round_status: dict[str, str] = {}  # stages run inside an iteration (error-driven loop): last status
    round_summary: dict[str, dict] = {}
    stages_started = False
    last_index: dict[str, int] = {}
    last_round_stage = -1  # index of the last event of a stage run inside an iteration
    for i, e in enumerate(events):
        k = f"{e['type']}/{e['step']}"
        for s in steps:
            if k in s.events:
                seen[s.key].append(e)
                last_index[s.key] = i
        if e["type"] == "stage" and ":" not in e["step"]:
            if e["data"].get("iteration") is not None:
                round_status[e["step"]] = e["data"].get("status", "start")
                round_summary[e["step"]] = e["data"]
                last_round_stage = i
                continue
            stages_started = True
            stage_status[e["step"]] = e["data"].get("status", "start")
            stage_summary[e["step"]] = e["data"]
    finished = run_state in ("done", "interrupted", "error")
    current = max(last_index, key=last_index.get) if last_index else None  # the funnel step being worked on
    if current is not None and last_index[current] < last_round_stage:
        current = None  # a slow test of the round runs after it
    out = []
    for s in steps:
        detail = None
        if s.stage:
            st = stage_status.get(s.stage)
            summary = stage_summary.get(s.stage, {})
            rst = round_status.get(s.stage)
            if rst is not None and (st is None or _skipped(summary)):
                st, summary = rst, {**round_summary[s.stage], "skipped": None}
                if st not in ("start", "interrupted", "error"):
                    st = "done"
                    summary = {**summary, "reason": None, "stopped": summary.get("stopped") or
                               f"run in each round (last: round {round_summary[s.stage]['iteration']})"}
            if st is None:
                state = INTERRUPTED if run_state == "interrupted" else SKIPPED if finished else PENDING
            elif st == "start":
                state = RUNNING if not finished else (INTERRUPTED if run_state == "interrupted" else FAILED)
            elif st == "interrupted":
                state = INTERRUPTED
            elif st == "error":
                state, detail = FAILED, summary.get("error")
            elif _skipped(summary):
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


def _skipped(summary: dict) -> bool:
    return bool(summary.get("skipped") or (summary.get("reason") and not summary.get("verdicts")))


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
    if key == "voltage":
        volts = [e["data"] for e in evs if e["step"] == "voltage" and e["data"].get("voltage_V") is not None]
        return (f"{len(volts)} charged: {min(v['voltage_V'] for v in volts):.2f}-{max(v['voltage_V'] for v in volts):.2f} V"
                if volts else None)
    return None
