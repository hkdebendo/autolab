"""PBE band gap with GPAW (plane-wave DFT). Runs only inside modal_app/dft_app.py (Modal CPU); never on the PC.

One self-consistent calculation on a Gamma-centred k-point mesh, then the bands at fixed density along the
high-symmetry path of the cell (ase bandpath, as Materials Project does): the gap is the smallest difference between
the lowest empty and the highest filled band over both sets of k-points (ase.dft.bandgap). With the mesh alone the
band edges can fall between mesh points and the gap is overestimated (Li3P: +0.38 eV, truth test 2026-11-03).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

# Run under MPI by pbe_gap: argv = atoms file, settings JSON, GPAW log, output JSON.
_SCRIPT = r"""
import json, sys
import numpy as np
from ase.io import read
from ase.dft.bandgap import bandgap
from gpaw import GPAW, PW, FermiDirac
from gpaw.mpi import world

atoms = read(sys.argv[1])
p = json.loads(sys.argv[2])
calc = GPAW(mode=PW(p["ecut"]), xc="PBE", kpts={"density": p["kdensity"], "gamma": True},
            occupations=FermiDirac(p["smearing"]), nbands="120%", txt=sys.argv[3])
atoms.calc = calc
energy = atoms.get_potential_energy()
efermi = calc.get_fermi_level()
nocc = int(np.ceil(calc.get_number_of_electrons() / 2))
eig = lambda c: [np.asarray(c.get_eigenvalues(kpt=k)) for k in range(len(c.get_ibz_k_points()))]
mesh = eig(calc)
path = atoms.cell.bandpath(npoints=p["path_points"])
bands = calc.fixed_density(kpts=path.kpts, symmetry="off", nbands=nocc + 8, convergence={"bands": nocc + 4},
                           txt=sys.argv[3] + ".path")
line = eig(bands)
width = min(len(e) for e in mesh + line)  # the same bands on the mesh and on the path
mesh, line = [e[:width] for e in mesh], [e[:width] for e in line]
gap_mesh = bandgap(eigenvalues=np.array([mesh]), efermi=efermi, output=None)[0]
gap, p1, p2 = bandgap(eigenvalues=np.array([mesh + line]), efermi=efermi, output=None)
if world.rank == 0:
    with open(sys.argv[4], "w") as f:
        json.dump({"gap_eV": float(gap), "gap_mesh_eV": float(gap_mesh), "path": path.path,
                   "direct": bool(p1 is not None and p2 is not None and p1[1] == p2[1]),
                   "n_kpoints": len(mesh), "n_path_kpoints": len(line), "n_bands": int(width),
                   "energy_eV": float(energy), "mpi_ranks": int(world.size)}, f)
"""


def pbe_gap(atoms: dict, ecut: float, kdensity: float, smearing: float, path_points: int, ncpu: int) -> dict:
    """PBE band gap (eV) of a serialised structure, with the time spent and the GPAW version."""
    import gpaw

    from autolab.sim.serialize import atoms_from_dict

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        paths = {k: os.path.join(tmp, k) for k in ("atoms.json", "run.py", "gpaw.txt", "out.json")}
        atoms_from_dict(atoms).write(paths["atoms.json"])
        with open(paths["run.py"], "w") as f:
            f.write(_SCRIPT)
        settings = json.dumps({"ecut": ecut, "kdensity": kdensity, "smearing": smearing, "path_points": path_points})
        env = {**os.environ, "OMP_NUM_THREADS": "1", "OMPI_ALLOW_RUN_AS_ROOT": "1",
               "OMPI_ALLOW_RUN_AS_ROOT_CONFIRM": "1"}
        cmd = ["mpiexec", "--oversubscribe", "-n", str(ncpu), "gpaw", "python", paths["run.py"], paths["atoms.json"],
               settings, paths["gpaw.txt"], paths["out.json"]]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(paths["out.json"]):
            log = open(paths["gpaw.txt"]).read()[-1500:] if os.path.exists(paths["gpaw.txt"]) else ""
            raise RuntimeError(f"GPAW failed ({proc.returncode}): {proc.stderr[-1500:]} {log}")
        with open(paths["out.json"]) as f:
            out = json.load(f)
    return {**out, "n_atoms": len(atoms["numbers"]), "seconds": round(time.perf_counter() - t0, 1),
            "gpaw_version": gpaw.__version__, "ncpu": ncpu}
