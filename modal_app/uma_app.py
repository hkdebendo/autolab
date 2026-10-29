"""UMA GPU functions on Modal (SPEC 2, 8.6).

Deploy:   modal deploy modal_app/uma_app.py
Then the code calls them through autolab.sim.backend.ModalBackend.

Budget rules (CLAUDE.md): cheapest GPU that works (T4 by default; callers may pick another GPU and more
containers with Function.with_options), short timeouts, no warm containers, no automatic retry, one container
at a time by default, and the UMA checkpoint lives in
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
    .env({"HF_HOME": f"{CACHE}/hf", "FAIRCHEM_CACHE_DIR": FAIRCHEM_DIR})  # fairchem 2.24 puts the checkpoint here
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
    scaledown_window=config.MODAL_SCALEDOWN_S,
)


@app.function(volumes={CACHE: volume}, secrets=[hf_secret], timeout=config.MODAL_DOWNLOAD_TIMEOUT)
def download_checkpoint(model: str = config.UMA_MODEL) -> dict:
    """CPU only: fetch the UMA checkpoint into the volume (no-op if already there)."""
    import os
    import time

    from autolab.sim import uma

    t0 = time.perf_counter()
    path = uma.download_checkpoint(model, cache_dir=FAIRCHEM_DIR)
    if not os.path.isdir(f"{FAIRCHEM_DIR}/models--facebook--UMA"):  # else it would vanish with the container
        raise RuntimeError(f"checkpoint outside the volume: {path} (FAIRCHEM_CACHE_DIR="
                           f"{os.environ.get('FAIRCHEM_CACHE_DIR')})")
    volume.commit()
    return {"model": model, "path": path, "size_gb": round(os.path.getsize(path) / 1e9, 2),
            "seconds": round(time.perf_counter() - t0, 1)}


def _gpu_name() -> str:
    import torch

    return torch.cuda.get_device_name(0)


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
    gpu = _gpu_name()
    return [{**relax(atoms_from_dict(d), calc, fmax, steps), "model_load_s": load_s, "gpu": gpu} for d in chunk]


@app.function(timeout=config.MODAL_MD_TIMEOUT, **gpu_options)
def md_run(atoms: dict, precision: str, temperature_K: float, n_steps: int, seed: int = 0) -> dict:
    """Molecular dynamics on one structure (supercell built inside run_md)."""
    from autolab.sim.md import run_md
    from autolab.sim.serialize import atoms_from_dict

    calc, load_s = _calculator(precision)
    res = run_md(atoms_from_dict(atoms), calc, temperature_K=temperature_K, n_steps=n_steps, seed=seed)
    return {**res, "model_load_s": load_s, "gpu": _gpu_name()}


@app.function(timeout=config.MODAL_SPEED_TIMEOUT, **gpu_options)
def md_speed(atoms: dict, precision: str, temperature_K: float, n_steps: int, warmup_steps: int = 50) -> dict:
    """MD speed on this GPU: a short warm-up run (CUDA start, first graphs), then a timed run, one model load."""
    import time

    from autolab.sim.md import run_md
    from autolab.sim.serialize import atoms_from_dict

    t0 = time.perf_counter()
    calc, load_s = _calculator(precision)
    a = atoms_from_dict(atoms)
    warm = run_md(a, calc, temperature_K=temperature_K, n_steps=warmup_steps)
    res = run_md(a, calc, temperature_K=temperature_K, n_steps=n_steps)
    return {"gpu": _gpu_name(), "n_atoms": res["n_atoms"], "n_steps": n_steps, "ms_per_step": res["ms_per_step"],
            "ms_per_atom_step": round(res["ms_per_step"] / res["n_atoms"], 4),
            "warmup_ms_per_step": warm["ms_per_step"], "model_load_s": load_s,
            "function_s": round(time.perf_counter() - t0, 1)}
