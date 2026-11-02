"""Publish a rerun of a recorded research (scripts/rerun_stages.py) into its conversation of the database: result,
events and report message replaced, nothing added. Free (database only).

    python scripts/publish_rerun.py results/<run> <conversation id>

Then open /api/champions?refresh=1 once so that the results page reads the new report.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from autolab.domains import get_domain
from autolab.store.conversations import PostgresStore


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("conversation")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result = json.loads((args.run / "result.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (args.run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    store = PostgresStore()
    if store.get(args.conversation) is None:
        raise SystemExit(f"unknown conversation {args.conversation}")
    store.save_result(args.conversation, result)
    store.replace_events(args.conversation, events)
    rep = result["stages"].get("report") or {}
    stage = next(s for s in get_domain(result["domain"]).stages if s.name == "report")
    replaced = store.replace_message(args.conversation, "report", "\n".join(stage.render(rep, result)),
                                     {"champion": rep.get("champion"), "completeness": rep.get("completeness")})
    print(f"{args.conversation}: result and {len(events)} events replaced, report message "
          f"{'replaced' if replaced else 'not found'}")


if __name__ == "__main__":
    main()
