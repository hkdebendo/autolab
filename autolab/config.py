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
MOBILE_IONS = ("Li", "Na")  # the conducting ion of a structure: the first of these it contains (MD species, vacancies)

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

BANDGAP_MIN = 2.0  # eV, on the PBE scale (the DFT check of the champion; Li6PS5Cl, a top electrolyte, is at about 2.2)

# Electronic insulation in the funnel (2026-11-03, owner: every model called at run time must be a Meta model):
# a rule, no model. Every ion must have a closed electron shell (noble gas, d10, d10 s2,
# 4f14 or 4f14 5d10): no partly filled shell, so no easy electron hopping. Electrons left on the ion = Z - charge.
CLOSED_SHELL_ELECTRONS = (0, 2, 10, 18, 28, 30, 36, 46, 48, 54, 68, 78, 80, 86)

# DFT band gap of the champion (GPAW, PBE, plane waves; modal_app/dft_app.py, Modal CPU only). Checked after the
# ranking: the champion first; if its gap is below the domain's limit it is excluded and the next one is checked.
DFT_GAP_APP = "autolab-dft"
DFT_GAP_CACHE_DIR = CACHE_DIR / "dft_gap"
DFT_GAP_ECUT_EV = 400  # plane-wave cutoff
DFT_GAP_KDENSITY = 2.5  # k-points per inverse Angstrom (Gamma-centred mesh of the self-consistent step)
DFT_GAP_SMEARING_EV = 0.01
DFT_GAP_PATH_POINTS = 40  # k-points of the band path after the mesh (the band edges are often between mesh points)
DFT_GAP_MAX_ATOMS = 90
DFT_GAP_MAX_CALCS = 2  # DFT calculations per research (champion, then at most one replacement)
DFT_GAP_CPU = 8
DFT_GAP_MEMORY_MB = 16384
DFT_GAP_TIMEOUT_S = 3600  # one calculation; the ~40-atom lithium candidates take 10 to 20 min
DFT_GAP_USD_PER_HOUR = 0.51  # Modal CPU estimate: 8 cores (0.38 $/h) + 16 GiB (0.13 $/h)
DFT_GAP_TRUTH_TOL_EV = 0.3  # truth test: GPAW vs Materials Project, both PBE (different codes, basis and k-points)

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
# Window sensitivity (2026-11-01): the window is recomputed with every polysulfide energy shifted by -/+ this amount;
# 2 x the largest UMA + MP2020 vs MP difference measured on 9 polysulfides (0.0124 eV/atom, LiS4;
# results/2026-11-01_uma_error_bars). Reduced confidence only when a limit then moves by more than WINDOW_SENSITIVITY_MAX_V.
POLYSULFIDE_ENERGY_ERROR_EV = 0.025  # eV/atom
WINDOW_SENSITIVITY_MAX_V = 0.1  # V
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
RELAX_TRAJECTORY_FRAMES = 12  # frames of the relaxation path kept for the interface (positions + cell); display only

MD_TIMESTEP_FS = 1.0
MD_FRICTION_PER_FS = 0.01
MD_RECORD_EVERY = 10
MD_MIN_LENGTH = 10.0  # Angstrom, minimum supercell side
MD_SCREEN_TEMPERATURE_K = 600  # ✅ calibration v2 (2026-10-29): parents separate at 600 K, not at 1000 K
MD_SCREEN_PS = 40  # ✅ ps per run (calibration v2)
MD_SCREEN_SEEDS = 2  # ✅ runs per structure, blocks pooled (calibration v2)
MD_SCREEN_MAX_RUNS = 14  # simulations to compute per screening (structures x seeds not in the cache)
MD_D_BLOCKS = 4  # ✅ D = mean of D fitted in 4 blocks (MSD over many time origins); standard error across blocks
MD_TIE_SIGMA = 2.0  # a candidate is "tied" with its parent when |D - D(parent)| <= 2 x their combined standard error (difference test since 2026-11-02; the ratio test before gave the same 39 recorded verdicts)
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
MODAL_MD_GPU = "H100"  # owner, 2026-11-01: 1.3-1.7x faster than A10G (measured), 2.1-2.7x dearer per run
MD_LEGACY_GPU = "A10G"  # MD cached before 2026-11-01 (calibration v2, screenings): keys without a GPU name, read as is;
# same D on A10G and H100 (results/2026-11-01_md_gpu_check), so candidates and parents may come from either
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

