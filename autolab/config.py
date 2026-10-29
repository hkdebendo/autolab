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

# Electrodes with UMA energies (step 9). Interfaces add Fe/Mn/Co-O to the system: with every phase
# up to 0.05 eV/atom that is ~1300 new relaxations for 5 candidates, with on-hull phases only ~100.
INTERFACE_REF_EHULL_MAX = 0.0  # eV/atom, MP references kept for cathode interfaces
INTERFACE_CALIBRATION_MAX_DIFF = 0.05  # eV/atom, max |UMA - MP| on Li3PS4/cathode before trusting UMA interfaces
CALIBRATION_CATHODES = ["LiCoO2", "LiFePO4"]  # LiCoO2: MP -0.416 eV/atom; LiFePO4: magnetic Fe, checked too
LI3PS4_WINDOW_MP = (1.72, 2.34)  # V, Li3PS4 window with MP energies (validated, SPEC 5.9)
# MP2020 corrections (pymatgen MaterialsProject2020Compatibility) on every UMA energy (E_hull, windows, passivation,
# interfaces): UMA reproduces raw PBE / PBE+U energies, comparable across oxides of U metals and sulfides only after
# this scheme. Each entry gets its structure and oxidation states, so the corrected anion atoms are conserved.
# Validated 2026-10-28: Li3PS4/LiCoO2 -0.648 -> -0.415 (MP -0.416), Li3PS4/LiFePO4 -0.348 -> -0.144 (MP -0.133) eV/atom.
# Known approximation of the scheme: polysulfides get the sulfide correction, elemental S none (moves As, Sb results).
UMA_MP2020 = True
MP2020_HUBBARD_U = {"Co": 3.32, "Cr": 3.7, "Fe": 5.3, "Mn": 3.9, "Mo": 4.38, "Ni": 6.2, "V": 3.25, "W": 6.2}  # eV, MP sets

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
MD_SCREEN_TEMPERATURE_K = 600  # ✅ calibration v2 (2026-10-29): parents separate at 600 K, not at 1000 K
MD_SCREEN_PS = 40  # ✅ ps per run (calibration v2)
MD_SCREEN_SEEDS = 2  # ✅ runs per structure, blocks pooled (calibration v2)
MD_SCREEN_MAX_RUNS = 14  # simulations to compute per screening (structures x seeds not in the cache)
MD_D_BLOCKS = 4  # ✅ D = mean of D fitted in 4 blocks (MSD over many time origins); standard error across blocks
MD_TIE_SIGMA = 2.0  # a candidate is "tied" with its parent when |D/D(parent) - 1| <= 2 x its propagated error
MD_FRAMEWORK_D_RATIO_MAX = 0.05  # framework intact if every non-Li element diffuses < 5 % of Li
MD_EXCLUDED_VERDICTS = ("lower",)  # significantly slower than its parent (> MD_TIE_SIGMA): excluded for conduction, still listed with its numbers; "tied" and "higher" pass
MD_EXCLUDE_IF_FRAMEWORK_MOVED = True  # a candidate whose host framework moves (non-Li element > MD_FRAMEWORK_D_RATIO_MAX of Li) is excluded: its D is that of a disordering lattice
# MD calibration (plan A, truth test of the block D): the two parents, below and above the beta -> alpha
# transition of Li3PS4 (~746 K). Li7P3S11 must diffuse faster than beta-Li3PS4 at 600 and 700 K.
MD_CALIBRATION_PARENTS = {"fast": "mp-641703", "slow": "mp-985583"}  # Li7P3S11, beta-Li3PS4 (Pnma)
MD_CALIBRATION_RUNS = ((600, 40, 0), (700, 30, 0), (1000, 20, 1))  # (T in K, ps, seed); 1000 K: new seed
MD_CALIBRATION_TEST_T = (600, 700)  # temperatures where the order must hold
MD_CALIBRATION_SIGMA = 2.0  # D(fast) - D(slow) must exceed 2 x their combined standard error
MD_EA_LITERATURE_EV = {"Li7P3S11": (0.19, 0.19), "Li3PS4": (0.35, 0.41)}  # MD in the literature, comparison only
# Calibration v2 (SPEC 7, fixed 2026-10-29 before the runs): 600 K only (700 K is too close to the beta -> alpha
# transition of Li3PS4), 3 seeds of 40 ps, the 12 blocks pooled; seed 0 is the plan A run.
MD_CALIBRATION_V2_T = 600
MD_CALIBRATION_V2_PS = 40
MD_CALIBRATION_V2_SEEDS = (0, 1, 2)

# --- Modal (GPU) ---------------------------------------------------------------

