# AutoLab

**A closed-loop autonomous lab for solid-state battery materials.**

AutoLab is an AI agent searching for **solid electrolytes for lithium-metal batteries**. A Meta language model proposes chemical substitutions, the code builds the crystals, UMA (Meta FAIR) simulates them, scientific filters judge them, and every failure, with the measured numbers, goes back to the model, which explains it and corrects its next proposals.

> Built for the **Meta Global AI Developer Hackathon** (Oct 26 – Nov 4, 2026), track *Push the Frontier*, Indie category. All code in this repository was written during the hackathon.

---

## Why

A good solid electrolyte must be stable, conduct lithium ions, block electrons and survive contact with lithium metal and with the cathode. Finding one means searching a huge chemical space, and each property is costly to evaluate. AutoLab automates the scientific loop: hypothesis, simulation, measurement, analysis of what failed, new hypothesis.

## The closed loop (error-driven design)

```
Goal (natural language)
   │
   ▼
Muse Spark ── proposes substitutions in known crystals (beta-Li3PS4, Li7P3S11), with a hypothesis
   │
   ▼
Fast funnel, every candidate
   ├─ pymatgen: charge-neutral structures, several arrangements each
   ├─ UMA (Meta FAIR): relaxation and energies (MP2020 corrections)
   ├─ stability: energy above the convex hull ≤ 0.05 eV/atom, with a UMA-vs-DFT error bar
   └─ electronic insulator: GapModel band gap ≥ 2.0 eV
   │
   ▼
Slow tests, inside each round
   ├─ electrodes: electrochemical window (sensitivity-checked), reaction with Li metal, LiFePO4 interface
   ├─ independent review of each candidate (Muse Spark Open)
   └─ Li diffusion by molecular dynamics (UMA, 600 K, 2 × 40 ps), one candidate chosen by Muse Spark
   │
   ▼
Feedback: failures with their measurements ("framework moved: Cl diffuses at 17.7 % of Li")
   │
   ▼
Muse Spark ── a hypothesis on each failure's cause + a correction ── next round
   │
   ▼
Final stages: ranking, room-temperature conductivity (Arrhenius + Nernst-Einstein),
literature check (web search, with a known control), final report with three finalists
```

The code only measures; the cause of a failure is the model's hypothesis and is always labelled as one. Thresholds come from `autolab/config.py`, never from the model.

## What happened in a real research (Nov 1, 2026)

Request: *"Find new sulfide solid electrolytes, derived from Li7P3S11 or beta-Li3PS4, that conduct lithium at least as fast as their parent and stay stable against lithium metal. Learn from the candidates that fail."* (`results/2026-11-01_feedback_run/`, 3 rounds, 9 new candidates)

| Round | Measured by the code | Muse Spark's reading (hypothesis → correction) |
|---|---|---|
| 1 | Li5P2S7Cl: framework moved (Cl at 17.7 % of Li); Li14P6S21O: framework moved (O at 5.3 %); NaLi13(P3S11)2: forms metallic Na with Li metal | weakly bound Cl⁻ and under-coordinated O follow Li; Na⁺ is reducible → one halogen per cell, Se instead of O, no Na |
| 2 | Li14P6SeS21: diffusion tied with its parent (1.34 ± 0.34); Li4Mg(PS4)2: forms LiMg with Li metal | Mg²⁺ is reducible → drop Mg, keep isovalent Se/As |
| 3 | Li13P6S21Br (single Br): tied with its parent (1.01 ± 0.20) | proposals state which earlier failures they correct |

Honest outcome: the agent stopped repeating its failures and its last proposals passed every test, but **no candidate diffused faster than its parent** (all "tied").

Finalists over the whole campaign (all candidates evaluated since Oct 28), all "close family already studied" in the literature:

