"""Re-evaluate the candidates of a loop result with the current funnel, from the cache only.

    python scripts/replay_candidates.py results/<run>/result.json --out results/<step>/candidates.json

No new UMA relaxation is allowed (budget 0): a missing one stops the replay. The output
keeps every candidate (with its best relaxed structure and energy), passed ones ranked by
E_hull per substitution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab.agent.pipeline import evaluate_candidate
from autolab.data.mp import get_structure
from autolab.sim.backend import RelaxBudget


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("result", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    result = json.loads(args.result.read_text(encoding="utf-8"))
    candidates = [evaluate_candidate(c["id"], c["parent"], get_structure(c["parent"]), c["substitution"],
                                     budget=RelaxBudget(0))
                  for it in result["iterations"] for c in it["candidates"]]
    passed = sorted((c for c in candidates if c["status"] == "passed"),
                    key=lambda c: (c["e_hull_per_substitution"], c["e_hull"]))
    out = {"source": str(args.result.as_posix()), "ranking": [c["id"] for c in passed], "candidates": candidates}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for i, c in enumerate(passed, 1):
        print(f"{i}. {c['id']} {c['formula']}: E_hull per atom {c['e_hull']:.3f} eV/atom, "
              f"per substitution {c['e_hull_per_substitution']:.3f} eV per modified site (n_modified {c['n_modified']}), "
              f"gap {c['gap_optb88']:.2f} eV")
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
