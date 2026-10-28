"""Single Markdown report of step 9: window and passivation (9A), cathode interfaces (9B), Li diffusion (9C).

    python scripts/step9_report.py --step-dir results/<step> [--run-dir <dir with interfaces.json, md_screen.json>]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _v(x, fmt=".2f"):
    return "—" if x is None else format(x, fmt)


def _empty_window(c: dict, parents: dict) -> str:
    """An empty window is not a rejection: the criterion is fragile for metastable compounds."""
    p = parents.get(c.get("parent"))
    if p and p.get("v_low") is not None:
        width = p["v_high"] - p["v_low"]
        return f"zero at the calculation precision (parent {p['formula']} already at {width:.2f} V); not rejected"
    return "zero at the calculation precision; not rejected"


def _ranking(candidates: dict, raw: dict) -> list[str]:
    """Old (raw UMA) and new (UMA + MP2020) rankings side by side, E_hull per atom and per substitution."""
    old = {c["id"]: c for c in raw["candidates"]}
    old_rank = {cid: i for i, cid in enumerate(raw["ranking"], 1)}
    by_id = {c["id"]: c for c in candidates["candidates"]}
    lines = ["| Rank (MP2020) | Rank (raw) | Candidate | Formula | E_hull per atom raw → MP2020 (eV/atom) | "
             "E_hull per substitution raw → MP2020 (eV per modified site) |", "|---|---|---|---|---|---|"]
    for i, cid in enumerate(candidates["ranking"], 1):
        c, o = by_id[cid], old.get(cid, {})
        lines.append(f"| {i} | {old_rank.get(cid, '—')} | {cid} | {c['formula']} | {_v(o.get('e_hull'), '.3f')} → "
                     f"{_v(c['e_hull'], '.3f')} | {_v(o.get('e_hull_per_substitution'), '.3f')} → "
                     f"{_v(c['e_hull_per_substitution'], '.3f')} |")
    return lines


NOTES = [
    "## Method notes", "",
    "- Energies: UMA (uma-s-1p2, omat head) with the MP2020 correction scheme of Materials Project "
    "(anion corrections, GGA/GGA+U mixing), as MP's own energies. Each entry carries its structure and oxidation "
    "states, so the corrected anion atoms are the same on both sides of every reaction (checked by a test for every "
    "candidate and every phase of its hull).",
    "- E_hull per atom is in eV/atom; E_hull per substitution = E_hull per atom x atoms / modified sites "
    "(replaced sites + Li vacancies), in eV per modified site.",
    "- As and Sb candidates move with MP2020 because of a known approximation of the scheme, not an inconsistency: "
    "polysulfides (e.g. LiS4, AsS2) get the sulfide correction while elemental S gets none, so the excess sulfur of "
    "the decomposition goes to polysulfides instead of S8. MP treats its own data the same way.",
    "- One reference is left out of the conservation check by design: LiSb3 (Sb formally -1/3), an alloy whose Sb "
    "the scheme does not correct (anion corrections only for oxidation states of -1 or lower), unlike Sb in Li3Sb.",
]


def render(candidates: dict, electrodes: dict | None, interfaces: dict | None, md: list | None,
           raw: dict | None = None) -> str:
    by_id = {c["id"]: c for c in candidates["candidates"]}
    lines = ["# AutoLab step 9 — electrodes and Li diffusion with UMA energies", "",
             "Energies: UMA + MP2020 corrections (see the method notes at the end).", ""]
    if raw:
        lines += ["## Ranking: raw UMA vs UMA + MP2020 (best first, lowest E_hull per substitution)", "",
                  *_ranking(candidates, raw), ""]

    lines += ["## 9A. Electrochemical window and contact with Li metal (UMA + MP2020 energies, CPU)", ""]
    if electrodes:
        cal = electrodes["calibration_li3ps4"]
        parents = electrodes.get("parents", {})
        lines += [f"Calibration Li3PS4: UMA {_v(cal['v_low'])}–{_v(cal['v_high'])} V vs MP "
                  f"{cal['mp_v_low']}–{cal['mp_v_high']} V. Parents (UMA): "
                  + "; ".join(f"{p['formula']} {_v(p['v_low'])}–{_v(p['v_high'])} V" for p in parents.values()), "",
                  "| Candidate | Formula | Window (V) | Against Li metal | Products at 0 V |", "|---|---|---|---|---|"]
        for r in electrodes["candidates"]:
            w, p = r["window"], r["passivation"]
            window = f"{_v(w['v_low'])}–{_v(w['v_high'])}" if w["stable"] else _empty_window(by_id[r["id"]], parents)
            prods = ", ".join(f"{d['formula']} {d['fraction']:.2f}" for d in p["products"])
            metal = f" (metallic: {', '.join(p['metallic_products'])})" if p["metallic_products"] else ""
            lines.append(f"| {r['id']} | {r['formula']} | {window} | {p['verdict']}{metal} | {prods} |")
    else:
        lines.append("Not available.")

    lines += ["", "## 9B. Interface with the cathode (UMA + MP2020 energies, on-hull references)", ""]
    if interfaces:
        lines += [f"Calibrations (Li3PS4, tolerance {interfaces['tolerance']} eV/atom):", ""]
        for c in interfaces["calibrations"]:
            lines.append(f"- Li3PS4 / {c['cathode']}: UMA {c['uma']['min_reaction_energy']:.3f} vs MP "
                         f"{c['mp']['min_reaction_energy']:.3f} eV/atom, diff {c['diff']:+.3f} → "
                         f"{'ok' if c['ok'] else 'TOO LARGE'} ({c['uma']['references']} UMA / "
                         f"{c['mp']['references']} MP references)")
        if interfaces.get("stopped"):
            lines += ["", f"**Stopped:** {interfaces['stopped']}"]
        if interfaces["candidates"]:
            lines += ["", f"| Candidate | Formula | Reaction energy with {interfaces['cathode']} (eV/atom) | "
                          "Mixing ratio | Reaction |", "|---|---|---|---|---|"]
            for r in interfaces["candidates"]:
                lines.append(f"| {r['id']} | {by_id[r['id']]['formula']} | {r['min_reaction_energy']:.3f} | "
                             f"{r['mixing_ratio']:.2f} | {r['reaction']} |")
        lines.append(f"\nNew UMA relaxations: {interfaces.get('new_relaxations')} / {interfaces['max_relaxations']}")
    else:
        lines.append("Not run.")

    lines += ["", "## 9C. Li diffusion (molecular dynamics, UMA normal precision)", ""]
    if md:
        parents = {r["id"]: r for r in md if r["kind"] == "parent"}
        lines += ["| Structure | Formula | Kind | Atoms / Li | T (K) | ps | D (cm²/s) | D / D(parent) | MSD final (Å²) | "
                  "ms/step |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in md:
            p = parents.get(r.get("parent"))
            ratio = "—" if not p or p["D_cm2_per_s"] <= 0 else f"{r['D_cm2_per_s'] / p['D_cm2_per_s']:.2f}"
            lines.append(f"| {r['id']} | {r['formula']} | {r['kind']} | {r['n_atoms']} / {r['n_li']} | "
                         f"{r['temperature_K']:.0f} | {r['ps']:.0f} | {r['D_cm2_per_s']:.2e} | {ratio} | "
                         f"{r['msd_final_A2']:.1f} | {r['ms_per_step']} |")
        lines += ["", "One temperature and one seed per structure: a first screening, not a conductivity value. "
                      "Cells of ~84 atoms hold only ~24-28 Li, so D is noisy."]
    else:
        lines.append("Not run.")
    lines += ["", *NOTES]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--step-dir", type=Path, required=True, help="folder with candidates.json and electrodes.json")
    ap.add_argument("--run-dir", type=Path, help="folder with interfaces.json and md_screen.json (default: step dir)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    run = args.run_dir or args.step_dir
    text = render(_load(args.step_dir / "candidates.json"), _load(args.step_dir / "electrodes.json"),
                  _load(run / "interfaces.json"), _load(run / "md_screen.json"),
                  _load(args.step_dir / "candidates_raw.json"))
    (args.out or run / "step9_report.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
