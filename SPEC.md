# AutoLab — Technical specification

> Version of October 27, 2026 (end of day 1), updated through the hackathon. This document describes **what to build** and **everything already validated** by tests (first on Google Colab, then on Modal). Parameters marked ✅ were measured: do not change them without a reason.

---

## 1. The product in one sentence

AutoLab is an AI agent that searches for new **solid electrolytes for lithium-metal batteries**: a Meta language model proposes chemical substitutions, the code builds the crystals, UMA (Meta FAIR) simulates them, scientific filters sort them, and the model reads the results to propose what comes next.

Hackathon: Meta Global AI Developer Hackathon, "Push the Frontier" track, Indie category (solo). Submission before **Wednesday, November 4, 2026, 9:00 pm ET** (Thursday, November 5, 3:00 am in Benin), with a 3-minute video. All the code must be written during the hackathon, in a **public** repository.

Do not write "cobalt-free electrolytes": an electrolyte contains no cobalt. Correct wording: "solid electrolytes for lithium-metal batteries". "Cobalt-free" can only apply to the **cathodes** tested against the electrolyte.

---

## 2. What runs where

| Component | Where | Why |
|---|---|---|
| UMA (relaxation, energies, molecular dynamics) | **NVIDIA GPU only**: Modal (credits received: $100) for tests, production and the demo; Colab/Kaggle as a fallback | The development PC (Ryzen 5, 8 GB RAM, AMD GPU) cannot run UMA; its connection (~50 KB/s) cannot download the 2.33 GB checkpoint |
| pymatgen (hull, electrodes, closed-shell rule), generator | CPU, anywhere | Light computations |
| GPAW (DFT band gap of the champion) | Modal CPU (8 cores) | A few minutes per structure |
| FastAPI backend + frontend | A single Render service (planned; finally served by `web/app.py` and the Modal `autolab-agent` service) | Orchestration, interface |
| Data (sessions, candidates, results, events) | Supabase (free PostgreSQL) | Later; a local cache is enough at first |
| Language models | Remote APIs (Meta, Baseten, Fireworks) | — |

**Consequence for the code:** the UMA computation must sit behind an interchangeable interface (`backend="local"` on a GPU machine such as Colab, `backend="modal"` in production). The rest of the code never imports fairchem directly.

---

## 3. Repository layout

```
autolab/
├── SPEC.md                   # this document
├── README.md
├── pyproject.toml            # installable package: pip install -e .
├── .env.example              # variable names, without values
├── .gitignore                # .env, caches, *.traj, checkpoints
├── autolab/
│   ├── config.py             # reads .env, scientific thresholds
│   ├── chem/
│   │   ├── oxidation.py      # oxidation states, neutrality
│   │   ├── generator.py      # substitutions → candidate structures
│   │   └── checks.py         # S–S bond detector
│   ├── data/
│   │   └── mp.py             # Materials Project access + disk cache
│   ├── sim/
│   │   ├── uma.py            # UMA calculator factory (the only file that imports fairchem)
│   │   ├── relax.py          # relaxation
│   │   ├── md.py             # molecular dynamics
│   │   └── backend.py        # local / modal interface
│   ├── analysis/
│   │   ├── stability.py      # convex hull, E_hull, decomposition
│   │   ├── bandgap.py        # closed-shell rule, DFT gap (GPAW) of the champion
│   │   ├── electrodes.py     # window, passivation, cathode interface
│   │   └── diffusion.py      # mean squared displacement, D
│   ├── llm/
│   │   ├── client.py         # OpenAI-compatible client, configurable provider
│   │   ├── prompts.py        # system instructions
│   │   └── schemas.py        # JSON schemas of the answers
│   ├── agent/
│   │   ├── pipeline.py       # funnel of filters for one candidate
│   │   ├── loop.py           # hypothesis → evaluation → analysis loop
│   │   └── events.py         # events streamed to the interface
│   └── store/
│       └── cache.py          # cache of relaxations and references (JSON/SQLite)
├── modal_app/                # GPU and CPU functions deployed on Modal
├── api/                      # FastAPI (planned)
├── web/                      # interface
├── tests/                    # truth tests (section 7)
├── scripts/
│   └── run_loop.py           # runs a loop from the command line
└── notebooks/                # day-1 validation notebooks
```

---

## 4. Environment variables (`.env.example`)

```
MP_API_KEY=
HF_TOKEN=
BASETEN_API_KEY=
MODEL_API_KEY=            # Meta Model API (Muse Spark)
FIREWORKS_API_KEY=        # Fireworks (Muse Glimmer)
LLM_PROVIDER=meta         # meta | baseten
SIM_BACKEND=modal         # modal | local (local = machine with an NVIDIA GPU, e.g. Colab)
```

**Modal** does not use `.env` to authenticate: the command `modal token new` (run once on the PC) stores the credentials in `~/.modal.toml`. `HF_TOKEN` is added to the **Modal Secrets** (secret `huggingface-secret` containing `HF_TOKEN`), so that the UMA checkpoint is downloaded directly in the cloud, never on the PC.

The `.env` file is in `.gitignore` **from the first commit**. No key may ever appear in the code, the notebooks, the logs or the browser.

---

## 5. Modules: contract and validated parameters

### 5.1 `chem/oxidation.py` ✅
- Fixed oxidation states (closed-shell ions only):
  `Li+1, Na+1, Mg+2, Al+3, Si+4, Ge+4, Sn+4, P+5, As+5, Sb+5, S-2, Se-2, O-2, F-1, Cl-1, Br-1, I-1`.
- `charge_totale(structure) -> float`, `est_neutre(structure) -> bool` (sum of the charges = 0).
- An element outside this table → candidate **rejected** (chemical rule for electronic insulation: no transition metals with variable valence such as Fe, Co, Ni, Mn, V, Ti³⁺).

### 5.2 `chem/generator.py` ✅
- Input: a parent structure (pymatgen) and a substitution in the format:
  ```json
  {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}
  ```
  or a total substitution `{"remove": "P", "add": "Sb", "count": "all"}`.
