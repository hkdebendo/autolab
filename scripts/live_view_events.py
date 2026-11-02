"""Add the start and relaxed structures to the relaxation events of a recorded run, for the live view of the interface.

    python scripts/live_view_events.py results/<run> [--conversation <id>]

Runs recorded before 2026-11-02 emitted only the energies of each relaxation. The arrangements are generated again
(the generator is deterministic: fixed seed) and the relaxed structure comes from result.json; the arrangement that
was kept is the one whose species order matches the relaxed structure. Nothing is relaxed again: no UMA, no GPU.
With --conversation, the events of that conversation in the database are replaced by the enriched run events.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pymatgen.core import Structure

from autolab.agent.pipeline import live_structure
from autolab.chem.generator import generate_candidates
from autolab.data.mp import get_structure
from autolab.sim.serialize import atoms_from_dict


def repaired(x):
    """Text read once with the wrong encoding on Windows ("±" saved as "Â±") put back; other values unchanged."""
    if isinstance(x, str) and any(ch in x for ch in "ÂÃâ"):
        try:
            return x.encode("cp1252").decode("utf-8")
        except UnicodeError:
            return x
    if isinstance(x, dict):
        return {k: repaired(v) for k, v in x.items()}
    if isinstance(x, list):
        return [repaired(v) for v in x]
    return x


def enrich(events: list[dict], candidates: dict[str, dict]) -> tuple[list[dict], int]:
    """The events with a "structure" in each relaxation event that can be rebuilt; the number rebuilt."""
    from ase.data import chemical_symbols

    done, parents = 0, {}
    for e in events:
        if e["type"] != "candidate" or e["step"] != "relax" or e["data"].get("structure"):
            continue
        c = candidates.get(e["candidate_id"])
        if not c or not c.get("relaxed_atoms") or not c.get("parent"):
            continue
        if c["parent"] not in parents:
            parents[c["parent"]] = get_structure(c["parent"])
        gen = generate_candidates(parents[c["parent"]], c["substitution"], c["parent"])
        order = [chemical_symbols[z] for z in c["relaxed_atoms"]["numbers"]]
        starts = [Structure.from_dict(g["structure"]) for g in gen["candidates"]]
        start = next((s for s in starts if [site.specie.symbol for site in s] == order), None)
        if start is None:
            continue
        best = {"atoms": c["relaxed_atoms"], "energy_per_atom": c["energy"] / len(order)}
        e["data"]["structure"] = live_structure(start, best, c["substitution"])
        e["data"]["cached"] = True  # recorded run: shown from the saved results
        done += 1
    return events, done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path)
    ap.add_argument("--conversation", help="replace this conversation's events in the database")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result = json.loads((args.run / "result.json").read_text(encoding="utf-8"))
    cands = {c["id"]: c for c in result.get("prior", []) + [c for r in result["iterations"] for c in r["candidates"]]}
    events = [repaired(json.loads(line)) for line in (args.run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    relax = sum(1 for e in events if e["type"] == "candidate" and e["step"] == "relax")
    events, n = enrich(events, cands)
    print(f"{n} of {relax} relaxation events given their structures")
    out = args.run / "events_live_view.jsonl"
    out.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    print(f"written: {out}")
    if args.conversation:
        from autolab.store.conversations import PostgresStore

        PostgresStore().replace_events(args.conversation, events)
        print(f"conversation {args.conversation}: {len(events)} events replaced")


if __name__ == "__main__":
    main()
