"""UMA GPU functions on Modal (SPEC 2, 8.6).

Deploy:   modal deploy modal_app/uma_app.py
Then the code calls them through autolab.sim.backend.ModalBackend.

Budget rules (CLAUDE.md): cheapest GPU that works (T4), short timeouts,
no warm containers, one container at a time, and the UMA checkpoint lives in
a Modal volume: downloaded once by a CPU-only function, GPU functions run
offline so they can never download it again.
"""

import modal

from autolab import config

CACHE = "/cache"
FAIRCHEM_DIR = f"{CACHE}/fairchem"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fairchem-core==2.24.0", "ase==3.29.0", "python-dotenv")
    .env({"HF_HOME": f"{CACHE}/hf"})
    .add_local_python_source("autolab")
)
volume = modal.Volume.from_name(config.MODAL_VOLUME, create_if_missing=True)
hf_secret = modal.Secret.from_name(config.MODAL_HF_SECRET)

app = modal.App(config.MODAL_APP, image=image)

gpu_options = dict(
    gpu=config.MODAL_GPU,
    volumes={CACHE: volume},
    env={"HF_HUB_OFFLINE": "1"},
    max_containers=1,
)


@app.function(volumes={CACHE: volume}, secrets=[hf_secret], timeout=config.MODAL_DOWNLOAD_TIMEOUT)
def download_checkpoint(model: str = config.UMA_MODEL) -> dict:
    """CPU only: fetch the UMA checkpoint into the volume (no-op if already there)."""
    import os
    import time

    from autolab.sim import uma

    t0 = time.perf_counter()
    path = uma.download_checkpoint(model, cache_dir=FAIRCHEM_DIR)
    volume.commit()
    return {"model": model, "path": path, "size_gb": round(os.path.getsize(path) / 1e9, 2),
            "seconds": round(time.perf_counter() - t0, 1)}


def _calculator(precision: str):
    import time

    from autolab.sim import uma

    t0 = time.perf_counter()
    calc = uma.get_calculator(precision, cache_dir=FAIRCHEM_DIR)
    return calc, round(time.perf_counter() - t0, 1)


@app.function(timeout=config.MODAL_RELAX_TIMEOUT, **gpu_options)
def relax_chunk(chunk: list[dict], precision: str, fmax: float, steps: int) -> list[dict]:
    """Relax a few structures in one container; the model is loaded once per container."""
    from autolab.sim.relax import relax
    from autolab.sim.serialize import atoms_from_dict

    calc, load_s = _calculator(precision)
    return [{**relax(atoms_from_dict(d), calc, fmax, steps), "model_load_s": load_s, "gpu": config.MODAL_GPU}
            for d in chunk]


@app.function(timeout=config.MODAL_MD_TIMEOUT, **gpu_options)
def md_run(atoms: dict, precision: str, temperature_K: float, n_steps: int, seed: int = 0) -> dict:
    """Molecular dynamics on one structure (supercell built inside run_md)."""
    from autolab.sim.md import run_md
    from autolab.sim.serialize import atoms_from_dict

    calc, load_s = _calculator(precision)
    res = run_md(atoms_from_dict(atoms), calc, temperature_K=temperature_K, n_steps=n_steps, seed=seed)
    return {**res, "model_load_s": load_s, "gpu": config.MODAL_GPU}
