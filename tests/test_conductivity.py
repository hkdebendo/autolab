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


def test_verdict_against_the_parent_uses_the_ranges():
    from autolab.domains.electrolyte import conductivity_verdict

    parent = {"sigma_mS_cm": 1.2, "sigma_low_mS_cm": 0.43, "sigma_high_mS_cm": 3.2}
    own = lambda s, lo, hi: {"sigma_mS_cm": s, "sigma_low_mS_cm": lo, "sigma_high_mS_cm": hi,
                             "method": "own Arrhenius fit (500, 600, 700 K)"}
    tied = conductivity_verdict(own(0.10, 0.012, 0.8), parent)  # 12x below in the centre, ranges overlap
    assert tied["verdict"] == "tied" and tied["ratio"] == pytest.approx(0.10 / 1.2, abs=1e-3)
    assert conductivity_verdict(own(0.05, 0.01, 0.3), parent)["verdict"] == "lower"
    assert conductivity_verdict(own(20, 5, 60), parent)["verdict"] == "higher"
    borrowed = {**own(0.5, 0.1, 2), "method": "D at 600 K with the parent's activation energy (assumed)"}
    assert conductivity_verdict(borrowed, parent) is None and conductivity_verdict(own(1, 0.5, 2), None) is None


def _ranked(cands):
    from types import SimpleNamespace

    from autolab.domains import Campaign
    from autolab.domains.electrolyte import ranking

    return ranking(Campaign(SimpleNamespace(tools=SimpleNamespace()), "g", cands))


def _cand(cid, rt, md="tied", eh=0.0, ea=None, window=None):
    own = {"Ea_eV": ea, "method": "own Arrhenius fit (500, 600, 700 K)"} if ea is not None else None
    return {"id": cid, "formula": "X", "status": "passed", "e_hull": eh, "e_hull_per_substitution": eh,
            "md_verdict": md, "conductivity_vs_parent": {"verdict": rt} if rt else None, "conductivity": own,
            "window": ({"stable": True, "v_low": window[0], "v_high": window[1]} if window else None)}


def test_ranking_levels_then_the_not_evaluated_group():
    cands = [_cand("slow", "lower", eh=0.0), _cand("best", "higher", eh=0.03), _cand("plain", None, eh=0.01),
             _cand("even", "tied", eh=0.02), _cand("md_up", None, md="higher", eh=0.04)]
    out = _ranked(cands)
    # higher > tied > lower, then the candidates without their own fit (ordered there by the MD verdict at 600 K)
    assert out["ranking"] == ["best", "even", "slow", "md_up", "plain"]
    assert out["levels"] == {"best": "higher", "even": "tied", "slow": "lower", "md_up": "not_fitted",
                             "plain": "not_fitted"}
    assert config.CONDUCTIVITY_RANK_ORDER[-1] == "not_fitted"


def test_tie_break_inside_a_level_a_ehull_b_ea_c_window():
    assert config.RANK_TIE_BREAK == ("e_hull_per_substitution", "activation_energy", "window_width")
    # a: lowest E_hull per substitution wins, whatever Ea and window
    out = _ranked([_cand("x", "tied", eh=0.02, ea=0.1, window=(1.0, 3.0)), _cand("y", "tied", eh=0.01, ea=0.5)])
    assert out["ranking"] == ["y", "x"] and out["finalists_order"].startswith("convention")
    # b: same E_hull, lowest own activation energy; an MD verdict at 600 K does not reorder an evaluated level
    out = _ranked([_cand("x", "tied", md="higher", eh=0.01, ea=0.40), _cand("y", "tied", eh=0.01, ea=0.20)])
    assert out["ranking"] == ["y", "x"]
    # c: same E_hull and Ea, widest window; zero width or not computed counts as 0 V
    out = _ranked([_cand("x", "tied", eh=0.01, ea=0.3), _cand("y", "tied", eh=0.01, ea=0.3, window=(1.8, 2.24)),
                   _cand("z", "tied", eh=0.01, ea=0.3, window=(1.7, 2.4))])
    assert out["ranking"] == ["z", "y", "x"]


