"""Comparisons between evaluated candidates, computed by the code (never by the model).

The model receives ready-made statements ("E_hull: A 0.023 < B 0.026") so that it does not
misread the tables. Only candidates with numbers (E_hull computed) are compared.
"""

from __future__ import annotations

import json
from collections import defaultdict
from itertools import combinations

# (field, label, unit, better) -- better = "low" or "high"
METRICS = (
    ("e_hull", "E_hull per atom", "eV/atom", "low"),
    ("e_hull_per_substitution", "E_hull per substitution", "eV per modified site", "low"),
    ("gap_optb88", "band gap optB88", "eV", "high"),
    ("interface_reaction_energy", "worst reaction energy with the cathode", "eV/atom", "high"),  # after the electrodes
)


def _label(c: dict) -> str:
    return f"{c['formula']} ({c['id']})"


def _sub_text(s: dict) -> str:
    vac = f", -{s['li_vacancies']} Li" if s.get("li_vacancies") else ""
    return f"{s['remove']}->{s['add']} x{s['count']}{vac}"


def _pair(a: dict, b: dict) -> list[str]:
    """One statement per metric known for both candidates, best first."""
    out = []
    for field, label, unit, better in METRICS:
        va, vb = a.get(field), b.get(field)
        if va is None or vb is None:
            continue
        if round(va, 3) == round(vb, 3):
            out.append(f"{label}: {_label(a)} {va:.3f} = {_label(b)} {vb:.3f} {unit}")
            continue
        first, second = (a, b) if (va < vb) == (better == "low") else (b, a)
        sign = "<" if better == "low" else ">"
        out.append(f"{label}: {_label(first)} {first[field]:.3f} {sign} {_label(second)} {second[field]:.3f} {unit} "
                   f"(better: {first['id']})")
    return out


def _ranking(items: list[dict], field: str, better: str) -> str:
    known = [c for c in items if c.get(field) is not None]
    known.sort(key=lambda c: c[field], reverse=better == "high")
    return ", ".join(f"{c['id']} {c[field]:.3f}" for c in known)


def comparisons(candidates: list[dict]) -> list[dict]:
    """Statements for: same substitution on different parents, same parent with a different added element,
    and per-parent rankings."""
    rows = [c for c in candidates if c.get("e_hull") is not None]
    out: list[dict] = []

    by_sub = defaultdict(list)
    for c in rows:
        by_sub[json.dumps(c["substitution"], sort_keys=True)].append(c)
    for items in by_sub.values():
        if len({c["parent"] for c in items}) < 2:
            continue
        for a, b in combinations(items, 2):
            if a["parent"] != b["parent"]:
                out.append({"kind": "same substitution, different parents",
                            "about": f"{_sub_text(a['substitution'])} on {a['parent']} vs {b['parent']}",
                            "statements": _pair(a, b)})

    by_family = defaultdict(list)
    for c in rows:
        s = c["substitution"]
        by_family[(c["parent"], s["remove"], str(s["count"]), s.get("li_vacancies", 0))].append(c)
    for (parent, remove, count, vac), items in by_family.items():
        for a, b in combinations(items, 2):
            if a["substitution"]["add"] != b["substitution"]["add"]:
                out.append({"kind": "same parent, different added element",
                            "about": f"on {parent}: {remove}->{a['substitution']['add']} vs "
                                     f"{remove}->{b['substitution']['add']} (x{count}, {vac} Li vacancies)",
                            "statements": _pair(a, b)})

    by_parent = defaultdict(list)
    for c in rows:
        by_parent[c["parent"]].append(c)
    for parent, items in by_parent.items():
        if len(items) < 2:
            continue
        out.append({"kind": "ranking on one parent", "about": parent, "statements": [
            f"{label} ({'lowest' if better == 'low' else 'highest'} first): {_ranking(items, field, better)}"
            for field, label, unit, better in METRICS if sum(c.get(field) is not None for c in items) >= 2]})
    return out
