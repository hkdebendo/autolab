# AutoLab loop report

**Domain.** electrolyte. **Goal.** Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically stable or slightly metastable, electronically insulating, by substitutions in known Li-P-S crystals.

**Parents.** Li3PS4 mp-985583 (Li12P4S16, 32 atoms); Li7P3S11 mp-641703 (Li14P6S22, 42 atoms)
**Settings.** 2 iterations max, 5 candidates max, 160 new UMA relaxations max; brain meta, fallback None.
**Stop reason.** relaxation budget: 21 new relaxations requested, 5 left (MAX_RELAXATIONS_PER_RUN)

## Iteration 1

**Hypothesis.** Halogen, As, and vacancy-creating cation dopants will retain sulfide frameworks with low hull energy.

_meta, 1 attempt(s), 4485 in / 3877 out tokens, ~$0.0221, 15.4 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-985583 | S->F x1, -1 Li | Small electronegative F for S with Li vacancy extends successful Cl/Br/I doping to improve stability. |
| it1-c2 | mp-641703 | S->I x1, -1 Li | Large polarizable I for S with Li vacancy expands lattice for conductivity while following passed Cl doping. |
| it1-c3 | mp-985583 | P->As x1 | Isovalent As for P preserves PS4 network while softening lattice as in passed As-doped Li7P3S11. |
| it1-c4 | mp-985583 | Li->Mg x1, -1 Li | Mg for Li creates a compensating Li vacancy to boost ionic carriers with divalent stabilization. |
| it1-c5 | mp-985583 | Li->Na x2 | Higher Na content builds on the best ultra-stable Na hit to tune bottleneck size for Li transport. |

<details><summary>Reasoning summary (proposals)</summary>

Generating up to five new, chemically motivated substitutions while avoiding previously evaluated combinations and ensuring diverse, non-repeating options.

Evaluating halogen and group-14 substitutions under charge-neutrality and allowed-element constraints.

Deriving charge-neutrality constraints for allowed element substitutions and vacancy counts.

Proposing new aliovalent Li-site dopants and halogen substitutions while avoiding prior parent-substitution pairs.

Selecting five partial substitutions across two parents to diversify halogen, pnictogen, and aliovalent Li-site dopants while avoiding full replacements.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it1-c1 | Li11P4S15F | 7/7 | 19.3 | 0.030 | 0.460 | 2.68 / 3.33 | no | — | passed |
| it1-c2 | Li13P6S21I | 8/8 | 14.8 | 0.024 | 0.489 | 2.40 / 2.95 | no | — | passed |
| it1-c3 | Li12AsP3S16 | 1/1 | 0.0 | -0.005 | -0.154 | 2.54 / 3.20 | no (reduced confidence: decomposes via LiS4) | — | passed |
| it1-c4 | Li10Mg(PS4)4 | 8/8 | 18.3 | 0.007 | 0.102 | 2.61 / 3.23 | no (reduced confidence: decomposes via P2S7) | — | passed |
| it1-c5 | NaLi5(PS4)2 | 7/7 | 10.6 | 0.003 | 0.055 | 2.70 / 3.30 | no | — | passed |
- it1-c1 decomposes into: Li3PS4 0.86, P2S5 0.08, LiF 0.06
- it1-c2 decomposes into: Li3PS4 0.78, P2S5 0.17, LiI 0.05
- it1-c3 decomposes into: Li3PS4 0.75, Li3AsS3 0.19, LiS4 0.04, LiAsS2 0.02
- it1-c4 decomposes into: Li3PS4 0.86, MgPS3 0.07, MgS 0.04, P2S7 0.03
- it1-c5 decomposes into: Li3PS4 0.83, Na3PS4 0.17

