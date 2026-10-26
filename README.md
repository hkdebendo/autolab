# AutoLab

**An autonomous AI scientist for solid-state battery materials.**

AutoLab is an AI agent that runs a closed-loop materials discovery cycle: it forms chemical hypotheses, generates candidate crystal structures, evaluates them with atomistic simulation, analyzes the results, and iterates. Our first target is **cobalt-free solid electrolytes for lithium batteries**.

> Built for the **Meta Global AI Developer Hackathon** (Oct 26 – Nov 4, 2026), track *Push the Frontier*. All code in this repository was written during the hackathon.

---

## Why

Solid-state batteries promise safer, denser energy storage, but finding a good solid electrolyte means searching a huge chemical space. A candidate must be stable, conduct lithium ions well, block electrons, and survive contact with the electrodes. Testing candidates one by one, by hand, is slow. AutoLab automates the loop of reasoning, simulating and refining.

## How it works

```
Goal (natural language)
   │
   ▼
Muse Spark ── proposes hypotheses and element substitutions
   │
   ▼
pymatgen ──── builds charge-balanced candidate structures from known crystals
   │
   ▼
UMA (Meta FAIR) ── relaxes structures and predicts energies
   │
   ▼
Stability filter ── energy above the convex hull (E_hull)
   │
   ▼
Electronic & electrode checks ── band gap, electrochemical window, interface reactivity
   │
   ▼
Molecular dynamics (UMA) ── estimates Li⁺ conduction on the top candidates
   │
   ▼
Muse Spark ── analyzes results, forms a new hypothesis → next iteration
   │
   ▼
Final report: ranked candidates, 3D structures, and the agent's reasoning
```

## Meta models used

- **Muse Spark** (Meta Model API): the scientific reasoning engine (hypotheses, tool calls, analysis).
- **UMA** (Meta FAIR, open weights): the universal atomistic model used for relaxations, energies and molecular dynamics.
- **Muse Code**: coding agent used for parts of the development.

## Tech stack

Python · ASE · pymatgen · fairchem (UMA) · Materials Project API · Modal (GPU compute) · lightweight web interface showing the agent's reasoning live

## Validation

To check that the agent finds good materials rather than just recalling them, we run a **rediscovery benchmark**: known electrolytes are hidden from the search space, and we measure whether, and how fast, the agent finds them again. Results are compared with random search and a simple heuristic, at the same simulation budget.

## Important note

AutoLab's outputs are **computationally predicted candidates**, not experimentally proven materials. The most promising ones would need higher-fidelity calculations (DFT) and laboratory synthesis to be confirmed.

## Status

🚧 Work in progress during the hackathon.

- [ ] Environment setup (pymatgen, fairchem, Materials Project)
- [ ] Candidate generation by element substitution
- [ ] UMA relaxation and stability filter
- [ ] Muse Spark agent loop
- [ ] Electronic and electrode stability checks
- [ ] Molecular dynamics on top candidates
- [ ] Rediscovery benchmark
- [ ] Web interface and final report
- [ ] Demo video

## Author

**Vincent Ricardo Amoussou** · Cotonou, Benin
