"""Configuration: environment variables (.env) and scientific thresholds.

Keys are only read from the environment; their values are never printed.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# --- Environment -------------------------------------------------------------

KEY_NAMES = ("MP_API_KEY", "HF_TOKEN", "BASETEN_API_KEY", "MODEL_API_KEY", "FIREWORKS_API_KEY")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "meta")
SIM_BACKEND = os.getenv("SIM_BACKEND", "modal")


class MissingKeyError(RuntimeError):
    """Raised when a required key is absent from .env."""


def has_key(name: str) -> bool:
    """Return True if the environment variable is set and non-empty."""
    return bool(os.getenv(name, "").strip())


def require_key(name: str) -> str:
    """Return the key value, or raise a message naming the missing variable (never its value)."""
    if not has_key(name):
        raise MissingKeyError(f"{name} is missing: fill it in {ROOT / '.env'} (see .env.example).")
    return os.environ[name].strip()


# --- Paths -------------------------------------------------------------------

CACHE_DIR = Path(os.getenv("AUTOLAB_CACHE_DIR", ROOT / ".cache"))
MP_CACHE_DIR = CACHE_DIR / "mp"
BANDGAP_CACHE_DIR = CACHE_DIR / "bandgap"
RELAX_CACHE_DIR = CACHE_DIR / "relax"

# --- Chemistry (SPEC 5.1 - 5.3) ----------------------------------------------

# Fixed closed-shell oxidation states; any other element is rejected.
OXIDATION_STATES: dict[str, int] = {
    "Li": 1, "Na": 1, "Mg": 2, "Al": 3, "Si": 4, "Ge": 4, "Sn": 4,
    "P": 5, "As": 5, "Sb": 5,
    "S": -2, "Se": -2, "O": -2, "F": -1, "Cl": -1, "Br": -1, "I": -1,
}
CHARGE_TOLERANCE = 1e-6

GENERATOR_N_ARRANGEMENTS = 8
GENERATOR_SEED = 42

SS_BOND_CUTOFF = 2.3  # Angstrom

# --- Materials Project (SPEC 5.4) --------------------------------------------

MP_REF_EHULL_MAX = 0.05  # eV/atom
MP_REF_MAX_SITES = 80
MP_THERMO_TYPES = ["GGA_GGA+U"]

# --- Stability (SPEC 5.7) ----------------------------------------------------

EHULL_SYNTHESIZABLE = 0.05  # eV/atom, metastable but acceptable
EHULL_VERY_GOOD = 0.025

# --- Band gap (SPEC 5.8) -----------------------------------------------------

BANDGAP_FILTER_MODEL = "optb88vdw_bandgap_knn"
BANDGAP_DISPLAY_MODEL = "mbj_bandgap_knn"
BANDGAP_MIN = 2.0  # eV, on the optb88 (PBE-like) scale

# --- Electrodes (SPEC 5.9) ---------------------------------------------------

WINDOW_V_MIN = 0.0
WINDOW_V_MAX = 5.0
WINDOW_V_STEP = 0.02
METALLIC_GAP_MAX = 0.1  # eV, MP band gap below which a product is metallic
PASSIVATION_FORCE_MAX = 0.1  # eV/atom, reaction energy at 0 V tolerated with metallic products
DEFAULT_CATHODES = ["LiFePO4", "LiMn2O4"]

# --- UMA simulation (SPEC 5.5, 5.6, 5.10) ------------------------------------

UMA_MODEL = "uma-s-1p2"
UMA_TASK = "omat"  # inorganic crystals head
UMA_PRECISION_ENERGY = "high-precision"  # relaxations, energies, E_hull
UMA_PRECISION_MD = "default"  # 2x faster, enough for molecular dynamics

RELAX_FMAX = 0.05  # eV/Angstrom
RELAX_STEPS = 500

MD_TIMESTEP_FS = 1.0
MD_FRICTION_PER_FS = 0.01
MD_RECORD_EVERY = 10
MD_MIN_LENGTH = 10.0  # Angstrom, minimum supercell side

# --- Modal (GPU) ---------------------------------------------------------------

MODAL_APP = "autolab-uma"
MODAL_GPU = "T4"  # cheapest GPU validated for UMA
MODAL_VOLUME = "autolab-uma-cache"  # UMA checkpoint, downloaded once
MODAL_HF_SECRET = "huggingface-secret"
MODAL_DOWNLOAD_TIMEOUT = 900  # s
MODAL_RELAX_TIMEOUT = 1200  # s, per chunk of structures
MODAL_MD_TIMEOUT = 1800  # s
MODAL_RELAX_CHUNK = 10  # structures per remote call

# --- Language models (SPEC 5.11) ---------------------------------------------

# One OpenAI-compatible client; prices in USD per million tokens (reasoning is billed as output).
LLM_PROVIDERS: dict[str, dict] = {
    "meta": {  # main brain; reasoning summaries only through the Responses API
        "base_url": "https://api.meta.ai/v1", "key": "MODEL_API_KEY", "model": "muse-spark-1.3",
        "api": "responses", "usd_per_m_input": 1.25, "usd_per_m_output": 4.25,
    },
    "baseten": {  # parallel candidate analyses, fallback for meta
        "base_url": "https://inference.baseten.co/v1", "key": "BASETEN_API_KEY",
        "model": "meta-models/muse-spark-open-1026",
        "api": "chat", "usd_per_m_input": 1.25, "usd_per_m_output": 4.25,
    },
    "fireworks": {  # small fast tasks (Muse Glimmer)
        "base_url": "https://api.fireworks.ai/inference/v1", "key": "FIREWORKS_API_KEY",
        "model": "accounts/fireworks/models/muse-glimmer-30b",
        "api": "chat", "usd_per_m_input": 0.35, "usd_per_m_output": 1.50,
    },
}
LLM_TIMEOUT = 300  # s per call
LLM_MAX_OUTPUT_TOKENS = 4000  # includes reasoning tokens

# --- Budget limits (CLAUDE.md) -----------------------------------------------

MAX_RELAXATIONS_PER_RUN = 80  # UMA relaxations not already in cache

MAX_ITERATIONS = 2
MAX_CANDIDATES_PER_ITERATION = 5
MAX_LLM_CALLS_PER_RUN = 10
MAX_TOKENS_PER_RUN = 200_000
MAX_LLM_COST_PER_RUN_USD = 1.0  # estimated from LLM_PROVIDERS prices
JSON_MAX_RETRIES = 3
