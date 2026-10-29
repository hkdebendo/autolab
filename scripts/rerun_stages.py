"""Run again the stages of a recorded run from one stage on (e.g. after a fix), without new proposals.

    SIM_BACKEND=modal python scripts/rerun_stages.py results/<run> --from molecular_dynamics [--novelty]

The candidates and the outputs of the earlier stages come from result.json; the stages from --from on run again
(computations come from the caches; the model stages use --brain, with --fallback, as the loop does). The
first pass is kept as result_first_pass.json, events_first_pass.jsonl and report_first_pass.md; the new events.jsonl is the first pass
up to the rerun stage followed by the new events, so that the replay stays one clean timeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.report import render
from autolab.domains import Campaign, get_domain
from autolab.sim.backend import RelaxBudget

from run_loop import analyst_client, client, show


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--from", dest="start", required=True)
    ap.add_argument("--novelty", action="store_true", help="run the novelty web search (paid, Meta)")
    ap.add_argument("--analyst", default=config.CANDIDATE_ANALYSIS_PROVIDER, help="'none' to disable")
    ap.add_argument("--brain", default=config.LLM_PROVIDER)
    ap.add_argument("--fallback", default=config.LLM_FALLBACK_PROVIDER)
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    first_result, first_events = args.run / "result_first_pass.json", args.run / "events_first_pass.jsonl"
    if not first_result.exists():  # keep the first pass once, never overwrite it
        (args.run / "result.json").rename(first_result)
        (args.run / "events.jsonl").rename(first_events)
        if (args.run / "report.md").exists():
            (args.run / "report.md").rename(args.run / "report_first_pass.md")
    result = json.loads(first_result.read_text(encoding="utf-8"))
    domain = get_domain(result["domain"])
    names = [s.name for s in domain.stages]
    if args.start not in names:
        raise SystemExit(f"--from must be one of {names}")
    rerun = set(names[names.index(args.start):])

    candidates = result["prior"] + [c for r in result["iterations"] for c in r["candidates"]]
    for c in candidates:  # forget what the rerun stages had decided
        if c.get("excluded_at") in rerun:
            c.pop("excluded_at"), c.pop("exclusion_reason", None)
        if "molecular_dynamics" in rerun:
            for k in ("D_cm2_per_s", "D_sem_cm2_per_s", "D_ratio_to_parent", "D_ratio_err", "md_verdict",
                      "conduction", "md_framework_intact"):
                c.pop(k, None)
        if "novelty" in rerun:
            c.pop("novelty", None)
        if "candidate_analyses" in rerun:
            c.pop("analysis", None)

    lines = first_events.read_text(encoding="utf-8").splitlines()
    cut = next(i for i, line in enumerate(lines)
               if (e := json.loads(line))["type"] == "stage" and e["step"] == args.start)
    out_events = args.run / "events.jsonl"
    out_events.write_text("\n".join(lines[:cut]) + "\n", encoding="utf-8")
    events = EventLog(out_events, sink=show)

    novelty = client(config.NOVELTY_PROVIDER, config.NOVELTY_COST_CAP_USD) if args.novelty else None
    brain = client(args.brain, config.LLM_COST_CAPS_USD[args.brain])
    fallback = client(args.fallback, config.LLM_COST_CAPS_USD[args.fallback]) if args.fallback != args.brain else None
    agent = Agent(brain or fallback, fallback if brain else None, domain=domain, events=events, budget=RelaxBudget(args.max_relaxations),
                  novelty_client=novelty, analyst=analyst_client(args.analyst), get_structure=lambda pid: None)
    campaign = Campaign(agent, result["goal"], candidates,
                        {k: v for k, v in result["stages"].items() if k not in rerun})
    result["stages"] = {k: v for k, v in result["stages"].items() if k not in rerun}

    class Only:  # the domain with the rerun stages only
        stages = [s for s in domain.stages if s.name in rerun]
    agent.domain = Only
    agent.run_stages(campaign, result)
    agent.domain = domain
    result["final_ranking"] = result["stages"].get("ranking", {}).get("ranking", result.get("final_ranking"))
    result["usage"]["novelty"] = novelty.tracker.summary() if novelty is not None else result["usage"].get("novelty")
    result["usage"]["md"] = result["stages"].get("molecular_dynamics", {}).get("plan")
    for c in (agent.brain, agent.fallback):  # model calls of the rerun, added to those of the first pass
        if c is not None and c.tracker.calls:
            result["usage"]["llm"][f"{c.provider} (rerun)"] = c.tracker.summary()
    if agent.analyst is not None:
        result["usage"]["analyst"] = agent.analyst.tracker.summary()
    result["rerun"] = {"from": args.start, "new_relaxations": agent.budget.used}
    events.emit("loop", "stop", {"reason": f"{result['stop_reason']} (stages rerun from {args.start})",
                                 "final_ranking": result["final_ranking"]})

    (args.run / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    report = render(result, domain)
    (args.run / "report.md").write_text(report, encoding="utf-8")
    print("\n" + report)


if __name__ == "__main__":
    main()
