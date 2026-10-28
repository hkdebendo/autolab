"""Mean squared displacement and diffusion coefficient (SPEC 5.10)."""

from __future__ import annotations

import numpy as np

from autolab import config

A2_PER_PS_TO_CM2_PER_S = 1e-4


def msd(positions: np.ndarray) -> np.ndarray:
    """MSD (Angstrom^2) per frame from unwrapped positions of shape (frames, atoms, 3)."""
    pos = np.asarray(positions, dtype=float)
    return ((pos - pos[0]) ** 2).sum(axis=2).mean(axis=1)


def windowed_msd(positions: np.ndarray, max_lag: int, origin_stride: int = 5) -> np.ndarray:
    """MSD for lags 1..max_lag frames, averaged over time origins every `origin_stride` frames."""
    pos = np.asarray(positions, dtype=float)
    return np.array([((pos[lag:][::origin_stride] - pos[:-lag][::origin_stride]) ** 2).sum(axis=2).mean()
                     for lag in range(1, max_lag + 1)])


def block_diffusion(positions, dt_record_fs: float, n_blocks: int = config.MD_D_BLOCKS) -> dict:
    """D (Angstrom^2/ps) in each of `n_blocks` consecutive blocks (MSD averaged over time origins, lags up to half a
    block, fit from a quarter of the window), their mean and standard error: D and its uncertainty from one run."""
    pos = np.asarray(positions, dtype=float)
    size = len(pos) // n_blocks
    if size < 8:
        raise ValueError("trajectory too short for a block estimate of D")
    lag_ps = np.arange(1, size // 2 + 1) * dt_record_fs / 1000.0
    fit = lag_ps >= lag_ps[-1] / 4
    d = np.array([np.polyfit(lag_ps[fit], windowed_msd(pos[b * size:(b + 1) * size], size // 2)[fit], 1)[0] / 6.0
                  for b in range(n_blocks)])
    return {"D_A2_per_ps": float(d.mean()), "sem_A2_per_ps": float(d.std(ddof=1) / np.sqrt(n_blocks)),
            "blocks_A2_per_ps": [float(x) for x in d]}


def diffusion_coefficient(positions, dt_record_fs: float) -> dict:
    """D from the block estimate (mean over blocks, standard error as uncertainty; SPEC 5.10), with the older
    one-origin D (MSD from the first frame, slope / 6 on the second half) kept for comparison."""
    m = msd(positions)
    t_ps = np.arange(len(m)) * dt_record_fs / 1000.0
    half = len(m) // 2
    if len(m) - half < 2:
        raise ValueError("trajectory too short to fit a diffusion coefficient")
    one_origin = float(np.polyfit(t_ps[half:], m[half:], 1)[0]) / 6.0
    if len(m) // config.MD_D_BLOCKS >= 8:
        b = block_diffusion(positions, dt_record_fs)
        d, sem, blocks, method = b["D_A2_per_ps"], b["sem_A2_per_ps"], b["blocks_A2_per_ps"], "blocks"
    else:  # too short for blocks (tests, smoke runs): one-origin D without uncertainty
        d, sem, blocks, method = one_origin, None, [], "one_origin"
    k = A2_PER_PS_TO_CM2_PER_S
    return {
        "D_A2_per_ps": d,
        "D_cm2_per_s": d * k,
        "D_sem_cm2_per_s": None if sem is None else sem * k,
        "D_blocks_cm2_per_s": [x * k for x in blocks],
        "D_method": method,
        "D_one_origin_cm2_per_s": one_origin * k,
        "msd_final_A2": float(m[-1]),
        "duration_ps": float(t_ps[-1]),
    }


def compare(d: float, sem: float, d_ref: float, sem_ref: float, n_sigma: float = config.MD_TIE_SIGMA) -> dict:
    """Ratio d / d_ref with its propagated uncertainty; "tied" when the ratio is within n_sigma of 1."""
    ratio = d / d_ref
    err = ratio * float(np.hypot(sem / d, sem_ref / d_ref))
    verdict = "tied" if abs(ratio - 1) <= n_sigma * err else ("higher" if ratio > 1 else "lower")
    return {"ratio": ratio, "ratio_err": err, "verdict": verdict, "n_sigma": n_sigma}


def arrhenius(temperatures_K, d, sem) -> dict:
    """Activation energy (eV) and its uncertainty from D(T) = D0 exp(-Ea / kT), weighted fit of ln D against 1/T."""
    t, d, sem = (np.asarray(x, dtype=float) for x in (temperatures_K, d, sem))
    x, y, w = 1.0 / t, np.log(d), d / sem  # sigma(ln D) = sem / D
    k_b = 8.617333262e-5  # eV/K
    if len(t) == 2:  # exact line through two points; error from the two D uncertainties
        slope = (y[1] - y[0]) / (x[1] - x[0])
        slope_err = float(np.hypot(1 / w[0], 1 / w[1]) / abs(x[1] - x[0]))
    else:
        (slope, _), cov = np.polyfit(x, y, 1, w=w, cov="unscaled")
        slope_err = float(np.sqrt(cov[0, 0]))
    return {"Ea_eV": float(-slope * k_b), "Ea_err_eV": slope_err * k_b,
            "temperatures_K": [float(v) for v in t]}


def framework_check(framework_msd: dict[str, list[float]], dt_record_fs: float, d_li_A2_per_ps: float,
                    ratio_max: float = config.MD_FRAMEWORK_D_RATIO_MAX) -> dict:
    """Did the host framework stay intact? Each non-Li element's D (second half of its MSD) against Li's:
    rotations of PS4 units give a bounded MSD (D ~ 0), melting gives D comparable to Li."""
    elements = {}
    for el, m in framework_msd.items():
        m = np.asarray(m, dtype=float)
        t_ps = np.arange(len(m)) * dt_record_fs / 1000.0
        half = len(m) // 2
        d = float(np.polyfit(t_ps[half:], m[half:], 1)[0]) / 6.0
        elements[el] = {"msd_final_A2": float(m[-1]), "D_ratio_to_Li": d / d_li_A2_per_ps if d_li_A2_per_ps > 0 else None}
    ratios = [e["D_ratio_to_Li"] for e in elements.values() if e["D_ratio_to_Li"] is not None]
    return {"intact": all(r < ratio_max for r in ratios), "ratio_max": ratio_max, "elements": elements}
