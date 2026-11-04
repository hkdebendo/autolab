# AutoLab

**An autonomous AI lab for materials discovery, built on Meta models.**

AutoLab is an AI agent that searches for **new materials for industry**. A researcher states a goal in plain language; a Meta language model proposes chemical substitutions in known crystals, the code builds the crystals, UMA (Meta FAIR) simulates them, scientific filters judge them, and every failure, with the measured numbers, goes back to the model, which explains it and corrects its next proposals. It is applied today to three battery challenges: **lithium solid electrolytes, cobalt-free cathodes and sodium solid electrolytes**.

> Built for the **Meta Global AI Developer Hackathon** (Oct 26 – Nov 4, 2026), track *Push the Frontier*, Indie category. All code in this repository was written during the hackathon.

▶ **Demo video (3 min):** https://www.youtube.com/watch?v=D2gCMGV8dIU

---

## What AutoLab does

Industry needs new materials, and finding one means searching a huge chemical space where every property is costly to evaluate. AutoLab automates the scientific loop of a computational materials lab: hypothesis, simulation, measurement, analysis of what failed, new hypothesis. A researcher states a goal in plain language and follows the agent at work, step by step, until a final report with ranked finalists, their numbers and the agent's reasoning.

It is applied today to **three battery challenges**: lithium solid electrolytes, cobalt-free cathodes and sodium solid electrolytes. A new challenge is a new domain module; the loop, the agents and the interface stay the same.

## How it works

```
Goal (plain language)
   │
   ▼
Muse Spark ── proposes chemical substitutions in known crystals of the domain, with a hypothesis
   │
   ▼
Fast funnel, every candidate
   ├─ pymatgen: charge-neutral crystal structures, several arrangements each
   ├─ UMA (Meta FAIR): relaxation and energies
   ├─ stability: energy above the convex hull of the known phases, with a UMA-vs-DFT error bar
   └─ the domain's rules (e.g. electronic insulation, no cobalt, lithium that can leave the crystal)
   │
   ▼
Slow tests, inside each round: the domain's measurements (contact with the metal anode, ion diffusion
by molecular dynamics, voltage and capacity...) and an independent review of each candidate (Muse Spark Open)
   │
   ▼
Feedback: every failure goes back with its measured numbers
   │
   ▼
Muse Spark ── a hypothesis on each failure's cause + a correction ── next round
   │
   ▼
Final stages: ranking, band gap of the champion (electrolytes), literature check (web search, with a known control),
final report with the finalists
   │
   ▼
Muse Wonder ── reads the whole campaign at once: what it taught, what worked, what failed,
               and the next campaign to run
```

The code measures and decides; the models propose, explain and report. The cause of a failure is the model's hypothesis and is always labelled as one. Thresholds come from `autolab/config.py`, never from the model. Every computation is cached: nothing is computed or paid for twice.

## The three domains

| Domain | Goal | What is measured | Recorded research |
|---|---|---|---|
| Lithium solid electrolytes | sulfide electrolytes for lithium-metal batteries, from β-Li3PS4 and Li7P3S11 | stability, electronic insulation, electrochemical window, reaction with lithium metal, interface with a LiFePO4 cathode, Li diffusion (molecular dynamics), conductivity at 300 K, band gap of the champion | [`results/2026-11-01_feedback_run/`](results/2026-11-01_feedback_run/) |
| Cobalt-free cathodes | a higher energy density than LiFePO4, from LiFePO4, LiMnPO4, LiMn2O4 and LiNi0.5Mn1.5O4 | stability, average voltage, capacity, energy density, volume change, each against its parent | [`results/2026-11-02_cathode_run/`](results/2026-11-02_cathode_run/) |
| Sodium solid electrolytes | Na+ conductors for sodium-metal batteries, from Na3PS4, Na3SbS4 and a NASICON | stability, electronic insulation, window vs Na/Na+, reaction with sodium metal, Na diffusion (molecular dynamics), band gap of the champion | [`results/2026-11-02_sodium_run/`](results/2026-11-02_sodium_run/) |

## Why it can be trusted