# Production: the whole agent loop runs on Modal (modal_app/agent_app.py); Render only shows it.
MODAL_AGENT_APP = "autolab-agent"
MODAL_DATA_VOLUME = "autolab-data"  # the whole .cache, uploaded once; live runs read and write it (never recompute)
MODAL_KEYS_SECRET = "autolab-keys"  # created by the owner: MODEL_API_KEY, BASETEN_API_KEY, MP_API_KEY, JURY_ACCESS_CODE
MODAL_LIVE_STORE = "autolab-live"  # modal.Dict: events of the live runs as they happen, lock, run counter
LIVE_ITERATIONS = 3  # owner, 2026-11-01: the error-driven loop needs rounds after a failure
LIVE_CANDIDATES = 3
# Owner, 2026-11-04: no usage cap may block a user (number of researches, one at a time, cost or budget per research).
# The values below are practically unlimited, finite so that they stay valid JSON; kept: 3 JSON attempts, 3 rounds.
UNLIMITED = 10**9
LIVE_MAX_RELAXATIONS = UNLIMITED  # new UMA relaxations of a live research
LIVE_MD_SELECT_MAX = 1  # new MD candidates per iteration of a live run (Modal budget; cached verdicts apply to all)
LIVE_MAX_RUNS = None  # no limit on the number of researches
LIVE_RUN_TIMEOUT_S = 24 * 3600  # the longest Modal allows
LIVE_GOAL_MAX_CHARS = 500
# A request identical (case and spaces aside) to a finished research reuses it (owner, 2026-11-02): its events, result,
# report and 3D files are copied into the new conversation, nothing is recomputed or paid, and the interface shows the
# steps at its own pace with a "reused" mark. The copy is not a live run (source "reuse").
REUSE_IDENTICAL_GOAL = True
# The three suggestions of the home page (owner, 2026-11-02): each replays one finished research of its domain (no
# computation); the interface shows the same sentences (web test checks it).
REPLAY_EXAMPLES = (
    ("Find new solid electrolytes for lithium batteries that conduct lithium as fast as their parent and stay stable "
     "against lithium metal.", "0245f94a24cf"),
    ("Find new cobalt-free cathodes for lithium-ion batteries that store more energy than LiFePO4.", "590fa5770002"),
    ("Find new sodium solid electrolytes that stay stable against sodium metal and let sodium ions move fast.",
     "7af9efdcdd9a"),
)
STOP_POLL_S = 5  # s between two reads of a stop request by a running research
LIVE_PRIOR = "results/2026-10-29_reference_run/result.json"  # candidates already evaluated, shown to the model

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
    # Muse Glimmer: not serverless on Fireworks (supportsServerless=false, 2026-10-29): it runs on a dedicated
    # deployment that scales to zero, named by GLIMMER_DEPLOYMENT ("accounts/<account>/deployments/<id>", not a
    # secret). Billed per GPU-second (H200, 8 $/h), not per token: the token prices below are not used for it.
    "fireworks": {
        "base_url": "https://api.fireworks.ai/inference/v1", "key": "FIREWORKS_API_KEY",
        "model": os.getenv("GLIMMER_DEPLOYMENT", "accounts/fireworks/models/muse-glimmer-30b"),
        "api": "chat", "usd_per_m_input": 0.0, "usd_per_m_output": 0.0,
    },
    "wonder": {  # Muse Wonder: Meta's model for long multi-step work (1M-token context), the campaign review
        "base_url": "https://api.meta.ai/v1", "key": "MODEL_API_KEY", "model": "muse-wonder-1.0",
        "api": "responses", "usd_per_m_input": 4.0, "usd_per_m_output": 20.0,
    },
}
# Voice (owner, 2026-11-02): the researcher may dictate a request; Meta Muse Voice Transcribe turns it into text
# (realtime WebSocket, push to talk, through the local web server: the key stays on the server). The agent's voice is
# the browser's speech synthesis (no Meta text-to-speech model on this account).
VOICE_MODEL = "muse-voice-transcribe-1.0"
VOICE_URL = "wss://api.meta.ai/v1/asr/realtime"
VOICE_ENCODING = "PCM_16KHZ"  # mono PCM16 at 16 kHz, 80 ms frames (2560 bytes)
VOICE_MAX_SECONDS = 30  # one recording at most (cost cap; about 0.18 $ per hour of audio, third-party figure)
LLM_FAST_PROVIDER = "baseten"  # small tasks (formula checks, JSON conversion) until Glimmer takes them
# Muse Glimmer (Fireworks) writes the plain-language summaries of each iteration and of the run, in the background.
SUMMARY_PROVIDER = "fireworks"
GLIMMER_WARMUP_MAX_S = 600  # wait at most this for a scaled-to-zero deployment to wake up (HTTP 503 meanwhile)
GLIMMER_POLL_S = 20
GLIMMER_MAX_OUTPUT_TOKENS = 1500  # reasoning + summary: Glimmer always thinks first (400 left an empty text)
GLIMMER_REASONING_EFFORT = "low"  # "none" is refused (thinking-only model); "low" answers in ~1 s
SUMMARY_MAX_PER_RUN = 4  # iteration summaries + the run summary
# Parallel analyses of the candidates (SPEC 5.11): Muse Spark Open writes one short analysis per eligible candidate
# after the electrodes; Muse Spark reads them before choosing the MD candidates.
CANDIDATE_ANALYSIS_PROVIDER = "baseten"
CANDIDATE_ANALYSIS_MAX = UNLIMITED  # candidates analysed per run (every eligible one)
CANDIDATE_ANALYSIS_WORKERS = 4  # parallel calls (Baseten limit: 2 M tokens/min)
CANDIDATE_ANALYSIS_MAX_OUTPUT_TOKENS = 3000
LLM_FALLBACK_PROVIDER = "baseten"  # used when the main provider fails
LLM_TIMEOUT = 300  # s per call
LLM_MAX_OUTPUT_TOKENS = 4000  # includes reasoning tokens
LLM_COST_CAPS_USD = {"meta": UNLIMITED, "baseten": UNLIMITED, "fireworks": UNLIMITED, "wonder": UNLIMITED}  # no cap
# Campaign review (last stage of every domain, agent/review.py): Muse Wonder reads the whole campaign at once (rounds,
# measurements, failures and Muse Spark's hypotheses, ranking, literature check, report) and writes what it taught and
# the next campaign to run. It decides nothing: thresholds, ranking and verdicts stay the code's.
CAMPAIGN_REVIEW_PROVIDER = "wonder"
CAMPAIGN_REVIEW_REASONING_EFFORT = "medium"
CAMPAIGN_REVIEW_MAX_OUTPUT_TOKENS = 12000  # reasoning + JSON (at most 0.24 $ of output)
CAMPAIGN_REVIEW_MAX_INPUT_CHARS = 240_000  # dossier size cap, about 60k tokens (0.24 $ of input)
LLM_REPLY_CACHE = True  # runs keep model replies by their exact question: a known request replays for free

