"""Real, paid LLM calls (small): per provider one plain call, one JSON reply, one streamed reasoning.

Run only with the owner's approval:  python scripts/llm_smoke.py [meta baseten fireworks]
Each provider has its own cost cap; results (no keys) go to .cache/llm_smoke.json.
"""

from __future__ import annotations

import json
import logging
import sys

from autolab import config
from autolab.llm import client as llm
from autolab.llm.schemas import template

BUDGET_USD = {"meta": 1.0, "baseten": 0.5, "fireworks": 0.5}
MAX_CALLS = 3 + config.JSON_MAX_RETRIES - 1

SYSTEM = (
    "You are a solid-state chemist designing solid electrolytes for lithium-metal batteries. "
    f"Fixed oxidation states: {json.dumps(config.OXIDATION_STATES)}. "
    "A substitution must keep the cell charge-neutral: compensate with li_vacancies "
    "(replacing one S(-2) by Cl(-1) needs one Li vacancy). "
    f"Reply with JSON only, exactly this shape: {template('proposal')}"
)
JSON_TASK = "Parent: Li3PS4 (mp-985583, cell Li12P4S16). Propose 2 substitutions worth exploring."
PLAIN_TASK = "In one sentence: why is Li3PS4 studied as a solid electrolyte?"
STREAM_TASK = ("In three short sentences: why does replacing one S by Cl in Li12P4S16 "
               "require removing one Li to stay charge-neutral?")


def short(text: str, n: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + " ..."


def run(provider: str) -> dict:
    effort = "low" if provider == "meta" else None
    tracker = llm.UsageTracker(max_calls=MAX_CALLS, max_cost_usd=BUDGET_USD[provider])
    out = {"provider": provider, "model": config.LLM_PROVIDERS[provider]["model"], "checks": {}}
    try:
        client = llm.LLMClient(provider, tracker=tracker)

        r = client.chat([{"role": "user", "content": PLAIN_TASK}], reasoning_effort=effort)
        out["checks"]["plain"] = {"ok": bool(r.text.strip()), "text": short(r.text), "seconds": r.seconds,
                                  "reasoning_chars": len(r.reasoning), "tokens": [r.input_tokens, r.output_tokens]}
        print(f"\n[{provider}] plain ({r.seconds} s): {short(r.text)}")

        obj, replies = client.complete_json([{"role": "system", "content": SYSTEM},
                                             {"role": "user", "content": JSON_TASK}], "proposal",
                                            reasoning_effort=effort)
        out["checks"]["json"] = {"ok": True, "attempts": len(replies), "reply": obj,
                                 "seconds": round(sum(x.seconds for x in replies), 2)}
        print(f"[{provider}] JSON valid after {len(replies)} attempt(s): {short(json.dumps(obj), 500)}")

        print(f"[{provider}] streamed reasoning: ", end="", flush=True)
        r = client.chat([{"role": "user", "content": STREAM_TASK}], stream=True,
                        on_reasoning=lambda s: print(s, end="", flush=True),
                        reasoning_effort="medium" if provider == "meta" else None)
        out["checks"]["stream"] = {"ok": bool(r.text.strip()), "reasoning_streamed": bool(r.reasoning),
                                   "reasoning_chars": len(r.reasoning), "reasoning_tokens": r.reasoning_tokens,
                                   "text": short(r.text), "seconds": r.seconds,
                                   "usage_estimated": r.usage_estimated}
        print(f"\n[{provider}] streamed answer: {short(r.text)}")
    except (llm.LLMError, config.MissingKeyError) as e:
        out["error"] = f"{type(e).__name__}: {e}"
        print(f"\n[{provider}] STOP: {out['error']}")
    out["usage"] = tracker.summary()
    return out


def main(providers: list[str]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    results = [run(p) for p in providers]
    path = config.CACHE_DIR / "llm_smoke.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n=== Usage ===")
    total = 0.0
    for res in results:
        u = res["usage"]
        total += u["cost_usd"]
        print(f"{res['provider']:<10} calls {u['calls']}, in {u['input_tokens']}, out {u['output_tokens']}, "
              f"~${u['cost_usd']:.4f} (cap ${BUDGET_USD[res['provider']]})")
    print(f"total ~${total:.4f}; details in {path}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(BUDGET_USD))
