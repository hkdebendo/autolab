"""Room-temperature conductivity of the candidates and parents from the MD runs in the cache (never computes).

For each structure, every cached run at the scanned temperatures (config.CONDUCTIVITY_SCAN_*; any length, seed and
GPU: A10G and H100 give the same D) is read, the blocks of the runs at one temperature are pooled into D with its
error, and the Arrhenius fit over the temperatures up to config.CONDUCTIVITY_FIT_T_MAX_K is extrapolated to 300 K.
A candidate simulated at a single temperature gets an estimate with its parent's activation energy, labelled so.
A candidate with its own fit is compared with a fit of its parent made with the same runs (same temperatures, same
number of runs per temperature, same lengths and seeds when cached: config.CONDUCTIVITY_PARENT_SAME_PROTOCOL); the
differences that remain are listed.
"""

from __future__ import annotations

from autolab import config


def _cached_runs(job: dict, t: float) -> list[tuple[int, int, dict]]:
    """The cached runs of a job at one temperature, one per (length, seed), any GPU: [(ps, seed, result)]."""
    from autolab.agent.dynamics import md_cached_result

    runs, seen = [], set()
    for ps in config.CONDUCTIVITY_SCAN_PS:
        for seed in config.CONDUCTIVITY_SCAN_SEEDS:
            for gpu in dict.fromkeys((config.MODAL_MD_GPU, config.MD_LEGACY_GPU)):
                res = md_cached_result(job, seed, t, ps, gpu=gpu)
                if res is not None and (ps, seed) not in seen:
                    seen.add((ps, seed))
                    runs.append((ps, seed, res))
    return runs


def matching_runs(runs: list[tuple], wanted: list) -> list[tuple]:
    """As many runs as `wanted` ([ps, seed] pairs, another structure's runs): the same (length, seed) first, then
    the same seed, then the same length, then any other run."""
    left, pending, chosen = list(runs), [tuple(w) for w in wanted], []
    for same in (lambda r, w: (r[0], r[1]) == w, lambda r, w: r[1] == w[1], lambda r, w: r[0] == w[0],
                 lambda r, w: True):
        for w in list(pending):
            hit = next((r for r in left if same(r, w)), None)
            if hit is not None:
                left.remove(hit), pending.remove(w), chosen.append(hit)
    return chosen


def cached_points(job: dict, temps=config.CONDUCTIVITY_SCAN_T_K, t_max: float = config.CONDUCTIVITY_FIT_T_MAX_K,
                  match: dict | None = None) -> list[dict]:
    """D ± error per temperature from the cached runs of a job ({"T", "D_cm2_per_s", "D_sem_cm2_per_s", "runs",
    "protocol": [[ps, seed], ...]}). With `match` ({T: [[ps, seed], ...]}, another structure's runs): only those
    temperatures, with as many runs each, chosen by matching_runs."""
    from autolab.analysis.diffusion import diffusion_coefficient, pool

    out = []
    for t in temps:
        if t > t_max or (match is not None and float(t) not in match):
            continue
        runs = _cached_runs(job, t)
        if match is not None:
            runs = matching_runs(runs, match[float(t)])
        if not runs:
            continue
        d = pool([diffusion_coefficient(res["positions"], res["dt_record_fs"]) for _, _, res in runs])
        if d["D_cm2_per_s"] > 0 and d["D_sem_cm2_per_s"]:
            out.append({"T": float(t), "D_cm2_per_s": d["D_cm2_per_s"], "D_sem_cm2_per_s": d["D_sem_cm2_per_s"],
                        "runs": len(runs), "protocol": sorted([ps, seed] for ps, seed, _ in runs)})
    return out


def protocol_differences(cand_points: list[dict], parent_points: list[dict]) -> list[str]:
    """What still differs between the runs of a candidate and those of its parent's matched fit (empty: none)."""
    parent = {p["T"]: p for p in parent_points}
    fmt = lambda pr: ", ".join(f"{ps} ps seed {s}" for ps, s in pr)
    out = []
    for c in cand_points:
        p = parent.get(c["T"])
        if p is None:
            out.append(f"{c['T']:.0f} K: no parent run")
        elif p.get("protocol") != c.get("protocol"):
            out.append(f"{c['T']:.0f} K: candidate {fmt(c.get('protocol') or [])}; parent {fmt(p.get('protocol') or [])}")
    return out


def structure_conductivity(job: dict, parent_fit: dict | None = None, match: dict | None = None) -> dict | None:
    """Conductivity at 300 K of one MD job (candidate or parent): its own Arrhenius fit with two temperatures or more,
    else with `parent_fit`'s activation energy (one temperature), else None. `match`: see cached_points."""
    from autolab.analysis.conductivity import conductivity, extrapolate, li_density_cm3, with_barrier

    pts = cached_points(job) if match is None else cached_points(job, match=match)
    n = li_density_cm3(job["atoms"])
    if len(pts) >= 2:
        fit = extrapolate([p["T"] for p in pts], [p["D_cm2_per_s"] for p in pts], [p["D_sem_cm2_per_s"] for p in pts])
        method = "own Arrhenius fit (" + ", ".join(str(round(p["T"])) for p in pts) + " K)"
    elif len(pts) == 1 and parent_fit:
        p = pts[0]
        fit = with_barrier(p["D_cm2_per_s"], p["D_sem_cm2_per_s"], p["T"], parent_fit["Ea_eV"], parent_fit["Ea_err_eV"])
        method = f"D at {p['T']:.0f} K with the parent's activation energy (assumed)"
    else:
        return None
    return {**conductivity(fit, n), "method": method, "points": pts}


def is_own_fit(res: dict) -> bool:
    return str(res.get("method", "")).startswith("own Arrhenius")


def candidates_conductivity(cands: list[dict], parent_job=None, candidate_job=None) -> dict:
    """Conductivity of each simulated candidate and of its parents, from the cache: {"parents": {id: ...},
    "candidates": {id: ...}}; a structure without usable runs is left out."""
    from autolab.agent import dynamics

    parent_job = parent_job or dynamics.parent_job
    candidate_job = candidate_job or dynamics.candidate_job
    parents = {}
    for pid in sorted({c["parent"] for c in cands}):
        parents[pid] = structure_conductivity(parent_job(pid))
    out = {}
    for c in cands:
        p = parents.get(c["parent"])
        res = structure_conductivity(candidate_job(c), p)
        if res is None:
            continue
        if config.CONDUCTIVITY_PARENT_SAME_PROTOCOL and p and is_own_fit(res):
            same = structure_conductivity(parent_job(c["parent"]),
                                          match={pt["T"]: pt["protocol"] for pt in res["points"]})
            if same is not None and is_own_fit(same):
                same["differences"] = protocol_differences(res["points"], same["points"])
                res["parent_same_protocol"] = same
        out[c["id"]] = res
    return {"parents": {k: v for k, v in parents.items() if v}, "candidates": out}