- Total substitution: `structure.replace_species({old: new})`.
- Partial substitution: replace `count` randomly drawn sites, remove `li_vacancies` randomly drawn Li, generate **8 arrangements** (fixed seed), remove duplicates with `StructureMatcher().group_structures`.
- **Neutrality check before any UMA computation**: a non-neutral candidate is rejected and the event is recorded with the reason.
- Output: list of candidate structures + metadata (parent, substitution, seed).
- Validated result: S→Cl with one Li removed in Li₃PS₄ (32-atom cell) gives 7 distinct arrangements; **26 meV/atom between the best and the worst** → always relax several arrangements and keep the lowest.
- Known limit: the structure inherited from the parent is not necessarily the most stable (Li₃SbS₄ generated at 0.047 eV/atom while another structure exists in MP). Plan several parents for the same composition.

### 5.3 `chem/checks.py` ✅
- `a_liaisons_SS(atoms, rayon=2.3)`: true if two S are closer than 2.3 Å (via `ase.neighborlist.neighbor_list`).
- **Applies to compounds only** (ignore elemental sulfur, made of S₈ rings).
- If true: the UMA result is flagged "reduced reliability" (raw UMA is wrong on polysulfides: LiS₄ at 0.178 eV/atom above the hull with UMA against 0 in MP).
- ⚠️ Measurement of 2026-11-01 (`results/2026-11-01_uma_error_bars`): **with the MP2020 corrections** (used everywhere since October 28), the decomposition energy of LiS₄ is −0.174 eV/atom against −0.162 in MP, and the UMA + MP2020 / MP difference stays ≤ 0.0124 eV/atom on 9 known polysulfides. The former figure (0.17) compared UMA without corrections.

### 5.4 `data/mp.py` ✅
- `MPRester(MP_API_KEY)`, `mpr.materials.summary.search(...)`.
- References of a chemical system: all subsystems (combinations of 1 to n elements), filtered to **MP E_hull ≤ 0.05 eV/atom and ≤ 80 atoms**.
- For electrodes: `mpr.get_entries_in_chemsys(elements, additional_criteria={"thermo_types": ["GGA_GGA+U"]})`.
- Disk cache required (per chemical system and per `material_id`).

### 5.5 `sim/uma.py` ✅ (the only file that imports fairchem)
```python
from fairchem.core import pretrained_mlip, FAIRChemCalculator
predictor = pretrained_mlip.get_predict_unit(MODEL, device="cuda", inference_settings=...)
calc = FAIRChemCalculator(predictor, task_name="omat")   # "inorganic crystals" head
```
- Model: `uma-s-1p2` (validated). `uma-s-1p2p1` ("nitro") brings nothing on a T4; to be retested on a recent GPU.
- **High precision** (`inference_settings="high-precision"`) for energies and E_hull.
- **Normal precision** (default setting) for molecular dynamics: 2× faster.
- To screen different compositions in series, UMA recommends `inference_settings="batch"`: **to be checked** before using it.
- Checkpoint access: gated Hugging Face repository `facebook/UMA`, read-only `HF_TOKEN`.

### 5.6 `sim/relax.py` ✅
- ASE: `FIRE(FrechetCellFilter(atoms), logfile=None).run(fmax=0.05, steps=500)`.
- Returns: total energy, energy per atom, relaxed structure, convergence (bool), number of steps.
- A non-converged candidate is never ranked as stable.
- Validation: LiCl relaxed to **5.145 Å** (experimental ≈ 5.13 Å).

### 5.7 `analysis/stability.py` ✅
- **All the energies of the hull come from UMA** (MP references relaxed by UMA). **Never** mix UMA energies and MP energies.
- `PDEntry(composition, energy, name=...)`, `PhaseDiagram(entries)`, `get_decomp_and_e_above_hull(entry, allow_negative=True)`.
- Output: E_hull (eV/atom), decomposition products with fractions.
- Li-P-S calibration: Li₃PS₄ 0.000 / 0.007 / 0.015 (MP: 0.000 / 0.007 / 0.014); Li₇P₃S₁₁ 0.010 (MP: 0.020); Li₂S 0.
- ⚠️ **Change of October 28, 2026 (validated by the owner)**: all UMA energies receive the **MP2020 corrections** (`config.UMA_MP2020`, `stability.uma_entry`), like MP energies: anion corrections and GGA/GGA+U mixing (U values in `config.MP2020_HUBBARD_U`). Without them, an interface where Co or Fe goes from an oxide (GGA+U) to a sulfide (GGA) is off by ≈ 0.2 eV/atom. Each entry receives its **structure** (sulfide or sulfate) and its **oxidation states**, guessed without pymatgen's 20-atom limit (otherwise Se is not corrected in Li₇P₃SeS₁₀). A test checks that the corrected anion atoms are conserved between each phase and its products (intended exception: an anion with a formal state between −1 and 0, e.g. Sb in LiSb₃). Truth tests rerun: Li₂S 0.0; fictitious LiS 0.445; Li₃PS₄ 0.0; mean difference to MP E_hull on 52 Li-P-S phases 0.0091 → 0.0057 eV/atom; polymorphs and Li₇P₃S₁₁ unchanged. Known approximation of the scheme: polysulfides receive the sulfide correction, elemental sulfur none (this shifts the As and Sb candidates).
- E_hull is always stated **per atom** (eV/atom) or **per substitution** (eV per modified site) in the reports.
- Thresholds: `E_hull ≤ 0.05` = synthesizable (acceptable metastability); `≤ 0.025` = very good.

### 5.8 `analysis/bandgap.py` ✅ (electronic insulation: rule + DFT of the champion; 2026-11-03)
Organizers' rule: every model called at run time must be a Meta model. The band gaps already recorded (fields `gap_optb88` / `gap_mbj`, cache `.cache/bandgap`) stay as they are and are shown as "recorded prediction".
- **In the funnel** (`bandgap` step, instantaneous, no model): each ion, at its fixed oxidation state, must have a closed electronic shell: remaining electrons Z − charge in `CLOSED_SHELL_ELECTRONS` (noble gas, d10, d10 s2, 4f14, 4f14 5d10). The tables `OXIDATION_STATES` and `SODIUM_OXIDATION_STATES` only contain such ions: the rule guarantees the principle, it rarely rejects.
- **After the ranking** (`dft_gap` step, `domains/electrolyte.py`): PBE band gap of the champion with **GPAW** (plane waves `DFT_GAP_ECUT_EV` = 400 eV, Γ-centred grid of density `DFT_GAP_KDENSITY` = 2.5 /Å for the self-consistent calculation, then bands at fixed density along the high-symmetry path, `DFT_GAP_PATH_POINTS` = 40; the gap is read on both sets of k-points). Thresholds unchanged, PBE scale: `BANDGAP_MIN` = 2.0 eV (lithium), `SODIUM_BANDGAP_MIN` = 1.8 eV (sodium). Below the threshold, the candidate is set aside and the next one is checked, at most `DFT_GAP_MAX_CALCS` = 2 calculations per research; an error stops the check (champion "not confirmed").
- Execution: `modal_app/dft_app.py` (Modal CPU, 8 cores, 16 GB, timeout `DFT_GAP_TIMEOUT_S`, no warm container, no retry), launched with MPI (`mpiexec -n 8 gpaw python`, GPAW 26.7.0 from conda-forge, OpenMPI build). Cache per structure and settings (`.cache/dft_gap/pbe_gpaw.json`): a calculation is never redone. Only `autolab/sim/dft.py` imports GPAW.
- Grid only: band edges between two grid points, gap overestimated (Li₃P +0.38 eV, Li₂S +0.28 eV); hence the band path.

