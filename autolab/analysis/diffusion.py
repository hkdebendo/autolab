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
    """D in each of `n_blocks` consecutive blocks (lags up to half a block, fit from a quarter of the
    window), their mean and standard error: the uncertainty of D from one trajectory."""
    pos = np.asarray(positions, dtype=float)
    size = len(pos) // n_blocks
    if size < 8:
        raise ValueError("trajectory too short for a block estimate of D")
    lag_ps = np.arange(1, size // 2 + 1) * dt_record_fs / 1000.0
    fit = lag_ps >= lag_ps[-1] / 4
    d = np.array([np.polyfit(lag_ps[fit], windowed_msd(pos[b * size:(b + 1) * size], size // 2)[fit], 1)[0] / 6.0
                  for b in range(n_blocks)])
    return {
        "D_block_cm2_per_s": float(d.mean()) * A2_PER_PS_TO_CM2_PER_S,
        "D_block_sem_cm2_per_s": float(d.std(ddof=1) / np.sqrt(n_blocks)) * A2_PER_PS_TO_CM2_PER_S,
        "D_blocks_cm2_per_s": [float(x) * A2_PER_PS_TO_CM2_PER_S for x in d],
    }


def diffusion_coefficient(positions, dt_record_fs: float) -> dict:
    """D = slope / 6 of MSD(t), fitted on the second half of the trajectory, plus its block estimate."""
    m = msd(positions)
    t_ps = np.arange(len(m)) * dt_record_fs / 1000.0
    half = len(m) // 2
    if len(m) - half < 2:
        raise ValueError("trajectory too short to fit a diffusion coefficient")
    slope = float(np.polyfit(t_ps[half:], m[half:], 1)[0])
    d = slope / 6.0
    out = {
        "D_A2_per_ps": d,
        "D_cm2_per_s": d * A2_PER_PS_TO_CM2_PER_S,
        "msd_final_A2": float(m[-1]),
        "duration_ps": float(t_ps[-1]),
    }
    if len(m) // config.MD_D_BLOCKS >= 8:
        out.update(block_diffusion(positions, dt_record_fs))
    return out


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