MODAL_APP = "autolab-uma"
MODAL_GPU = "T4"  # cheapest GPU validated for UMA
MODAL_VOLUME = "autolab-uma-cache"  # UMA checkpoint, downloaded once
MODAL_HF_SECRET = "huggingface-secret"
MODAL_DOWNLOAD_TIMEOUT = 900  # s
MODAL_RELAX_TIMEOUT = 1200  # s, per chunk of structures
MODAL_MD_TIMEOUT = 3600  # s per MD run (40 ps on A10G: 16-27 min)
MODAL_MD_GPU = "A10G"  # GPU of the MD calibration: screening runs must use the same one (TF32)
MODAL_SPEED_TIMEOUT = 600  # s, MD speed measurement (warm-up + 0.5 ps)
MODAL_SPEED_DEADLINE_S = 900  # s; speed calls unfinished by then are cancelled (GPU never available)
MODAL_SCALEDOWN_S = 2  # s a GPU container stays up after its work (Modal's default of 60 s is billed)
MODAL_MD_MS_PER_ATOM_STEP = {"H100": 0.147, "A10G": 0.281, "A100": 0.398}  # ms, Li7P3S11 84 atoms, 0.5 ps after warm-up (2026-10-29); L4 never got a container
MODAL_STARTUP_S = 180  # s per container: start, model load and compilation (estimate)
MODAL_TIMEOUT_FACTOR = 2.0  # time limit of a run = factor x its estimate
MODAL_MAX_TIMEOUT_S = 4 * 3600  # hard cap per run
MODAL_GPU_USD_PER_H = {"T4": 0.59, "L4": 0.80, "A10G": 1.10, "A100": 2.10, "H100": 3.95}  # modal.com/pricing, 2026-10-29
MODAL_RELAX_CHUNK = 10  # structures per remote call

# --- Kaggle (GPU worker driven from the PC, no secret on Kaggle) -------------------

KAGGLE_KERNEL = "adladeeba/autolab-gpu"  # notebook overwritten by each job (kaggle kernels push)
KAGGLE_UMA_KERNEL = "adladeeba/autolab-uma-download"  # its output (run once from the UI with HF_TOKEN) holds
# FAIRCHEM_CACHE_DIR with the uma-s-1p2 checkpoint; the GPU notebooks attach it as a kernel source
KAGGLE_WHEELS_KERNEL = "adladeeba/autolab-wheels"  # CPU notebook whose output holds the wheels (offline install)
KAGGLE_FAIRCHEM = "fairchem-core==2.24.0"
KAGGLE_ACCELERATOR = "NvidiaTeslaT4"  # "GPU T4 x2"
KAGGLE_N_GPUS = 2
KAGGLE_POLL_S = 60  # s between two status checks (free)
KAGGLE_SETUP_S = 420  # s per session: start, pip install fairchem, checkpoint copy, model load
KAGGLE_RELAX_S = 45  # s per relaxation (estimate, T4, high precision)
KAGGLE_MD_MS_PER_ATOM_STEP = 1.2  # ms, T4, default precision; measured 0.56-1.16 on step 9 (small cells slower per atom)
KAGGLE_TIMEOUT_FACTOR = 2.0  # session time limit = factor x (setup + estimated compute)
KAGGLE_MAX_SESSION_S = 4 * 3600  # hard cap per session (weekly quota ~30 h)

# --- Language models (SPEC 5.11) ---------------------------------------------

# One OpenAI-compatible client; prices in USD per million tokens (reasoning is billed as output).
LLM_PROVIDERS: dict[str, dict] = {
    "meta": {  # main brain; reasoning summaries only through the Responses API
        "base_url": "https://api.meta.ai/v1", "key": "MODEL_API_KEY", "model": "muse-spark-1.3",
        "api": "responses", "usd_per_m_input": 1.25, "usd_per_m_output": 4.25,
        "usd_per_web_search": 0.0025,  # web_search tool, $2.50 per 1,000 queries, on top of tokens
    },
    "baseten": {  # parallel candidate analyses, fallback for meta
        "base_url": "https://inference.baseten.co/v1", "key": "BASETEN_API_KEY",
        "model": "meta-models/muse-spark-open-1026",
        "api": "chat", "usd_per_m_input": 1.25, "usd_per_m_output": 4.25,
    },
    # Muse Glimmer: not serverless on Fireworks (HTTP 404 "not deployed", 2026-10-28), so unused for now;
    # kept for a possible short dedicated deployment later.
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1", "key": "FIREWORKS_API_KEY",
        "model": "accounts/fireworks/models/muse-glimmer-30b",
        "api": "chat", "usd_per_m_input": 0.35, "usd_per_m_output": 1.50,
    },
}
LLM_FAST_PROVIDER = "baseten"  # small tasks (formula checks, JSON conversion, iteration summaries)
LLM_FALLBACK_PROVIDER = "baseten"  # used when the main provider fails
LLM_TIMEOUT = 300  # s per call
LLM_MAX_OUTPUT_TOKENS = 4000  # includes reasoning tokens
LLM_COST_CAPS_USD = {"meta": 1.0, "baseten": 0.5, "fireworks": 0.5}  # per run and provider

