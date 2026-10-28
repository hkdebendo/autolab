# Rapport étape 8 — première boucle AutoLab sur Colab
GPU : Tesla T4, 15360 MiB, 580.82.07 | Python 3.13.16 | commit b469c42 agent: candidate funnel, minimal loop, report, run_loop script, Colab notebook (mocked tests only)
Versions : {'fairchem-core': '2.24.0', 'alignn': '2026.8.11', 'torch': '2.13.0', 'pymatgen': '2026.10.24', 'openai': '2.54.0', 'cuda': True}
Secrets : {'MP_API_KEY': 'présent', 'HF_TOKEN': 'présent', 'MODEL_API_KEY': 'présent', 'BASETEN_API_KEY': 'présent'}

Cache de départ : 54 relaxations ; références Li-P-S réutilisées : 52/52 
ALIGNN sur LiCl : optB88 6.616 eV (attendu > 5,5), mBJ 6.866 eV, 10.8 s

# AutoLab loop report

**Goal.** Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically stable or slightly metastable, electronically insulating, by substitutions in known Li-P-S crystals.

**Parents.** Li3PS4 mp-985583 (Li12P4S16, 32 atoms); Li7P3S11 mp-641703 (Li14P6S22, 42 atoms)
**Settings.** 2 iterations max, 5 candidates max, 250 new UMA relaxations max; brain meta, fallback baseten.
**Stop reason.** iterations done

## Iteration 1

**Hypothesis.** Soft-lattice expansion with isovalent Sb/Se/Na/O mixing plus dilute halide vacancy doping improves stability and Li mobility.

_meta, 1 attempt(s), 695 in / 4123 out tokens, ~$0.0184, 18.0 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-985583 | S->Cl x1, -1 Li | Dilute Cl-for-S with Li vacancy mimics argyrodite doping to boost conductivity. |
| it1-c2 | mp-985583 | S->O x2 | Partial O-for-S strengthens P-(O,S) bonds for moisture and Li-metal stability. |
| it1-c3 | mp-985583 | P->Sb all | Full Sb-for-P gives Li3SbS4-type softer lattice for wider Li channels. |
| it1-c4 | mp-641703 | S->Se x2 | Se-for-S expands the sulfide framework to lower Li migration barriers. |
| it1-c5 | mp-641703 | Li->Na x2 | Isovalent Na-for-Li probes mixed-alkali lattice expansion without vacancies. |

<details><summary>Reasoning summary (proposals)</summary>

Evaluating charge-neutral anion and cation substitutions for sulfide solid electrolytes within the allowed element set.

Resolving charge balance for P-site substitutions and the resulting lithium vacancy count.

Deriving charge-balance rules and allowed element substitutions for Li, P, and S sites.

Finalizing five charge-neutral substitution proposals with vacancy counts and stability rationales.

Selecting a diverse final set of five substitutions across anion, cation, and total replacement strategies.

Replacing Mg with Na for safer cation diversity and finalizing five isovalent and halide substitutions with neutrality checks.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull (eV/at) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|
| it1-c1 | Li11P4S15Cl | 7/7 | 17.3 | 0.026 | 2.67 / 3.26 | no | — | passed |
| it1-c2 | Li6P2S7O | 6/6 | 11.4 | 0.024 | 2.84 / 3.39 | no | — | passed |
| it1-c3 | Li3SbS4 | 1/1 | 0.0 | 0.047 | 1.94 / 3.06 | — | mp-756316, mp-760415 | rejected at bandgap: gap 1.94 < 2.0 eV |
| it1-c4 | Li7P3SeS10 | 8/8 | 2.6 | 0.018 | 2.35 / 2.89 | no | — | passed |
| it1-c5 | NaLi6P3S11 | 8/8 | 5.3 | 0.017 | 2.40 / 3.01 | no | — | passed |
- it1-c1 decomposes into: Li3PS4 0.86, P2S5 0.08, LiCl 0.06
- it1-c2 decomposes into: Li3PS4 0.88, Li3PO4 0.12
- it1-c3 decomposes into: Li3SbS4 1.00
- it1-c4 decomposes into: Li3PS4 0.89, P4S7 0.05, Se 0.03, PSe 0.03
- it1-c5 decomposes into: Li3PS4 0.76, NaPS3 0.24

**Analysis.** ranking ['it1-c5', 'it1-c4', 'it1-c2', 'it1-c1']; stop=False

- Full P-to-Sb substitution fails bandgap filter and reproduces known Li3SbS4.
- Na-for-Li and Se-for-S substitutions give lowest E_hull under 0.018 eV/atom while retaining gaps above 2.3 eV.
- Dilute O and Cl mixing passes filters but with higher metastability near 0.024-0.026 eV/atom.

**Next direction.** Combine Na plus Se co-substitution with dilute Cl vacancy doping on Li7P3S11-type parent.

_meta, 1 attempt(s), 1608 in / 1138 out tokens, ~$0.0069, 4.8 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking passed candidates by stability, band gap, and reliability while preparing a concise JSON with lessons, next step, and stop flag.

Finalizing the ranking by prioritizing lowest hull energy and acceptable band gap while noting decomposition and lattice softness factors.

</details>

## Iteration 2

**Hypothesis.** Dilute halide vacancy doping plus soft As/dilute Sb and Na mixing retains low E_hull and wide gap while adding carriers.