- **Truth tests**: every module is checked against known results (lattice parameters, stabilities, electrochemical windows, diffusion order, cathode voltages), with criteria fixed before the runs. Failed tests are kept and recorded, and the rules they set are applied.
- **Blind benchmarks**: known good and bad materials go through the same funnel as candidates, their own composition removed from the references and never shown to the model, for the electrolytes and for the cathodes.
- **Error bars**: every stability carries the UMA-vs-DFT difference measured on known compounds of the same chemical system.
- **DFT check**: the band gap of the champion is computed by density functional theory (GPAW), itself checked against Materials Project on six known crystals.

Every test, criterion and measured number is in [`SPEC.md`](SPEC.md) (section 7); every run, benchmark and calibration is in [`results/`](results/).

## Meta models used

- **Muse Spark** (Meta Model API): proposals, choice of the MD candidate, analysis of failures, final report, literature check with web search.
- **Muse Spark Open** (Baseten): one independent review per candidate, in parallel; fallback of Muse Spark.
- **Muse Glimmer** (Fireworks, dedicated deployment): plain-language summaries of each round and of the research.
- **Muse Wonder** (Meta Model API): the research director. At the end of each research it reads the whole campaign at once (every round, measurement, failure and Muse Spark hypothesis, the ranking, the literature check and the report) and writes what the campaign taught, what worked, what failed and the next campaign to run.  Reviews of the three recorded researches: `results/2026-11-01_feedback_run/`, `results/2026-11-02_cathode_run/`, `results/2026-11-02_sodium_run/` (`campaign_review.md`).
- **UMA** `uma-s-1p2` (Meta FAIR, open weights): relaxations, energies and molecular dynamics, on Modal GPUs (T4 for relaxations, H100 for MD).
- **Muse Voice Transcribe** (Meta Model API, realtime): the researcher can dictate a request; the local web server relays the microphone to Meta, so the key never reaches the browser.
- **Muse Code** (Meta coding agent): the web interface was built with Muse Code.
### What is a Meta model call, and what is not

| Part | What it is |
|---|---|
| Reasoning, proposals, decisions, reviews, summaries, report, literature check, campaign review | **Meta model calls**: Muse Spark, Muse Spark Open, Muse Glimmer, Muse Wonder |
| Atomistic simulation (structures, energies, molecular dynamics) | **Meta model**: UMA (Meta FAIR), run on Modal GPUs |
| Dictation of a request | **Meta model call**: Muse Voice Transcribe |
| The agent's spoken lines | **Browser function**: the browser's built-in speech synthesis with a voice installed on the computer (`localService`); online voices (for example Edge "Online (Natural)" voices) are filtered out and never used; with no local voice, the agent stays silent |
| Microphone capture and resampling to 16 kHz | **Browser function** (Web Audio), no model |
| 3D structures, charts, PDF export of a report | **Browser functions** (3Dmol.js, SVG, print), no model |
| Charge neutrality, convex hull, electrochemical window, diffusion analysis, ranking | **Code** (pymatgen, NumPy, ASE), no model |
| Known phases and reference energies | **Data**: Materials Project database |
| Electronic insulation of a candidate | **Code**: every ion must have a closed electron shell, no model |
| Band gap of the champion | **Physics, no model**: density functional theory (GPAW, PBE) on Modal CPU; checked against Materials Project on 6 known crystals (mean difference 0.03 eV, `results/2026-11-03_dft_gap_truth`) |

No other model runs during a research.

## Run it

### Run AutoLab on your computer

`scripts/run_autolab.py` runs the **full AutoLab**: the same interface, agents and research engine as the cloud version, with a database in memory (no Supabase). It starts with **sample data: three researches** (lithium solid electrolytes, cobalt-free cathodes, sodium solid electrolytes; `results/2026-11-01_feedback_run/`, `results/2026-11-02_cathode_run/`, `results/2026-11-02_sodium_run/`), whose computations (UMA relaxations and molecular dynamics on GPUs, DFT, Materials Project) are stored in the repository with their 3D files: replaying them needs **no GPU**.

```bash
git clone https://github.com/hkdebendo/autolab.git && cd autolab
python -m venv .venv                  # Python 3.12
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -e ".[web,research,dev]"
cp .env.example .env                  # then fill in your keys (see "Your own keys" below)
python scripts/run_autolab.py         # then open http://127.0.0.1:8100
```