# --- Agent loop (SPEC 6) -------------------------------------------------------

AGENT_GOAL = ("Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically "
              "stable or slightly metastable, electronically insulating, by substitutions in known Li-P-S crystals.")
AGENT_PARENTS = ["mp-985583", "mp-641703"]  # Li3PS4 (32 atoms), Li7P3S11 (42 atoms); UMA references cached
AGENT_REASONING_EFFORT = "medium"
AGENT_MAX_OUTPUT_TOKENS = 8000  # proposals and analyses: reasoning + JSON
EVENT_REASONING_CHARS = 2000  # reasoning summary kept in each LLM event (replay mode)
REPLAY_MD_FRAMES = 400  # frames per MD run in the replay files (one every 100 fs over 40 ps)

# Novelty check (last step, final candidates only): Meta web search, links only from API citations.
NOVELTY_PROVIDER = "meta"
NOVELTY_COST_CAP_USD = UNLIMITED
NOVELTY_SEARCH_CONTEXT = "medium"  # low | medium | high
NOVELTY_REASONING_EFFORT = "low"
NOVELTY_MAX_OUTPUT_TOKENS = 3000
NOVELTY_CONTROL = {"id": "control-LGPS", "formula": "Li10GeP2S12", "parent": None, "substitution": None}
NOVELTY_STOP_IF_CONTROL_FAILS = True  # control not found as published: the search is not trusted, finalists not checked

