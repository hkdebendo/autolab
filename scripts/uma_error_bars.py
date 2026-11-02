"""UMA vs DFT error bars on known compounds, per chemical system (limit "UMA, not DFT"; SPEC 5.7).

    python scripts/uma_error_bars.py --out results/<dir>
    python scripts/uma_error_bars.py --out results/<dir> --systems Li-Mn-Ni-O-Ti Li-Mn-Al-O --ehull 0.0   (cathodes)

For every system whose MP references are cached (config.MP_CACHE_DIR / references, near-hull phases): each known
compound is left out of its hull and its decomposition energy is computed with UMA + MP2020 and with MP energies,
in separate hulls (analysis.uma_errors). No new UMA relaxation; one light MP request per system (energies only).
Writes uma_error_bars.json and uma_error_bars.md, and fills the cache read by the reports.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.analysis.uma_errors import cached_system_errors


def systems() -> list[list[str]]:
    """Systems with cached near-hull references (the hull references of the candidates)."""
    out = []
    for p in sorted((config.MP_CACHE_DIR / "references").glob(f"*_e{config.MP_REF_EHULL_MAX}_n{config.MP_REF_MAX_SITES}.json")):
        els = p.name.split("_")[0].split("-")
        if len(els) >= 2:
            out.append(els)
    return out


def render(rows: list[dict]) -> str:
    v = lambda x, f=".4f": "—" if x is None else format(x, f)
    lines = ["# UMA vs DFT (Materials Project) on known compounds", "",
             "Each known compound of a system is left out of the hull and its decomposition energy (eV/atom, negative "
             "when stable) is computed with UMA + MP2020 and with MP (GGA/GGA+U, MP2020) energies, in separate hulls. "
             "The mean absolute difference is the error bar given with the E_hull of a candidate of that system.", "",
             "| System | Compounds | Mean abs. diff. (eV/atom) | Largest (eV/atom) | Mean signed (eV/atom) | "
             "Polysulfides: n / mean abs. / largest |", "|---|---|---|---|---|---|"]
    for r in rows:
        if not r["available"]:
            lines.append(f"| {r['system']} | not available: {r['reason']} | | | | |")
            continue
        c, p = r["compounds"], r["polysulfides"]
        lines.append(f"| {r['system']} | {c['n']} | {v(c['mae'])} | {v(c['max_abs'])} | {v(c['bias'], '+.4f')} | "
                     f"{p['n']} / {v(p['mae'])} / {v(p['max_abs'])} |")
    unique = {x["id"]: x for r in rows if r["available"] for x in r["rows"]}  # a compound appears in each super-system
    worst = sorted(unique.values(), key=lambda x: -abs(x["diff"]))[:10]
    lines += ["", "## Largest differences", "", "| Compound | MP (eV/atom) | UMA + MP2020 (eV/atom) | Difference | "
              "Polysulfide |", "|---|---|---|---|---|"]
    lines += [f"| {x['formula']} ({x['id']}) | {x['mp']:+.4f} | {x['uma']:+.4f} | {x['diff']:+.4f} | "
              f"{'yes' if x['polysulfide'] else ''} |" for x in worst]
    polys = {x["formula"]: x for r in rows if r["available"] for x in r["rows"] if x["polysulfide"]}
    if polys:
        lines += ["", "## Polysulfides (S-S bonds)", "",
                  f"Largest difference over {len(polys)} polysulfides: "
                  f"{max(abs(x['diff']) for x in polys.values()):.4f} eV/atom "
                  "(" + ", ".join(f"{f} {x['diff']:+.4f}" for f, x in sorted(polys.items())) + ")."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--systems", nargs="*", help="systems to measure (default: every system with cached references)")
    ap.add_argument("--ehull", type=float, default=config.MP_REF_EHULL_MAX,
                    help="hull references of the domain (cathodes: 0.0, the stable phases only)")
    args = ap.parse_args()
    rows = []
    for els in ([x.split("-") for x in args.systems] if args.systems else systems()):
        try:
            r = cached_system_errors(els, ehull_max=args.ehull)
        except Exception as e:  # reported, not retried
            r = {"system": "-".join(els), "available": False, "reason": f"{type(e).__name__}: {e}"[:200], "rows": []}
        print(f"{r['system']}: {'n = ' + str(r['compounds']['n']) + ', MAE ' + str(r['compounds']['mae']) if r['available'] else r['reason']}",
              flush=True)
        rows.append(r)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "uma_error_bars.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    text = render(rows)
    (args.out / "uma_error_bars.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