**With your keys, the Meta models do the real work** (`autolab/agent/hybrid.py`):

- **Muse Spark** reads every request and answers your questions, written or dictated (**Muse Voice Transcribe**, microphone button): about a research, about AutoLab ("who are you?", "what can you do?"), or general science ("is copper a good conductor?").
- Click one of the three examples of the home page, or ask for the same research in your own words.  Every computation comes from the recorded research, while the agents work live on those results, **Muse Spark** analyses each round's failures and corrects its strategy, **Muse Spark Open** reviews the candidates, the plain-language summaries are written again and **Muse Wonder** reviews the whole campaign and plans the next one. About 5 minutes and 0.2 $ of your credits per replay.
- Any other request within AutoLab's domains **starts a real research** (see "Run a real research" below); if something it needs is missing (a key, Modal), the conversation says exactly what and how to add it. Only a request outside AutoLab's domains is declined.
- A missing model key: another Meta model takes the role and its name shows in the interface (Muse Spark writes the summaries unless you have your own Muse Glimmer deployment); a step whose call fails keeps its recorded answer, and the conversation says so.

The interface shows the agent at work: one card per action, naming the model or tool and what it does (Muse Spark reasoning and proposing, pymatgen building, UMA relaxing the crystal in 3D while the cell parameters move, the electronic insulation check, Muse Spark Open reviews, molecular dynamics with the lithium trajectory, failures sent back and explained, Muse Wonder reviewing the whole campaign), the progress list ticking and a lab notebook of the decisions, with the agent's voice (the browser's speech synthesis) that can be muted from the lab. A **Results** page gathers the champion of every research by domain: what it is, its crystal structure in 3D, its properties with units and error bars, the comparison with its parent, the literature check, why it was chosen and what limits the confidence, with its final report as a PDF.

### Your own keys

Copy the template and fill in your keys (each line of `.env.example` says what it powers and where to get it)

```bash
cp .env.example .env
```

| Key | Powers | Needed for |
|---|---|---|
| `MODEL_API_KEY` | **Meta Model API**: Muse Spark, Muse Wonder, Muse Voice Transcribe | the live agents (questions, researches) |
| `BASETEN_API_KEY` | Muse Spark Open (independent reviews) | recommended (else Muse Spark reviews) |
| `FIREWORKS_API_KEY`, `GLIMMER_DEPLOYMENT` | Muse Glimmer (plain-language summaries): on Fireworks it runs only on a dedicated deployment of your own account | optional (else Muse Spark writes them) |
| `MP_API_KEY` | Materials Project (known phases, reference energies) | a new research |
| `HF_TOKEN` | the UMA weights (gated: accept the FAIR Chemistry License on Hugging Face), stored in a Modal secret | a new research |

### Run a real research

Write your own request (e.g. *"Find new sulfide solid electrolytes derived from Li3PS4 by bromine substitution, stable against lithium metal."*): AutoLab runs the whole research on new crystals. The agents use the keys of `.env`; UMA (relaxations, molecular dynamics) and the DFT band gap run on **your Modal account** (GPUs billed by Modal). Set it up once:

```bash
# 1. keys in .env: MODEL_API_KEY and MP_API_KEY (BASETEN_API_KEY recommended)
# 2. accept the FAIR Chemistry License of UMA on https://huggingface.co/facebook/UMA and create a Hugging Face token
modal setup                                                        # log in to your Modal account
modal secret create huggingface-secret HF_TOKEN=<your Hugging Face token>
modal deploy modal_app/uma_app.py                                  # UMA on Modal GPUs
modal deploy modal_app/dft_app.py                                  # DFT band gap on Modal CPU
python scripts/modal_setup.py download                             # the UMA weights into your Modal volume, once
python scripts/run_autolab.py                                      # then write your request at http://127.0.0.1:8100
```

