"""The sodium solid-electrolyte domain (domains/sodium.py): Na as the mobile ion through the shared funnel and slow
tests. No GPU, no network: the relaxations, the hull and the band gaps are stand-ins."""

import pytest
from ase.build import bulk
from ase.calculators.emt import EMT

from autolab import config
from autolab.agent.events import EventLog
from autolab.agent.scope import enforce
from autolab.analysis.electrodes import li_metal_mu, passivation
from autolab.analysis.stability import make_entry
from autolab.chem.generator import generate_candidates, mobile_ion, vacancies_of
from autolab.chem.oxidation import check_charge
from autolab.domains import electrolyte as el
from autolab.domains import get_domain
from autolab.domains import sodium as dom
from autolab.sim.md import run_md
from conftest import load_structure
from test_agent import fake_relax

PARENT = "mp-28782"


@pytest.fixture(scope="module")
def na3ps4():
    """A Na3PS4 stand-in: the Li3PS4 test crystal with every Li replaced by Na."""
    s = load_structure("Li3PS4_mp-985583")
    s.replace_species({"Li": "Na"})
    return s


@pytest.fixture(autouse=True)
def raw_uma_energies(monkeypatch):
    monkeypatch.setattr(config, "UMA_MP2020", False)


def fake_hull(elements, budget):
    """Elements at 0 eV/atom, plus Na3PS4 at -1.0 eV/atom when Na, P and S are all present."""
    entries = [make_entry(e, 0.0, e, "uma") for e in elements]
    if {"Na", "P", "S"} <= set(elements):
        entries.append(make_entry("Na3PS4", -8.0, PARENT, "uma"))
    return entries, []


def tools(gap=1.9):
    bandgap = lambda s: {"gap_optb88": gap, "gap_mbj": gap + 1, "passes": gap >= config.BANDGAP_MIN,
                         "low_confidence": False}
    return dom.SodiumTools(relax=fake_relax(), hull_entries=fake_hull, bandgap=bandgap, known=lambda f: [])


def test_vacancies_are_taken_on_the_sodium_sites(na3ps4):
    assert mobile_ion(na3ps4) == "Na"
    assert vacancies_of({"vacancies": 1}) == 1 and vacancies_of({"li_vacancies": 2}) == 2
    gen = generate_candidates(na3ps4, {"remove": "S", "add": "Cl", "count": 1, "vacancies": 1}, PARENT)
    assert gen["accepted"] and gen["formula"] == "Na11P4S15Cl"
    too_many = generate_candidates(na3ps4, {"remove": "S", "add": "Cl", "count": 1, "vacancies": 99}, PARENT)
    assert not too_many["accepted"] and "Na" in too_many["reason"]


def test_charge_neutrality_with_the_sodium_oxidation_table():
    table = config.SODIUM_OXIDATION_STATES
    assert check_charge("Na3Zr2Si2PO12", table)["ok"] and check_charge("Na3SbS4", table)["ok"]
    assert check_charge("Na2.875Zr2Si1.875P1.125O12".replace(".", ""), table)["ok"] is False  # not a formula: refused
    assert not check_charge("Na3Zr2Si2PO12")["ok"]  # Zr is outside the lithium table
    assert not check_charge("Na4PS4", table)["ok"]


def test_the_sodium_band_gap_limit_is_the_domain_one(na3ps4):
    # 1.9 eV fails the lithium limit (2.0) but passes the sodium one (1.8): Na3SbS4, a working electrolyte, sits there
    sub = {"remove": "S", "add": "Cl", "count": 1, "vacancies": 1}
    out = dom.evaluate("c1", PARENT, na3ps4, sub, tools(gap=1.9), EventLog())
    assert out["status"] == "passed" and out["formula"] == "Na11P4S15Cl" and out["n_modified"] == 2
    low = dom.evaluate("c2", PARENT, na3ps4, sub, tools(gap=1.5), EventLog())
    assert (low["status"], low["rejected_at"]) == ("rejected", "bandgap") and "1.8 eV" in low["reason"]


