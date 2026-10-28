# AutoLab

**An autonomous AI scientist for solid-state battery materials.**

AutoLab is an AI agent searching for **solid electrolytes for lithium-metal batteries**: a Meta language model proposes chemical substitutions, the code builds the crystals, UMA (Meta FAIR) simulates them, scientific filters rank them, and the model reads the results to decide what to try next.

> Built for the **Meta Global AI Developer Hackathon** (Oct 26 – Nov 4, 2026), track *Push the Frontier*, Indie category. All code in this repository was written during the hackathon.

---

## Why

Solid-state batteries promise safer, denser energy storage, but finding a good solid electrolyte means searching a huge chemical space. A candidate must be stable, conduct lithium ions well, block electrons, and survive contact with the electrodes. Testing candidates one by one, by hand, is slow. AutoLab automates the loop of reasoning, simulating and refining.

Cathodes tested against the electrolyte default to cobalt-free materials (LiFePO₄, LiMn₂O₄).

## How it works

```
Goal (natural language)
   │
   ▼
Muse Spark ── proposes hypotheses and element substitutions
   │
   ▼
pymatgen ──── builds charge-balanced candidate structures from known crystals
   │          (several arrangements per substitution; non-neutral candidates rejected)
   ▼
UMA (Meta FAIR) ── relaxes structures and predicts energies
   │
   ▼
Stability filter ── energy above the convex hull (E_hull ≤ 0.05 eV/atom)
   │
   ▼
Electronic check ── band gap (ALIGNN, ≥ 2.0 eV) + S–S bond warning
   │
   ▼
Electrode checks (top 20) ── electrochemical window, passivation against Li metal,
   │                         interface reactivity with cathodes
   ▼
Molecular dynamics (UMA, top 3–5) ── estimates Li⁺ conduction
   │
   ▼
Muse Spark ── analyzes results, forms a new hypothesis → next iteration
   │
   ▼
Final report: ranked candidates, 3D structures, and the agent's reasoning
```

## Meta models used

- **Muse Spark** (Meta Model API): the scientific reasoning engine (hypotheses, decisions, analysis).
- **Muse Spark Open** (Baseten): parallel analysis of candidates, fallback for Muse Spark.
- **Muse Glimmer** (Fireworks): small fast tasks (formula validation, JSON conversion, iteration summaries).
- **UMA** (Meta FAIR, open weights): the universal atomistic model used for relaxations, energies and molecular dynamics.
- **Muse Code**: coding agent used for parts of the development; commits written with it say so in their message.

## Tech stack

Python · ASE · pymatgen · fairchem (UMA) · ALIGNN · Materials Project API · Modal (GPU compute) · lightweight web interface showing the agent's reasoning live

## Install

```bash
pip install -e ".[bandgap,dev]"
cp .env.example .env   # then fill in the keys yourself
```

## Tests

```bash
pytest            # CPU tests; GPU and paid-API tests are skipped
pytest --gpu      # UMA tests (NVIDIA GPU only)
pytest --api      # real LLM calls (costs credits)
```

See `SPEC.md` for the architecture and validated parameters.

## Validation

**Calibration on known materials.** Each module has a truth test against known results (`tests/`). Current results on CPU, with Materials Project energies:

| Check | AutoLab | Reference |
|---|---|---|
| Li₃PS₄ electrochemical window | 1.72 – 2.34 V | 1.71 – 2.31 V (Zhu, He & Mo 2015) |
| LGPS against Li metal | non-passivating (metallic Li₁₅Ge₄) | non-passivating |
| LLZO against Li metal | quasi-stable (0.028 eV/atom) | quasi-stable |
| Li₃PS₄ / LiCoO₂ interface | −0.416 eV/atom | — |
| E_hull Li₂S / Li₃PS₄ | 0.000 / 0.000 eV/atom | on the hull |
| Band gap Li / Li₂S / LiCl (ALIGNN) | 0.00 / 3.44 / 6.59 eV | metal / insulator / insulator |
| S→Cl + 1 Li vacancy in Li₃PS₄ | 7 distinct arrangements, all neutral | — |

With UMA energies (`uma-s-1p2`, high precision, every hull reference relaxed by UMA), on an NVIDIA T4:

| Check | AutoLab (UMA) | Reference |
|---|---|---|
| LiCl lattice parameter (relaxed from 5.0 Å) | 5.135 Å, converged | ≈ 5.13 Å (experiment) |
| E_hull Li₂S | 0.000 eV/atom | on the hull |
| E_hull of a fictitious rock-salt LiS | 0.508 eV/atom | unstable (≥ 0.3 expected) |
| E_hull Li₃PS₄ polymorphs | 0.000 / 0.007 / 0.015 eV/atom | 0.000 / 0.007 / 0.014 (Materials Project) |
| E_hull Li₇P₃S₁₁ | 0.010 eV/atom | 0.020 (Materials Project) |
| 52 Li-P-S references | mean \|UMA − MP\| = 0.009 eV/atom | — |

Cost on a T4: ≈ 7 s per relaxation (median), plus ≈ 2 min of one-time model compilation; molecular dynamics at 75 ms/step for 128 atoms (50 ps ≈ 1 h).

**Rediscovery benchmark (planned).** To check that the agent finds good materials rather than just recalling them, known electrolytes (Li₆PS₅Cl, LGPS, LLZO, Li₃PS₄) are hidden from the search space, and we measure whether, and how fast, the agent finds them again. Results are compared with random search and a simple heuristic, at the same simulation budget.

## Important note

AutoLab's outputs are **computationally predicted candidates**, not experimentally proven materials. The most promising ones would need higher-fidelity calculations (DFT) and laboratory synthesis to be confirmed.

## Status

🚧 Work in progress during the hackathon.

- [x] Repository skeleton, configuration, test markers
- [x] Candidate generation by element substitution, charge-neutrality check, S–S bond detector
- [x] Materials Project access with disk cache
- [x] Band gap filter (ALIGNN, CPU)
- [x] Convex hull and electrode checks (window, passivation, cathode interface), validated with Materials Project energies
- [x] UMA relaxation, energies and convex hull on GPU (validated on a Colab T4; Modal deployment pending)
- [x] Language-model client (Muse Spark via the Meta Model API, Muse Spark Open via Baseten)
- [ ] Electrode checks with UMA energies
- [ ] Muse Spark agent loop
- [ ] Molecular dynamics on top candidates
- [ ] Rediscovery benchmark
- [ ] Web interface and final report
- [ ] Demo video

## Author

**Vincent Ricardo Amoussou** · Benin
