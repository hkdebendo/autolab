"""The memristor domain (domains/memristor.py, analysis/migration.py): funnel, barrier stage, verdicts, ranking.
No GPU, no network: relaxations, hull, band gaps and NEB results are stand-ins."""

from types import SimpleNamespace

import pytest
from pymatgen.core import Lattice, Structure

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.scope import enforce
from autolab.analysis.migration import compact_supercell, hop_items, lowest_barrier, vs_parent
from autolab.analysis.stability import make_entry
from autolab.domains import Campaign, get_domain
from autolab.domains import memristor as dom
from test_agent import fake_relax


def rutile() -> Structure:
    return Structure.from_spacegroup("P4_2/mnm", Lattice.tetragonal(4.59, 2.96), ["Ti", "O"],
                                     [[0, 0, 0], [0.305, 0.305, 0]])


@pytest.fixture(autouse=True)
def raw_uma_energies(monkeypatch):
    monkeypatch.setattr(config, "UMA_MP2020", False)
    dom._PARENT_BARRIERS.clear()


def fake_hull(elements, budget):
    entries = [make_entry(e, 0.0, e, "uma") for e in elements]
    if {"Ti", "O"} <= set(elements):
        entries.append(make_entry("TiO2", -3.0, "mp-2657", "uma"))
    return entries, []


def fake_nebs(barrier_doped=0.6, barrier_parent=0.9, fail=False):
    def nebs(items):
        out = []
        for it in items:
            doped = 40 in it["atoms"]["numbers"]  # Zr
            if fail and doped:
                out.append(None)
                continue
            b = barrier_doped if doped else barrier_parent
            out.append({"barrier_eV": b, "converged": True, "endpoints_converged": True,
                        "energies_eV": [0.0, b / 2, b, b / 2, 0.0], "cached": False})
        return out
    return nebs


def tools(**kw):
    return dom.MemristorTools(relax=fake_relax(), hull_entries=fake_hull, known=lambda f: [], not_run=[],
                              bandgap=lambda s: {"gap_optb88": 2.5, "gap_mbj": 3.5, "passes": True, "low_confidence": False},
                              parent_structure=lambda m: rutile(), nebs=kw.get("nebs", fake_nebs()),
                              neb_cost=kw.get("neb_cost", lambda items: 0.1))


def test_isovalent_substitution_passes_and_vacancies_are_refused():
    ok = dom.evaluate("c1", "mp-2657", rutile(), {"remove": "Ti", "add": "Zr", "count": 1}, tools(), EventLog())
    assert ok["status"] == "passed" and ok["formula"] == "ZrTiO4"
    vac = dom.evaluate("c2", "mp-2657", rutile(), {"remove": "Ti", "add": "Zr", "count": 1, "vacancies": 1}, tools(),
                       EventLog())
    assert (vac["status"], vac["rejected_at"]) == ("rejected", "generate") and "isovalent" in vac["reason"]
    assert vac["substitution"]["vacancies"] == 1  # the proposal is kept as written
    alio = dom.evaluate("c3", "mp-2657", rutile(), {"remove": "Ti", "add": "Al", "count": 1}, tools(), EventLog())
    assert (alio["status"], alio["rejected_at"]) == ("rejected", "generate")  # Al3+ on Ti4+: not neutral


def test_hops_next_to_the_dopant_and_compact_supercell():
    s = rutile()
    assert len(compact_supercell(s)) >= 6 * 8  # every width >= 9 A
    doped = s.copy()
    doped.replace(0, "Zr")
    items, info = hop_items(doped, near="Zr")
    assert 1 <= len(items) <= config.NEB_MAX_HOPS and all(h["distance_A"] < config.NEB_HOP_CUTOFF_A for h in info["hops"])


