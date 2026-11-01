"""Room-temperature conductivity from MD diffusion coefficients (analysis/conductivity.py, agent/conductivity.py)."""

import math

import pytest

from autolab import config
from autolab.agent import conductivity as agent_cond
from autolab.analysis.conductivity import (K_B_EV, conductivity, extrapolate, li_density_cm3, nernst_einstein_mS_cm,
                                           with_barrier)


def test_nernst_einstein_by_hand():
    # n = 1.7e22 cm-3, D = 3.2e-7 cm2/s, 300 K: n q2 D / kT = 1.7e28 * (1.602e-19)^2 * 3.2e-11 / (1.381e-23 * 300) S/m
    expected = 1.7e28 * 1.602176634e-19 ** 2 * 3.2e-11 / (1.380649e-23 * 300) * 1e-2 * 1e3
    assert nernst_einstein_mS_cm(3.2e-7, 1.7e22, 300) == pytest.approx(expected) and 30 < expected < 40


def test_li_density_of_a_cell():
    atoms = {"numbers": [3, 3, 16], "cell": [[5, 0, 0], [0, 5, 0], [0, 0, 4]]}  # 2 Li in 100 A3
    assert li_density_cm3(atoms) == pytest.approx(2 / 100e-24)


def test_extrapolation_recovers_an_exact_arrhenius_law():
    ea, d0 = 0.30, 1e-2
    ts = [500.0, 600.0, 700.0]
    d = [d0 * math.exp(-ea / (K_B_EV * t)) for t in ts]
    fit = extrapolate(ts, d, [0.1 * x for x in d])
    assert fit["Ea_eV"] == pytest.approx(ea) and fit["D_cm2_per_s"] == pytest.approx(d0 * math.exp(-ea / (K_B_EV * 300)))
    assert fit["factor"] > 1.1  # the extrapolation widens the 10 % errors
    with pytest.raises(ValueError):
        extrapolate([600.0], d[:1], [1e-7])


def test_parent_barrier_estimate_and_range():
    est = with_barrier(1e-5, 1e-6, 600.0, 0.2, 0.05)
    assert est["D_cm2_per_s"] == pytest.approx(1e-5 * math.exp(-0.2 / K_B_EV * (1 / 300 - 1 / 600)))
    r = conductivity(est, 1.6e22)
    assert r["sigma_low_mS_cm"] < r["sigma_mS_cm"] < r["sigma_high_mS_cm"]
    assert r["sigma_high_mS_cm"] / r["sigma_mS_cm"] == pytest.approx(est["factor"])


def test_candidate_without_second_temperature_uses_its_parent(monkeypatch):
    ea = 0.25
    pts = {"parent": [{"T": t, "D_cm2_per_s": math.exp(-ea / (K_B_EV * t)), "D_sem_cm2_per_s": 0.1 * math.exp(-ea / (K_B_EV * t)),
                       "runs": 1} for t in (600.0, 700.0)],
           "c1": [{"T": 600.0, "D_cm2_per_s": 2e-5, "D_sem_cm2_per_s": 2e-6, "runs": 2}], "c2": []}
    monkeypatch.setattr(agent_cond, "cached_points", lambda job, **kw: pts[job["id"]])
    atoms = {"numbers": [3] * 4 + [16] * 4, "cell": [[6, 0, 0], [0, 6, 0], [0, 0, 6]]}
    cands = [{"id": "c1", "parent": "p"}, {"id": "c2", "parent": "p"}]
    res = agent_cond.candidates_conductivity(cands, parent_job=lambda pid: {"id": "parent", "atoms": atoms},
                                             candidate_job=lambda c: {"id": c["id"], "atoms": atoms})
    assert res["parents"]["p"]["Ea_eV"] == pytest.approx(ea) and "own Arrhenius" in res["parents"]["p"]["method"]
    assert set(res["candidates"]) == {"c1"} and "parent's activation energy" in res["candidates"]["c1"]["method"]
    assert res["candidates"]["c1"]["Ea_eV"] == pytest.approx(ea)


def test_runs_above_the_fit_limit_are_left_out(monkeypatch):
    seen = []

    def cached(job, seed, t, ps, gpu=None):
        seen.append(t)
        return None

    monkeypatch.setattr("autolab.agent.dynamics.md_cached_result", cached)
    agent_cond.cached_points({"id": "x"}, temps=(600, 1000))
    assert set(seen) == {600} and config.CONDUCTIVITY_FIT_T_MAX_K < 1000