### 5.9 `analysis/electrodes.py` ✅ (method of Zhu, He & Mo 2015)
- **Electrochemical window**: scan from 0 to 5 V in steps of 0.02 V. At each voltage V, `GrandPotentialPhaseDiagram(entries, {Li: mu_Li_metal - V})` and `GrandPotPDEntry(entry, {Li: mu})`. The compound is stable at V if its **decomposition products are exactly those of its natural decomposition** (no Li exchange). This criterion works for metastable compounds.
- **Passivation at 0 V** (contact with lithium metal): list the products; a product is metallic if its MP gap is `< 0.1` (write `g is not None and g < 0.1`, **not** `(g or 1) < 0.1`, which misses metals).
  - no metallic product → "passivating";
  - metallic product but reaction driving force at 0 V < 0.1 eV/atom → "quasi-stable";
  - metallic product and driving force ≥ 0.1 → "non-passivating" (disqualifying).
- **Interface with a cathode**: `InterfacialReactivity(comp_electrolyte, comp_cathode, pd, norm=True, use_hull_energy=True)`, minimum of `get_kinks()`.
- Cathodes: the list must be configurable. Validated with LiCoO₂; for the "cobalt-free" story, use **LiFePO₄** and **LiMn₂O₄** by default (not yet tested).
- Validated with MP energies: Li₃PS₄ 1.72–2.34 V (published 1.71–2.31), Li₆PS₅Cl 1.72–2.14 (1.71–2.01), LGPS 1.72–2.28 (1.71–2.14), LLZO 0.06–2.88 (0.05–2.91); LGPS non-passivating (Li₁₅Ge₄), LLZO quasi-stable (driving force 0.028), Li₃PS₄/LiCoO₂ −0.416 eV/atom.
- ✅ Same method with UMA + MP2020 energies (October 28, 2026): Li₃PS₄ window 1.74–2.36 V (MP 1.72–2.34); interfaces with only the references on the MP hull (`INTERFACE_REF_EHULL_MAX = 0`): Li₃PS₄/LiCoO₂ −0.415 (MP −0.416), Li₃PS₄/LiFePO₄ −0.144 (MP −0.133) eV/atom, tolerance 0.05.
- Cost: window 4–8 s; 5-element interface 16–28 s (relaxations not included). Reserved for the **top 20**.