# Domain of the loop (autolab/domains): its funnel, its stages after the iterations, its prompts and thresholds.
AGENT_DOMAIN = "electrolyte"
# How the interface names each domain (the results page groups the champions by domain, in this order; a new domain
# adds its entry here).
DOMAIN_LABELS = {
    "electrolyte": {"label": "Lithium solid electrolytes", "kind": "Lithium solid electrolyte · lithium-metal batteries",
                    "about": "Ion conductors placed between the lithium-metal anode and the cathode: they must be "
                             "stable, block electrons, survive contact with lithium metal and let Li+ move fast."},
    "cathode": {"label": "Cobalt-free cathodes", "kind": "Cobalt-free cathode · lithium-ion batteries",
                "about": "Positive electrodes that store lithium without cobalt: they must be stable and give a high "
                         "voltage and capacity (energy density) with a small volume change on charge."},
    "sodium": {"label": "Sodium solid electrolytes", "kind": "Sodium solid electrolyte · sodium-metal batteries",
               "about": "Beyond lithium, a geopolitical bottleneck: superionic Na+ conductors for the stationary storage of "
                        "renewable energy. They must be stable, block electrons, survive contact with sodium metal and "
                        "let Na+ move fast."},
}
CHAMPIONS_EXCLUDED = ("first-2026-10-29", "test-2026-10-29-br-i")  # test researches, left out of the results page

# What AutoLab can really do (interface.md 11): the scope check of a request relies on this list, never on a guess.
CAPABILITIES = {
    "supported": {
        "electrolyte": "Solid electrolytes for lithium-metal batteries: new sulfide compositions by substitution in known "
                       "Li-P-S crystals (beta-Li3PS4, Li7P3S11), evaluated for thermodynamic stability, electronic band "
                       "gap, electrochemical window, reaction with lithium metal and with a LiFePO4 cathode, lithium "
                       "diffusion by molecular dynamics at 600 K, and prior publication.",
        "sodium": "Sodium solid electrolytes (superionic Na+ conductors) for sodium-metal batteries and the stationary "
                  "storage of renewable energy: new compositions by substitution in known sodium conductors (Na3PS4, "
                  "Na3SbS4, NASICON Na3Zr2Si2PO12), evaluated for thermodynamic stability, band gap, electrochemical "
                  "window, reaction with sodium metal and sodium diffusion by molecular dynamics at 600 K.",
        "cathode": "Cobalt-free cathode materials for lithium-ion batteries: new compositions by substitution in known "
                   "cobalt-free cathodes (LiFePO4, LiMnPO4, spinel LiMn2O4, LiNi0.5Mn1.5O4), evaluated for thermodynamic "
                   "stability, average voltage, theoretical capacity, energy density and volume change on charge.",
    },
    "planned": {},
    "not_computed": "measured ionic conductivity (room-temperature values are extrapolated estimates from molecular "
                    "dynamics at 500-700 K, with their range), DFT calculations (UMA energies carry an error bar measured "
                    "against DFT on known compounds), synthesis routes, cost of the elements, experimental data, "
                    "for cathodes: voltage profiles and rate capability (only the average voltage over full "
                    "delithiation), lithium diffusion in the cathode, cycling",
}
FOLLOWUP_MAX_OUTPUT_TOKENS = 3000
REPORT_MAX_OUTPUT_TOKENS = 6000

# Stages after the iterations, electrolyte domain (SPEC 6.1, steps 6-7); decisions taken by the code from these rules.
ELECTRODES_TOP = 20  # passed candidates (lowest E_hull per substitution first) that get window, passivation, interfaces
AGENT_CATHODES = ("LiFePO4",)  # cathode interfaces in the loop (cobalt-free, calibrated against MP); informative, no threshold
ELECTRODE_EXCLUDED_PASSIVATION = ("non_passivating",)  # SPEC 5.9: metallic products and reaction >= 0.1 eV/atom with Li metal
MD_SELECT_MAX = 3  # candidates the model may send to MD (without the feedback loop); within MD_SCREEN_MAX_RUNS
MD_MAX_USD_PER_RUN = UNLIMITED  # estimated Modal cost of the MD of one research: no cap (about 5 $ for 3 rounds)

# Error-driven loop (owner, 2026-11-01): the slow tests (electrodes, reviews, MD choice, MD) run inside each iteration
# on its candidates; their results, failures included with their measurements, go back to the model before it
# analyses the iteration (hypothesis on the cause, correction) and proposes the next one.
FEEDBACK_LOOP = True
ITERATION_MD_SELECT_MAX = 1  # candidates of one iteration sent to MD (the model chooses)
FINAL_MD_SELECT_MAX = 0  # new MD after the iterations with the feedback loop (cached verdicts still apply to all)
FINAL_RANK_MD_ORDER = ("higher", "tied", "not_run")  # MD verdicts, best first, inside the "not_fitted" group of
# CONDUCTIVITY_RANK_ORDER; then RANK_TIE_BREAK;
# excluded candidates (passivation, MD "lower", framework moved) come last and stay listed with their reason
FINALISTS_MAX = 3  # best kept candidates sent to the novelty check