| Finalist | E_hull (eV/atom) | Diffusion at 600 K vs parent | σ at 300 K (mS/cm, estimate) | Parent σ at 300 K |
|---|---|---|---|---|
| Li6P2SeS7 (champion) | −0.007 ± 0.005 | tied (0.66 ± 0.21) | 0.10 (0.01–0.8) | beta-Li3PS4: 1.2 |
| Li12P4SeS15 | −0.004 ± 0.005 | tied (0.82 ± 0.25) | 5.7 (1.5–22) | beta-Li3PS4: 1.2 |
| Li7P3SeS10 | +0.015 ± 0.005 | tied (1.07 ± 0.23) | 134 (50–360) | Li7P3S11: 100 |

The champion has the lowest central conductivity at room temperature (activation energy 0.42 eV), but its range overlaps its parent's: every finalist is **tied** with its parent at 300 K as at 600 K. The ranking uses this verdict first: a candidate counts as slower or faster than its parent only when the two ranges do not overlap, and the parent's range is fitted on the same runs as the candidate's. Inside a level the order is a stated convention (lowest E_hull per substitution, then activation energy, then window), not a significant difference: the three finalists share one level, so the champion is first by convention. These rules were written after the 600 K screen had picked, as champion, the finalist with the lowest central conductivity at room temperature.

## Validation: truth tests and benchmarks

Every module has a truth test against known results (`tests/`, `SPEC.md` section 7). Failures are kept.

| Check | Result | Reference |
|---|---|---|
| LiCl lattice parameter (UMA relaxation) | 5.135 Å | ≈ 5.13 Å (experiment) |
| E_hull of Li3PS4 polymorphs (UMA + MP2020) | 0.000 / 0.007 / 0.015 eV/atom | 0.000 / 0.007 / 0.014 (Materials Project) |
| Li3PS4 window (UMA + MP2020) | 1.74–2.36 V | 1.71–2.31 V (Zhu, He & Mo 2015) |
| Li3PS4 / LiFePO4 interface | −0.144 eV/atom | −0.133 (MP energies) |
| MD calibration, plan A (600 + 700 K, 1 seed) | **failed**: right order, 1.9 σ and 0.4 σ | Li7P3S11 faster than beta-Li3PS4 |
| MD calibration v2 (fixed before the runs: 600 K, 3 seeds) | passed: ratio 2.04, 3.6 σ, frameworks intact | same |
| MD on A10G vs H100 (fixed before the runs) | same D: −0.0 σ and +0.4 σ | — |
| Conductivity at 300 K (fixed before the runs: order + factor 10) | passed: Li7P3S11 100 mS/cm (58–170), beta-Li3PS4 1.2 (0.43–3.2); both ~6–7 × above experiment | 3.2–17 and 0.16 mS/cm |
| UMA vs DFT on known compounds (18 systems) | mean 0.004–0.006 eV/atom for the sulfide systems; ≤ 0.0124 on 9 polysulfides; Sb systems worse (LiSb3 0.16) | Materials Project |

**Blind benchmark** (`results/2026-11-01_benchmark_hard/`): known compounds go through the same funnel as candidates, their own composition removed from the hull, never shown to the model.

| Group | Rejected by stability + band gap | Rejected after Li metal + diffusion vs beta-Li3PS4 |
|---|---|---|
| 4 good electrolytes (Li6PS5Cl, LGPS, Li7P3S11, beta-Li3PS4) | pass 3/4 | pass 2/4 (Li6PS5Cl at 0.080 eV/atom in an ordered cell; LGPS forms Li15Ge4, its known weakness) |
| 8 bad compounds (metals, semiconductors, unstable Li2PS3) | 8/8 | 8/8 |
| 5 hard negatives: stable insulators, poor Li conductors (Li2S, LiCl, LiI, Li3PO4, Li4GeS4) | **0/5** | **5/5** (LiI only by the framework rule, weakly: near its melting point at 600 K) |

## Second domain: cobalt-free cathodes

The same agent, loop and interface search **cobalt-free cathodes for lithium-ion batteries** (`autolab/domains/cathode.py`): Muse Spark proposes substitutions in LiFePO4, LiMnPO4, spinel LiMn2O4 and LiNi0.5Mn1.5O4; the code refuses cobalt, checks charge neutrality with mixed valence, relaxes the crystal with UMA, measures its stability against the stable known phases (relaxed with UMA), then removes the lithium that neutrality allows and relaxes the charged crystal: average voltage, theoretical capacity, energy density and volume change, each compared with the parent computed the same way. Failures go back to the model as in the electrolyte loop; finalists are reviewed by Muse Spark Open, ranked by energy density and reported.