# --- Agent loop (SPEC 6) -------------------------------------------------------

AGENT_GOAL = ("Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically "
              "stable or slightly metastable, electronically insulating, by substitutions in known Li-P-S crystals.")
AGENT_PARENTS = ["mp-985583", "mp-641703"]  # Li3PS4 (32 atoms), Li7P3S11 (42 atoms); UMA references cached
AGENT_REASONING_EFFORT = "medium"
AGENT_MAX_OUTPUT_TOKENS = 8000  # proposals and analyses: reasoning + JSON
EVENT_REASONING_CHARS = 2000  # reasoning summary kept in each LLM event (replay mode)

# Novelty check (last step, final candidates only): Meta web search, links only from API citations.
NOVELTY_PROVIDER = "meta"
NOVELTY_COST_CAP_USD = 1.0
NOVELTY_SEARCH_CONTEXT = "medium"  # low | medium | high
NOVELTY_REASONING_EFFORT = "low"
NOVELTY_MAX_OUTPUT_TOKENS = 3000
NOVELTY_CONTROL = {"id": "control-LGPS", "formula": "Li10GeP2S12", "parent": None, "substitution": None}
NOVELTY_STOP_IF_CONTROL_FAILS = True  # control not found as published: the search is not trusted, finalists not checked

# Domain of the loop (autolab/domains): its funnel, its stages after the iterations, its prompts and thresholds.
AGENT_DOMAIN = "electrolyte"

# Stages after the iterations, electrolyte domain (SPEC 6.1, steps 6-7); decisions taken by the code from these rules.
ELECTRODES_TOP = 20  # passed candidates (lowest E_hull per substitution first) that get window, passivation, interfaces
AGENT_CATHODES = ("LiFePO4",)  # cathode interfaces in the loop (cobalt-free, calibrated against MP); informative, no threshold
ELECTRODE_EXCLUDED_PASSIVATION = ("non_passivating",)  # SPEC 5.9: metallic products and reaction >= 0.1 eV/atom with Li metal
MD_SELECT_MAX = 3  # candidates the model may send to MD; with their parents and MD_SCREEN_SEEDS within MD_SCREEN_MAX_RUNS
MD_MAX_USD_PER_RUN = 5.0  # estimated Modal cost of the MD stage above which it is not launched
FINAL_RANK_MD_ORDER = ("higher", "tied", "not_run")  # MD verdicts, best first; then lowest E_hull per substitution;
# excluded candidates (passivation, MD "lower", framework moved) come last and stay listed with their reason
FINALISTS_MAX = 3  # best kept candidates sent to the novelty check

# --- Budget limits (CLAUDE.md) -----------------------------------------------

MAX_RELAXATIONS_PER_RUN = 80  # UMA relaxations not already in cache

# Validation benchmark (roadmap step 2): known compounds judged blind by the funnel (their own composition is
# removed from the hull references; the language model never sees them). Lowest-energy MP polymorph of each.
BENCHMARK_GOOD = {  # known solid electrolytes, expected to pass
    "mp-985592": "Li6PS5Cl (argyrodite; ordered MP cell 0.083 eV/atom above the MP hull)",
    "mp-696138": "Li10GeP2S12 (LGPS; known to react with Li metal)",
    "mp-641703": "Li7P3S11",
    "mp-985583": "beta-Li3PS4",
}
BENCHMARK_BAD = {  # expected to be rejected: electronic conductors or unstable
    "mp-736": "Li3P (semiconductor, MP PBE gap 0.70 eV)",
    "mp-7955": "Li3Sb (semiconductor, MP PBE gap 0.48 eV)",
    "mp-9588": "LiP (semiconductor, MP PBE gap 0.81 eV)",
    "mp-9918": "LiGe (metal)",
    "mp-795": "LiSi (metal)",
    "mp-569849": "Li15Si4 (metal)",
    "mp-38200": "Li2PS3 (unstable, 0.121 eV/atom above the MP hull)",
    "mp-1222635": "Li2PS3 (unstable, 0.126 eV/atom above the MP hull, metallic)",
}

MAX_ITERATIONS = 2
MAX_CANDIDATES_PER_ITERATION = 5
MAX_LLM_CALLS_PER_RUN = 10
MAX_TOKENS_PER_RUN = 200_000
MAX_LLM_COST_PER_RUN_USD = 1.0  # estimated from LLM_PROVIDERS prices
JSON_MAX_RETRIES = 3
