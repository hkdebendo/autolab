"""Import a recorded research (results/<run>: result.json, events.jsonl, replay/) as a conversation of the history,
so that it can be reopened without any new computation (interface.md 6). The stored data are the source of truth:
nothing is rebuilt from a title or a summary."""

from __future__ import annotations

import json
from pathlib import Path

from autolab.domains import get_domain


def import_run(svc, run_dir: Path, cid: str, title: str, request: str, file_path=None) -> str:
    """Create the conversation `cid` from a recorded run; `file_path(cid, name)` gives where a 3D file is stored
    (default: the file inside the run folder). Returns the conversation id; an existing one is left as it is."""
    store = svc.store
    if store.get(cid) is not None:
        return cid
    run_dir = Path(run_dir)
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
              if line.strip()]
    store.create({"id": cid, "title": title, "goal": request, "domain": result.get("domain", "electrolyte"),
                  "status": "done", "source": f"imported:{run_dir.name}",
                  "scope": {"intent": "new_discovery", "status": "supported", "domain": result.get("domain")}})
    store.add_message(cid, "user", "request", request)
    store.add_message(cid, "assistant", "scope",
                      "AutoLab searches new solid electrolytes for lithium-metal batteries by substitution in known "
                      "lithium thiophosphate crystals, and evaluates their stability, band gap, electrode "
                      "compatibility and lithium diffusion.")
    for seq, e in enumerate(events):
        store.append_event(cid, seq, e)
    store.save_result(cid, result)
    svc.finish(cid, result, get_domain(result.get("domain", "electrolyte")))
    index_file = run_dir / "replay" / "index.json"
    if index_file.exists():
        index = json.loads(index_file.read_text(encoding="utf-8"))
        where = file_path or (lambda c, name: str(run_dir / "replay" / name))
        store.add_artifact(cid, "index.json", "index", where(cid, "index.json"))
        for kind in ("structures", "md"):
            for e in index[kind]:
                store.add_artifact(cid, e["file"], kind.rstrip("s"), where(cid, e["file"]), e)
    return cid


RECORDED = [  # (folder, conversation id, title, request as it was given)
    ("results/2026-10-29_reference_run", "ref-2026-10-29", "Sulfide electrolytes: reference research",
     "Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically stable or slightly "
     "metastable, electronically insulating, by substitutions in known Li-P-S crystals."),
    ("results/2026-10-29_live_smoke", "test-2026-10-29-br-i", "Br and I in Li7P3S11 (test)",
     "Try Br and I for S in Li7P3S11 with Li vacancies, and compare with the Li3PS4 analogues"),
    ("results/2026-10-29_step1_run", "first-2026-10-29", "First complete research (test)",
     "Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically stable or slightly "
     "metastable, electronically insulating, by substitutions in known Li-P-S crystals."),
]
