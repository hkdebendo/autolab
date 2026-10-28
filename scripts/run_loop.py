"""Run the minimal agent loop (paid: LLM calls and UMA on a GPU). Only with the owner's approval.

    SIM_BACKEND=local LLM_PROVIDER=meta python scripts/run_loop.py --iterations 2 --candidates 5

Writes result.json, events.jsonl and report.md in --out, and prints the report.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.loop import Agent
from autolab.agent.report import render
from autolab.llm.client import LLMClient, UsageTracker
from autolab.sim.backend import RelaxBudget


def client(provider: str, cap: float) -> LLMClient | None:
    if not config.has_key(config.LLM_PROVIDERS[provider]["key"]):
        print(f"{config.LLM_PROVIDERS[provider]['key']} missing: provider {provider} disabled")
        return None
    return LLMClient(provider, tracker=UsageTracker(max_cost_usd=cap))


def show(event: dict) -> None:
    data = {k: v for k, v in event["data"].items() if k not in ("energies_per_atom", "decomposition")}
    print(f"[{event['type']}:{event['step']}] {event['candidate_id'] or ''} {json.dumps(data, default=str)[:300]}",
          flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--goal", default=config.AGENT_GOAL)
    ap.add_argument("--parents", nargs="+", default=config.AGENT_PARENTS)
    ap.add_argument("--iterations", type=int, default=config.MAX_ITERATIONS)
    ap.add_argument("--candidates", type=int, default=config.MAX_CANDIDATES_PER_ITERATION)
    ap.add_argument("--max-relaxations", type=int, default=config.MAX_RELAXATIONS_PER_RUN)
    ap.add_argument("--brain", default=config.LLM_PROVIDER)
    ap.add_argument("--fallback", default=config.LLM_FALLBACK_PROVIDER)
    ap.add_argument("--brain-budget", type=float, help="USD cap for the brain (default: LLM_COST_CAPS_USD)")
    ap.add_argument("--fallback-budget", type=float, help="USD cap for the fallback")
    ap.add_argument("--out", type=Path, default=config.CACHE_DIR / "runs" / time.strftime("%Y%m%d-%H%M%S"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "openai", "mp_api"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    args.out.mkdir(parents=True, exist_ok=True)

    brain = client(args.brain, args.brain_budget or config.LLM_COST_CAPS_USD[args.brain])
    fallback = None
    if args.fallback and args.fallback != args.brain:
        fallback = client(args.fallback, args.fallback_budget or config.LLM_COST_CAPS_USD[args.fallback])
    if brain is None and fallback is None:
        raise SystemExit("no language model available: fill the keys in .env")

    agent = Agent(brain or fallback, fallback if brain else None,
                  events=EventLog(args.out / "events.jsonl", sink=show), budget=RelaxBudget(args.max_relaxations))
    result = agent.run(args.goal, args.parents, args.iterations, args.candidates)

    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    report = render(result)
    (args.out / "report.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"\nSaved in {args.out}")


if __name__ == "__main__":
    main()