<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (s1:it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2SeS7 (s1:it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c2)
- **same substitution, different parents**, Li->Na x2 on mp-641703 vs mp-985583: E_hull per atom: NaLi5(PS4)2 (it1-c5) 0.003 < NaLi6P3S11 (s9:it1-c5) 0.017 eV/atom (better: it1-c5); E_hull per substitution: NaLi5(PS4)2 (it1-c5) 0.055 < NaLi6P3S11 (s9:it1-c5) 0.347 eV per modified site (better: it1-c5); band gap optB88: NaLi5(PS4)2 (it1-c5) 2.699 > NaLi6P3S11 (s9:it1-c5) 2.397 eV (better: it1-c5)
- **same substitution, different parents**, S->I x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li13P6S21I (it1-c2) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (it1-c2) 0.489 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15I (s9:it2-c5) 2.522 > Li13P6S21I (it1-c2) 2.397 eV (better: s9:it2-c5)
- **same parent, different added element**, on mp-985583: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li11P4S15F (it1-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li11P4S15F (it1-c1) 0.460 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15F (it1-c1) 2.678 > Li11P4S15Cl (s9:it1-c1) 2.669 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Br (s1:it1-c1) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Br (s1:it1-c1) 0.367 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s1:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15F (it1-c1) 0.030 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15F (it1-c1) 0.460 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15F (it1-c1) 2.678 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->Br vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15F (it1-c1) 0.030 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15F (it1-c1) 0.460 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15F (it1-c1) 2.678 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->O vs S->Se (x2, 0 Li vacancies): E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li6P2S7O (s9:it1-c2) 0.024 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li6P2S7O (s9:it1-c2) 0.384 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li6P2SeS7 (s1:it1-c2) 2.485 eV (better: s9:it1-c2)
- **same parent, different added element**, on mp-641703: S->Se vs S->O (x2, 0 Li vacancies): E_hull per atom: Li7P3SeS10 (s9:it1-c4) 0.015 < Li7P3S10O (s1:it1-c3) 0.024 eV/atom (better: s9:it1-c4); E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c4); band gap optB88: Li7P3S10O (s1:it1-c3) 2.560 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c3)
- **same parent, different added element**, on mp-641703: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (it1-c2) 0.024 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: it1-c2); E_hull per substitution: Li13P6S21I (it1-c2) 0.489 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: it1-c2); band gap optB88: Li13P6S21I (it1-c2) 2.397 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: it1-c2)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): s1:it1-c2 -0.007, it1-c3 -0.005, s9:it2-c4 0.003, it1-c5 0.003, it1-c4 0.007, s9:it2-c5 0.023, s1:it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026, it1-c1 0.030; E_hull per substitution (lowest first): it1-c3 -0.154, s1:it1-c2 -0.115, it1-c5 0.055, s9:it2-c4 0.089, it1-c4 0.102, s9:it2-c5 0.362, s1:it1-c1 0.367, s9:it1-c2 0.384, s9:it1-c1 0.399, it1-c1 0.460; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, it1-c5 2.699, it1-c1 2.678, s9:it1-c1 2.669, s1:it1-c1 2.660, it1-c4 2.610, it1-c3 2.542, s9:it2-c5 2.522, s1:it1-c2 2.485
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): s9:it1-c4 0.015, s9:it1-c5 0.017, it1-c2 0.024, s9:it2-c2 0.024, s1:it1-c3 0.024, s9:it2-c1 0.030, s9:it2-c3 0.033; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, it1-c2 0.489, s9:it2-c2 0.503, s1:it1-c3 0.510, s9:it2-c1 0.618, s9:it2-c3 1.381; band gap optB88 (highest first): s1:it1-c3 2.560, s9:it1-c5 2.397, it1-c2 2.397, s9:it1-c4 2.355, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200

</details>

**Analysis.** ranking ['it1-c3', 'it1-c5', 'it1-c4', 'it1-c1', 'it1-c2']; stop=False

- Li->Na x2 favors mp-985583 (0.055) over mp-641703 (0.347 eV per modified site).
- On mp-985583 S->I (0.362) beats S->F (0.460 eV per modified site).
- S->I x1 favors mp-985583 (0.362) over mp-641703 (0.489 eV per modified site).

**Next direction.** Prioritize low-dose Na, Mg and As/Se substitutions on mp-985583.

_meta, 1 attempt(s), 9652 in / 1892 out tokens, ~$0.0201, 7.4 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking passed candidates by e_hull_per_substitution while accounting for reduced confidence and parent comparison overrides.

Deriving three short lessons from quoted comparisons while noting reduced confidence uncertainty for the top candidate.

Finalizing the candidate ranking by e_hull per substitution and quoting comparison numbers for the lessons.

</details>

## Iteration 2

**Hypothesis.** Low-dose isovalent As/Sb/Se expansion plus Mg/Al vacancy creation on Li3PS4 will retain stability and insulation.

_meta, 1 attempt(s), 6107 in / 3071 out tokens, ~$0.0207, 11.6 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it2-c1 | mp-985583 | P->Sb x1 | Isovalent Sb for P expands tetrahedra like successful As to aid conductivity while staying charge-balanced. |
| it2-c2 | mp-985583 | S->Se x1 | Dilute Se for S tests the low-dose limit of the hull-negative Se substitution to soften lattice for ion transport. |
| it2-c3 | mp-985583 | P->As x2 | Increase successful As doping to two sites to map solubility and framework tolerance for larger pnictogen. |
| it2-c4 | mp-641703 | Li->Mg x1, -1 Li | Transfer the low-cost Mg-plus-vacancy strategy from Li3PS4 to Li7P3S11 to create Li vacancies for conductivity. |
| it2-c5 | mp-985583 | Li->Al x1, -2 Li | Trivalent Al for Li creates two vacancies per dopant for stronger vacancy-mediated transport than Mg. |