def test_lowest_barrier_and_verdict_against_the_parent():
    hops = [{"distance_A": 2.5}, {"distance_A": 2.8}]
    res = [{"barrier_eV": 1.2, "converged": True, "endpoints_converged": True, "energies_eV": [0, 1.2, 0]},
           {"barrier_eV": 0.7, "converged": False, "endpoints_converged": True, "energies_eV": [0, 0.7, 0]}]
    low = lowest_barrier(res, hops)
    assert low["barrier_eV"] == 1.2 and low["converged_hops"] == 1  # a band that did not converge is not used
    assert vs_parent(0.60, 0.90)["verdict"] == "lower"
    assert vs_parent(0.85, 0.90)["verdict"] == "comparable"  # within MEMRISTOR_EA_SIGNIFICANT_EV
    assert vs_parent(None, 0.9)["verdict"] == "undetermined"


def _campaign(t, neb_usd=0.0):
    agent = SimpleNamespace(tools=t, budget=None, events=EventLog(), neb_usd=neb_usd)
    c = dom.evaluate("c1", "mp-2657", rutile(), {"remove": "Ti", "add": "Zr", "count": 1}, t, EventLog())
    return Campaign(agent, "g", [c], settings={"neb_max_usd": 1.0}), c


def test_migration_stage_measures_the_candidate_against_its_parent_and_feeds_it_back():
    camp, c = _campaign(tools())
    out = dom.migration(camp)
    assert out["verdicts"] == {"c1": "lower"} and out["parents"] == {"mp-2657": 0.9}
    assert (c["barrier_eV"], c["parent_barrier_eV"], c["barrier_difference_eV"]) == (0.6, 0.9, -0.3)
    fb = dom.feedback([c])
    assert fb[0]["outcome"] == "passed" and "0.60 eV" in fb[0]["message"]
    assert dom.migration(camp)["skipped"]  # nothing new: not computed again


def test_migration_stops_beyond_the_cost_cap_and_a_failed_band_is_undetermined():
    camp, c = _campaign(tools(neb_cost=lambda items: 0.8), neb_usd=0.5)
    out = dom.migration(camp)
    assert out["stopped"] and "MEMRISTOR_NEB_MAX_USD" in out["stopped"] and c.get("barrier_eV") is None
    camp, c = _campaign(tools(nebs=fake_nebs(fail=True)))
    dom.migration(camp)
    assert c["barrier_vs_parent"] == "undetermined"
    assert dom.feedback([c])[0]["outcome"] == "failed"


def test_ranking_puts_lower_barriers_first():
    cands = [{"id": "a", "status": "passed", "barrier_vs_parent": "comparable", "barrier_eV": 0.8, "e_hull": 0.01,
              "e_hull_per_substitution": 0.1, "formula": "A"},
             {"id": "b", "status": "passed", "barrier_vs_parent": "lower", "barrier_eV": 0.5, "e_hull": 0.03,
              "e_hull_per_substitution": 0.3, "formula": "B"},
             {"id": "c", "status": "passed", "barrier_vs_parent": None, "e_hull": 0.0, "e_hull_per_substitution": 0.0,
              "formula": "C"}]
    out = dom.ranking(Campaign(SimpleNamespace(tools=None), "g", cands))
    assert out["ranking"] == ["b", "a", "c"]


def test_the_memristor_domain_is_supported_and_has_its_own_steps():
    from autolab.agent.progress import steps_from_events

    d = get_domain("memristor")
    assert d.parents == tuple(config.MEMRISTOR_PARENTS) and [s.name for s in d.iteration_stages] == ["migration"]
    reply = {"intent": "new_discovery", "status": "supported", "domain": "memristor", "title": "Memristor oxides",
             "constraints": [], "reply": "ok"}
    assert enforce(reply, in_conversation=False)["action"] == "start"
    keys = [s["key"] for s in steps_from_events([{"type": "loop", "step": "start", "data": {"domain": "memristor"}}],
                                                "running")]
    assert "migration" in keys and "md" not in keys
    assert "isovalent" in dom.proposal_system(3) and "Li metal" not in dom.proposal_system(3)
