"""Mean squared displacement and diffusion coefficient (SPEC 5.10)."""

from __future__ import annotations

import numpy as np

A2_PER_PS_TO_CM2_PER_S = 1e-4


def msd(positions: np.ndarray) -> np.ndarray:
    """MSD (Angstrom^2) per frame from unwrapped positions of shape (frames, atoms, 3)."""
    pos = np.asarray(positions, dtype=float)
    return ((pos - pos[0]) ** 2).sum(axis=2).mean(axis=1)


def diffusion_coefficient(positions, dt_record_fs: float) -> dict:
    """D = slope / 6 of MSD(t), fitted on the second half of the trajectory."""
    m = msd(positions)
    t_ps = np.arange(len(m)) * dt_record_fs / 1000.0
    half = len(m) // 2
    if len(m) - half < 2:
        raise ValueError("trajectory too short to fit a diffusion coefficient")
    slope = float(np.polyfit(t_ps[half:], m[half:], 1)[0])
    d = slope / 6.0
    return {
        "D_A2_per_ps": d,
        "D_cm2_per_s": d * A2_PER_PS_TO_CM2_PER_S,
        "msd_final_A2": float(m[-1]),
        "duration_ps": float(t_ps[-1]),
    }