# Ionic conductivity at room temperature (2026-11-01, limit "only D at 600 K"): Arrhenius fit of the MD diffusion
# coefficients, extrapolated to CONDUCTIVITY_T_K, then Nernst-Einstein (analysis/conductivity.py). Runs above
# CONDUCTIVITY_FIT_T_MAX_K are left out of the fit (beta -> alpha transition of Li3PS4 at ~746 K; 1000 K runs).
CONDUCTIVITY_T_K = 300
CONDUCTIVITY_FIT_T_MAX_K = 750
CONDUCTIVITY_SCAN_T_K = (500, 550, 600, 650, 700)  # temperatures looked up in the MD cache
CONDUCTIVITY_SCAN_PS = (20, 30, 40, 60)  # run lengths looked up in the MD cache
CONDUCTIVITY_SCAN_SEEDS = (0, 1, 2)
CONDUCTIVITY_EXTRA_RUNS = ((500, 40, 0), (700, 40, 0))  # (K, ps, seed) added for the finalists by scripts/conductivity.py
# Truth test, fixed before the runs: Li7P3S11 above beta-Li3PS4, each within CONDUCTIVITY_TRUTH_FACTOR of its
# experimental room-temperature conductivity (mS/cm): Li7P3S11 glass-ceramic 3.2 (Yamane 2007) to 17 (Seino 2014);
# nanoporous beta-Li3PS4 0.16 (Liu 2013).
CONDUCTIVITY_REFERENCE_MS_CM = {"Li7P3S11": (3.2, 17.0), "Li3PS4": (0.16, 0.16)}
CONDUCTIVITY_TRUTH_FACTOR = 10.0
# Ranking with the conductivity at 300 K (owner, 2026-11-01 and 11-02): a candidate with its own Arrhenius fit is
# compared with its parent's fit by their ranges (one standard error of the extrapolation): "lower" when its whole
# range is below the parent's, "higher" when above, else "tied". This level comes first in the final ranking (best
# first); candidates without their own fit (one temperature) form a separate group, "not_fitted" ("not evaluated
# at 300 K"), after every evaluated candidate.
CONDUCTIVITY_RANK_ORDER = ("higher", "tied", "lower", "not_fitted")
# The parent's fit used in the comparison is made with the same runs as the candidate's (same temperatures, same
# number of runs at each, same lengths and seeds when cached); the parent's full fit (all its runs) stays the one of
# the truth test and of the parents' table.
CONDUCTIVITY_PARENT_SAME_PROTOCOL = True
# Order inside a level (owner, 2026-11-02), a convention, not a significant difference (the gaps are usually smaller
# than the error bars): lowest E_hull per substitution, then lowest activation energy (own fit only), then widest
# electrochemical window (zero width or not computed: 0 V). The MD verdict at 600 K is a pre-filter (a "lower" verdict
# excludes); it orders only the "not_fitted" group, before these keys.
RANK_TIE_BREAK = ("e_hull_per_substitution", "activation_energy", "window_width")

# --- Second domain: cobalt-free cathodes (owner, 2026-11-02; autolab/domains/cathode.py) ---------------------
# Substitutions in known cobalt-free cathodes; each candidate is relaxed lithiated, its stability is measured against
# the stable Materials Project phases of its system (relaxed with UMA: never MP energies), then the Li that charge
# neutrality allows is removed and the delithiated cell relaxed: average voltage, capacity, energy density and volume
# change come from the two UMA energies and the UMA energy of Li metal (the MP2020 corrections cancel: same O and
# transition-metal atoms on both sides).
CATHODE_GOAL = ("Find new cobalt-free cathode materials for lithium-ion batteries: high energy density (voltage x "
                "capacity), thermodynamically stable, with a small volume change on charge.")
