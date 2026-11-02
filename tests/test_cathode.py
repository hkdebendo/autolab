"""The cobalt-free cathode domain (domains/cathode.py, analysis/cathode.py): physics, funnel, feedback, ranking.
No GPU, no network: the relaxations and the hull are stand-ins."""

import pytest
from pymatgen.core import Lattice, Structure

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.scope import enforce
from autolab.analysis.cathode import (average_voltage, capacity_mAh_g, cathode_charge_check, energy_density_Wh_kg,
                                      removable_li, volume_change_pct)
from autolab.domains import cathode as dom


def test_capacities_of_the_known_cathodes_match_the_literature():
    # LiFePO4 170, LiMnPO4 171, LiMn2O4 148, LiNi0.5Mn1.5O4 147 mAh/g (theoretical)
    for formula, k, cap in (("Li4Fe4P4O16", 4, 169.9), ("Li4Mn4P4O16", 4, 170.9), ("Li6Mn12O24", 6, 148.2),
                            ("Li4Ni2Mn6O16", 4, 146.7)):
        assert removable_li(formula) == k
        assert capacity_mAh_g(formula, k) == pytest.approx(cap, abs=0.1)


def test_neutrality_with_mixed_valence_cobalt_refused_and_li_that_can_leave():
    assert cathode_charge_check("Li6Mn11AlO24")["ok"] and removable_li("Li6Mn11AlO24") == 5  # Al3+ dilutes the redox
    assert not cathode_charge_check("Li4Fe3CoP4O16")["ok"]  # cobalt-free
    assert "cobalt-free" in cathode_charge_check("LiCoO2")["reason"]
    assert not cathode_charge_check("Li2Fe2O5")["ok"]  # Fe cannot reach +4
    assert removable_li("LiFeO2") == 0 and removable_li("Li2MnO3") == 0  # no oxidisable element (O fixed at -2)


def test_voltage_volume_and_energy_density_formulas():
    # LiFePO4 -> FePO4 + Li: V = -(E_lith - E_delith - k E_Li) / k
    assert average_voltage(-100.0, -80.0, 4, -1.9) == pytest.approx(3.1)
    assert volume_change_pct(300.0, 280.0) == pytest.approx(6.667, abs=1e-3)
    assert energy_density_Wh_kg(3.45, 170) == pytest.approx(586.5)
    with pytest.raises(ValueError):
        average_voltage(-1, -1, 0, -1.9)


PARENT = Structure(Lattice.cubic(4.2), ["Li", "Li", "Mn", "Mn", "O", "O", "O", "O"],
                   [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5], [0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5],
                    [0.5, 0.5, 0.5]])


def _tools(a=5.9, e_li=-1.9, converged=True):
    """Stand-ins: the energy of a cell is -a per Li and -7 per other atom, so V = a + E_Li for any charge."""
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_to_dict

    def relax(structures, budget):
        out = []
        for s in structures:
            n_li = sum(1 for site in s if site.specie.symbol == "Li")
            e = -a * n_li - 7.0 * (len(s) - n_li)
            out.append({"converged": converged, "energy": e, "energy_per_atom": e / len(s), "cached": True,
                        "atoms": atoms_to_dict(AseAtomsAdaptor.get_atoms(s))})
        return out

    return dom.CathodeTools(relax=relax, hull_entries=lambda els, b: ([], []), known=lambda f: [],
                            li_energy=lambda b: e_li, not_run=[])


@pytest.fixture(autouse=True)
def fake_hull(monkeypatch):
    import autolab.analysis.stability as stab

    monkeypatch.setattr(stab, "uma_entry", lambda *a, **k: None)
    monkeypatch.setattr(stab, "e_hull", lambda target, entries: {"e_hull": 0.02, "decomposition": []})
    monkeypatch.setattr(dom, "_PARENTS", {})


def test_a_candidate_goes_through_the_funnel_and_is_compared_with_its_parent():
    events = EventLog()
    out = dom.evaluate("c1", "p", PARENT, {"remove": "Mn", "add": "Ni", "count": 1}, _tools(), events)
    assert out["status"] == "passed" and out["formula"] == "Li2MnNiO4"
    assert out["voltage_V"] == pytest.approx(4.0) and out["parent_voltage_V"] == pytest.approx(4.0)
    assert out["li_removed"] == 2 and out["capacity_mAh_g"] == pytest.approx(279.9, abs=0.2)
    assert out["volume_change_pct"] == pytest.approx(0.0) and out["e_hull"] == 0.02
    steps = [e["step"] for e in events.events]
    assert steps == ["generate", "known_check", "relax", "hull", "voltage", "done"]
    v = next(e["data"] for e in events.events if e["step"] == "voltage")
    assert v["structure"]["removed"] == [0, 1] and len(v["structure"]["delithiated"]["positions"]) == 6