<details><summary>Reasoning summary (proposals)</summary>

Compiling up to five chemically diverse substitution proposals while excluding previously evaluated ones.

Proposing a P-to-Sb single substitution on mp-985583 with charge-neutrality validation.

Evaluating charge-neutrality constraints and proposing low-dose Se, As, and Mg substitutions on new parents.

Selecting five chemically distinct single-site substitutions with explicit vacancy accounting and charge balance.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it2-c1 | Li12SbP3S16 | 1/1 | 0.0 | 0.013 | 0.412 | 2.46 / 3.17 | no | — | passed |
| it2-c2 | Li12P4SeS15 | 3/3 | 1.9 | -0.004 | -0.113 | 2.59 / 3.15 | no | — | passed |
| it2-c3 | Li6AsPS8 | 3/3 | 0.3 | -0.010 | -0.153 | 2.37 / 3.15 | no (reduced confidence: decomposes via LiS4) | — | passed |
| it2-c4 | Li12Mg(P3S11)2 | 8/8 | 10.1 | 0.022 | 0.453 | 2.35 / 2.96 | no (reduced confidence: decomposes via P2S7) | — | passed |
| it2-c5 | — | —/— | — | — | — | — | — | — | budget at —: 21 new relaxations requested, 5 left (MAX_RELAXATIONS_PER_RUN) |
- it2-c1 decomposes into: Li3PS4 0.75, Li3SbS4 0.25
- it2-c2 decomposes into: Li3PS4 0.94, Li7PSe6 0.05, P2Se5 0.02
- it2-c3 decomposes into: Li3PS4 0.50, Li3AsS3 0.38, LiS4 0.09, LiAsS2 0.04
- it2-c4 decomposes into: Li3PS4 0.78, MgPS3 0.12, P2S7 0.05, P2S5 0.04

