"""Kaggle GPU check: two LiCl relaxations, one per GPU, through the Kaggle backend (no secret on Kaggle).

    python scripts/kaggle_smoke.py

The results are not written to the relaxation cache (it already holds LiCl): the point is to compute them.
"""

from __future__ import annotations

import sys

from pymatgen.core import Lattice, Structure
from pymatgen.io.ase import AseAtomsAdaptor

from autolab import config
from autolab.sim.kaggle_gpu import relax_job, run_job
from autolab.sim.serialize import atoms_from_dict, atoms_to_dict


def licl(a: float) -> dict:
    s = Structure.from_spacegroup("Fm-3m", Lattice.cubic(a), ["Li", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    return atoms_to_dict(AseAtomsAdaptor.get_atoms(s))


def main() -> None:
    starts = (5.0, 5.3)
    job = relax_job([licl(a) for a in starts], config.UMA_PRECISION_ENERGY, config.RELAX_FMAX, config.RELAX_STEPS)
    results, info = run_job(job)
    ok = True
    for i, (a0, res) in enumerate(zip(starts, results)):
        if res is None:
            print(f"LiCl from a = {a0}: FAILED {info['errors'].get(i, '(no result)')}")
            ok = False
            continue
        a = atoms_from_dict(res["atoms"]).cell.lengths().mean()
        good = res["converged"] and 5.10 <= a <= 5.18
        ok &= good
        print(f"LiCl from a = {a0}: a = {a:.3f} A (validated 5.145, exp. ~5.13), {res['steps']} steps, "
              f"{res['seconds']} s, GPU {info['gpus'].get(i)} -> {'ok' if good else 'WRONG'}")
    gpus_used = sorted(set(info["gpus"].values()))
    print(f"GPUs seen: {info['status'].get('gpus')} | GPUs used: {gpus_used} | session steps: "
          f"{info['status'].get('steps')}")
    sys.exit(0 if ok and len(gpus_used) == min(2, len(starts)) else 1)


if __name__ == "__main__":
    main()
