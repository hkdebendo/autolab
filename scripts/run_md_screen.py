"""Step 9C (GPU): Li diffusion screening by molecular dynamics, candidates next to their parents (SPEC 5.10).

    SIM_BACKEND=modal python scripts/run_md_screen.py results/<step>/candidates.json --ids it2-c5 it1-c2 \
        --parents mp-985583 mp-641703 --out <dir> [--dry-run]

Defaults are the validated screening settings (config: 600 K, 40 ps, 2 seeds pooled, Modal A10G). On Modal every
run gets its own container and is cached as soon as it ends (an interrupted screening resumes, nothing is ever
recomputed). md_screen.json (rows with D / D(parent) and the verdict) and md_screen.md are written at the end.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autolab import config
from autolab.agent.dynamics import candidate_job, md_runs_to_compute, md_screen, md_verdicts, modal_md_plan, parent_job
from autolab.sim.backend import ModalBackend, get_backend

from run_interfaces import backup


def _number(x: str) -> float | int:
    """600 stays an int: the cache key is built from the JSON of the settings, and 600.0 != 600 there."""
    v = float(x)
    return int(v) if v.is_integer() else v


def render(rows: list[dict]) -> str:
    e = lambda x, d=2: "—" if x is None else f"{x:.{d}e}"
    t, ps, seeds = rows[0]["temperature_K"], rows[0]["ps"], rows[0]["seeds"]
    lines = [f"# Li diffusion screening: {t:g} K, {seeds} seeds of {ps:g} ps pooled (UMA, block D, Modal "
             f"{rows[0].get('gpu') or '?'})", "",
             f"Verdict rule (config.MD_EXCLUDED_VERDICTS): a candidate slower than its parent by more than "
             f"{config.MD_TIE_SIGMA:g} combined errors is excluded for conduction but stays listed; tied or faster "
             "passes.", "",
             "| Structure | Kind | Parent | D ± s.e. (cm²/s) | D per seed | D / D(parent) | Verdict | Conduction | Framework |",
             "|---|---|---|---|---|---|---|---|---|"]
    by_id = {r["id"]: r for r in rows}
    for r in sorted(rows, key=lambda r: (r.get("parent") or r["id"], r["kind"] != "parent", r["id"])):
        v = r.get("vs_parent")
        fw = r.get("framework")
        lines.append(
            f"| {r['formula']} ({r['id']}) | {r['kind']} | "
            f"{by_id[r['parent']]['formula'] if r.get('parent') in by_id else '—'} | "
            f"{e(r['D_cm2_per_s'])} ± {e(r['D_sem_cm2_per_s'], 1)} | "
            f"{', '.join(e(d) for d in r.get('D_per_seed_cm2_per_s', []))} | "
            f"{'—' if not v else format(v['ratio'], '.2f') + ' ± ' + format(v['ratio_err'], '.2f')} | "
            f"{(v or {}).get('verdict', '—') if r['kind'] == 'candidate' else '—'} | {r.get('conduction', '—')} | "
            f"{'—' if not fw else ('intact' if fw['intact'] else 'MOVED')} |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", type=Path)
    ap.add_argument("--ids", nargs="*", default=[])
    ap.add_argument("--parents", nargs="*", default=[])
    ap.add_argument("--temperature", type=_number, default=config.MD_SCREEN_TEMPERATURE_K)
    ap.add_argument("--ps", type=_number, default=config.MD_SCREEN_PS)
    ap.add_argument("--gpu", default=config.MODAL_MD_GPU, help="Modal GPU type (SIM_BACKEND=modal)")
    ap.add_argument("--dry-run", action="store_true", help="print the runs to compute and the estimated cost only")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--backup", type=Path)
    args = ap.parse_args()

    by_id = {c["id"]: c for c in json.loads(args.candidates.read_text(encoding="utf-8"))["candidates"]}
    jobs = [parent_job(p) for p in args.parents] + [candidate_job(by_id[i]) for i in args.ids]
    runs = [{"formula": j["formula"], **r} for j in jobs
            for r in md_runs_to_compute([j], args.temperature, args.ps, all_runs=True)]
    todo = [r for r in runs if not r["cached"]]
    backend = get_backend()
    if config.SIM_BACKEND == "modal" and todo:
        plan = modal_md_plan(todo, args.gpu)
        for r, s in zip(todo, plan["seconds"]):
            print(f"{r['formula']:12s} seed {r['seed']}: about {s / 60:.0f} min")
        print(f"{len(todo)} of {len(runs)} runs to compute on Modal {args.gpu}, all in parallel: about "
              f"{plan['wall_s'] / 60:.0f} min, about {plan['usd']:.2f} $ (at most {plan['usd_max']:.2f} $ if every "
              f"run hit its {plan['timeout_s'] / 60:.0f} min limit)", flush=True)
        backend = ModalBackend(gpu=args.gpu, md_timeout_s=plan["timeout_s"])
    else:
        print(f"{len(todo)} of {len(runs)} runs to compute", flush=True)
    if args.dry_run:
        return

    args.out.mkdir(parents=True, exist_ok=True)
    rows = md_screen(jobs, args.temperature, args.ps, backend=backend)
    errors = getattr(backend, "errors", None)
    if errors:
        print(f"failed runs (not retried): {errors}")
    rows = md_verdicts(rows)
    for r in rows:
        v = r.get("vs_parent")
        print(f"{r['id']} {r['formula']} ({r['kind']}): D = {r['D_cm2_per_s']:.2e} ± {r['D_sem_cm2_per_s'] or 0:.1e} "
              f"cm2/s" + (f", D/D(parent) = {v['ratio']:.2f} ± {v['ratio_err']:.2f} ({v['verdict']})" if v else "")
              + (f" -> {r['conduction']}" if r.get("conduction") else ""), flush=True)
    (args.out / "md_screen.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    (args.out / "md_screen.md").write_text(render(rows), encoding="utf-8")
    backup(args.backup)


if __name__ == "__main__":
    main()
