"""Add Muse Wonder's campaign review to finished researches of the history (no other computation).

The campaign review is the last stage of every research since 2026-11-03 (agent/review.py). A research finished
before is given its review here: one Muse Wonder call on its stored result; the stage's events are inserted before
the research's last event ("loop/stop"), the result is saved with the new stage and the review becomes the last
message of the conversation. Nothing else changes. The matching results/<run> folder (same goal) gets the same
events and result, and campaign_review.md. A research that already has its review is left as it is.

    python scripts/add_campaign_review.py --dry-run     # dossier sizes and the cost cap, no call
    python scripts/add_campaign_review.py               # the home page researches (config.REPLAY_EXAMPLES)
    python scripts/add_campaign_review.py 0245f94a24cf
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autolab import config  # noqa: E402
from autolab.agent import review  # noqa: E402
from autolab.agent.events import EventLog  # noqa: E402
from autolab.agent.runs import director_client  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def with_review(events: list[dict], new: list[dict]) -> list[dict]:
    """The events with `new` inserted before the last "loop/stop" event (at the end if there is none)."""
    events = [{k: v for k, v in e.items() if k != "seq"} for e in events]
    stop = max((i for i, e in enumerate(events) if e["type"] == "loop" and e["step"] == "stop"), default=len(events))
    return events[:stop] + new + events[stop:]


def results_folder(goal: str) -> Path | None:
    for f in sorted(ROOT.glob("results/*/result.json")):
        if json.loads(f.read_text(encoding="utf-8")).get("goal") == goal:
            return f.parent
    return None


def write_folder(folder: Path, stage: dict, new: list[dict], out: dict) -> None:
    """The local copy: the stage added to result.json, the new event lines inserted (old lines kept byte for byte)."""
    f = folder / "result.json"
    text = f.read_text(encoding="utf-8")
    local = json.loads(text)
    local.setdefault("stages", {})["campaign_review"] = stage
    f.write_text(json.dumps(local, indent=2, default=str, ensure_ascii=text.isascii()), encoding="utf-8")
    for name in ("events.jsonl", "events_live_view.jsonl"):
        f = folder / name
        if not f.exists():
            continue
        lines = [line for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
        kinds = [json.loads(line) for line in lines]
        stop = max((i for i, e in enumerate(kinds) if e["type"] == "loop" and e["step"] == "stop"), default=len(lines))
        lines[stop:stop] = [json.dumps(e, default=str) for e in new]
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "campaign_review.md").write_text("\n".join(review.render(out, local)), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("conversations", nargs="*", help="conversation ids (default: the home page researches)")
    ap.add_argument("--dry-run", action="store_true", help="sizes and cost cap only, no model call, nothing written")
    args = ap.parse_args()

    from autolab.store.conversations import PostgresStore

    store = PostgresStore()
    cids = args.conversations or [cid for _, cid in config.REPLAY_EXAMPLES]
    p = config.LLM_PROVIDERS[config.CAMPAIGN_REVIEW_PROVIDER]
    if not args.dry_run and not config.has_key(p["key"]):
        raise SystemExit(f"{p['key']} missing in .env: Muse Wonder unavailable")
    total, calls = 0.0, 0
    for cid in cids:
        result = store.result(cid)
        if result is None:
            print(f"{cid}: no stored result, skipped")
            continue
        if (result.get("stages", {}).get("campaign_review") or {}).get("status") == "done":
            print(f"{cid}: already reviewed, left as it is")
            continue
        chars = len(review.review_messages(result)[1]["content"])
        cap = (chars / 4 * p["usd_per_m_input"] + config.CAMPAIGN_REVIEW_MAX_OUTPUT_TOKENS * p["usd_per_m_output"]) / 1e6
        folder = results_folder(result.get("goal"))
        print(f"{cid}: dossier {chars} characters (~{chars // 4} tokens), at most {cap:.2f} $; folder: "
              f"{folder.relative_to(ROOT) if folder else 'none'}")
        if args.dry_run:
            continue
        backup = config.CACHE_DIR / "backup" / f"{cid}-{time.strftime('%Y%m%d-%H%M%S')}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(json.dumps({"result": result, "events": store.events(cid)}, default=str), encoding="utf-8")
        director = director_client()  # its own caps for each research (one call, JSON retries)
        log = EventLog()
        log.emit("stage", "campaign_review", {"status": "start"})
        out = review.campaign_review(SimpleNamespace(agent=SimpleNamespace(director=director, result=result,
                                                                            events=log)))
        log.emit("stage", "campaign_review", {"status": "done", **out["summary"]})
        result.setdefault("stages", {})["campaign_review"] = {"status": "done", **out}
        store.replace_events(cid, with_review(store.events(cid), log.events))
        store.save_result(cid, result)
        store.add_message(cid, "assistant", "review", "\n".join(review.render(out, result)), data=out["review"])
        if folder:
            write_folder(folder, result["stages"]["campaign_review"], log.events, out)
        total, calls = total + out["cost_usd"], calls + director.tracker.calls
        print(f"  {out['input_tokens']} in, {out['output_tokens']} out, {out['cost_usd']:.4f} $, {out['seconds']} s: "
              f"{out['review']['headline']}")
    if not args.dry_run:
        print(f"Muse Wonder: {total:.4f} $ in total ({calls} calls)")


if __name__ == "__main__":
    main()