<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (s1:it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2SeS7 (s1:it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c2)
- **same substitution, different parents**, Li->Na x2 on mp-641703 vs mp-985583: E_hull per atom: NaLi5(PS4)2 (it1-c5) 0.003 < NaLi6P3S11 (s9:it1-c5) 0.017 eV/atom (better: it1-c5); E_hull per substitution: NaLi5(PS4)2 (it1-c5) 0.055 < NaLi6P3S11 (s9:it1-c5) 0.347 eV per modified site (better: it1-c5); band gap optB88: NaLi5(PS4)2 (it1-c5) 2.699 > NaLi6P3S11 (s9:it1-c5) 2.397 eV (better: it1-c5)
- **same substitution, different parents**, P->As x2 on mp-641703 vs mp-985583: E_hull per atom: Li6AsPS8 (it2-c3) -0.010 < Li7AsP2S11 (s9:it2-c2) 0.024 eV/atom (better: it2-c3); E_hull per substitution: Li6AsPS8 (it2-c3) -0.153 < Li7AsP2S11 (s9:it2-c2) 0.503 eV per modified site (better: it2-c3); band gap optB88: Li6AsPS8 (it2-c3) 2.374 > Li7AsP2S11 (s9:it2-c2) 2.200 eV (better: it2-c3)
- **same substitution, different parents**, P->Sb x1 on mp-641703 vs mp-985583: E_hull per atom: Li12SbP3S16 (it2-c1) 0.013 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: it2-c1); E_hull per substitution: Li12SbP3S16 (it2-c1) 0.412 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: it2-c1); band gap optB88: Li12SbP3S16 (it2-c1) 2.457 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: it2-c1)
- **same substitution, different parents**, S->I x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li13P6S21I (it1-c2) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (it1-c2) 0.489 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15I (s9:it2-c5) 2.522 > Li13P6S21I (it1-c2) 2.397 eV (better: s9:it2-c5)
- **same substitution, different parents**, Li->Mg x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li10Mg(PS4)4 (it1-c4) 0.007 < Li12Mg(P3S11)2 (it2-c4) 0.022 eV/atom (better: it1-c4); E_hull per substitution: Li10Mg(PS4)4 (it1-c4) 0.102 < Li12Mg(P3S11)2 (it2-c4) 0.453 eV per modified site (better: it1-c4); band gap optB88: Li10Mg(PS4)4 (it1-c4) 2.610 > Li12Mg(P3S11)2 (it2-c4) 2.355 eV (better: it1-c4)
- **same parent, different added element**, on mp-985583: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li11P4S15F (it1-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li11P4S15F (it1-c1) 0.460 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15F (it1-c1) 2.678 > Li11P4S15Cl (s9:it1-c1) 2.669 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Br (s1:it1-c1) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Br (s1:it1-c1) 0.367 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s1:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15F (it1-c1) 0.030 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15F (it1-c1) 0.460 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15F (it1-c1) 2.678 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->Br vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15F (it1-c1) 0.030 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15F (it1-c1) 0.460 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15F (it1-c1) 2.678 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->O vs S->Se (x2, 0 Li vacancies): E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li6P2S7O (s9:it1-c2) 0.024 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li6P2S7O (s9:it1-c2) 0.384 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li6P2SeS7 (s1:it1-c2) 2.485 eV (better: s9:it1-c2)
- **same parent, different added element**, on mp-641703: S->Se vs S->O (x2, 0 Li vacancies): E_hull per atom: Li7P3SeS10 (s9:it1-c4) 0.015 < Li7P3S10O (s1:it1-c3) 0.024 eV/atom (better: s9:it1-c4); E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c4); band gap optB88: Li7P3S10O (s1:it1-c3) 2.560 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c3)
- **same parent, different added element**, on mp-641703: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (it1-c2) 0.024 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: it1-c2); E_hull per substitution: Li13P6S21I (it1-c2) 0.489 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: it1-c2); band gap optB88: Li13P6S21I (it1-c2) 2.397 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: it1-c2)
- **same parent, different added element**, on mp-985583: P->As vs P->Sb (x1, 0 Li vacancies): E_hull per atom: Li12AsP3S16 (it1-c3) -0.005 < Li12SbP3S16 (it2-c1) 0.013 eV/atom (better: it1-c3); E_hull per substitution: Li12AsP3S16 (it1-c3) -0.154 < Li12SbP3S16 (it2-c1) 0.412 eV per modified site (better: it1-c3); band gap optB88: Li12AsP3S16 (it1-c3) 2.542 > Li12SbP3S16 (it2-c1) 2.457 eV (better: it1-c3)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): it2-c3 -0.010, s1:it1-c2 -0.007, it1-c3 -0.005, it2-c2 -0.004, s9:it2-c4 0.003, it1-c5 0.003, it1-c4 0.007, it2-c1 0.013, s9:it2-c5 0.023, s1:it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026, it1-c1 0.030; E_hull per substitution (lowest first): it1-c3 -0.154, it2-c3 -0.153, s1:it1-c2 -0.115, it2-c2 -0.113, it1-c5 0.055, s9:it2-c4 0.089, it1-c4 0.102, s9:it2-c5 0.362, s1:it1-c1 0.367, s9:it1-c2 0.384, s9:it1-c1 0.399, it2-c1 0.412, it1-c1 0.460; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, it1-c5 2.699, it1-c1 2.678, s9:it1-c1 2.669, s1:it1-c1 2.660, it1-c4 2.610, it2-c2 2.594, it1-c3 2.542, s9:it2-c5 2.522, s1:it1-c2 2.485, it2-c1 2.457, it2-c3 2.374
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): s9:it1-c4 0.015, s9:it1-c5 0.017, it2-c4 0.022, it1-c2 0.024, s9:it2-c2 0.024, s1:it1-c3 0.024, s9:it2-c1 0.030, s9:it2-c3 0.033; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, it2-c4 0.453, it1-c2 0.489, s9:it2-c2 0.503, s1:it1-c3 0.510, s9:it2-c1 0.618, s9:it2-c3 1.381; band gap optB88 (highest first): s1:it1-c3 2.560, s9:it1-c5 2.397, it1-c2 2.397, s9:it1-c4 2.355, it2-c4 2.355, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200

</details>

**Analysis.** ranking ['it2-c3', 'it2-c2', 'it2-c1', 'it2-c4']; stop=False

- On mp-985583, P->As x1 (-0.154) beats P->Sb x1 (0.412 eV per modified site).
- P->As x2 on mp-985583 (-0.153) beats same on mp-641703 (0.503 eV per modified site).
- Li->Mg x1 on mp-985583 (0.102) beats same on mp-641703 (0.453 eV per modified site).

**Next direction.** Prioritize low-dose As/Se on mp-985583 and retry Al vacancy creation.

_meta, 1 attempt(s), 11996 in / 2124 out tokens, ~$0.0240, 8.4 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking passed candidates by e_hull_per_substitution while noting reduced confidence flags and parent comparison context without performing value comparisons.

