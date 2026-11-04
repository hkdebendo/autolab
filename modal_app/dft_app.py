"""DFT band gap with GPAW on Modal CPU (the champion's check, autolab/analysis/bandgap.py).

Deploy:   modal deploy modal_app/dft_app.py

Budget rules: CPU only, short timeout per calculation, no warm container, no automatic retry, at most
two containers at a time. The PAW datasets are baked into the image (downloaded once, at build time, by Modal).
"""

import modal

from autolab import config

image = (
    modal.Image.micromamba(python_version="3.12")
    .micromamba_install("gpaw=*=*openmpi*", "openmpi", "ase=3.29", channels=["conda-forge"])
    .pip_install("python-dotenv")
    .run_commands("gpaw install-data /opt/gpaw-data --no-register",
                  "ln -s /opt/gpaw-data/gpaw-setups-* /opt/gpaw-setups")
    .env({"GPAW_SETUP_PATH": "/opt/gpaw-setups"})
    .add_local_python_source("autolab")
)

app = modal.App(config.DFT_GAP_APP, image=image)


@app.function(cpu=config.DFT_GAP_CPU, memory=config.DFT_GAP_MEMORY_MB, timeout=config.DFT_GAP_TIMEOUT_S,
              max_containers=2, retries=0, scaledown_window=10)
def pbe_gap(atoms: dict, ecut: float = config.DFT_GAP_ECUT_EV, kdensity: float = config.DFT_GAP_KDENSITY,
            smearing: float = config.DFT_GAP_SMEARING_EV, path_points: int = config.DFT_GAP_PATH_POINTS) -> dict:
    """PBE band gap of one structure (autolab.sim.dft)."""
    from autolab.sim import dft

    return dft.pbe_gap(atoms, ecut=ecut, kdensity=kdensity, smearing=smearing, path_points=path_points,
                       ncpu=config.DFT_GAP_CPU)