CATHODE_PARENTS = ["mp-19017", "mp-18997", "mp-22584", "mp-771112"]  # LiFePO4 (Pnma, 28 atoms), LiMnPO4 (Pnma, 28),
# LiMn2O4 cubic spinel (Fd-3m, 42; 0.045 eV/atom above the MP hull, the commercial phase), LiNi0.5Mn1.5O4 (P4_332, 56)
CATHODE_LI_METAL = "mp-135"  # bcc Li, the reference of the voltage
CATHODE_FORBIDDEN = ("Co",)  # cobalt-free: never in a parent or a substitution
# Oxidation states allowed per element, as (lowest, highest); every range is contiguous, so a composition is neutral
# when 0 lies between the sums of the lowest and of the highest states (mixed valence allowed). Oxygen is fixed at -2:
# no oxygen redox. Elements outside the table are refused before any simulation.
CATHODE_OXIDATION_RANGES = {
    "Li": (1, 1), "Na": (1, 1), "K": (1, 1), "Mg": (2, 2), "Ca": (2, 2), "Zn": (2, 2), "Al": (3, 3), "Ga": (3, 3),
    "B": (3, 3), "Sc": (3, 3), "Y": (3, 3), "Cr": (3, 3), "Ti": (3, 4), "Zr": (4, 4), "Si": (4, 4), "Ge": (4, 4),
    "Sn": (4, 4), "V": (3, 5), "Nb": (5, 5), "Mo": (4, 6), "W": (6, 6), "Mn": (2, 4), "Fe": (2, 3), "Ni": (2, 4),
    "Cu": (1, 2), "P": (5, 5), "O": (-2, -2), "F": (-1, -1),
}
CATHODE_N_ARRANGEMENTS = 4  # random placements of a partial substitution, the lowest in energy kept
CATHODE_HULL_REF_EHULL_MAX = 0.0  # hull references: the stable MP phases of the system (+ the most stable terminals),
# relaxed with UMA; transition-metal oxide systems hold many near-hull phases that would cost hundreds of relaxations
CATHODE_EHULL_MAX = 0.08  # eV/atom: the commercial spinel LiMn2O4 sits 0.045 above the MP hull (GGA+U), so the
# electrolyte limit (0.05) would leave no room for doped spinels; above 0.08 a cathode is unlikely to be made
CATHODE_VOLTAGE_MIN = 3.0  # V vs Li/Li+: below, too little energy
CATHODE_VOLTAGE_MAX = 4.8  # V: above, common electrolytes decompose on charge
CATHODE_CAPACITY_MIN = 120.0  # mAh/g, theoretical, from the Li that can be removed
CATHODE_VOLUME_CHANGE_MAX = 10.0  # % between lithiated and delithiated cells: above, particles crack on cycling
CATHODE_REVIEW_MAX = 6  # passed candidates reviewed by Muse Spark Open after the iterations
CATHODE_FINALISTS_MAX = 3
# Truth test, fixed before the runs (2026-11-02): UMA average voltage of the four parents (x = 1 -> 0) within
# CATHODE_VOLTAGE_TRUTH_TOL_V of experiment, and LiFePO4 the lowest, LiNi0.5Mn1.5O4 the highest. Experiment: LiFePO4
# 3.45 V (Padhi 1997), LiMnPO4 4.1 V (Yamada 2001), LiMn2O4 4.05 V (mean of the 4.0 and 4.15 V plateaus, Thackeray
# 1983), LiNi0.5Mn1.5O4 4.7 V (Zhong 1997).
CATHODE_VOLTAGE_REFERENCE_V = {"mp-19017": 3.45, "mp-18997": 4.10, "mp-22584": 4.05, "mp-771112": 4.70}
CATHODE_VOLTAGE_TRUTH_TOL_V = 0.4
# A candidate's voltage is called different from its parent's only beyond this margin (the largest error of the truth
# test, 0.31 V, rounded up); the capacity comes from the stoichiometry and is exact.
CATHODE_VOLTAGE_SIGNIFICANT_V = 0.35
# --- Third domain: sodium solid electrolytes (owner, 2026-11-02; autolab/domains/sodium.py) -------------------
# The electrolyte funnel and slow tests with Na+ as the mobile ion: substitutions in known sodium conductors, charge
# neutrality with fixed oxidation states, stability against the stable MP phases relaxed with UMA, closed-shell ions,
# window and passivation against sodium metal, Na diffusion by molecular dynamics against the parent.
SODIUM_GOAL = ("Find new sodium solid electrolytes (superionic Na+ conductors) for sodium-metal batteries: "
               "thermodynamically stable, electronically insulating, compatible with sodium metal, with fast Na+ motion.")