@pytest.mark.parametrize("sub,tools,step", [
    ({"remove": "Mn", "add": "Co", "count": 1}, {}, "generate"),  # cobalt-free
    ({"remove": "Mn", "add": "Ni", "count": 1}, {"a": 8.0}, "voltage"),  # 6.1 V: above the window
    ({"remove": "Mn", "add": "Al", "count": "all"}, {}, "voltage"),  # Al3+ only: no Li can leave
])
def test_failures_stop_at_their_step_with_a_reason(sub, tools, step):
    out = dom.evaluate("c1", "p", PARENT, sub, _tools(**tools), EventLog())
    assert out["status"] == "rejected" and out["rejected_at"] == step and out["reason"]


def test_feedback_gives_every_outcome_with_its_numbers():
    ok = dom.evaluate("c1", "p", PARENT, {"remove": "Mn", "add": "Ni", "count": 1}, _tools(), EventLog())
    bad = dom.evaluate("c2", "p", PARENT, {"remove": "Mn", "add": "Ni", "count": 1}, _tools(a=8.0), EventLog())
    fb = dom.feedback([ok, bad])
    assert [f["outcome"] for f in fb] == ["passed", "failed"]
    assert "4.00 V" in fb[0]["message"] and "average voltage" in fb[1]["message"] and "6.10 V" in fb[1]["message"]


def test_ranking_by_energy_density_then_stability_cost():
    from types import SimpleNamespace

    from autolab.domains import Campaign

    cands = [{"id": "a", "status": "passed", "energy_density_Wh_kg": 500, "e_hull_per_substitution": 0.1},
             {"id": "b", "status": "passed", "energy_density_Wh_kg": 650, "e_hull_per_substitution": 0.3},
             {"id": "c", "status": "passed", "energy_density_Wh_kg": 650, "e_hull_per_substitution": 0.2},
             {"id": "d", "status": "rejected"}]
    out = dom.ranking(Campaign(SimpleNamespace(), "g", cands))
    assert out["ranking"] == ["c", "b", "a"] and out["finalists"] == ["c", "b", "a"]


def test_the_cathode_domain_is_supported_and_has_its_own_steps():
    from autolab.agent.progress import steps_from_events
    from autolab.domains import get_domain

    assert get_domain("cathode").parents == tuple(config.CATHODE_PARENTS)
    reply = {"intent": "new_discovery", "status": "supported", "domain": "cathode", "title": "Cobalt-free cathodes",
             "constraints": [], "reply": "ok"}
    assert enforce(reply, in_conversation=False)["action"] == "start"
    keys = [s["key"] for s in steps_from_events([{"type": "loop", "step": "start", "data": {"domain": "cathode"}}],
                                                "running")]
    assert "voltage" in keys and "md" not in keys


def test_the_parent_comparison_is_decided_by_the_code():
    close = dom.vs_parent({"voltage_V": 4.754, "parent_voltage_V": 4.718, "capacity_mAh_g": 147.4,
                           "parent_capacity_mAh_g": 146.7, "energy_density_Wh_kg": 701, "parent_energy_density_Wh_kg": 692})
    assert not close["voltage_difference_beyond_model_error"] and close["verdict"].startswith("comparable")
    far = dom.vs_parent({"voltage_V": 4.3, "parent_voltage_V": 3.8, "capacity_mAh_g": 150, "parent_capacity_mAh_g": 148,
                         "energy_density_Wh_kg": 645, "parent_energy_density_Wh_kg": 562})
    assert far["voltage_difference_beyond_model_error"] and far["verdict"] == "higher voltage than its parent"
    assert dom.vs_parent({"voltage_V": None}) is None


def test_the_literature_check_asks_about_a_cathode_with_a_known_cathode_as_control():
    from autolab.agent.novelty import SYSTEM, messages_for

    c = {"id": "x", "formula": "Li8TiMn11(NiO8)4", "parent": "mp-771112", "parent_formula": "Li2Mn3NiO8",
         "substitution": {"remove": "Mn", "add": "Ti", "count": 1}, "kind": "cathode"}
    system = messages_for(c)[0]["content"]
    assert "cathode" in system and "solid electrolyte" not in system
    assert messages_for({**c, "kind": None})[0]["content"] == SYSTEM  # electrolyte questions unchanged (cache kept)
    assert config.CATHODE_NOVELTY_CONTROL["kind"] == "cathode"
    assert [s.name for s in dom.make_domain().stages] == ["candidate_analyses", "ranking", "novelty", "report"]