The research is followed live in the lab, then come its summary, final report (exportable as PDF) and Muse Wonder's campaign review; you can question the agent about it. A research of 3 rounds takes about 30 to 60 minutes and costs about 5 to 6 $ of Modal GPU time and under 1 $ of model calls. Every computation is cached in `.cache/`: nothing is computed twice. UMA can also run on a local NVIDIA GPU instead of Modal (`SIM_BACKEND=local` in `.env`, `pip install -e ".[gpu]"`).

### Cloud deployment (optional)
The same AutoLab can run as an online service: the research engine on Modal, the conversations in a PostgreSQL database (e.g. a free Supabase project), the interface served by `web/app.py`. Conversations and results then persist, researches keep running when your computer is off, and the page can be opened from anywhere. On top of the steps of "Run a real research":

```bash
# 1. a PostgreSQL database: e.g. create a Supabase project, copy its session pooler connection string,
#    put it in .env as DATABASE_URL
# 2. the keys of the service, in one Modal secret (the service never reads your .env):
modal secret create autolab-keys MODEL_API_KEY=... BASETEN_API_KEY=... MP_API_KEY=... DATABASE_URL=... \
    FIREWORKS_API_KEY=... GLIMMER_DEPLOYMENT=...                   # the last two only with your own Muse Glimmer deployment
modal deploy modal_app/agent_app.py                                # the service; it prints its URL
python scripts/db_setup.py                                         # creates the tables, imports the recorded researches
# 3. put the printed URL in .env as AUTOLAB_API_URL, then open the interface:
uvicorn web.app:app --port 8000                                    # http://127.0.0.1:8000
```

Researches run on Modal, and dictation is relayed by `web/app.py` (it reads `MODEL_API_KEY` from `.env`).

### Meta open-weight model

**UMA** `uma-s-1p2` (Meta FAIR), released under the **FAIR Chemistry License v1** (gated on Hugging Face: `facebook/UMA`). In the recorded researches it ran on **Modal GPUs** (T4 for relaxations, H100 for molecular dynamics); only `autolab/sim/uma.py` loads it.

### Paid runs

Paid runs (Modal, Meta), each prints its estimated cost first (`--dry-run` / `--plan`):

```bash
SIM_BACKEND=modal python scripts/run_loop.py --iterations 3 --candidates 3 --novelty --out results/<dir>
SIM_BACKEND=modal python scripts/run_benchmark.py --out results/<dir>
SIM_BACKEND=modal python scripts/conductivity.py --out results/<dir>
python scripts/uma_error_bars.py --out results/<dir>
```

## Architecture

```
autolab/
  chem/       oxidation states, substitution generator, S-S bond detector
  data/       Materials Project access with disk cache
  sim/        UMA (only uma.py imports fairchem), relaxation, molecular dynamics, DFT; local/Modal/Kaggle backends
  analysis/   convex hull, band gap, electrodes, diffusion, conductivity, cathode voltages, UMA-vs-DFT error bars
  agent/      generic loop, events, conversations service, hybrid replay, report, campaign review
  domains/    electrolyte (lithium), cathode (cobalt-free), sodium: funnel, slow tests, feedback, stages, report
  llm/        one OpenAI-compatible client (Meta, Baseten, Fireworks), prompts, JSON schemas
modal_app/    UMA on GPUs, DFT on CPU, the research service and the replays, on Modal
web/          conversational interface (history, live steps, 3D structures, diffusion animation, report)
scripts/      run AutoLab, runs, calibrations, benchmarks, conductivity, error bars
results/      every recorded run with its events, result and report
```

The loop is generic: a domain provides its funnel, prompts, slow tests, ranking and the thresholds it uses, these thresholds can be modified by the researchers. Every step reads the caches before computing (relaxations, molecular dynamics, Materials Project, band gaps, model replies). See [`SPEC.md`](SPEC.md) for the architecture and every validated parameter.

## Tests

```bash
pytest                        # CPU tests; GPU and paid-API tests are skipped
pytest web/tests              # tests of the interface
pytest --gpu                  # UMA truth tests (NVIDIA GPU only)
```

## Limits

AutoLab's candidates are **computational predictions**, not materials proven in a lab: synthesis and measurements would be needed to confirm them. 
## Author

**Vincent Ricardo Amoussou** · Benin

## License

Open source under the [MIT License](LICENSE).