def test_contact_with_sodium_metal_uses_the_sodium_chemical_potential():
    entries = [make_entry("Na", 0.0, "Na", "uma"), make_entry("P", 0.0, "P", "uma"), make_entry("S", 0.0, "S", "uma"),
               make_entry("Na2S", -3.6, "na2s", "uma"), make_entry("Na3P", -1.6, "na3p", "uma")]
    target = make_entry("Na3PS4", -8.0, PARENT, "uma")
    assert li_metal_mu(entries, "Na") == 0.0
    with pytest.raises(ValueError):
        li_metal_mu(entries)  # no elemental Li among sodium references
    out = passivation(target, entries + [target], get_gaps=lambda fs: {f: 2.0 for f in fs}, ion="Na")
    assert {p["formula"] for p in out["products"]} == {"Na2S", "Na3P"}


def test_md_follows_the_mobile_ion_of_the_structure(monkeypatch):
    monkeypatch.setattr(config, "MOBILE_IONS", ("Li", "Al"))  # EMT has no Na: Al stands for the mobile ion
    atoms = bulk("Cu", "fcc", a=3.61, cubic=True)
    atoms.symbols[0] = "Al"
    out = run_md(atoms, EMT(), temperature_K=300, n_steps=10, record_every=10, min_length=7.0)
    assert out["species"] == "Al" and list(out["framework_msd"]) == ["Cu"]


def test_the_feedback_names_sodium_metal_and_sodium_diffusion():
    cands = [{"id": "a", "formula": "Na3PS4", "status": "passed", "excluded_at": "electrodes",
              "exclusion_reason": "non_passivating against Na metal"},
             {"id": "b", "formula": "Na3SbS4", "status": "passed", "md_verdict": "comparable", "D_ratio_to_parent": 1.1,
              "D_ratio_err": 0.2}]
    out = el.feedback(cands, ion="Na")
    assert out[0]["test"] == "contact with Na metal" and "Na diffusion" in out[1]["test"]


def test_the_sodium_domain_settings_stages_and_steps():
    from autolab.agent.progress import steps_from_events

    d = get_domain("sodium")
    assert d.parents == tuple(config.SODIUM_PARENTS)
    assert d.settings["ion"] == "Na" and tuple(d.settings["cathodes"]) == ()
    assert d.settings["md_can_exclude"] is config.SODIUM_MD_CAN_EXCLUDE
    assert [s.name for s in d.stages][-3:] == ["ranking", "novelty", "report"]
    assert "molecular_dynamics" in [s.name for s in d.iteration_stages]
    assert "sodium" in dom.proposal_system(3).lower() and "Li metal" not in dom.proposal_system(3)
    reply = {"intent": "new_discovery", "status": "supported", "domain": "sodium", "title": "Sodium electrolytes",
             "constraints": [], "reply": "ok"}
    assert enforce(reply, in_conversation=False)["action"] == "start"
    steps = steps_from_events([{"type": "loop", "step": "start", "data": {"domain": "sodium"}}], "running")
    titles = {s["key"]: s["label"] for s in steps}
    assert "sodium metal" in titles["electrodes"] and "Sodium" in titles["md"]


def test_an_uncalibrated_md_verdict_neither_ranks_nor_excludes():
    from types import SimpleNamespace

    from autolab.domains import Campaign

    cands = [{"id": "fast", "formula": "A", "status": "passed", "md_verdict": "higher", "e_hull": 0.02,
              "e_hull_per_substitution": 0.4},
             {"id": "slow", "formula": "B", "status": "passed", "md_verdict": "lower", "e_hull": 0.01,
              "e_hull_per_substitution": 0.1}]
    lithium = el.ranking(Campaign(SimpleNamespace(tools=None), "g", [dict(c) for c in cands]))
    sodium = el.ranking(Campaign(SimpleNamespace(tools=None), "g", [dict(c) for c in cands],
                                 settings={"md_ranks": config.SODIUM_MD_CAN_EXCLUDE}))
    assert lithium["finalists"] == ["fast", "slow"]
    assert config.SODIUM_MD_CAN_EXCLUDE is False and sodium["finalists"] == ["slow", "fast"]