Extracting quoted lessons and next direction while preserving the passed-only ranking constraint.

</details>

**Earlier runs.** 13 candidates given to the model and to the stages: s9:it1-c1, s9:it1-c2, s9:it1-c3, s9:it1-c4, s9:it1-c5, s9:it2-c1, s9:it2-c2, s9:it2-c3, s9:it2-c4, s9:it2-c5, s1:it1-c1, s1:it1-c2, s1:it1-c3.

## Electrodes (UMA + MP2020 energies)

- Calibration Li3PS4 / LiFePO4: UMA -0.144 vs MP -0.133 eV/atom (diff -0.011, tolerance 0.05) → trusted

| Candidate | Formula | Window (V) | Against Li metal | Worst reaction with LiFePO4 (eV/atom) | Confidence | Decision |
|---|---|---|---|---|---|---|
| it1-c3 | Li12AsP3S16 | 2.08–2.26 | passivating (2.358) | -0.152 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |
| it2-c3 | Li6AsPS8 | 2.08–2.26 | passivating (2.414) | -0.161 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c2 | Li6P2SeS7 | 1.80–2.24 | passivating (2.309) | -0.145 | reduced (electrolyte decomposes via SeS7); cathode reaction forms FeS2 (information) | kept |
| it2-c2 | Li12P4SeS15 | 1.80–2.24 | passivating (2.306) | -0.145 | reduced (electrolyte decomposes via SeS7); cathode reaction forms FeS2 (information) | kept |
| it1-c5 | NaLi5(PS4)2 | 1.94–2.26 | non_passivating (2.112) | — | reduced (electrolyte decomposes via Na2S5) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.112 eV/atom) |
| s9:it2-c4 | NaLi11(PS4)4 | 1.94–2.26 | non_passivating (2.204) | — | reduced (electrolyte decomposes via Na2S5) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom) |
| it1-c4 | Li10Mg(PS4)4 | zero width (not a rejection) | non_passivating (2.287) | — | reduced (electrolyte decomposes via P2S7) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.287 eV/atom) |
| s9:it1-c4 | Li7P3SeS10 | 2.28–2.30 | passivating (2.529) | -0.143 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c5 | NaLi6P3S11 | 2.26–2.34 | non_passivating (2.365) | — | reduced (electrolyte decomposes via Na2S5, P2S7) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom) |
| s9:it2-c5 | Li11P4S15I | 2.28–2.30 | passivating (2.368) | -0.139 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c1 | Li11P4S15Br | 2.28–2.30 | passivating (2.368) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c2 | Li6P2S7O | 1.74–2.36 | passivating (2.197) | -0.138 | reduced (electrolyte decomposes via LiS4, P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c1 | Li11P4S15Cl | 2.28–2.30 | passivating (2.372) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| it2-c1 | Li12SbP3S16 | 2.00–2.30 | passivating (2.353) | -0.151 | reduced (electrolyte decomposes via LiS4); cathode reaction forms FeS2 (information) | kept |
| it2-c4 | Li12Mg(P3S11)2 | zero width (not a rejection) | non_passivating (2.507) | — | reduced (electrolyte decomposes via P2S7) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.507 eV/atom) |
| it1-c1 | Li11P4S15F | 2.28–2.30 | passivating (2.378) | — | reduced (electrolyte decomposes via P2S7); interface not computed | kept |
| it1-c2 | Li13P6S21I | 2.28–2.30 | passivating (2.564) | -0.136 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c2 | Li7AsP2S11 | zero width (not a rejection) | passivating (2.598) | -0.149 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c3 | Li7P3S10O | 2.28–2.30 | passivating (2.442) | -0.136 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c1 | Li13P6S21Cl | 2.28–2.30 | passivating (2.574) | -0.135 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
- it1-c1: not computed (interface with LiFePO4: 14 new relaxations requested, 5 left (MAX_RELAXATIONS_PER_RUN))

**Stopped:** relaxation budget: 1 computation(s) skipped

Reduced confidence: the decomposition of the electrolyte (window limits, Li metal) goes through a polysulfide, where UMA is least reliable. Interfaces are informative (no threshold); a polysulfide formed with the cathode (FeS2 for almost every sulfide against LiFePO4) is shown as information only.

## Choice of the candidates for molecular dynamics

Eligible: it1-c3, it2-c3, s1:it1-c2, it2-c2, s9:it1-c4, s9:it2-c5, s1:it1-c1, s9:it1-c2, s9:it1-c1, it2-c1, it1-c1, it1-c2, s9:it2-c2, s1:it1-c3, s9:it2-c1, s9:it2-c3. Selected by meta: s1:it1-c2, s9:it1-c4, s9:it2-c5.

