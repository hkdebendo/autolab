"""UMA calculator factory: the only module that imports fairchem (SPEC 5.5).

Runs on an NVIDIA GPU only (Modal, Colab), never on the development PC.
"""

from __future__ import annotations

from functools import lru_cache

from fairchem.core import FAIRChemCalculator, pretrained_mlip

from autolab import config


@lru_cache(maxsize=None)
def get_calculator(
    precision: str = config.UMA_PRECISION_ENERGY,
    model: str = config.UMA_MODEL,
    device: str = "cuda",
    cache_dir: str | None = None,
) -> FAIRChemCalculator:
    """UMA calculator on the omat head; one per (precision, model) per process."""
    kwargs = {"cache_dir": cache_dir} if cache_dir else {}
    predictor = pretrained_mlip.get_predict_unit(model, inference_settings=precision, device=device, **kwargs)
    return FAIRChemCalculator(predictor, task_name=config.UMA_TASK)


def download_checkpoint(model: str = config.UMA_MODEL, cache_dir: str | None = None) -> str:
    """Download the checkpoint and reference energies (once); return the checkpoint path."""
    kwargs = {"cache_dir": cache_dir} if cache_dir else {}
    return str(pretrained_mlip.resolve_checkpoint(model, **kwargs).path)
