"""Vacancy migration barriers (sim/neb.py) with the EMT potential: no GPU, no network."""

import pytest
from ase.calculators.emt import EMT
from pymatgen.core import Lattice, Structure

from autolab.sim.neb import endpoints, run_neb, supercell_for, vacancy_barrier, vacancy_hops


def fcc_cu() -> Structure:
    return Structure.from_spacegroup("Fm-3m", Lattice.cubic(3.61), ["Cu"], [[0, 0, 0]])


def test_supercell_and_distinct_hops():
    sc = supercell_for(fcc_cu(), min_length=7.0)
    assert len(sc) == 32  # 2x2x2 conventional cells
    hops = vacancy_hops(sc, species="Cu", max_hops=3, cutoff=2.7)
    assert len(hops) == 1 and hops[0]["distance_A"] == pytest.approx(2.55, abs=0.01)  # one kind of nearest hop


def test_endpoints_keep_the_atom_order_and_move_one_ion():
    sc = supercell_for(fcc_cu(), min_length=7.0)
    h = vacancy_hops(sc, species="Cu", cutoff=2.7)[0]
    a, b = endpoints(sc, h["i"], h["j"])
    assert len(a) == len(b) == 31
    moved = [k for k in range(31) if ((a.positions[k] - b.positions[k]) ** 2).sum() > 1e-6]
    assert len(moved) == 1


def test_emt_vacancy_barrier_of_copper_is_symmetric_and_physical():
    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_to_dict

    sc = supercell_for(fcc_cu(), min_length=7.0)
    h = vacancy_hops(sc, species="Cu", cutoff=2.7)[0]
    out = vacancy_barrier(atoms_to_dict(AseAtomsAdaptor.get_atoms(sc)), h["i"], h["j"], EMT(), n_images=3,
                          fmax=0.1, steps=200)
    assert out["converged"] and out["endpoints_converged"]
    assert abs(out["reaction_eV"]) < 0.01  # equivalent sites
    assert 0.3 < out["barrier_eV"] < 1.2  # EMT copper vacancy hop, about 0.5-0.7 eV
    assert len(out["energies_eV"]) == 5 and out["energies_eV"][0] == 0.0


def test_an_unconverged_band_is_computed_once_more_with_more_images(tmp_path):
    from autolab import config
    from autolab.sim.backend import run_nebs
    from autolab.store.cache import JsonCache

    class Fake:
        def __init__(self):
            self.sent = []

        def neb_iter(self, items, precision):
            for k, it in enumerate(items):
                n = it.get("n_images", config.NEB_IMAGES)
                self.sent.append(n)
                yield k, {"barrier_eV": 1.0, "converged": n >= config.NEB_IMAGES_RETRY, "endpoints_converged": True,
                          "energies_eV": [0.0] * (n + 2), "hop": [it["i"], it["j"]]}

    from pymatgen.io.ase import AseAtomsAdaptor

    from autolab.sim.serialize import atoms_to_dict

    atoms = atoms_to_dict(AseAtomsAdaptor.get_atoms(supercell_for(fcc_cu(), min_length=7.0)))
    fake, cache = Fake(), JsonCache(tmp_path)
    out = run_nebs([{"atoms": atoms, "i": 0, "j": 1}], backend=fake, cache=cache)
    assert fake.sent == [config.NEB_IMAGES, config.NEB_IMAGES_RETRY]  # one retry, never more
    assert out[0]["converged"] and out[0]["retried_from_images"] == config.NEB_IMAGES
    again = run_nebs([{"atoms": atoms, "i": 0, "j": 1}], backend=fake, cache=cache)
    assert fake.sent == [config.NEB_IMAGES, config.NEB_IMAGES_RETRY] and again[0]["cached"]  # both from the cache