Rationale: Cover soft-anion Se on both parents with E_hull per substitution Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site plus Li-vacancy I with Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (it1-c2) 0.489 eV per modified site, all MD-cached for free diverse conduction testing.

## Li diffusion (600 K, 2 seeds of 40 ps pooled, Modal A10G)

Runs computed: 0 of 16 (others from the cache); estimate 0.00 $, about 0 min in parallel.
Not selected but already simulated (verdict from the cache, no cost): s9:it1-c2, s9:it1-c1, s9:it2-c1.

| Structure | Kind | D ± s.e. (cm²/s) | D / D(parent) | Verdict | Conduction | Framework |
|---|---|---|---|---|---|---|
| Li7P3S11 (mp-641703) | parent | 1.30e-05 ± 2.2e-06 | — | — | — | intact |
| Li3PS4 (mp-985583) | parent | 5.94e-06 ± 1.2e-06 | — | — | — | intact |
| Li6P2SeS7 (s1:it1-c2) | candidate | 3.90e-06 ± 9.6e-07 | 0.66 ± 0.21 | tied | passes | intact |
| Li7P3SeS10 (s9:it1-c4) | candidate | 1.39e-05 ± 1.8e-06 | 1.07 ± 0.23 | tied | passes | intact |
| Li11P4S15I (s9:it2-c5) | candidate | 5.34e-06 ± 1.7e-06 | 0.90 ± 0.34 | tied | passes | intact |
| Li6P2S7O (s9:it1-c2) | candidate | 7.86e-06 ± 8.1e-07 | 1.32 ± 0.30 | tied | passes | intact |
| Li11P4S15Cl (s9:it1-c1) | candidate | 5.53e-06 ± 1.2e-06 | 0.93 ± 0.28 | tied | passes | intact |
| Li13P6S21Cl (s9:it2-c1) | candidate | 1.25e-05 ± 1.4e-06 | 0.96 ± 0.20 | tied | excluded | MOVED |

## Final ranking

Order: MD verdict (higher > tied > not_run), then lowest E_hull per substitution; excluded candidates last, with their reason. Candidates are computational predictions, not proven materials.

1. s1:it1-c2 Li6P2SeS7 **finalist**: E_hull per substitution -0.115 eV, E_hull -0.007 eV/atom, gap 2.48 eV, MD tied (D/D(parent) 0.66 ± 0.21); reduced confidence of the window (decomposes via SeS7)
2. s9:it1-c4 Li7P3SeS10 **finalist**: E_hull per substitution 0.323 eV, E_hull 0.015 eV/atom, gap 2.35 eV, MD tied (D/D(parent) 1.07 ± 0.23); reduced confidence of the window (decomposes via P2S7)
3. s9:it2-c5 Li11P4S15I **finalist**: E_hull per substitution 0.362 eV, E_hull 0.023 eV/atom, gap 2.52 eV, MD tied (D/D(parent) 0.90 ± 0.34); reduced confidence of the window (decomposes via P2S7)
4. s9:it1-c2 Li6P2S7O: E_hull per substitution 0.384 eV, E_hull 0.024 eV/atom, gap 2.84 eV, MD tied (D/D(parent) 1.32 ± 0.30); reduced confidence of the window (decomposes via LiS4, P2S7)
5. s9:it1-c1 Li11P4S15Cl: E_hull per substitution 0.399 eV, E_hull 0.026 eV/atom, gap 2.67 eV, MD tied (D/D(parent) 0.93 ± 0.28); reduced confidence of the window (decomposes via P2S7)
6. it1-c3 Li12AsP3S16: E_hull per substitution -0.154 eV, E_hull -0.005 eV/atom, gap 2.54 eV, MD not run; reduced confidence (E_hull via LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
7. it2-c3 Li6AsPS8: E_hull per substitution -0.153 eV, E_hull -0.010 eV/atom, gap 2.37 eV, MD not run; reduced confidence (E_hull via LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
8. it2-c2 Li12P4SeS15: E_hull per substitution -0.113 eV, E_hull -0.004 eV/atom, gap 2.59 eV, MD not run; reduced confidence of the window (decomposes via SeS7)
9. s1:it1-c1 Li11P4S15Br: E_hull per substitution 0.367 eV, E_hull 0.024 eV/atom, gap 2.66 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
10. it2-c1 Li12SbP3S16: E_hull per substitution 0.412 eV, E_hull 0.013 eV/atom, gap 2.46 eV, MD not run; reduced confidence of the window (decomposes via LiS4)
11. it1-c1 Li11P4S15F: E_hull per substitution 0.460 eV, E_hull 0.030 eV/atom, gap 2.68 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
12. it1-c2 Li13P6S21I: E_hull per substitution 0.489 eV, E_hull 0.024 eV/atom, gap 2.40 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
13. s9:it2-c2 Li7AsP2S11: E_hull per substitution 0.503 eV, E_hull 0.024 eV/atom, gap 2.20 eV, MD not run; reduced confidence (E_hull via AsS2, LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
14. s1:it1-c3 Li7P3S10O: E_hull per substitution 0.510 eV, E_hull 0.024 eV/atom, gap 2.56 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
15. s9:it2-c3 Li14SbP5S22: E_hull per substitution 1.381 eV, E_hull 0.033 eV/atom, gap 2.23 eV, MD not run; reduced confidence (E_hull via LiS4)
16. s9:it2-c1 Li13P6S21Cl: E_hull per substitution 0.618 eV, E_hull 0.030 eV/atom, gap 2.25 eV, MD tied (D/D(parent) 0.96 ± 0.20); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at molecular_dynamics: framework moved: Cl diffuses at 40% of Li (limit 5%), seed 0, final MSD 5.4 A2
17. it1-c5 NaLi5(PS4)2: E_hull per substitution 0.055 eV, E_hull 0.003 eV/atom, gap 2.70 eV, MD not run; reduced confidence of the window (decomposes via Na2S5) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.112 eV/atom)
18. s9:it2-c4 NaLi11(PS4)4: E_hull per substitution 0.089 eV, E_hull 0.003 eV/atom, gap 2.71 eV, MD not run; reduced confidence of the window (decomposes via Na2S5) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom)
19. it1-c4 Li10Mg(PS4)4: E_hull per substitution 0.102 eV, E_hull 0.007 eV/atom, gap 2.61 eV, MD not run; reduced confidence (E_hull via P2S7); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.287 eV/atom)
20. s9:it1-c5 NaLi6P3S11: E_hull per substitution 0.347 eV, E_hull 0.017 eV/atom, gap 2.40 eV, MD not run; reduced confidence of the window (decomposes via Na2S5, P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom)
21. it2-c4 Li12Mg(P3S11)2: E_hull per substitution 0.453 eV, E_hull 0.022 eV/atom, gap 2.35 eV, MD not run; reduced confidence (E_hull via P2S7); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.507 eV/atom)