### 5.10 `sim/md.py` + `analysis/diffusion.py` ✅ (block D validated by calibration v2, 2026-10-29; candidate/parent verdict by the difference |D − D(parent)| ≤ 2 combined errors since 2026-11-02, same 39 verdicts as with the ratio)
- Supercell of at least ~10 Å per side (`reps = ceil(10 / L)` per axis).
- Langevin NVT, 1 fs time step, friction 0.01/fs. Use `thermalize_momenta` (not `MaxwellBoltzmannDistribution`) and `fixcm=False` with `ase.constraints.FixCom`.
- Li positions recorded every 10 steps; trajectory saved for the 3D display. For each other element (P, S, …), the mean squared displacement is recorded at each frame (`framework_msd`): the framework is intact if each element other than Li diffuses at less than 5% of Li (`MD_FRAMEWORK_D_RATIO_MAX`).
- **Change of a ✅ parameter (2026-10-29, validated by the owner)**: D is now the **mean of the D fitted in 4 consecutive blocks** (`MD_D_BLOCKS`), with, in each block, the mean squared displacement averaged over many time origins (fit from L/8 to L/2); the **standard error** between blocks gives the uncertainty (`D_sem_cm2_per_s`). The former D (`((pos - pos[0])**2).sum(axis=2).mean(axis=1)`, slope / 6 over the second half) is still computed alongside (`D_one_origin_cm2_per_s`) for comparison. Reason: on the 20 ps runs at 1000 K (step 9C), the former D differed by up to 50% from the block mean (Li₃PS₄: 9.5e-5 against 6.2e-5 ± 0.4e-5 cm²/s).
- A candidate is "tied" with its parent if |D/D(parent) − 1| ≤ 2 propagated errors (`MD_TIE_SIGMA`).
- **Screening parameters ✅ (calibration v2)**: 600 K, 40 ps, 2 seeds per structure, blocks of the seeds pooled (`MD_SCREEN_*`, `analysis.diffusion.pool`), on Modal A10G (`MODAL_MD_GPU`, compiled TF32: keep the same GPU for parents and candidates). At 1000 K, the two parents are tied (two seeds): 1000 K does not sort.
- ⚠️ **Change of a ✅ parameter (2026-11-01, owner's decision)**: molecular dynamics moves to **Modal H100** (`MODAL_MD_GPU`), about 2 times faster and about 2 times more expensive per simulation. Results already computed on A10G keep their cache keys (`MD_LEGACY_GPU`) and are read back as they are (parents included: never recomputed); new keys carry the name of the card (`sim.backend.md_settings`, `dynamics.with_md_gpu`). **Check (criterion fixed before the runs, `scripts/md_gpu_check.py`, `results/2026-11-01_md_gpu_check`) ✅**: one 40 ps run at 600 K per parent on H100 against the A10G v2 calibration (3 seeds): D(Li₇P₃S₁₁) 1.27e-5 ± 0.32e-5 against 1.28e-5 ± 0.15e-5 (−0.0 σ), D(Li₃PS₄) 0.70e-5 ± 0.19e-5 against 0.63e-5 ± 0.09e-5 (+0.4 σ), framework intact: **same D on both cards**, an H100 candidate can be compared with an A10G parent and the v2 calibration remains valid. Measured H100 speed: 14–17 ms/step (1.3–1.7× faster than the A10G, not 2×), i.e. 2.1–2.7× more expensive per simulation.
- Calibration (2026-10-29, Modal A10G): initial test 600 + 700 K ❌ (1.9 σ and 0.4 σ); v2 test, fixed before the runs, 600 K, 3 seeds ✅: D(Li₇P₃S₁₁) = 1.28e-5 ± 0.15e-5, D(Li₃PS₄) = 0.63e-5 ± 0.09e-5 cm²/s, ratio 2.04, 3.6 σ; P/S framework intact (final MSD P ≤ 0.12 Å², S ≤ 0.24 Å²). Barriers 600–700 K: 0.19 ± 0.07 eV (Li₇P₃S₁₁, literature 0.19) and 0.33 ± 0.09 eV (Li₃PS₄, literature 0.35–0.41). A10G speed: 18–24 ms/step for 84–128 atoms.
- **Truth test of this change: the calibration (plan A)**, on the two parents only: β-Li₃PS₄ (mp-985583, Pnma) and Li₇P₃S₁₁ (mp-641703), at 600 K / 40 ps, 700 K / 30 ps and 1000 K / 20 ps (another seed) (`MD_CALIBRATION_*`, `scripts/md_calibration.py`). At 600 and 700 K, below the β → α transition of Li₃PS₄ (~746 K): framework intact, and D(Li₇P₃S₁₁) > D(Li₃PS₄) by more than 2 combined errors. Arrhenius barriers compared (without a threshold) with published simulations: ~0.19 eV for Li₇P₃S₁₁, 0.35–0.41 eV for β-Li₃PS₄. At 1000 K, Li₃PS₄ may legitimately catch up with Li₇P₃S₁₁ (higher barrier, α phase): 1000 K is shown for information only.
- Speed measured on a T4, 128 atoms: 129 ms/step in high precision, **65 ms/step in normal precision**. 50 ps ≈ 55 min on a T4.
- Kaggle T4 (torch 2.13, step 9C, 20 ps at 1000 K): 72–128 ms/step for 84–128 atoms, i.e. 0.56–1.16 ms per atom and per step (small cells are slower per atom); estimate kept `KAGGLE_MD_MS_PER_ATOM_STEP = 1.2`.
- 2 ps is not enough for a reliable D (Li₃PS₄ at 800 K: plateau at ~1 Å², no hops). For the real measurement: 1000–1200 K, longer simulations, several temperatures in parallel on Modal. Reserved for the **top 3 to 5**.

### 5.11 `llm/client.py` ✅
- A single OpenAI-compatible client; the provider is chosen by `LLM_PROVIDER`.

| Provider | base_url | model | role |
|---|---|---|---|
| `meta` ✅ | `https://api.meta.ai/v1` | `muse-spark-1.3` | **main brain**: hypotheses, decisions, analysis |
| `baseten` ✅ | `https://inference.baseten.co/v1` | `meta-models/muse-spark-open-1026` (the only name the key accepts) | parallel analyses of the candidates; fallback if Meta fails |
| `fireworks` ✅ | given by Fireworks (dedicated deployment) | Muse Glimmer | small fast tasks: plain-language summaries of the steps |
| `wonder` ✅ (2026-11-03) | `https://api.meta.ai/v1` (Responses API, reasoning summary) | `muse-wonder-1.0` ($4 / $20 per million input / output tokens) | **campaign review** (`agent/review.py`), last step of every domain |

**Campaign review (2026-11-03, owner)**: after the report, Muse Wonder reads at once a compact file of the whole campaign (hypothesis and candidates of each round with their measurements, slow tests, Muse Spark's failure analyses, step summaries, finalists, literature, report; without structures or raw series; size ≤ `CAMPAIGN_REVIEW_MAX_INPUT_CHARS`, otherwise the candidates of earlier researches are removed). JSON answer `campaign_review`: `headline`, `learned`, `worked`, `failed`, `next_campaign` {`goal`, `parents`, `directions`, `why`}. One call per research (separate client, `CAMPAIGN_REVIEW_MAX_OUTPUT_TOKENS`); it decides nothing (thresholds, ranking and verdicts remain those of the code). Without a key, the step is skipped and says so. Event `llm/campaign_review`, last message of the conversation (`review`), copied when a known research is reused. The three researches of the home page received it afterwards (`scripts/add_campaign_review.py`, $0.26 in total).

- Baseten reasoning: `message.reasoning_content` (≈ 11 s per answer). Streaming: `stream=True`, fields `delta.reasoning_content` and `delta.content`.
- Muse Spark (Meta): the Responses API keeps the reasoning from one turn to the next with `include=["reasoning.encrypted_content"]`; the OpenAI SDK does not read `MODEL_API_KEY` by itself, pass `api_key` explicitly.
- Count the tokens of every call (`response.usage`) in a global counter.
- Baseten calls in parallel to analyse several candidates (limit: 2 M tokens/min).

### 5.12 `llm/prompts.py` and `llm/schemas.py` ✅ (validated principles)
- System instructions **in English**.
- Answer **in JSON only**; on the code side: strip the ```` ```json ```` fences, `json.loads`, check the keys, up to **3 attempts**, sending the error back to the model.
- **Thresholds come from the code, not from the model**: the instructions state them explicitly (E_hull ≤ 0.05, optb88 gap ≥ 2.0, etc.).
- Every field sent to the model is explained in the instructions (e.g. `ss_bonds: true` = S–S chains, UMA less reliable).
- Proposal schema (agent → generator):
  ```json
  {"hypothesis": "short sentence",
   "proposals": [{"parent": "mp-985583",
                  "substitution": {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1},
                  "rationale": "short sentence"}]}
  ```
- Analysis schema (after a batch is evaluated):
  ```json
  {"ranking": ["candidate_id", "..."],
   "lessons": ["short sentence"],
   "next_direction": "short sentence",
   "stop": false}
  ```

---

## 6. The pipeline and the loop

### 6.1 Funnel for each candidate (`agent/pipeline.py`)
1. Chemical rule + neutrality (instantaneous) → immediate rejection otherwise.
2. High-precision UMA relaxation of each arrangement, the lowest is kept.
3. UMA E_hull ≤ 0.05 → otherwise rejection (with the decomposition products, useful to the model).
4. Closed-shell ions (rule, no model) → otherwise rejection; the DFT band gap of the champion (GPAW, ≥ 2.0 eV) is computed after the ranking.
5. S–S detector → warning.
6. **Top 20**: electrochemical window, passivation, interface with the cathodes.
7. **Top 3 to 5**: molecular dynamics on GPU.

Each step emits an **event** (`events.py`): `{"type", "candidate_id", "step", "data", "timestamp"}`, for the live display.

### 6.2 Loop (`agent/loop.py`)
1. The researcher gives a goal in natural language.
2. The model receives the goal, the available parents and the history → **proposals** (JSON).
3. The generator builds the candidates; the funnel evaluates them.
4. The model receives the numerical results → **analysis** (JSON) and a new direction.
5. Stop after N iterations or if `stop: true`.
6. Final report: ranked candidates, numbers, the agent's reasoning.

Minimal version (day 3): sequential loop, `LLM_PROVIDER=meta` (Baseten as a fallback), UMA on Modal, 2–3 iterations of 5–10 candidates, without electrodes or MD. Steps 6 and 7 are added afterwards.

**Complete loop (2026-10-29)**: after the iterations, the domain's steps run in order on all the candidates (those of the run and, with `--prior`, those of earlier runs, never proposed again). Each step reads the caches before computing, emits its events (`stage` and `candidate`, step `name:sub-step`) and decides according to `config.py`.
1. **Electrodes** (first `ELECTRODES_TOP` by E_hull per substitution): window, passivation, then interface with `AGENT_CATHODES` (LiFePO₄) if the Li₃PS₄/cathode calibration is within tolerance. "Non-passivating" → set aside (`ELECTRODE_EXCLUDED_PASSIVATION`, SPEC 5.9), without an interface computation. A polysulfide among the products → reduced confidence in the electrode results (information only: almost all sulfides give FeS₂ against LiFePO₄).
2. **Choice for molecular dynamics**: Muse Spark chooses at most `MD_SELECT_MAX` candidates that were not set aside, from the comparisons computed by the code; ids outside the list are ignored; without an answer from the model, rule: best E_hull per substitution.
3. **Molecular dynamics** with the ✅ screening parameters (600 K, 2 seeds of 40 ps, Modal H100 since 2026-11-01, A10G before; same D on both cards), parents included. Slower than the parent by more than `MD_TIE_SIGMA` combined errors (`MD_EXCLUDED_VERDICTS`) or a displaced framework → set aside for conduction, but listed with its numbers.
4. **Final ranking** (since 2026-11-02, see "Conductivity at 300 K"): level against the parent at 300 K, then tie-break by convention (`RANK_TIE_BREAK`); those set aside at the end of the list with their reason; `FINALISTS_MAX` finalists.
5. **Novelty** (only with `--novelty`): the LGPS control first; if it is not found as published, the research is not considered reliable and the finalists are not queried (`NOVELTY_STOP_IF_CONTROL_FAILS`); answers cached.

**Error feedback loop (2026-11-01, owner's decision, `FEEDBACK_LOOP`)**: steps 1 to 3 above (electrodes, reviews, choice for molecular dynamics, molecular dynamics) also run **in each iteration**, on the candidates of that iteration: `ITERATION_MD_SELECT_MAX` = 1 candidate simulated per iteration (chosen by Muse Spark), no new one after the iterations (`FINAL_MD_SELECT_MAX` = 0; cached verdicts always apply). The results of these slow tests (`domains.electrolyte.feedback`) — failures in contact with lithium (products, energy), slower than the parent, a moving framework (diffusion ratio of each element to Li, final displacement) — are given to Muse Spark with their measurements, as facts, before the analysis of the iteration; for each failure it gives a **hypothesis** on the cause (labelled as such: the code only measured the numbers) and a **correction** (`failure_analysis`, optional, checked if given), carried over into the history of the next proposal. Live research: 3 iterations, 1 candidate simulated per iteration. The former sequence is still possible (`FEEDBACK_LOOP = False`). No iteration is promised to succeed.

**Conductivity at 300 K (2026-11-01)**: `conductivity` step after the ranking, without computation (cache only): D of the cached runs up to `CONDUCTIVITY_FIT_T_MAX_K` (750 K, below the β → α transition of Li₃PS₄), weighted Arrhenius fit, extrapolation to 300 K, Nernst-Einstein (Li density of the relaxed cell, Haven ratio 1), range = one standard error of the extrapolation. Candidate at a single temperature: activation energy of the parent, labelled. Extra temperatures (500 and 700 K) with `scripts/conductivity.py`. **Ranking (2026-11-01, owner)**: the step comes before the ranking; a candidate with its own line is "slower" or "faster" than its parent only if the two ranges do not overlap, otherwise "tied" (`CONDUCTIVITY_RANK_ORDER`: faster > tied > not fitted > slower), a criterion placed before the 600 K verdict; the report always quotes the ranges. **Rules completed (2026-11-02, owner)**: (1) candidates without their own line form a separate group, "not evaluated at 300 K", after all the evaluated candidates (`CONDUCTIVITY_RANK_ORDER` = faster > tied > slower > not fitted), ordered among themselves by their 600 K verdict; elsewhere, diffusion at 600 K is only a pre-filter ("slower" sets aside); (4) within a level, tie-break **by convention**, not a significant difference (`RANK_TIE_BREAK`): lowest E_hull per substitution, then lowest activation energy (own line), then widest window (zero or uncomputed width: 0 V); the ranking gives the levels (`levels`) and the report says so; the E_hull gap of each finalist to the champion is judged by the code (inside or outside the sum of the error bars); (5) the parent's line used for the comparison is made with the same runs as the candidate's (`CONDUCTIVITY_PARENT_SAME_PROTOCOL`: same temperatures, same number of runs, same durations and seeds if cached), the remaining differences are listed (today: 700 K, 30 ps for the parents against 40 ps); the full line of the parents remains that of the truth test. Not done (cost): σ(300 K) given to Muse Spark at each iteration, a second seed at 500 and 700 K.

**Second domain: cobalt-free cathodes (2026-11-02, owner; `domains/cathode.py`, `analysis/cathode.py`)**: substitutions in four known cobalt-free cathodes (`CATHODE_PARENTS`: LiFePO₄, LiMnPO₄, spinel LiMn₂O₄, LiNi₀.₅Mn₁.₅O₄). Funnel: cobalt refused and neutrality with mixed valence (`CATHODE_OXIDATION_RANGES`, contiguous ranges: neutral if 0 lies between the sums of the low and high states; oxygen fixed at −2, no oxygen redox) → composition already in MP not computed → UMA relaxation of `CATHODE_N_ARRANGEMENTS` arrangements → E_hull against the stable MP phases of the system relaxed with UMA (`CATHODE_HULL_REF_EHULL_MAX` = 0, never an MP energy), ≤ `CATHODE_EHULL_MAX` (0.08 eV/atom: the commercial spinel LiMn₂O₄ is 0.045 above the MP hull) → Li removal allowed by neutrality, charged cell relaxed: average voltage V = −(E_lith − E_delith − k E_Li)/k (raw UMA energies; the MP2020 corrections of O and the transition metals cancel out), theoretical capacity k F/(3.6 M), energy density, volume change; filters `CATHODE_VOLTAGE_MIN`–`MAX` (3.0–4.8 V), `CATHODE_CAPACITY_MIN` (120 mAh/g), `CATHODE_VOLUME_CHANGE_MAX` (10%); each candidate compared with its parent computed the same way. Error-driven loop: each failure, with its numbers, goes back to the model (the loop calls `feedback` even without slow tests). After the iterations: Muse Spark Open reviews, ranking by energy density then E_hull per substitution, Muse Spark report. A cathode request runs in this domain (service: the conversation's domain), without the electrolyte candidates. A compound from which no Li can be removed is refused from its composition, before any simulation. Each E_hull carries its UMA/DFT error bar, measured on the stable phases of the system (`cached_system_errors(..., ehull_max=0.0)`). Not computed: voltage profile (only the average over the full charge), Li diffusion in the cathode, cycling.

**Third domain: sodium solid electrolytes (2026-11-02, owner; `domains/sodium.py`)**: the funnel and slow tests of the lithium electrolytes, with Na⁺ as the mobile ion (`MOBILE_IONS`: the ion followed by molecular dynamics and removed by vacancies, `"vacancies"` in a substitution, is the first of this list present in the crystal). Parents (`SODIUM_PARENTS`): tetragonal Na₃PS₄ (mp-28782), cubic Na₃SbS₄ (mp-10167), NASICON Na₃Zr₂Si₂PO₁₂ (mp-532695). Neutrality with fixed oxidation states (`SODIUM_OXIDATION_STATES`, Zr, Ti, Nb… added) → composition already in MP not computed → UMA relaxation → E_hull against the stable MP phases of the system relaxed with UMA (`SODIUM_HULL_REF_EHULL_MAX` = 0), ≤ `SODIUM_EHULL_MAX` (0.05) → closed-shell ions; after the ranking, DFT band gap (GPAW) of the champion ≥ `SODIUM_BANDGAP_MIN` (1.8 eV: Na₃SbS₄, a working electrolyte, has a PBE gap of 1.93 eV; the lithium limit of 2.0 eV would reject it). In each round: window in V vs Na/Na⁺ and reaction with sodium metal (chemical potential of Na metal; non-passivating → set aside), independent review, choice of one candidate by the model, Na diffusion at 600 K against its parent (2 seeds × 40 ps). No cathode interface (`SODIUM_CATHODES` empty: the interface calibration only exists for lithium cathodes). After the rounds: ranking (diffusion verdict, then E_hull per substitution), literature check (Na₃PS₄ control), report. No conductivity at 300 K. Molecular dynamics can set aside or rank a candidate only if its sodium calibration succeeded (`SODIUM_MD_CAN_EXCLUDE`, `md_ranks` setting, section 7): no. 1 (two different crystals) failed, no. 2 (a crystal against its own parent, which is what the domain does) succeeded with the difference test: it sets aside and ranks. The shared steps read the domain's settings (`Domain.settings`: ion, cathodes, prompts).

**Live view of the interface (2026-11-02, owner)**: during a research, the page plays the events one by one as cards (who is working — Muse Spark, Muse Spark Open, Muse Glimmer, UMA, GPAW, pymatgen, Materials Project — and what it does, with its numbers), the "Progress" list ticks and a notebook records the decisions; the cards disappear, the Research card, the summary and the final report appear at the end. The events arrive by WebSocket (`web/app.py`, `/ws/conversations/{id}`, polling as a fallback). The relaxation event carries the structure before and after relaxation of the best arrangement (`pipeline.live_structure`) and, for new relaxations, `RELAX_TRAJECTORY_FRAMES` (12) frames of the real path (display only: the result does not change); without a recorded path, the animation between the two structures is labelled as interpolated. Results taken from the cache are played at a readable pace and marked "reused". A request identical to a finished research reuses it (`REUSE_IDENTICAL_GOAL`): events, result, last summary, last report and 3D files copied, nothing is recomputed or paid for, the conversation is not a live research (source `reuse`). Formulas are written with subscripts (Li₇P₃S₁₁).

**Hybrid replay (2026-11-04, owner; `agent/hybrid.py`)**: a request for one of the recorded researches (the same words, or other words matched by Muse Spark to the same domain) replays it: Muse Spark's proposals and every computation come from the recorded research, while the agents work live on those results with the same prompts as in a research (failure analyses, independent reviews, summaries, Muse Wonder's campaign review). A missing key: another Meta model takes the role and its name is shown; a failed call keeps the recorded answer and the conversation says so. Without any key, the recorded research is replayed as it is.

**No usage caps (2026-11-04, owner)**: nothing blocks a user except a request outside AutoLab's domains: any number of researches, several at once, no cost cap per research (practically unlimited values, `config.UNLIMITED`). Kept: 3 attempts for a malformed JSON answer, and the number of rounds of a research (3 by default, adjustable).

**UMA error bars (2026-11-01)**: each E_hull is given with the mean UMA + MP2020 / DFT (MP) difference measured on the known compounds of its system (decomposition energy, compound removed from the hull, two separate hulls; `analysis/uma_errors.py`, `scripts/uma_error_bars.py`). **Window**: reduced confidence only if its limits move by more than `WINDOW_SENSITIVITY_MAX_V` (0.1 V) when the energy of each polysulfide is shifted by ±`POLYSULFIDE_ENERGY_ERROR_EV` (0.025 eV/atom, 2 × the largest error measured on 9 polysulfides).

**Domains** (`autolab/domains/`): the loop is generic. A domain provides the funnel of a candidate, the prompts, the fields seen by the model, the comparisons, the steps after the iterations and the `config.py` thresholds it uses (`AGENT_DOMAIN`). Three domains: `electrolyte` (lithium), `cathode` (cobalt-free cathodes), `sodium` (sodium electrolytes); a new domain is a new module in this folder, without changing the loop.

### 6.3 What the results are not
The candidates are **computational predictions**, never proven discoveries. The only DFT calculation in the pipeline is the band gap of the champion (GPAW, section 5.8). Confidence rests on calibration on known cases (section 7).

---

## 7. Truth tests (`tests/`)

A module is finished only if its truth test passes. UMA tests run on GPU only (marker `@pytest.mark.gpu`).

| Test | Expected |
|---|---|
| LiCl relaxation (rocksalt, start a = 5.0 Å) | 5.10 – 5.18 Å, converged |
| E_hull Li₂S (Li-S system, UMA energies) | ≤ 0.005 |
| E_hull fictitious rocksalt LiS | ≥ 0.3 |
| Calibration Li₃PS₄ mp-985583 (Li-P-S system) | ≤ 0.01 |
| Li₃PS₄ window (UMA + MP2020 energies, cache) | 1.6–1.9 V to 2.2–2.5 V |
| Interfaces Li₃PS₄/LiCoO₂ and Li₃PS₄/LiFePO₄ (UMA + MP2020 against MP) | difference ≤ 0.05 eV/atom |
| Conservation of the corrected anion atoms (MP2020), each candidate and each hull phase | no difference |
| Neutrality: S→Cl without Li removal in Li₁₂P₄S₁₆ | rejected (charge +1) |
| Generator S→Cl + 1 Li vacancy | ≥ 2 distinct arrangements, all neutral |
| GPAW DFT band gap (PBE) against Materials Project: Li, Li₂S, LiI, Li₃P, Na₃SbS₄, Li₃PS₄ (2026-11-03, `results/2026-11-03_dft_gap_truth`) | difference ≤ 0.3 eV (metals ≤ 0.1): **6/6**, mean difference 0.03 eV, maximum 0.08 (Na₃SbS₄); Li₃PS₄ (32 atoms) 7 min 18 s |
| Li₃PS₄ window (MP energies) | 1.6–1.9 V to 2.2–2.5 V |
| LGPS passivation | non-passivating (Li₁₅Ge₄) |
| LLZO passivation | quasi-stable |
| S–S detector on Li₂S / LiS₄ | false / true |
| LLM client: valid JSON answer | keys present after ≤ 3 attempts |
| Molecular dynamics calibration (plan A, block D): Li₇P₃S₁₁ against β-Li₃PS₄ at 600 and 700 K ❌ (2026-10-29, Modal A10G: framework intact, right order at both temperatures but 1.9 σ at 600 K and 0.4 σ at 700 K; barriers 0.19 ± 0.07 and 0.33 ± 0.09 eV) | P/S framework intact; D(Li₇P₃S₁₁) > D(Li₃PS₄) by more than 2 combined errors |
| Molecular dynamics calibration v2 (fixed on 2026-10-29, before the runs): 600 K only, 3 seeds of 40 ps combined (seeds 0, 1, 2; seed 0 is the plan A run). Combined D = mean of the 12 blocks (4 per seed), error = standard deviation of the blocks / √12. Justification: 700 K is too close to the β→α transition of Li₃PS₄ (746 K), known before the runs. If passed: block D ✅ and screening at 600 K, 2 seeds, 40 ps; if failed: UMA molecular dynamics stays secondary information, unable to eliminate a candidate ✅ (passed: ratio 2.04, 3.6 σ, framework intact) | P/S framework intact; D(Li₇P₃S₁₁) > D(Li₃PS₄) with a difference larger than 2 combined errors |
| A10G / H100 comparison of molecular dynamics (2026-11-01, criterion fixed before: difference ≤ 2 combined errors, framework intact, for both parents; `scripts/md_gpu_check.py`) ✅ | measured: Li₇P₃S₁₁ −0.0 σ, Li₃PS₄ +0.4 σ: same D |
| Conductivity at 300 K (2026-11-01, fixed before the new runs, `CONDUCTIVITY_REFERENCE_MS_CM`): Li₇P₃S₁₁ > β-Li₃PS₄ and each within a factor of 10 of experiment (3.2–17 and 0.16 mS/cm) | ✅ measured (500, 600, 700 K): Li₇P₃S₁₁ 99.9 mS/cm (58–170), β-Li₃PS₄ 1.18 (0.43–3.2), right order; both ~6–7 × above experiment (perfect crystal); Ea 0.14 ± 0.03 and 0.34 ± 0.05 eV |
| UMA / DFT error bars (2026-11-01, measurement without a threshold) | mean difference 0.004–0.006 eV/atom on the sulfide systems, ≤ 0.0124 on 9 polysulfides, Sb systems worse (LiSb₃ 0.161) |
| Benchmark with traps (2026-11-01, measurement without a threshold): 5 stable insulators that are poor Li conductors (Li₂S, LiCl, LiI, Li₃PO₄, Li₄GeS₄), molecular dynamics against β-Li₃PS₄ | measured: traps set aside by stability + gap 0/5, after lithium metal and diffusion 5/5 (Li₂S, Li₃PO₄ without Li hops; LiCl slower; Li₄GeS₄ non-passivating; LiI tied in D, set aside only by the framework rule, weakly); good 3/4 (2/4 with lithium), bad 8/8 |
| UMA average voltage of four known cobalt-free cathodes (2026-11-02, criterion fixed before: each difference to experiment ≤ `CATHODE_VOLTAGE_TRUTH_TOL_V` = 0.4 V, LiFePO₄ the lowest and LiNi₀.₅Mn₁.₅O₄ the highest; same relaxation and same delithiation as a candidate; `scripts/cathode_truth.py`, `results/2026-11-02_cathode_truth/`) ✅ | measured: LiFePO₄ 3.45 V (exp. 3.45), LiMnPO₄ 3.79 (4.10), LiMn₂O₄ 3.82 (4.05), LiNi₀.₅Mn₁.₅O₄ 4.72 (4.70); right order; capacities 169.9 / 170.9 / 148.2 / 146.7 mAh/g; volume change 3.6–5.8% (LiFePO₄ 6.8% measured: underestimated) |
| Blind cathode benchmark (2026-11-02, expected outcomes fixed before, `CATHODE_BENCHMARK`; known compound removed from its own hull; `scripts/run_cathode_benchmark.py`, `results/2026-11-02_cathode_benchmark/`) | measured 9/10: good 2/2 (LiNiO₂ 3.95 V, Li₃V₂(PO₄)₃ 3.73 V), bad 6/6 (LiCoO₂ cobalt; Li₂MnO₃, LiFeO₂, Li₃PO₄, LiAlO₂, Li₄Ti₅O₁₂: no Li can be removed, decided before any simulation), traps 1/2 (LiTiO₂ rejected at 1.46 V; ❌ Li₂FeSiO₄ passes at 3.29 V against 2.8 V measured: UMA overestimates this iron silicate) |
| UMA / DFT error bars of the cathode systems (2026-11-02, stable phases, measurement without a threshold; `results/2026-11-02_cathode_error_bars/`) | mean difference 0.005–0.010 eV/atom on 8 systems (Li-Mn-Ni-O-Ti/V/Zr, Li-Mn-Ni-O, Li-Mn-Al-O, Li-Mn-Ti-O, Li-Mn-P-Si-O, Li-Fe-P-O); largest difference Fe₂O₃ 0.064 |
| Sodium molecular dynamics calibration (2026-11-02, criterion fixed before: at 600 K, 2 seeds × 40 ps, D(Na₃SbS₄) > D(tetragonal Na₃PS₄) by more than 2 combined errors, frameworks intact; `scripts/sodium_md_calibration.py`, `results/2026-11-02_sodium_md_calibration/`) ❌ | measured: Na₃SbS₄ 7.6 ± 6.0 × 10⁻⁸ cm²/s (24 Na), Na₃PS₄ 2.3 ± 0.9 × 10⁻⁷ cm²/s (48 Na), ratio 0.33 ± 0.29: the reverse of the experimental order, frameworks intact. Rule fixed before applied: `SODIUM_MD_CAN_EXCLUDE` = False, Na diffusion only informs (neither sets aside nor ranks). Untested hypotheses: ordered crystals without Na vacancies (the fast conduction of Na₃SbS₄ goes through its vacancies); Na₃PS₄ turns cubic around 530 K |
| Sodium molecular dynamics calibration no. 2 (2026-11-02, fixed before its runs after no. 1 failed, `SODIUM_MD_CALIBRATION_V2`: Na vacancies created by W⁶⁺ on Sb⁵⁺ must speed up Na in Na₃SbS₄, as in experiment where Na₂.₈₈Sb₀.₈₈W₀.₁₂S₄ reaches about 32 mS/cm; same 64-atom cell, same seeds; `scripts/sodium_md_calibration_v2.py`, `results/2026-11-02_sodium_md_calibration_v2/`) ❌ | measured: Na₂₃Sb₇WS₃₂ 2.1 ± 0.7 × 10⁻⁶ cm²/s against Na₃SbS₄ 7.6 ± 6.0 × 10⁻⁸, i.e. 28 times faster, in the experimental direction; but the ratio test gives 27.7 ± 24.0 (1.1 σ, "comparable") because Na₃SbS₄ barely moves (80% relative error). With this ratio test: failed. **Then the owner chose the difference test** (the one of the lithium v2 calibration ✅, already in use) for every candidate/parent verdict (`analysis/diffusion.compare`, 2026-11-02): difference +2.8 combined errors → ✅ passed, `SODIUM_MD_CAN_EXCLUDE` = True. No. 1 stays failed (−1.5). The 39 verdicts already recorded (lithium and sodium) are identical with both tests; the lithium calibration, which already used the difference, does not change |
| Blind validation benchmark (2026-10-29, measurement without a threshold): 4 good electrolytes and 8 known bad compounds go through the funnel, their own composition removed from the references, without the model (`scripts/run_benchmark.py`, `results/2026-10-29_benchmark/`) | measured: good ones passing 3/4 (2/4 with lithium metal: Li₆PS₅Cl set aside at 0.080 eV/atom, ordered cell; LGPS non-passivating, Li₁₅Ge₄); bad ones set aside 8/8 (6 by the band gap, 2 Li₂PS₃ by stability) |

---

## 8. Build order

1. Repository skeleton, `pyproject.toml`, `.gitignore`, `.env.example`, `config.py`.
2. `chem/` + tests (CPU).
3. `data/mp.py` + cache (CPU).
4. `analysis/bandgap.py` + tests (CPU).
5. `analysis/stability.py` and `analysis/electrodes.py` with MP energies + tests (CPU).
6. `sim/` (uma, relax, md) + `modal_app/`: GPU functions on Modal, UMA checkpoint stored in a **Modal volume** (downloaded once), UMA truth tests run on Modal. Start with the cheapest suitable GPU, measure the time per relaxation and per dynamics step, and retest `uma-s-1p2p1` (nitro) on a recent GPU.
7. `llm/`: client with three providers. First real test with Muse Spark (Meta): one call, one JSON answer, streamed reasoning. Then Baseten (already validated), then Fireworks.
8. `agent/pipeline.py` then `agent/loop.py` + `scripts/run_loop.py` → **first complete loop** (UMA on Modal).
9. Electrodes with UMA energies.
10. `api/`, `web/`, "replay" mode.

---

## 9. Later (outside the scope of the first night)

- Rediscovery benchmark: hide Li₆PS₅Cl, LGPS, LLZO, Li₃PS₄; compare the agent with a random search and with a heuristic, at equal UMA budget, over several seeds; ablation with and without UMA results.
- Web interface (FastAPI + Render, Supabase), 3D visualisation of molecular dynamics (3Dmol.js or NGL), **"replay" mode** with already computed results to secure the demo.
- Possible next domain: cobalt-free cathodes (first calibrate the UMA voltages on LiFePO₄ ≈ 3.4 V, LiMn₂O₄ ≈ 4.0 V, LiNi₀.₅Mn₁.₅O₄ ≈ 4.7 V).
- Muse Code for a visible part of the development, to be mentioned in the submission.
