"""Truth test of the DFT band gap (SPEC 7): GPAW PBE gaps against the Materials Project PBE gaps of known compounds.

Usage: python scripts/dft_gap_truth_test.py mp-1153 [mp-135 ...]   (one Modal CPU call per structure not cached)
Passed when every |GPAW - MP| <= DFT_GAP_TRUTH_TOL_EV and every metal stays below METALLIC_GAP_MAX.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from autolab import config
from autolab.analysis.bandgap import dft_gap
from autolab.data.mp import get_band_gaps, get_structure

OUT = config.ROOT / "results" / "2026-11-03_dft_gap_truth"


def main(ids: list[str]) -> None:
    ref = get_band_gaps(ids)
    rows = []
    for mid in ids:
        s = get_structure(mid)
        r = dft_gap(s)
        err = None if ref[mid] is None else round(r["gap_eV"] - ref[mid], 3)
        ok = err is not None and (abs(err) <= config.DFT_GAP_TRUTH_TOL_EV if ref[mid] > config.METALLIC_GAP_MAX
                                  else r["gap_eV"] <= config.METALLIC_GAP_MAX)
        rows.append({"id": mid, "formula": s.composition.reduced_formula, "atoms": len(s), "gap_mp_eV": ref[mid],
                     "gap_gpaw_eV": r["gap_eV"], "error_eV": err, "passed": ok, "seconds": r.get("seconds"),
                     "n_kpoints": r.get("n_kpoints"), "cached": r["cached"], "gpaw": r.get("gpaw_version")})
        print(rows[-1], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    old = json.loads((OUT / "results.json").read_text()) if (OUT / "results.json").exists() else []
    merged = {r["id"]: r for r in old} | {r["id"]: r for r in rows}
    (OUT / "results.json").write_text(json.dumps(list(merged.values()), indent=1), encoding="utf-8")
    lines = ["# Truth test: DFT band gap (GPAW, PBE) vs Materials Project (PBE)", "",
             f"Settings: plane waves {config.DFT_GAP_ECUT_EV} eV, k-point density {config.DFT_GAP_KDENSITY} /Å, "
             f"{config.DFT_GAP_CPU} CPUs on Modal. Passed when |GPAW - MP| <= {config.DFT_GAP_TRUTH_TOL_EV} eV "
             f"(metals: GPAW <= {config.METALLIC_GAP_MAX} eV).", "",
             "| Compound | Atoms | MP PBE (eV) | GPAW PBE (eV) | Difference (eV) | Time (s) | Verdict |", "|---|---|---|---|---|---|---|"]
    for r in merged.values():
        lines.append(f"| {r['formula']} ({r['id']}) | {r['atoms']} | {r['gap_mp_eV']:.2f} | {r['gap_gpaw_eV']:.2f} | "
                     f"{r['error_eV']:+.2f} | {r['seconds']} | {'passed' if r['passed'] else 'failed'} |")
    lines += ["", f"**{sum(r['passed'] for r in merged.values())} / {len(merged)} passed.**"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