SODIUM_PARENTS = ["mp-28782", "mp-10167", "mp-532695"]  # Na3PS4 (P-42_1c, 16 atoms, the tetragonal phase), Na3SbS4
# (I-43m, 8), NASICON Na3Zr2Si2PO12 (P1 ordering, 80; the most stable one in MP)
SODIUM_OXIDATION_STATES = {
    "Na": 1, "Li": 1, "K": 1, "Mg": 2, "Ca": 2, "Sr": 2, "Ba": 2, "Zn": 2, "Al": 3, "Ga": 3, "In": 3, "Sc": 3, "Y": 3,
    "La": 3, "B": 3, "Si": 4, "Ge": 4, "Sn": 4, "Ti": 4, "Zr": 4, "Hf": 4, "P": 5, "As": 5, "Sb": 5, "Nb": 5, "Ta": 5,
    "W": 6, "Mo": 6, "O": -2, "S": -2, "Se": -2, "F": -1, "Cl": -1, "Br": -1, "I": -1,
}
SODIUM_HULL_REF_EHULL_MAX = 0.0  # the stable MP phases (the NASICON system Na-Zr-Si-P-O holds many near-hull phases)
SODIUM_EHULL_MAX = 0.05  # eV/atom, as for the lithium electrolytes
SODIUM_BANDGAP_MIN = 1.8  # eV (PBE scale; the champion's DFT gap): Na3SbS4, a working electrolyte (about 1 mS/cm), has a PBE gap of 1.93 eV
# in MP; the lithium limit (2.0) would reject it; metals and narrow-gap semiconductors stay out
SODIUM_MD_MAX_USD = UNLIMITED  # MD of one sodium research (no cap, owner 2026-11-04)
SODIUM_CATHODES: tuple = ()  # no cathode interface: the UMA interface calibration was made for Li cathodes only
# Calibration of the sodium MD, fixed before the runs (2026-11-02): at 600 K, 2 seeds of 40 ps each, Na3SbS4 (about
# 1-3 mS/cm at room temperature) faster than tetragonal Na3PS4 (0.01-0.2 mS/cm) by more than 2 combined errors, both
# frameworks intact. If it fails, the sodium MD informs and never excludes a candidate (SODIUM_MD_CAN_EXCLUDE False).
SODIUM_MD_CALIBRATION = {"fast": "mp-10167", "slow": "mp-28782"}
SODIUM_MD_CALIBRATION_SEEDS = 2
SODIUM_MD_CAN_EXCLUDE = True  # calibration v2 PASSED with the difference test (2026-11-02, owner's choice of the test,
# the one of the lithium calibration v2): Na23Sb7WS32 faster than Na3SbS4 by 2.8 combined errors (2.1e-6 against 7.6e-8
# cm2/s), frameworks intact; by the ratio test first used it was a tie (1.1 sigma). v1 (Na3SbS4 against tetragonal
# Na3PS4, two different crystals) still fails (-1.5 sigma): only a candidate against its own parent is trusted
# Calibration v2 of the sodium MD, fixed before its runs (2026-11-02, after v1 failed): what the domain really compares
# is a candidate against its OWN parent. Test: Na vacancies made by W6+ on Sb5+ sites must speed up Na in Na3SbS4, as in
# experiment (Na2.88Sb0.88W0.12S4 about 32 mS/cm against 1-3 mS/cm). One W for one Sb and one Na vacancy in the 2x2x2
# supercell of the relaxed primitive cell (Na23Sb7WS32 = Na2.875Sb0.875W0.125S4), lowest of a few arrangements, against
# the cached Na3SbS4 runs of v1 (same 64-atom cell, same seeds): passed if faster by more than MD_TIE_SIGMA combined
# errors, frameworks intact. Passed: the sodium MD verdict against the parent may exclude and rank again
# (SODIUM_MD_CAN_EXCLUDE True); v1 stays recorded (comparisons across different crystals are not reliable). Failed: no
# change.
SODIUM_MD_CALIBRATION_V2 = {"parent": "mp-10167", "supercell": (2, 2, 2), "n_arrangements": 4,
                            "substitution": {"remove": "Sb", "add": "W", "count": 1, "vacancies": 1}}
SODIUM_NOVELTY_CONTROL = {"id": "control-Na3PS4", "formula": "Na3PS4", "parent": None, "substitution": None,
                          "kind": "sodium"}
SODIUM_NOT_COMPUTED = ("DFT calculations (UMA energies with an error bar measured against DFT on known compounds), "
                       "ionic conductivity at room temperature (only the Na diffusion at 600 K against the parent, "
                       "calibrated on Na vacancies in Na3SbS4; comparisons between different crystals failed their "
                       "calibration), the "
                       "interface with a sodium cathode, grain boundaries, synthesis, cost of the elements, experimental "
                       "data")