## Novelty check (literature, web search)

Search date: 2026-10-29. Links come only from the API (its citations, or the relevant search results it returned when it gave no citation). "No publication found in this search" does not mean the material was never reported.

### control-LGPS Li10GeP2S12 (control, expected: already published): already published

Li10GeP2S12 is reported as a lithium superionic conductor with a new three-dimensional framework structure in Nature Materials 10, 682–686 (2011). Single-crystal X-ray work describes tetragonal Li10GeP2S12 as the best solid Li ion conductor known, with structure previously determined from powder diffraction. It is widely available as LGPS powder solid-state electrolyte with very high Li+ ionic conductivity for lithium-ion battery research.

Sources:
- [Synthesis and detailed electrochemical analysis of sulfide-based solid electrolyte with practical level ionic conductivity via liquid phase method | TUT Research](http://www.tut.ac.jp/english/newsletter/contents/2025/36/research/research03.html)
- [Solid Electrolytes for Lithium Ion Batteries](https://www.msesupplies.com/blogs/news/77251268-solid-electrolytes-for-lithium-ion-batteries)
- [A new solid polymer electrolyte incorporating Li>10>GeP>2>S>12> into a polyethylene oxide matrix for all-solid-state lithium batteries
      -  Beijing Institute of Technology](http://pure.bit.edu.cn/en/publications/a-new-solid-polymer-electrolyte-incorporating-lisub10subgepsub2su/)
- [Single-crystal X-ray structure analysis of the superionic conductor Li10GeP2S12† | Physical Chemistry Chemical Physics | The Royal Society of Chemistry](http://pubs.rsc.org/en/Content/ArticleLanding/2013/CP/C3CP51985F)
- [Li10GeP2S12 solid electrolytes synthesised via liquid-phase methods - Chemical Communications (RSC Publishing)](https://pubs.rsc.org/en/Content/ArticleHtml/2023/CC/d3cc01018j)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_1 web searches, 11 sources considered, ~$0.0109, 2026-10-29_

### s1:it1-c2 Li6P2SeS7: close family already studied

Se has been introduced as an anion dopant for the Li7P3S11-type sulfide electrolyte to enhance conductivity and moisture stability, and SnSe2-doped 70Li2S-(30-x)P2S5-xSnSe2 glass-ceramic electrolytes based on Li7P3S11 have been prepared by ball-milling and annealing. In the Li-P-Se system, Li7PSe6 has been successfully synthesized in the argyrodite structure, while “Li3PSe4” was noted as unconfirmed experimentally. A computational review notes Li4P2Se6 and Li7PSe6 as reported phases and describes Li4PSe3 constructed by replacing S in Li3PS4 with Se. This search found no exact Li6P2SeS7 report.

Sources:
- [TW201336147A - Sulfide-based solid electrolyte](https://patents.google.com/patent/TW201336147A/en)
- [JP2022515440A - 
        High energy density molten lithium-sulfur and lithium-selenium batteries with solid electrolytes
       
        - Google Patents](https://patents.google.com/patent/JP2022515440A/en)
- [Solid-state battery electrolyte makes a fast lithium-ion conductor](https://physicsworld.com/a/solid-state-battery-electrolyte-makes-a-fast-lithium-ion-conductor/)
- [US20230022865A1 - Solid electrolyte interphase in li secondary batteries](https://patents.google.com/patent/US20230022865A1/en)
- [Lithium-Ion Battery Electrolytes: Simulations Show About 40% of Li+ Ions Form Multi-Ion Clusters](https://xenospectrum.com/en/lithium-ion-clusters-battery-electrolyte-nature/)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_7 web searches, 74 sources considered, ~$0.0720, 2026-10-29_

### s9:it1-c4 Li7P3SeS10: close family already studied

This search found no exact Li7P3SeS10 entry, but found Se-containing modification of the same Li7P3S11 parent by SnSe2 doping. The SnSe2-doping study reports improved ionic conductivity and air stability of Li7P3S11, with SnSe doping enhancing chemical stability. All-solid-state batteries based on the resulting LiPSnSSe electrolyte demonstrate enhanced rate capability and cycling stability. A related listing also cites a Bi2Se3 co-doping route to Se-containing sulfide electrolytes in the same Li-P-S family.

Sources:
- [CN114447423B - Sulfide solid electrolyte with lithium supplementing and moisture absorbing effects](https://patents.google.com/patent/CN114447423B/en)
- [TW201336147A - Sulfide-based solid electrolyte](https://patents.google.com/patent/TW201336147A/en)
- [CN105210154A - Crystalline solid electrolyte and production method therefor 
        - Google Patents](https://patents.google.com/patent/CN105210154A/en)
- [MoO2‑Doped Li7P3S11 for High-Performance
All-Solid-State Lithium Batteries | ACS Omega | ACS Publications](https://pubs.acs.org/doi/full/10.1021/acsomega.5c10706)
- [Improved ionic conductivity and air stability of Li7P3S11 by SnSe2 doping and two-step pressing sintering method,Electrochimica Acta - X](https://www.x-mol.com/paper/1826835894267092992)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_7 web searches, 67 sources considered, ~$0.0602, 2026-10-29_

### s9:it2-c5 Li11P4S15I: close family already studied

This search found no exact hit for Li11P4S15I, but iodine-doped Li3PS4 / LiI–Li3PS4 amorphous electrolytes are widely reported with about 1.2 mS cm-1 at 25°C. The same parent-doping family includes crystalline iodine thiophosphates such as Li7P2S8I, reported to retain good stability against Li metal with conductivity 6.3×10-4 S cm-1. A closely related composition Li6P2S8I solid electrolyte with excellent ionic conductivity is also patented for all-solid lithium batteries. LiI addition to Li2S–P2S5 / Li3PS4 is therefore an established dopant family, differing only in I concentration and stoichiometry from the queried phase.

Sources:
- [The Electrochemical Characteristics and Applicability of an Amorphous Sulfide-Based Solid Ion Conductor for the Next-Generation Solid-State Lithium Secondary Batteries](https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2016.00018/full)
- [KR102381363B1 - Li6P2S8I SOLID ELECTROLYTE AND LITHIUM ION BATTERY INCLUDING THE SAME          - Google Patents](https://patents.google.com/patent/KR102381363B1/en)

_6 web searches, 41 sources considered, ~$0.0590, 2026-10-29_

Total: 0 calls, ~$0.0000.


Model ranking (last analysis): ['it2-c3', 'it2-c2', 'it2-c1', 'it2-c4']

## Usage

- meta: 5 calls, 41965 in / 14038 out tokens, ~$0.1121
- novelty web search: 0 calls, ~$0.0000
- molecular dynamics: 0 new runs of 16 on Modal A10G, estimate 0.00 $
- UMA relaxations: 155 new / 160 allowed
- events: 112; duration 27.2 min