Truth test, fixed before the runs (each within 0.4 V of experiment, LiFePO4 lowest, LiNi0.5Mn1.5O4 highest; `results/2026-11-02_cathode_truth/`):

| Cathode | Experiment | UMA | Capacity |
|---|---|---|---|
| LiFePO4 | 3.45 V | 3.45 V | 170 mAh/g |
| LiMnPO4 | 4.10 V | 3.79 V | 171 mAh/g |
| LiMn2O4 (spinel) | 4.05 V | 3.82 V | 148 mAh/g |
| LiNi0.5Mn1.5O4 | 4.70 V | 4.72 V | 147 mAh/g |

First live research (Nov 2, 2026, `results/2026-11-02_cathode_run/`): *"Find new cobalt-free cathodes for lithium-ion batteries with a higher energy density than LiFePO4."* 3 rounds, 9 proposals: 2 already in Materials Project (not computed), 7 passed every filter. Finalists, all on the LiNi0.5Mn1.5O4 spinel: Ti-doped (4.75 V, 147 mAh/g, 701 Wh/kg), V-doped (4.69 V, 690 Wh/kg), Zr-doped (4.72 V, 676 Wh/kg). Honest outcome: each is **comparable to its parent** (4.72 V, 692 Wh/kg) within the model's voltage error, and the literature check (a known cathode first as a control) finds each family **already studied**. 142 relaxations, about 1 $ in all.

Each E_hull carries its UMA-vs-DFT error bar, measured on the stable known compounds of its system: 0.005-0.010 eV/atom on 8 cathode systems (`results/2026-11-02_cathode_error_bars/`).