# Blind benchmark of the cathode funnel (fixed before the runs, 2026-11-02): known compounds go through steps 3-5 of the
# funnel with their own composition removed from the hull; expected outcome of each, from experiment.
CATHODE_BENCHMARK = [
    {"id": "mp-865631", "formula": "LiNiO2", "group": "good", "expected": "passed",
     "why": "layered Ni cathode, about 3.8 V"},
    {"id": "mp-6396", "formula": "Li3V2(PO4)3", "group": "good", "expected": "passed",
     "why": "NASICON V cathode, 3.6-4.6 V plateaus"},
    {"id": "mp-38280", "formula": "LiTiO2", "group": "hard negative", "expected": "voltage",
     "why": "Ti3+/Ti4+ couple far below 3 V"},
    {"id": "mp-18968", "formula": "Li2FeSiO4", "group": "hard negative", "expected": "voltage",
     "why": "real cathode at 2.8 V after cycling (Nyten 2005): below the 3.0 V window"},
    {"id": "mp-22526", "formula": "LiCoO2", "group": "bad", "expected": "generate", "why": "contains cobalt"},
    {"id": "mp-18988", "formula": "Li2MnO3", "group": "bad", "expected": "voltage", "why": "Mn4+: no Li can leave"},
    {"id": "mp-19419", "formula": "LiFeO2", "group": "bad", "expected": "voltage", "why": "Fe3+: no Li can leave"},
    {"id": "mp-13725", "formula": "Li3PO4", "group": "bad", "expected": "voltage", "why": "no redox element"},
    {"id": "mp-8001", "formula": "LiAlO2", "group": "bad", "expected": "voltage", "why": "no redox element"},
    {"id": "mp-685194", "formula": "Li4Ti5O12", "group": "bad", "expected": "voltage", "why": "Ti4+: an anode, no Li can leave"},
]
CATHODE_BENCHMARK_MAX_RELAXATIONS = 120
CATHODE_NOT_COMPUTED = ("DFT calculations (UMA energies; the voltage of four known cathodes within 0.31 V of experiment), "
                        "the voltage profile (only the average voltage over the whole charge), oxygen redox, lithium "
                        "diffusion and electronic conductivity in the cathode, cycling and capacity fade, synthesis, cost "
                        "of the elements, experimental data")
CATHODE_NOVELTY_CONTROL = {"id": "control-LNMO", "formula": "LiNi0.5Mn1.5O4", "parent": None, "substitution": None,
                           "kind": "cathode"}

# --- Budget limits --------------------------------------------------------------

MAX_RELAXATIONS_PER_RUN = UNLIMITED  # UMA relaxations not already in cache

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
# Hard negatives (2026-11-01, limit "the benchmark lacks bad compounds that are hard to reject"): stable insulators,
# poor Li conductors at room temperature (below 1e-6 S/cm, against ~1.6e-4 for beta-Li3PS4): the hull and the gap
# let them pass, only the Li-diffusion test can reject them. Li4P2S6 has no stable phase in MP (only the two Li2PS3
# above). The lowest-energy MP polymorph of each.
BENCHMARK_HARD = {
    "mp-1153": "Li2S (stable insulator, poor Li conductor)",
    "mp-22905": "LiCl (stable insulator, poor Li conductor)",
    "mp-570935": "LiI (stable insulator, poor Li conductor)",
    "mp-13725": "Li3PO4 (stable insulator, poor Li conductor)",
    "mp-1222529": "Li4GeS4 (stable insulator, poor Li conductor)",
}
# Absolute diffusion test of the benchmark: every compound still passing goes to MD at the screening settings and is
# rejected when its D is lower than that of beta-Li3PS4 by more than MD_TIE_SIGMA combined errors (or no Li hop,
# or its framework moves); not launched above BENCHMARK_MD_MAX_USD estimated.
BENCHMARK_MD_REFERENCE = "mp-985583"  # beta-Li3PS4, the slower calibration parent (0.16 mS/cm in experiment)
BENCHMARK_MD_MAX_USD = 10.0

MAX_ITERATIONS = 3
MAX_CANDIDATES_PER_ITERATION = 5
MAX_LLM_CALLS_PER_RUN = UNLIMITED
MAX_TOKENS_PER_RUN = UNLIMITED * 1000
MAX_LLM_COST_PER_RUN_USD = UNLIMITED
JSON_MAX_RETRIES = 3
