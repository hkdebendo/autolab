"""Run the agent loop (paid: LLM calls, UMA and MD on Modal, web search). Only with the owner's approval.

    SIM_BACKEND=modal python scripts/run_loop.py --iterations 1 --candidates 3 \
        --prior results/2026-10-28_step9/candidates.json --prior-tag s9 --novelty --out results/<dir> [--plan]

Iterations (proposal, funnel, analysis), then the stages of the domain (electrolyte: electrodes, choice of the MD
candidates, MD on Modal, final ranking, novelty check). --prior: candidates of an earlier run, never proposed again
and ranked with the new ones (their computations come from the cache). The novelty web search runs only with
--novelty. --plan prints the limits of the run and stops. Writes result.json, events.jsonl and report.md in --out.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.report import render
from autolab.domains import get_domain
from autolab.agent.runs import analyst_client, client, load_prior  # noqa: F401  (rerun_stages imports them)
from autolab.sim.backend import RelaxBudget


def show(event: dict) -> None:
    data = {k: v for k, v in event["data"].items() if k not in ("energies_per_atom", "decomposition")}
    print(f"[{event['type']}:{event['step']}] {event['candidate_id'] or ''} {json.dumps(data, default=str)[:300]}",
          flush=True)


def plan(args, brain_cap: float) -> None:
    """Upper bounds of the run, from config and the arguments (nothing is called)."""
    calls = 2 * args.iterations + 1
    print(f"language model ({args.brain}): {calls} calls (proposal + analysis per iteration, MD choice), up to "
          f"{config.JSON_MAX_RETRIES} attempts each for a malformed JSON; cap {brain_cap} $ and "
          f"{config.MAX_LLM_CALLS_PER_RUN} calls")
    print(f"UMA relaxations on Modal ({config.MODAL_GPU}): at most {args.max_relaxations} new "
          f"(about {config.GENERATOR_N_ARRANGEMENTS} per candidate, plus references of new elements and of the "
          f"cathode interfaces)")
    print(f"molecular dynamics on Modal {config.MODAL_MD_GPU}: at most {config.MD_SELECT_MAX} candidates x "
          f"{config.MD_SCREEN_SEEDS} seeds of {config.MD_SCREEN_PS} ps at {config.MD_SCREEN_TEMPERATURE_K} K "
          f"(cached runs are free); not launched above {config.MD_MAX_USD_PER_RUN} $ estimated")
    print(f"candidate analyses ({args.analyst}): one call per eligible candidate (at most "
          f"{config.CANDIDATE_ANALYSIS_MAX}), {config.CANDIDATE_ANALYSIS_WORKERS} in parallel, cap "
          f"{config.LLM_COST_CAPS_USD.get(args.analyst, 0)} $")
    print(f"novelty: {'control + at most ' + str(config.FINALISTS_MAX) + ' finalists, cap ' + str(config.NOVELTY_COST_CAP_USD) + ' $' if args.novelty else 'disabled (--novelty to enable)'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--domain", default=config.AGENT_DOMAIN)
    ap.add_argument("--goal")
    ap.add_argument("--parents", nargs="+")
    ap.add_argument("--iterations", type=int, default=config.MAX_ITERATIONS)
    ap.add_argument("--candidates", type=int, default=config.MAX_CANDIDATES_PER_ITERATION)
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    ap.add_argument("--prior", type=Path, help="candidates.json or result.json of an earlier run")
    ap.add_argument("--prior-tag", default="prev")
    ap.add_argument("--novelty", action="store_true", help="run the novelty web search (paid, Meta)")
    ap.add_argument("--analyst", default=config.CANDIDATE_ANALYSIS_PROVIDER,
                    help="provider of the parallel candidate analyses ('none' to disable)")
    ap.add_argument("--no-stages", action="store_true", help="iterations only")
    ap.add_argument("--plan", action="store_true", help="print the limits of the run and stop")
    ap.add_argument("--brain", default=config.LLM_PROVIDER)
    ap.add_argument("--fallback", default=config.LLM_FALLBACK_PROVIDER)
    ap.add_argument("--brain-budget", type=float, help="USD cap for the brain (default: LLM_COST_CAPS_USD)")
    ap.add_argument("--fallback-budget", type=float, help="USD cap for the fallback")
    ap.add_argument("--out", type=Path, default=config.CACHE_DIR / "runs" / time.strftime("%Y%m%d-%H%M%S"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the Windows console is cp1252

    brain_cap = args.brain_budget or config.LLM_COST_CAPS_USD[args.brain]
    if args.plan:
        plan(args, brain_cap)
        return
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "openai", "mp_api"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    args.out.mkdir(parents=True, exist_ok=True)

    brain = client(args.brain, brain_cap)
    fallback = None
    if args.fallback and args.fallback != args.brain:
        fallback = client(args.fallback, args.fallback_budget or config.LLM_COST_CAPS_USD[args.fallback])
    if brain is None and fallback is None:
        raise SystemExit("no language model available: fill the keys in .env")
    novelty = client(config.NOVELTY_PROVIDER, config.NOVELTY_COST_CAP_USD) if args.novelty else None
    analyst = analyst_client(args.analyst)

    prior = load_prior(args.prior, args.prior_tag) if args.prior else []
    agent = Agent(brain or fallback, fallback if brain else None, domain=get_domain(args.domain),
                  events=EventLog(args.out / "events.jsonl", sink=show), budget=RelaxBudget(args.max_relaxations),
                  novelty_client=novelty, analyst=analyst)
    result = agent.run(args.goal, args.parents, args.iterations, args.candidates, prior=prior,
                       stages=not args.no_stages)

    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    report = render(result, agent.domain)
    (args.out / "report.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"\nSaved in {args.out}")


if __name__ == "__main__":
    main()