**Blind benchmark** (`results/2026-11-02_cathode_benchmark/`, expected outcomes fixed before the runs, each compound's own composition removed from its hull): **9/10 as expected**. Good cathodes pass 2/2 (LiNiO2 3.95 V, Li3V2(PO4)3 3.73 V); bad compounds rejected 6/6 before any simulation (LiCoO2: cobalt; Li2MnO3, LiFeO2, Li3PO4, LiAlO2, Li4Ti5O12: no Li can leave); hard negatives 1/2: LiTiO2 rejected at 1.46 V, but **Li2FeSiO4 passes at 3.29 V** while it works at 2.8 V in experiment (failure kept: UMA overestimates this iron silicate).

Limits: average voltage over the whole charge only (no voltage profile), no oxygen redox, lithium diffusion in the cathode and cycling not computed; UMA underestimates the Mn voltages by about 0.2-0.3 V, overestimates Li2FeSiO4 by about 0.5 V, and underestimates the volume change of LiFePO4 (3.6 % against 6.8 % measured).

## Third domain: sodium solid electrolytes

Beyond lithium, a geopolitical bottleneck: the same agent searches **sodium solid electrolytes (Na+ conductors) for sodium-metal batteries**, the post-lithium option for the stationary storage of renewable energy (`autolab/domains/sodium.py`). Muse Spark proposes substitutions in tetragonal Na3PS4, cubic Na3SbS4 and the NASICON Na3Zr2Si2PO12; the code checks charge neutrality, relaxes the crystal with UMA, measures its stability against the stable known phases (relaxed with UMA), predicts its band gap (kept at 1.8 eV or more: Na3SbS4, a working electrolyte, sits at 1.93 eV in DFT), then in each round its electrochemical window vs Na/Na+, its reaction with sodium metal and, for one candidate chosen by the model, its sodium diffusion by molecular dynamics against its parent. The lithium stages are reused with Na+ as the mobile ion; the lithium behaviour is unchanged.

**Calibrating the sodium MD took two tests, each fixed before its runs.** (1) Na3SbS4 (about 1-3 mS/cm at room temperature) against tetragonal Na3PS4 (0.01-0.2 mS/cm), two different crystals: UMA gave the reverse order (D ratio 0.33 ± 0.29): **failed**, kept as such (`results/2026-11-02_sodium_md_calibration/`). (2) What the domain really compares, a crystal against its own parent: Na vacancies made by tungsten in Na3SbS4 (Na2.88Sb0.88W0.12S4 reaches about 32 mS/cm in experiment). UMA saw the vacancy compound diffuse **28 times faster** (2.1e-6 against 7.6e-8 cm²/s), faster by 2.8 combined standard errors (the difference test of the lithium calibration, |D − D(parent)| within 2 errors = tied), frameworks intact: **passed** (`results/2026-11-02_sodium_md_calibration_v2/`). So in the sodium domain the MD verdict against the parent excludes and ranks; comparisons between different crystals are not trusted.

First live research (Nov 2, 2026, `results/2026-11-02_sodium_run/`): *"Find new sodium solid electrolytes derived from Na3PS4 or Na3SbS4 that stay stable against sodium metal and let Na+ move fast."* 3 rounds, 9 proposals: 6 passed every filter, 1 already in Materials Project, 1 rejected for its band gap (1.77 eV), 1 above the hull limit; Na5PWS8 was then excluded because it reacts with sodium metal into metallic tungsten. Finalists: Na3PSeS3 (E_hull 0.002 ± 0.002 eV/atom, gap 2.27 eV, Na diffusion at 600 K tied with Na3PS4: 0.94 ± 0.71), the NASICON Na3Zr2Ge2PO12 and Na6P2SeS7. Honest outcome: every finalist is within the UMA error of the hull, none is shown to conduct faster, and each is only kinetically stable against sodium metal (it forms a passivating layer). The MD cost cap stopped two simulations (a NASICON candidate estimated at 9 $). During this research the Meta API answered "model not found" to every Muse Spark call for about 30 minutes (the model was listed for the same key): Muse Spark Open (Baseten) proposed and chose in its place. Once Meta answered again, the literature check and the report were run again with Muse Spark from the saved results (no new computation): the control Na3PS4 was found, Na3PSeS3 (Na3PS3Se in the Na3PS4-xSex series) and Na6P2SeS7 are **already published**, and the Ge-NASICON belongs to a studied family.

## Limits that were addressed, and what remains

| Limit | What was done | What remains |
|---|---|---|
| No room-temperature conductivity | Arrhenius fits (500–700 K) and Nernst-Einstein, calibrated on the two parents | an extrapolated estimate (range ×2–8), ideal crystal (no grain boundaries), ~6–7 × above experiment on the parents |
| No candidate faster than its parent | MD inside each round, failures fed back; room-temperature conductivity compared with the parent's by ranges, first criterion of the ranking | still none faster, at 600 K or at 300 K (all tied) |
| Energies from a learned potential, not DFT | UMA-vs-DFT error bar on every E_hull, measured on known compounds of the same system | no DFT recheck of the finalists |
| "Reduced confidence" on almost every window | window recomputed with polysulfide energies shifted by ±0.025 eV/atom; flag kept only if a limit moves > 0.1 V (11 of 20 windows robust) | the flag stays for the Li7P3S11 family (its 2.28–2.30 V window depends on P2S7) |
| Benchmark lacked hard negatives | 5 stable insulators that conduct Li poorly, absolute diffusion test | small sample; LiI rejected weakly |

Outputs are **computational predictions**, not proven materials: DFT checks, synthesis and impedance measurements would be needed.

## Meta models used

- **Muse Spark** (Meta Model API): proposals, choice of the MD candidate, analysis of failures, final report, literature check with web search.
- **Muse Spark Open** (Baseten): one independent review per candidate, in parallel; fallback of Muse Spark.
- **Muse Glimmer** (Fireworks, dedicated deployment): plain-language summaries of each round and of the research.
- **UMA** `uma-s-1p2` (Meta FAIR, open weights): relaxations, energies and molecular dynamics, on Modal GPUs (T4 for relaxations, H100 for MD).
- **Muse Code**: coding agent used for parts of the web interface; commits written with it say so.

## Architecture

```
autolab/
  chem/       oxidation states, substitution generator, S-S bond detector
  data/       Materials Project access with disk cache
  sim/        UMA (only uma.py imports fairchem), relaxation, MD, local/Modal/Kaggle backends
  analysis/   convex hull, band gap, electrodes, diffusion, conductivity, UMA-vs-DFT error bars
  agent/      generic loop, events, MD, benchmark, conversations service, report
  domains/    electrolyte: funnel, slow tests, feedback, stages, report
  llm/        one OpenAI-compatible client (Meta, Baseten, Fireworks), prompts, JSON schemas
modal_app/    GPU functions (UMA) and the research service (CPU), on Modal
web/          conversational interface (history, live steps, 3D structures, Li-diffusion animation, report)
scripts/      runs, calibrations, benchmark, conductivity, error bars
results/      every recorded run with its events, result and report
```

Every step reads the caches before computing (relaxations, MD runs, Materials Project, band gaps, model replies): nothing already computed is computed or paid twice. Every loop has hard limits in `config.py` (iterations, candidates, relaxations, model calls, Modal cost per research).

## Cost of the project (hackathon credits)

About 36 $ of Modal GPU time (calibrations, benchmark, runs), 1.2 $ of Muse Spark, 0.9 $ of Muse Spark Open, 2–3 $ of Muse Glimmer. A complete 3-round research costs about 5–6 $ of Modal and 0.3 $ of Muse Spark.

## Reproduce

```bash
pip install -e ".[bandgap,dev]"
cp .env.example .env          # then fill in your own keys
pytest                        # 188 CPU tests; GPU and paid-API tests are skipped
pytest web/tests              # 18 tests of the interface
pytest --gpu                  # UMA truth tests (NVIDIA GPU only)
```

Recorded results need no key: open `results/*/report.md`, or preview the interface on the recorded researches:

```bash
python scripts/dev_server.py  # http://127.0.0.1:8100, no database, no paid call
# watch the agent at work on the Nov 1 research: http://127.0.0.1:8100/c/feedback-2026-11-01?watch=2
# and on the cobalt-free cathode research: http://127.0.0.1:8100/c/cathode-2026-11-02?watch=2
```

The interface shows the agent at work: one card per action, naming the model or tool and what it does (Muse Spark reasoning and proposing, pymatgen building, UMA relaxing the crystal in 3D while the cell parameters move, GapModel band gap, Muse Spark Open reviews, molecular dynamics with the recorded lithium trajectory, failures sent back and explained), the progress list ticking and a lab notebook of the decisions; the research card, the summary and the report come at the end. The lab opens full screen in landscape (progress, current action and lab notebook side by side; a button reduces it into the chat); after a research, "Watch the agent at work" replays it there, with pause, stop, restart and leave (a paused replay resumes where it stopped). Results taken from the saved computations are played at a readable pace and marked "reused"; an identical request reuses a finished research without computing anything. A **Results** page gathers the champion of every research by domain (solid electrolytes, cobalt-free cathodes): what it is, its crystal structure in 3D, its properties with units and error bars, the comparison with its parent, the literature check, why it was chosen and what limits the confidence, with its final report as a PDF and a link back to the research to talk with the agent.

Paid runs (Modal, Meta), each prints its estimated cost first (`--dry-run` / `--plan`):

```bash
SIM_BACKEND=modal python scripts/run_loop.py --iterations 3 --candidates 3 --novelty --out results/<dir>
SIM_BACKEND=modal python scripts/run_benchmark.py --out results/<dir>
SIM_BACKEND=modal python scripts/conductivity.py --out results/<dir>
python scripts/uma_error_bars.py --out results/<dir>
```

The full interface: deploy `modal_app/uma_app.py` and `modal_app/agent_app.py` (`modal deploy`), set `AUTOLAB_API_URL` in `.env`, then `uvicorn web.app:app`.

See `SPEC.md` for the architecture and every validated parameter, `docs/DECISIONS.md` for the decisions and `docs/PROGRESS.md` for the log.

## Author

**Vincent Ricardo Amoussou** · Benin
-