_meta, 1 attempt(s), 1990 in / 4170 out tokens, ~$0.0202, 16.3 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it2-c1 | mp-641703 | S->Cl x1, -1 Li | Dilute Cl on Li7P3S11 creates one Li vacancy for conductivity with minimal strain as in Li3PS4 success. |
| it2-c2 | mp-641703 | P->As x2 | Isovalent As softens PS4 framework more than P but keeps larger gap than failed full Sb. |
| it2-c3 | mp-641703 | P->Sb x1 | Dilute Sb avoids bandgap collapse of full Li3SbS4 while expanding lattice for Li motion. |
| it2-c4 | mp-985583 | Li->Na x1 | Na expansion stabilized Li7P3S11 best and should stabilize Li3PS4 framework similarly. |
| it2-c5 | mp-985583 | S->I x1, -1 Li | Large I with Li vacancy widens diffusion bottleneck and softens lattice versus Cl. |

<details><summary>Reasoning summary (proposals)</summary>

Reviewing substitution rules and rejection criteria for solid electrolyte proposals before simulation.

Filtering substitution candidates against charge neutrality, hull energy, band gap, and S-S bond constraints.

Extending charge-neutrality validation to enforce non-negative Li vacancy counts for higher-valence substitutions.

Expanding the substitution set to aliovalent Li→Mg/Al and S→halide cases with vacancy balancing.

Selecting five new parent-specific substitutions while avoiding prior parent-substitution pairs.

Validating charge neutrality and band-gap constraints while finalizing five distinct substitution proposals.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull (eV/at) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|
| it2-c1 | Li13P6S21Cl | 8/8 | 14.4 | 0.030 | 2.25 / 2.88 | no | — | passed |
| it2-c2 | Li7AsP2S11 | 6/6 | 5.3 | 0.037 | 2.20 / 2.88 | no | — | passed |
| it2-c3 | Li14SbP5S22 | 3/3 | 1.3 | 0.040 | 2.23 / 2.92 | no | — | passed |
| it2-c4 | NaLi11(PS4)4 | 2/2 | 3.6 | 0.003 | 2.71 / 3.21 | no | — | passed |
| it2-c5 | Li11P4S15I | 7/7 | 16.1 | 0.023 | 2.52 / 3.18 | no | — | passed |
- it2-c1 decomposes into: Li3PS4 0.78, P2S5 0.17, LiCl 0.05
- it2-c2 decomposes into: Li3PS4 0.76, LiAsS2 0.19, S 0.05
- it2-c3 decomposes into: Li3PS4 0.89, SbPS4 0.05, Sb2S3 0.04, S 0.02
- it2-c4 decomposes into: Li3PS4 0.92, Na3PS4 0.08
- it2-c5 decomposes into: Li3PS4 0.86, P2S5 0.08, LiI 0.06

**Analysis.** ranking ['it2-c4', 'it2-c5', 'it2-c1', 'it2-c2', 'it2-c3']; stop=False

- Ultra-dilute Na-for-Li gives near-hull stability at 0.0028 eV/atom with the widest gap of 2.71 eV.
- Dilute I-for-S vacancy doping passes with lower E_hull and wider gap than the Cl analogs.
- As and dilute Sb for P retain gaps above 2.2 eV but raise E_hull to 0.037-0.040 eV/atom.

**Next direction.** Co-combine ultra-dilute Na with Se and I vacancy doping on Li3PS4-type parent.

_meta, 1 attempt(s), 2970 in / 1483 out tokens, ~$0.0100, 5.7 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking passed candidates by lowest e_hull and highest gap, with it2-c4 first.

Finalizing the ranking order by weighing hull stability against gap margin for the last two candidates.

</details>

## Final ranking (passed candidates, lowest E_hull first)

1. it2-c4 NaLi11(PS4)4 (Li->Na x1 in mp-985583): E_hull 0.003 eV/atom, gap 2.71 eV
2. it1-c5 NaLi6P3S11 (Li->Na x2 in mp-641703): E_hull 0.017 eV/atom, gap 2.40 eV
3. it1-c4 Li7P3SeS10 (S->Se x2 in mp-641703): E_hull 0.018 eV/atom, gap 2.35 eV
4. it2-c5 Li11P4S15I (S->I x1, -1 Li in mp-985583): E_hull 0.023 eV/atom, gap 2.52 eV
5. it1-c2 Li6P2S7O (S->O x2 in mp-985583): E_hull 0.024 eV/atom, gap 2.84 eV
6. it1-c1 Li11P4S15Cl (S->Cl x1, -1 Li in mp-985583): E_hull 0.026 eV/atom, gap 2.67 eV
7. it2-c1 Li13P6S21Cl (S->Cl x1, -1 Li in mp-641703): E_hull 0.030 eV/atom, gap 2.25 eV
8. it2-c2 Li7AsP2S11 (P->As x2 in mp-641703): E_hull 0.037 eV/atom, gap 2.20 eV
9. it2-c3 Li14SbP5S22 (P->Sb x1 in mp-641703): E_hull 0.040 eV/atom, gap 2.23 eV

Model ranking (last analysis): ['it2-c4', 'it2-c5', 'it2-c1', 'it2-c2', 'it2-c3']

Not computed in this minimal loop: electrochemical window, interfaces, molecular dynamics. Candidates are computational predictions, not proven materials.

## Usage

- meta: 4 calls, 7263 in / 10914 out tokens, ~$0.0555
- baseten: 0 calls, 0 in / 0 out tokens, ~$0.0000
- UMA relaxations: 205 new / 250 allowed
- events: 66; duration 25.6 min

## Durées du notebook
- A_clone : ok, 0.0 min 
- A_install : ok, 0.6 min 
- A_versions : ok, 0.1 min 
- B_seed : ok, 0.4 min {'relaxations_in_cache': 54}
- B_reuse : ok, 0.1 min 
- C_alignn : ok, 0.2 min 
- D_loop : ok, 25.8 min 
- durée totale : 29.8 min