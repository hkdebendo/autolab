"""Step 9A (CPU, cache only): electrochemical window and passivation with UMA energies for the top candidates.

    python scripts/step9a_electrodes.py results/<step>/candidates.json --top 5

Starts with the Li3PS4 calibration (UMA window vs the MP 1.72-2.34 V). No new relaxation is allowed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pymatgen.core import Composition

from autolab.agent.electrochem import li3ps4_window_calibration, reference_window, window_and_passivation
from autolab.sim.backend import RelaxBudget


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", type=Path)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--out", type=Path, help="default: electrodes.json next to the candidates file")
    args = ap.parse_args()

    data = json.loads(args.candidates.read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in data["candidates"]}
    cal = li3ps4_window_calibration(budget=RelaxBudget(0))
    print(f"Li3PS4 window, UMA: {cal['v_low']} - {cal['v_high']} V | MP: {cal['mp_v_low']} - {cal['mp_v_high']} V "
          f"(diff {cal['diff_low']} / {cal['diff_high']})")
    rows = []
    for cid in data["ranking"][:args.top]:
        r = window_and_passivation(by_id[cid], budget=RelaxBudget(0))
        w, p = r["window"], r["passivation"]
        print(f"{cid} {r['formula']}: window {w['v_low']} - {w['v_high']} V (contiguous {w['contiguous']}); "
              f"vs Li metal: {p['verdict']}, reaction {p['reaction_energy']:.3f} eV/atom, "
              f"products {[d['formula'] for d in p['products']]}, metallic {p['metallic_products']}")
        rows.append(r)
    # Parent windows: an empty candidate window is read next to its parent's (Li7P3S11 is only 0.02 V wide).
    parents = {}
    for pid in sorted({by_id[r["id"]]["parent"] for r in rows}):
        formula = by_id[next(r["id"] for r in rows if by_id[r["id"]]["parent"] == pid)]["parent_formula"]
        parents[pid] = {"formula": formula, **reference_window(
            pid, sorted(el.symbol for el in Composition(formula).elements), budget=RelaxBudget(0))}
        print(f"parent {pid} {formula}: window {parents[pid]['v_low']} - {parents[pid]['v_high']} V")
    out = args.out or args.candidates.with_name("electrodes.json")
    out.write_text(json.dumps({"calibration_li3ps4": cal, "parents": parents, "candidates": rows}, indent=1),
                   encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