def test_parent_fit_on_the_same_runs_as_the_candidate():
    runs = [(40, 0, "a"), (40, 1, "b"), (40, 2, "c"), (30, 0, "d")]
    assert agent_cond.matching_runs(runs, [[40, 0], [40, 1]]) == [(40, 0, "a"), (40, 1, "b")]
    # same seed at another length when the exact run is missing, then any run, never more than asked
    assert agent_cond.matching_runs([(30, 0, "d"), (40, 2, "c")], [[40, 0]]) == [(30, 0, "d")]
    assert agent_cond.matching_runs([(40, 2, "c")], [[40, 0], [40, 1]]) == [(40, 2, "c")]
    cand = [{"T": 500.0, "protocol": [[40, 0]]}, {"T": 600.0, "protocol": [[40, 0], [40, 1]]},
            {"T": 700.0, "protocol": [[40, 0]]}]
    parent = [{"T": 500.0, "protocol": [[40, 0]]}, {"T": 600.0, "protocol": [[40, 0], [40, 1]]},
              {"T": 700.0, "protocol": [[30, 0]]}]
    assert agent_cond.protocol_differences(cand, parent) == ["700 K: candidate 40 ps seed 0; parent 30 ps seed 0"]


def test_candidate_is_compared_with_the_parent_fitted_on_its_runs(monkeypatch):
    ea = 0.25
    law = lambda t, k=1.0: k * math.exp(-ea / (K_B_EV * t))

    def points(job, match=None, **kw):
        if job["id"] == "c1":
            return [{"T": t, "D_cm2_per_s": law(t, 2.0), "D_sem_cm2_per_s": 0.1 * law(t, 2.0), "runs": n,
                     "protocol": [[40, s] for s in range(n)]} for t, n in ((500.0, 1), (600.0, 2))]
        full = [(500.0, 1), (600.0, 3), (700.0, 1)]
        pts = [{"T": t, "D_cm2_per_s": law(t), "D_sem_cm2_per_s": 0.1 * law(t), "runs": n,
                "protocol": [[40, s] for s in range(n)]} for t, n in full]
        if match is None:
            return pts
        return [{**p, "runs": len(match[p["T"]]), "protocol": match[p["T"]]} for p in pts if p["T"] in match]

    monkeypatch.setattr(agent_cond, "cached_points", points)
    atoms = {"numbers": [3] * 4 + [16] * 4, "cell": [[6, 0, 0], [0, 6, 0], [0, 0, 6]]}
    res = agent_cond.candidates_conductivity([{"id": "c1", "parent": "p"}],
                                             parent_job=lambda pid: {"id": "parent", "atoms": atoms},
                                             candidate_job=lambda c: {"id": c["id"], "atoms": atoms})
    same = res["candidates"]["c1"]["parent_same_protocol"]
    assert [p["T"] for p in same["points"]] == [500.0, 600.0] and same["differences"] == []
    assert [p["T"] for p in res["parents"]["p"]["points"]] == [500.0, 600.0, 700.0]  # full fit kept for the table

    from autolab.domains.electrolyte import conductivity_verdict

    v = conductivity_verdict(res["candidates"]["c1"], same)
    assert v["parent_fit"] == "same runs as the candidate" and v["ratio"] == pytest.approx(2.0, rel=1e-3)


def test_e_hull_gap_to_the_champion_is_decided_by_the_code():
    from autolab.domains.electrolyte import e_hull_gap

    champ = {"e_hull_eV_per_atom": -0.007, "e_hull_error_eV_per_atom": 0.005}
    close = e_hull_gap({"e_hull_eV_per_atom": -0.004, "e_hull_error_eV_per_atom": 0.005}, champ)
    far = e_hull_gap({"e_hull_eV_per_atom": 0.015, "e_hull_error_eV_per_atom": 0.005}, champ)
    assert close["within_error_bars"] and close["difference_eV_per_atom"] == 0.003
    assert not far["within_error_bars"] and far["difference_eV_per_atom"] == 0.022
    assert e_hull_gap({"e_hull_eV_per_atom": 0.01}, champ) is None
