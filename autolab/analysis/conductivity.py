"""Ionic conductivity at room temperature from the diffusion coefficients of the MD (limit "only D at 600 K").

D(T) measured at several temperatures is fitted to the Arrhenius law ln D = ln D0 - Ea / kT and extrapolated to
300 K; the Nernst-Einstein relation sigma = n q^2 D / (kB T) then gives the conductivity, with n the Li number
density of the relaxed cell and the tracer D (Haven ratio taken as 1, no correlated hops). The extrapolation over
300-600 K multiplies the uncertainty: the result is an estimate with a range (one standard error of ln D(300 K)).
With a single temperature, the parent's activation energy can stand in for the candidate's (labelled as such).
"""

from __future__ import annotations

import math

import numpy as np

from autolab import config

K_B_EV = 8.617333262e-5  # eV/K
K_B_J = 1.380649e-23  # J/K
Q_E = 1.602176634e-19  # C


def li_density_cm3(atoms: dict) -> float:
    """Li atoms per cm3 of a cell (serialised ASE atoms: numbers and cell in Angstrom)."""
    volume_A3 = abs(float(np.linalg.det(np.asarray(atoms["cell"], dtype=float))))
    n_li = sum(1 for z in atoms["numbers"] if z == 3)
    return n_li / (volume_A3 * 1e-24)


def nernst_einstein_mS_cm(d_cm2_s: float, n_cm3: float, temperature_K: float = config.CONDUCTIVITY_T_K) -> float:
    """sigma = n q^2 D / (kB T), in mS/cm (D in cm2/s, n in cm-3)."""
    return n_cm3 * 1e6 * Q_E ** 2 * d_cm2_s * 1e-4 / (K_B_J * temperature_K) * 1e-2 * 1e3  # SI then S/cm then mS/cm


def extrapolate(temperatures_K, d, sem, to_K: float = config.CONDUCTIVITY_T_K) -> dict:
    """Weighted fit of ln D against 1/T (sigma(ln D) = sem / D) and its value at `to_K`, with the standard error
    of the prediction (fit covariance). Needs at least two temperatures with D > 0."""
    t, d, sem = (np.asarray(x, dtype=float) for x in (temperatures_K, d, sem))
    if len(t) < 2 or np.any(d <= 0) or np.any(sem <= 0):
        raise ValueError("an Arrhenius fit needs at least two temperatures with D > 0 and an error")
    x, y, s = 1.0 / t, np.log(d), sem / d
    w = 1.0 / s ** 2
    a = np.vstack([np.ones_like(x), x]).T
    cov = np.linalg.inv(a.T @ (a * w[:, None]))
    coef = cov @ (a.T @ (w * y))
    x0 = np.array([1.0, 1.0 / to_K])
    ln_d0, ln_err = float(x0 @ coef), float(math.sqrt(x0 @ cov @ x0))
    return {"Ea_eV": float(-coef[1] * K_B_EV), "Ea_err_eV": float(math.sqrt(cov[1, 1]) * K_B_EV),
            "D_cm2_per_s": math.exp(ln_d0), "ln_D_err": ln_err, "factor": math.exp(ln_err),
            "temperatures_K": [float(v) for v in t], "to_K": to_K}


def with_barrier(d_cm2_s: float, d_sem: float, temperature_K: float, ea_eV: float, ea_err_eV: float,
                 to_K: float = config.CONDUCTIVITY_T_K) -> dict:
    """D at `to_K` from one temperature and a given activation energy (e.g. the parent's), error of both."""
    dx = 1.0 / to_K - 1.0 / temperature_K
    ln_d0 = math.log(d_cm2_s) - ea_eV / K_B_EV * dx
    ln_err = math.hypot(d_sem / d_cm2_s, ea_err_eV / K_B_EV * dx)
    return {"Ea_eV": ea_eV, "Ea_err_eV": ea_err_eV, "D_cm2_per_s": math.exp(ln_d0), "ln_D_err": ln_err,
            "factor": math.exp(ln_err), "temperatures_K": [float(temperature_K)], "to_K": to_K}


def conductivity(fit: dict, n_cm3: float) -> dict:
    """Conductivity at the fit's target temperature, with its range (x/÷ the fit's factor)."""
    sigma = nernst_einstein_mS_cm(fit["D_cm2_per_s"], n_cm3, fit["to_K"])
    return {"sigma_mS_cm": sigma, "sigma_low_mS_cm": sigma / fit["factor"], "sigma_high_mS_cm": sigma * fit["factor"],
            "temperature_K": fit["to_K"], "Ea_eV": fit["Ea_eV"], "Ea_err_eV": fit["Ea_err_eV"],
            "D_cm2_per_s": fit["D_cm2_per_s"], "fit_temperatures_K": fit["temperatures_K"],
            "li_density_cm3": n_cm3}
