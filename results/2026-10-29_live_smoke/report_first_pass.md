# AutoLab loop report

**Domain.** electrolyte. **Goal.** Try Br and I for S in Li7P3S11 with Li vacancies, and compare with the Li3PS4 analogues

**Parents.** Li3PS4 mp-985583 (Li12P4S16, 32 atoms); Li7P3S11 mp-641703 (Li14P6S22, 42 atoms)
**Settings.** 1 iterations max, 3 candidates max, 60 new UMA relaxations max; brain meta, fallback baseten.
**Stop reason.** iterations done

## Iteration 1

**Hypothesis.** Single Br/I for S with Li vacancy is stable in both hosts and higher doping reveals host-dependent halogen solubility.

_meta, 1 attempt(s), 7226 in / 3986 out tokens, ~$0.0260, 16.8 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-641703 | S->Br x1, -1 Li | Direct Br analogue to passed Li7P3S11 Cl/I and Li3PS4 Br to complete halide size trend. |
| it1-c2 | mp-641703 | S->I x2, -2 Li | Tests higher I doping in Li7P3S11 versus the passed single-I with low E_hull. |
| it1-c3 | mp-985583 | S->Br x2, -2 Li | Li3PS4 higher-Br analogue to compare Br solubility against Li7P3S11 at same doping. |

<details><summary>Reasoning summary (proposals)</summary>

Generating three new chemically diverse S→Br and S→I substitutions with Li vacancies for Li7P3S11 and Li3PS4 while avoiding prior substitutions.

Extending the substitution set with new S→Br and S→I variants that include Li vacancies.

Selecting three new compositions to fill the missing Br analogue and higher-doping comparisons while avoiding known entries.

Finalizing three Li7P3S11 Br and I substitutions with varying Li vacancy counts for concentration comparison.

Finalizing three new substitution proposals to cover Br and I doping across both hosts with varied vacancy counts.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it1-c1 | Li13P6S21Br | 8/8 | 15.8 | 0.026 | 0.529 | 2.38 / 2.89 | no | — | passed |
| it1-c2 | Li6P3S10I | 8/8 | 24.3 | 0.041 | 0.413 | 2.19 / 2.94 | no | — | passed |
| it1-c3 | Li5P2S7Br | 8/8 | 30.1 | 0.044 | 0.334 | 2.61 / 3.30 | no | — | passed |
- it1-c1 decomposes into: Li3PS4 0.78, P2S5 0.17, LiBr 0.05
- it1-c2 decomposes into: Li3PS4 0.67, P2S5 0.23, LiI 0.10
- it1-c3 decomposes into: Li3PS4 0.71, P2S5 0.16, LiBr 0.13

<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (s1:it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2SeS7 (s1:it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c2)
- **same substitution, different parents**, Li->Na x2 on mp-641703 vs mp-985583: E_hull per atom: NaLi5(PS4)2 (ref:it1-c5) 0.003 < NaLi6P3S11 (s9:it1-c5) 0.017 eV/atom (better: ref:it1-c5); E_hull per substitution: NaLi5(PS4)2 (ref:it1-c5) 0.055 < NaLi6P3S11 (s9:it1-c5) 0.347 eV per modified site (better: ref:it1-c5); band gap optB88: NaLi5(PS4)2 (ref:it1-c5) 2.699 > NaLi6P3S11 (s9:it1-c5) 2.397 eV (better: ref:it1-c5)
- **same substitution, different parents**, P->As x2 on mp-641703 vs mp-985583: E_hull per atom: Li6AsPS8 (ref:it2-c3) -0.010 < Li7AsP2S11 (s9:it2-c2) 0.024 eV/atom (better: ref:it2-c3); E_hull per substitution: Li6AsPS8 (ref:it2-c3) -0.153 < Li7AsP2S11 (s9:it2-c2) 0.503 eV per modified site (better: ref:it2-c3); band gap optB88: Li6AsPS8 (ref:it2-c3) 2.374 > Li7AsP2S11 (s9:it2-c2) 2.200 eV (better: ref:it2-c3)
- **same substitution, different parents**, P->Sb x1 on mp-641703 vs mp-985583: E_hull per atom: Li12SbP3S16 (ref:it2-c1) 0.013 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: ref:it2-c1); E_hull per substitution: Li12SbP3S16 (ref:it2-c1) 0.412 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: ref:it2-c1); band gap optB88: Li12SbP3S16 (ref:it2-c1) 2.457 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: ref:it2-c1)
- **same substitution, different parents**, S->I x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li13P6S21I (ref:it1-c2) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (ref:it1-c2) 0.489 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15I (s9:it2-c5) 2.522 > Li13P6S21I (ref:it1-c2) 2.397 eV (better: s9:it2-c5)
- **same substitution, different parents**, S->Br x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li13P6S21Br (it1-c1) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li13P6S21Br (it1-c1) 0.529 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li13P6S21Br (it1-c1) 2.382 eV (better: s1:it1-c1)
- **same substitution, different parents**, Li->Mg x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li10Mg(PS4)4 (ref:it1-c4) 0.007 < Li12Mg(P3S11)2 (ref:it2-c4) 0.022 eV/atom (better: ref:it1-c4); E_hull per substitution: Li10Mg(PS4)4 (ref:it1-c4) 0.102 < Li12Mg(P3S11)2 (ref:it2-c4) 0.453 eV per modified site (better: ref:it1-c4); band gap optB88: Li10Mg(PS4)4 (ref:it1-c4) 2.610 > Li12Mg(P3S11)2 (ref:it2-c4) 2.355 eV (better: ref:it1-c4)
- **same parent, different added element**, on mp-985583: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15Cl (s9:it1-c1) 2.669 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Br (s1:it1-c1) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Br (s1:it1-c1) 0.367 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s1:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->Br vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->O vs S->Se (x2, 0 Li vacancies): E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li6P2S7O (s9:it1-c2) 0.024 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li6P2S7O (s9:it1-c2) 0.384 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li6P2SeS7 (s1:it1-c2) 2.485 eV (better: s9:it1-c2)
- **same parent, different added element**, on mp-641703: S->Se vs S->O (x2, 0 Li vacancies): E_hull per atom: Li7P3SeS10 (s9:it1-c4) 0.015 < Li7P3S10O (s1:it1-c3) 0.024 eV/atom (better: s9:it1-c4); E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c4); band gap optB88: Li7P3S10O (s1:it1-c3) 2.560 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c3)
- **same parent, different added element**, on mp-641703: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (ref:it1-c2) 0.024 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: ref:it1-c2); E_hull per substitution: Li13P6S21I (ref:it1-c2) 0.489 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: ref:it1-c2); band gap optB88: Li13P6S21I (ref:it1-c2) 2.397 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: ref:it1-c2)
- **same parent, different added element**, on mp-641703: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li13P6S21Br (it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: it1-c1); E_hull per substitution: Li13P6S21Br (it1-c1) 0.529 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: it1-c1); band gap optB88: Li13P6S21Br (it1-c1) 2.382 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: it1-c1)
- **same parent, different added element**, on mp-641703: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (ref:it1-c2) 0.024 < Li13P6S21Br (it1-c1) 0.026 eV/atom (better: ref:it1-c2); E_hull per substitution: Li13P6S21I (ref:it1-c2) 0.489 < Li13P6S21Br (it1-c1) 0.529 eV per modified site (better: ref:it1-c2); band gap optB88: Li13P6S21I (ref:it1-c2) 2.397 > Li13P6S21Br (it1-c1) 2.382 eV (better: ref:it1-c2)
- **same parent, different added element**, on mp-985583: P->As vs P->Sb (x1, 0 Li vacancies): E_hull per atom: Li12AsP3S16 (ref:it1-c3) -0.005 < Li12SbP3S16 (ref:it2-c1) 0.013 eV/atom (better: ref:it1-c3); E_hull per substitution: Li12AsP3S16 (ref:it1-c3) -0.154 < Li12SbP3S16 (ref:it2-c1) 0.412 eV per modified site (better: ref:it1-c3); band gap optB88: Li12AsP3S16 (ref:it1-c3) 2.542 > Li12SbP3S16 (ref:it2-c1) 2.457 eV (better: ref:it1-c3)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): ref:it2-c3 -0.010, s1:it1-c2 -0.007, ref:it1-c3 -0.005, ref:it2-c2 -0.004, s9:it2-c4 0.003, ref:it1-c5 0.003, ref:it1-c4 0.007, ref:it2-c1 0.013, s9:it2-c5 0.023, s1:it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026, ref:it1-c1 0.030, it1-c3 0.044; E_hull per substitution (lowest first): ref:it1-c3 -0.154, ref:it2-c3 -0.153, s1:it1-c2 -0.115, ref:it2-c2 -0.113, ref:it1-c5 0.055, s9:it2-c4 0.089, ref:it1-c4 0.102, it1-c3 0.334, s9:it2-c5 0.362, s1:it1-c1 0.367, s9:it1-c2 0.384, s9:it1-c1 0.399, ref:it2-c1 0.412, ref:it1-c1 0.460; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, ref:it1-c5 2.699, ref:it1-c1 2.678, s9:it1-c1 2.669, s1:it1-c1 2.660, ref:it1-c4 2.610, it1-c3 2.608, ref:it2-c2 2.594, ref:it1-c3 2.542, s9:it2-c5 2.522, s1:it1-c2 2.485, ref:it2-c1 2.457, ref:it2-c3 2.374
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): s9:it1-c4 0.015, s9:it1-c5 0.017, ref:it2-c4 0.022, ref:it1-c2 0.024, s9:it2-c2 0.024, s1:it1-c3 0.024, it1-c1 0.026, s9:it2-c1 0.030, s9:it2-c3 0.033, it1-c2 0.041; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, it1-c2 0.413, ref:it2-c4 0.453, ref:it1-c2 0.489, s9:it2-c2 0.503, s1:it1-c3 0.510, it1-c1 0.529, s9:it2-c1 0.618, s9:it2-c3 1.381; band gap optB88 (highest first): s1:it1-c3 2.560, s9:it1-c5 2.397, ref:it1-c2 2.397, it1-c1 2.382, s9:it1-c4 2.355, ref:it2-c4 2.355, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200, it1-c2 2.189

</details>

**Analysis.** ranking ['it1-c3', 'it1-c2', 'it1-c1']; stop=False

- S->Br x1 with Li vacancy favors Li3PS4 over Li7P3S11 (0.367 < 0.529 eV per modified site, better: s1:it1-c1).
- S->I x1 with Li vacancy favors Li3PS4 over Li7P3S11 (0.362 < 0.489 eV per modified site, better: s9:it2-c5).

**Next direction.** Test S->I x2 with 2 Li vacancies on Li3PS4 to complete the Br/I host comparison.

_meta, 1 attempt(s), 13600 in / 2341 out tokens, ~$0.0270, 10.7 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking three passed candidates by energy per substitution, noting it1-c3 has the lowest value and drafting lessons and next direction.

Quoting comparison numbers to draft three lessons and a next-direction sentence while keeping stop=false.

Extracting quoted comparisons to form two lessons and a next-direction sentence without adding new numbers.

</details>

**Earlier runs.** 23 candidates given to the model and to the stages: s9:it1-c1, s9:it1-c2, s9:it1-c3, s9:it1-c4, s9:it1-c5, s9:it2-c1, s9:it2-c2, s9:it2-c3, s9:it2-c4, s9:it2-c5, s1:it1-c1, s1:it1-c2, s1:it1-c3, ref:it1-c1, ref:it1-c2, ref:it1-c3, ref:it1-c4, ref:it1-c5, ref:it2-c1, ref:it2-c2, ref:it2-c3, ref:it2-c4, ref:it2-c5.

## Electrodes (UMA + MP2020 energies)

- Calibration Li3PS4 / LiFePO4: UMA -0.144 vs MP -0.133 eV/atom (diff -0.011, tolerance 0.05) → trusted

| Candidate | Formula | Window (V) | Against Li metal | Worst reaction with LiFePO4 (eV/atom) | Confidence | Decision |
|---|---|---|---|---|---|---|
| ref:it1-c3 | Li12AsP3S16 | 2.08–2.26 | passivating (2.358) | -0.152 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c3 | Li6AsPS8 | 2.08–2.26 | passivating (2.414) | -0.161 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c2 | Li6P2SeS7 | 1.80–2.24 | passivating (2.309) | -0.145 | reduced (electrolyte decomposes via SeS7); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c2 | Li12P4SeS15 | 1.80–2.24 | passivating (2.306) | -0.145 | reduced (electrolyte decomposes via SeS7); cathode reaction forms FeS2 (information) | kept |
| ref:it1-c5 | NaLi5(PS4)2 | 1.94–2.26 | non_passivating (2.112) | — | reduced (electrolyte decomposes via Na2S5) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.112 eV/atom) |
| s9:it2-c4 | NaLi11(PS4)4 | 1.94–2.26 | non_passivating (2.204) | — | reduced (electrolyte decomposes via Na2S5) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom) |
| ref:it1-c4 | Li10Mg(PS4)4 | zero width (not a rejection) | non_passivating (2.287) | — | reduced (electrolyte decomposes via P2S7) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.287 eV/atom) |
| s9:it1-c4 | Li7P3SeS10 | 2.28–2.30 | passivating (2.529) | -0.143 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| it1-c3 | Li5P2S7Br | 2.28–2.30 | passivating (2.428) | -0.131 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c5 | NaLi6P3S11 | 2.26–2.34 | non_passivating (2.365) | — | reduced (electrolyte decomposes via Na2S5, P2S7) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom) |
| s9:it2-c5 | Li11P4S15I | 2.28–2.30 | passivating (2.368) | -0.139 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c1 | Li11P4S15Br | 2.28–2.30 | passivating (2.368) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c2 | Li6P2S7O | 1.74–2.36 | passivating (2.197) | -0.138 | reduced (electrolyte decomposes via LiS4, P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c1 | Li11P4S15Cl | 2.28–2.30 | passivating (2.372) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c1 | Li12SbP3S16 | 2.00–2.30 | passivating (2.353) | -0.151 | reduced (electrolyte decomposes via LiS4); cathode reaction forms FeS2 (information) | kept |
| it1-c2 | Li6P3S10I | 2.28–2.30 | passivating (2.609) | -0.132 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c4 | Li12Mg(P3S11)2 | zero width (not a rejection) | non_passivating (2.507) | — | reduced (electrolyte decomposes via P2S7) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.507 eV/atom) |
| ref:it1-c1 | Li11P4S15F | 2.28–2.30 | passivating (2.378) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| ref:it1-c2 | Li13P6S21I | 2.28–2.30 | passivating (2.564) | -0.136 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c2 | Li7AsP2S11 | zero width (not a rejection) | passivating (2.598) | -0.149 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |

Reduced confidence: the decomposition of the electrolyte (window limits, Li metal) goes through a polysulfide, where UMA is least reliable. Interfaces are informative (no threshold); a polysulfide formed with the cathode (FeS2 for almost every sulfide against LiFePO4) is shown as information only.

## Candidate analyses (Muse Spark Open, in parallel)

**ref:it1-c3 Li12AsP3S16** (MD priority: low): Li12AsP3S16 is stable and passivating with good gap but off-goal As chemistry with polysulfide uncertainty and narrow 2.08 to 2.26 V window limits diffusion learning for Br/I vacancy strategy.
- strength: E_hull -0.004814 eV/atom and E_hull per substitution -0.154 eV per modified site pass the filter and is lowest per substitution on mp-985583.
- strength: Band gap optB88 2.542 eV with ss_bonds false meets insulation criteria.
- strength: Rated passivating against Li metal with window stable true from 2.08 to 2.26 V and passivation reaction energy 2.358006 eV/atom.
- risk: reduced_confidence true as E_hull goes through polysulfide LiS4 and electrodes_reduced_confidence true via AsS2 and LiS4 where UMA is least reliable.
- risk: Interface reaction energy -0.152231 eV/atom with LiFePO4 indicates cathode reactivity near bottom of mp-985583 ranking.
- risk: P->As with 0 Li vacancies is off-target for Br/I for S with Li vacancies goal and brings As toxicity and sulfide moisture sensitivity.

**ref:it2-c3 Li6AsPS8** (MD priority: low): Li6AsPS8 is the most stable As-variant on Li3PS4 with a stable window and Li passivation, but off-goal chemistry, poorest cathode interface on its parent and polysulfide-reduced confidence limit its priority for Br/I diffusion work.
- strength: E_hull -0.009578 eV/atom is the lowest on mp-985583 and per comparison better than Li7AsP2S11 at 0.024 eV/atom.
- strength: Has a stable window from v_low 2.08 V to v_high 2.26 V and is passivating against Li metal with passivation_reaction_energy 2.413547 eV/atom.
- strength: Shows no S-S bonds (ss_bonds false) and gap_optb88 2.374 eV.
- risk: Reduced confidence true because E_hull goes through LiS4 and window goes through AsS2 and LiS4 where UMA is least reliable.
- risk: Interface reaction energy -0.160895 eV/atom is the lowest (worst) among mp-985583 variants in ranking.
- risk: As substitution does not address the goal of Br and I for S with Li vacancies and brings As toxicity/cost.

**s1:it1-c2 Li6P2SeS7** (MD priority: low): Stable passivating Li6P2SeS7 Li3PS4 analogue is off-target for Br/I vacancy goal and has narrow window, so Li-diffusion MD is low priority as baseline only.
- strength: E_hull -0.007 eV/atom and -0.115 eV per modified site ranks second lowest on mp-985583, with reduced_confidence false and no S-S bonds.
- strength: Passivating against Li metal with stable window 1.8 to 2.24 V and gap_optb88 2.485 eV.
- strength: Better stability than Li7P3SeS10 analogue on same S->Se x2 (E_hull -0.007 < 0.015 eV/atom per comparison), providing useful Li3PS4 baseline.
- risk: Off-goal chemistry: S->Se with 0 Li vacancies does not test requested Br/I for S with Li vacancies in Li7P3S11.
- risk: Narrow window 1.8-2.24 V with electrodes_reduced_confidence true via SeS7 polysulfide reduces confidence in electrochemical stability.
- risk: Interface reaction energy -0.145 eV/atom with LiFePO4 and selenide moisture sensitivity suggest interfacial and handling risks.

**ref:it2-c2 Li12P4SeS15** (MD priority: low): Se-substituted Li3PS4 with no vacancies is thermodynamically stable and passivating but off-target from the Br/I + Li-vacancy Li7P3S11 goal, so Li-diffusion simulation would teach little about the intended vacancy-halogen mechanism.
- strength: E_hull of -0.00353 eV/atom and E_hull per substitution of -0.113 eV with reduced_confidence false and no polysulfide decomposition indicates reliable thermodynamic stability.
- strength: optB88 gap of 2.594 eV passes the >=2.0 eV filter with ss_bonds false, supporting electronic insulation.
- strength: Window stable=true from 1.8 to 2.24 V with passivating reaction against Li metal at 2.306084 eV/atom forming Li2Se.
- risk: Substitution is Se for S with 0 Li vacancies on Li3PS4 (mp-985583), not the targeted Br/I for S with Li vacancies in Li7P3S11.
- risk: Interface reaction energy of -0.144769 eV/atom with LiFePO4 and electrodes_reduced_confidence true via SeS7 indicates interfacial reactivity and low UMA reliability at the oxidation edge.
- risk: Sulfide/selenide thiophosphates are known for moisture sensitivity and Se adds cost/toxicity versus halide strategy.

**s9:it1-c4 Li7P3SeS10** (MD priority: medium): Li7P3SeS10 is the most thermodynamically stable variant on Li7P3S11 in this set and is passivating to Li, but its impractically narrow 2.28-2.3 V window and off-goal Se chemistry without Li vacancies make it a medium-priority baseline for Br/I vacancy analogues.
- strength: E_hull per atom 0.015 eV/atom (0.015388 eV/atom) meets the <=0.05 eV/atom filter and is ranked lowest first as s9:it1-c4 0.015 in the mp-641703 ranking with reduced_confidence false and ss_bonds false.
- strength: Passivating against Li metal despite window v_low 2.28 V to v_high 2.30 V stable true, with band gap optB88 2.355 eV above the filter.
- strength: E_hull per substitution 0.323 eV per modified site ranked lowest first as s9:it1-c4 0.323 in the mp-641703 ranking, lower than S->O analogue s1:it1-c3 0.510 eV per modified site
- risk: Electrochemical window v_low 2.28 V to v_high 2.3 V stable true is extremely narrow in practice, and electrodes_reduced_confidence true due to P2S7 polysulfide makes window reliability low.
- risk: Interface reaction energy with LiFePO4 is -0.14292 eV/atom indicating cathode reactivity, and substitution is S->Se x2 with li_vacancies 0 which does not address the goal of Br/I with Li vacancies.
- risk: Selenide sulfide retains moisture sensitivity and adds cost versus sulfides without introducing Li vacancies known to aid Li diffusion

**it1-c3 Li5P2S7Br** (MD priority: medium): Li5P2S7Br is a borderline-stable Br-doped Li3PS4 analogue that offers the best cathode interface stability in its group but with high substitution penalty and a very narrow electrochemical window, making Li-diffusion simulations moderately informative for halide vs oxide doping trends.
- strength: Meets screening filters with E_hull 0.044462 eV/atom, gap_optb88 2.608 eV, ss_bonds false, reduced_confidence false and passivating interface with Li metal (passivation_reaction_energy 2.427511 eV/atom).
- strength: Ranks highest on mp-985583 for worst reaction energy with LiFePO4 cathode at -0.131239 eV/atom (better than s9:it1-c2 -0.138 eV/atom and others to -0.161 eV/atom per ranking).
- strength: Maintains electrochemical stability as stable true albeit narrow, with window v_low 2.28 V to v_high 2.3 V.
- risk: Ranks worst on mp-985583 for E_hull per atom at 0.044462 eV/atom with E_hull per substitution 0.3335 eV per modified site, near the 0.05 eV/atom limit and far worse than 0.024 eV/atom for S->O analogues.
- risk: Narrow stable window (v_low 2.28 V, v_high 2.3 V) decomposes to Li3PS4/LiBr/P4S7 on reduction and LiBr/P2S7 on oxidation, with electrodes_reduced_confidence true due to P2S7 reducing window reliability.
- risk: Br-for-S sulfide with 2 Li vacancies implies strong moisture sensitivity/H2S risk and Li-deficiency trapping typical of halide-doped sulfides.

**s9:it2-c5 Li11P4S15I** (MD priority: high): Li11P4S15I is the most stable halogen-substituted Li3PS4 analogue in this set with Li vacancies and Li-metal passivation but has an essentially zero-width window and uncertain cathode stability, making Li-diffusion simulation highly informative for the Br/I comparison goal.
- strength: E_hull 0.023 eV/atom passes 0.05 eV/atom filter with reduced_confidence false, ss_bonds false, gap_optb88 2.522 eV and passivating vs Li metal supports synthesizability and electronic insulation.
- strength: On mp-985583 E_hull per atom 0.023 < 0.024 eV/atom vs Li11P4S15Br 0.024 eV/atom (better: s9:it2-c5) and E_hull per substitution 0.362 < 0.367 eV per modified site (better: s9:it2-c5), and 0.023 < 0.026 eV/atom vs Li11P4S15Cl 0.026 eV/atom (better: s9:it2-c5).
- strength: Same S->I x1 -1 Li on mp-985583 outperforms mp-641703 analogue with E_hull per atom 0.023 < 0.024 eV/atom (better: s9:it2-c5) and band gap optB88 2.522 > 2.397 eV (better: s9:it2-c5).
- risk: Window stable=true but only v_low 2.28 to v_high 2.3 V with reduction to Li3PS4/LiI/P4S7 and oxidation to Li3PS4/LiI/P2S7 indicates negligible practical stability window.
- risk: Electrodes_reduced_confidence true via P2S7 polysulfide reduces confidence in the window and in interface_reaction_energy -0.139 eV/atom with LiFePO4 indicating cathode reactivity.
- risk: I-substituted sulfide with Li vacancies is hygroscopic and moisture-sensitive in well-known sulfide chemistry, and iodide adds cost.

**s1:it1-c1 Li11P4S15Br** (MD priority: high): Br-doped Li3PS4 with one Li vacancy is thermodynamically accessible and Li-metal passivating with good gap but narrow window and cathode reactivity, and directly beats the Li7P3S11 Br analogue.
- strength: Passes stability filter at E_hull 0.024 eV/atom with reduced_confidence false and ss_bonds false.
- strength: OptB88 gap 2.66 eV and passivating against Li metal despite passivation reaction energy 2.368 eV/atom.
- strength: Outperforms same S->Br substitution on Li7P3S11 analogue Li13P6S21Br with E_hull per atom 0.024 < 0.026 eV/atom and gap 2.660 > 2.382 eV.
- risk: Electrochemical window is very narrow at 2.28 to 2.30 V with reduction to Li3PS4, LiBr and P4S7 and oxidation to Li3PS4, LiBr and P2S7.
- risk: Reacts with LiFePO4 cathode with interface reaction energy -0.138 eV/atom.
- risk: Window prediction has electrodes_reduced_confidence true due to P2S7 polysulfide plus inherent sulfide moisture sensitivity.

**s9:it1-c2 Li6P2S7O** (MD priority: low): O-doped Li3PS4 baseline with excellent band gap and passivation but off-target for Br/I plus vacancy strategy and with less favorable substitution energetics than Se analogue.
- strength: Passes filters with E_hull 0.024011 eV/atom, gap_optb88 2.838 eV, ss_bonds false, reduced_confidence false, window stable 1.74 to 2.36 V and passivating against Li metal.
- strength: Highest optB88 band gap on mp-985583 at 2.838 eV, better than Se analogue 2.485 eV and better than same S->O x2 on Li7P3S11 analogue 2.560 eV.
- strength: Better cathode reactivity at -0.138 eV/atom than Se analogue at -0.145 eV/atom and E_hull per substitution 0.384 eV per modified site better than Li7P3S10O analogue at 0.510 eV.
- risk: Off-target for goal of Br/I for S in Li7P3S11 with Li vacancies as it is S->O x2 with 0 Li vacancies on Li3PS4 parent mp-985583.
- risk: O incorporation cost 0.384 eV per modified site is much less favorable than Se analogue -0.115 eV and E_hull per atom 0.024 eV/atom is worse than Se analogue -0.007 eV/atom.
- risk: Window 1.74 to 2.36 V is narrow and has electrodes_reduced_confidence true due to LiS4 and P2S7, and O for S with harder anion chemistry typically risks lower Li-ion mobility.

**s9:it1-c1 Li11P4S15Cl** (MD priority: medium): Li11P4S15Cl is a metastable Li3PS4-derived Cl analogue with passivating Li contact and adequate band gap but its very narrow window and higher substitution energy than Br/I analogues make it a modest-priority MD case for the Li7P3S11 Br/I objective.
- strength: E_hull per atom 0.026 eV/atom passes the <=0.05 eV/atom filter with reduced_confidence false and ss_bonds false.
- strength: Band gap optB88 2.669 eV meets >=2.0 eV filter and is higher than Li13P6S21Cl (s9:it2-c1) 2.250 eV per comparison.
- strength: Passivation against Li metal is passivating with passivation_reaction_energy 2.37156 eV/atom indicating possible kinetic stabilization.
- risk: Electrochemical window is only v_low 2.28 V to v_high 2.30 V and has electrodes_reduced_confidence true due to polysulfide P2S7.
- risk: E_hull per substitution 0.399 eV per modified site is higher than Li11P4S15Br 0.367 and Li11P4S15I 0.362 on same parent mp-985583 per comparisons.
- risk: Sulfide-chloride with Li vacancies is typically moisture-sensitive and as a Cl/Li3PS4 analogue it is off-target for the stated Br/I in Li7P3S11 goal.

**ref:it2-c1 Li12SbP3S16** (MD priority: low): Metastable Li3PS4-derived Sb analogue is insulating and passivating but narrow-window, poorly ranked versus As analogue, and off-target for the Br/I plus vacancy goal so MD is low priority.
- strength: E_hull 0.012872 eV/atom with ss_bonds false and reduced_confidence false passes stability filters reliably.
- strength: gap_optb88 2.457 eV exceeds 2.0 eV threshold and passivation is passivating against Li metal.
- strength: E_hull per atom 0.013 < 0.033 eV/atom and gap 2.457 > 2.231 eV versus Li14SbP5S22 (s9:it2-c3) shows best host for P->Sb x1.
- risk: Window v_low 2.0 V to v_high 2.3 V does not extend to Li-metal potential and electrodes_reduced_confidence true due to LiS4 makes window uncertain.
- risk: E_hull per substitution 0.412 eV per modified site and interface_reaction_energy -0.150597 eV/atom rank near worst on mp-985583 behind Li12AsP3S16 at -0.005 eV/atom and -0.154 eV per site.
- risk: No Li vacancies and P->Sb substitution does not test the requested Br/I for S in Li7P3S11 with Li vacancies and retains sulfide moisture sensitivity and Sb handling concerns.

**it1-c2 Li6P3S10I** (MD priority: medium): Li6P3S10I tests double I plus 2 Li vacancies on Li7P3S11 with best cathode interface on parent but narrow window and high substitution cost limit priority.
- strength: E_hull 0.041313 eV/atom within 0.05 eV/atom filter with reduced_confidence false and ss_bonds false.
- strength: Passivating against Li metal with interface_reaction_energy -0.132102 eV/atom ranked highest on mp-641703 as it1-c2 -0.132 eV/atom.
- strength: Realizes goal S->I x2 with 2 Li vacancies on Li7P3S11 parent Li6P3S10I for direct comparison to Li3PS4 analogues.
- risk: E_hull_per_substitution 0.4131 eV per site is high, ranking second on mp-641703 behind s9:it1-c4 0.323 eV per modified site.
- risk: Window v_low 2.28 V to v_high 2.3 V stable true is very narrow with oxidation to LiI, P2S5, P2S7 and reduction to Li3PS4, LiI, P4S7.
- risk: Electrodes_reduced_confidence true via P2S7 polysulfide where UMA is least reliable and gap_optb88 2.189 eV is lowest on mp-641703.

**ref:it1-c1 Li11P4S15F** (MD priority: low): Li11P4S15F is a metastable Li3PS4-derived fluoride with good electronic insulation and Li-metal passivation but is the least thermodynamically favored among Br/Cl/I analogues with a very narrow stable window, making it low priority for diffusion studies versus Br/I targets.
- strength: Passivating against Li metal with no S-S bonds and band gap optB88 2.678 eV above the 2.0 eV filter.
- strength: E_hull 0.02965 eV/atom is within 0.05 eV/atom with reduced_confidence false and stable window v_low 2.28 V to v_high 2.3 V.
- risk: E_hull per substitution 0.460 eV per modified site is worst among Li3PS4 S->halogen (x1) candidates, higher than Li11P4S15I 0.362 and Li11P4S15Br 0.367.
- risk: Narrow window v_low 2.28 V to v_high 2.3 V with electrodes_reduced_confidence true due to P2S7 and interface reaction energy -0.138 eV/atom indicates limited electrochemical stability.
- risk: Sulfide chemistry implies moisture sensitivity and potential HF release for the F-substituted composition with Li vacancies.

**ref:it1-c2 Li13P6S21I** (MD priority: medium): Li13P6S21I is the best I-doped Li7P3S11 vacancy candidate versus Br/Cl but its very narrow polysulfide-uncertain window and cathode reactivity make diffusion simulation useful mainly to compare halogen size and parent effects versus Li3PS4 analogues.
- strength: E_hull per atom 0.023844 eV/atom with reduced_confidence false and ss_bonds false passes the 0.05 eV/atom filter as a metastable sulfide.
- strength: Band gap optB88 2.397 eV passes the 2.0 eV filter and is higher than the Br analogue 2.382 eV and Cl analogue 2.250 eV on the same mp-641703 parent.
- strength: Passivating against Li metal despite sulfide chemistry, with 1 Li vacancy per I substitution enabling vacancy-mediated transport study.
- risk: Electrochemical window v_low 2.28 V to v_high 2.3 V is extremely narrow and has electrodes_reduced_confidence true due to P2S7, so stability is uncertain.
- risk: Interface reaction energy -0.136 eV/atom with LiFePO4 indicates thermodynamic driving force for cathode reaction.
- risk: Sulfide-iodide with Li vacancies implies moisture sensitivity and H2S risk, plus iodide hygroscopicity and cost.

**s9:it2-c2 Li7AsP2S11** (MD priority: low): Li7AsP2S11 is metastable by the filter and passivating to Li but has zero window, polysulfide reduced confidence, and tests P->As rather than the targeted Br/I-with-vacancy strategy, giving low value for Li-diffusion MD.
- strength: E_hull per atom 0.02395 eV/atom passes the <=0.05 eV/atom filter for metastability.
- strength: Passivation against Li metal is passivating and ss_bonds is false with gap_optb88 2.2 eV meeting the >=2.0 eV screen.
- strength: Interface reaction energy -0.149435 eV/atom with LiFePO4 is quoted as -0.149 eV/atom in comparisons, better than Li6AsPS8 at -0.161 eV/atom.
- risk: reduced_confidence is true as E_hull goes through AsS2 and LiS4 polysulfides and electrodes_reduced_confidence is true.
- risk: Electrochemical window is stable=false with v_low null and v_high null, indicating zero width at calculation precision.
- risk: Substitution P->As x2 with 0 Li vacancies does not test the requested Br/I for S with Li vacancies and E_hull per substitution 0.503 eV per modified site is quoted as worse than Li6AsPS8 at -0.153 eV per modified site, with added As toxicity.

**s1:it1-c3 Li7P3S10O** (MD priority: low): Metastable Li7P3S10O meets hull/gap filters but is S->O with no vacancies, not the requested Br/I+vacancy chemistry, and is less favorable per-site than Se and Li3PS4 analogues so MD would not advance the goal.
- strength: E_hull per atom 0.02428 eV/atom passes the 0.05 eV/atom filter with reduced_confidence false and ss_bonds false
- strength: gap_optb88 2.56 eV passes the 2.0 eV filter and band gap optB88 (highest first): s1:it1-c3 2.560 on mp-641703 per ranking
- strength: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom per same-substitution comparison
- risk: Does not address goal: substitution is S->O x2 with li_vacancies 0, not Br/I for S with Li vacancies, and has no comparison to Li3PS4 Br/I analogues
- risk: E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c4) and Li6P2S7O 0.384 < Li7P3S10O 0.510 eV per modified site (better: s9:it1-c2)
- risk: O is a harder anion than Br/I and with 0 vacancies provides no test of soft-lattice/vacancy-assisted Li transport sought in goal

**it1-c1 Li13P6S21Br** (MD priority: low): Br+vacancy in Li7P3S11 is viable but is dominated by the Li3PS4 Br analogue and by the I analogue on the same parent, so diffusion simulation teaches less than those higher-ranked candidates.
- strength: Passes stability filter with E_hull 0.025825 eV/atom, reduced_confidence false and no S-S bonds (ss_bonds false).
- strength: Electronic insulation retained with gap_optb88 2.382 eV above 2.0 eV threshold.
- strength: On Li7P3S11 parent S->Br outperforms S->Cl with E_hull per atom 0.026 vs 0.030 eV/atom and gap_optb88 2.382 vs 2.250 eV.
- risk: Same S->Br substitution in Li3PS4 analogue Li11P4S15Br is more stable with E_hull per atom 0.024 vs 0.026 eV/atom and per substitution 0.367 vs 0.529 eV per modified site and higher gap 2.660 vs 2.382 eV.
- risk: On same Li7P3S11 parent the I analogue Li13P6S21I is slightly better with E_hull per atom 0.024 vs 0.026 eV/atom and gap_optb88 2.397 vs 2.382 eV.
- risk: Li-vacancy sulfide with Br retains typical moisture sensitivity and H2S risk of sulfides.

**s9:it2-c1 Li13P6S21Cl** (MD priority: low): Li13P6S21Cl is a metastable Cl-doped Li7P3S11 analogue with Li vacancy that passes filters but is outperformed by the requested Br/I analogues and by the Li3PS4 analogue, making Li-diffusion simulation low priority versus those candidates.
- strength: Passes metastability filter with E_hull 0.030159 eV/atom and reduced_confidence false with no polysulfide decomposition products.
- strength: Electronically insulating by optB88 gap 2.25 eV and ss_bonds false, supporting use as solid electrolyte baseline.
- risk: On same parent mp-641703, S->I (0.024 eV/atom, 0.489 eV per modified site, 2.397 eV gap) and S->Br (0.026 eV/atom, 0.529 eV per modified site, 2.382 eV gap) are both listed as better than S->Cl Li13P6S21Cl (0.030 eV/atom, 0.618 eV per modified site, 2.250 eV gap), so Cl is not the Br/I target of the goal.
- risk: Same S->Cl x1 with 1 Li vacancy is better on Li3PS4-derived Li11P4S15Cl (0.026 eV/atom, 0.399 eV per modified site, 2.669 eV gap) than on Li7P3S11-derived Li13P6S21Cl (0.030 eV/atom, 0.618 eV per modified site, 2.250 eV gap).
- risk: Ranks low on mp-641703 with E_hull per substitution 0.618 eV per modified site (7th of 8 in ranking) indicating relatively high substitution cost, and sulfide thiophosphate chemistry implies moisture sensitivity.

**s9:it2-c3 Li14SbP5S22** (MD priority: low): P-site Sb substitution without vacancies misses the requested Br/I-for-S with Li-vacancy goal and shows worst, low-confidence stability on Li7P3S11 versus its Li3PS4 analogue, so MD would teach little about target Li7P3S11 halide conductivity.
- strength: Passes nominal filters with E_hull 0.032887 eV/atom (<=0.05), gap optB88 2.231 eV (>=2.0) and ss_bonds false indicating no S-S dimerization.
- strength: Provides Sb-for-P cross-parent comparison point: Li12SbP3S16 (ref:it2-c1) 0.013 eV/atom and 0.412 eV per modified site vs Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom and 1.381 eV per modified site (better: ref:it2-c1).
- risk: Does not address the goal chemistry: P->Sb x1 with 0 Li vacancies instead of Br/I for S with Li vacancies in Li7P3S11.
- risk: Reduced confidence: E_hull 0.032887 eV/atom goes through polysulfide LiS4 where UMA is least reliable.
- risk: E_hull per substitution 1.381 eV per modified site is worst on mp-641703 ranking (lowest first: s9:it1-c4 0.323 ... s9:it2-c3 1.381), indicating poor Sb incorporation and added Sb toxicity/cost.


## Choice of the candidates for molecular dynamics

Not simulated yet (the choice): ref:it1-c3, ref:it2-c3, it1-c3, ref:it2-c1, it1-c2, ref:it1-c1, s9:it2-c2, s1:it1-c3, it1-c1, s9:it2-c3. Selected by meta: it1-c2.

Rationale: Direct goal test of S->I x2 with 2 Li vacancies on Li7P3S11 using soft I framework, ranking highest for cathode interface with it1-c2 -0.132 eV/atom.

## Li diffusion (600 K, 2 seeds of 40 ps pooled, Modal A10G)

Runs computed: 2 of 24 (others from the cache); estimate 0.66 $, about 18 min in parallel.
Not selected but already simulated (verdict from the cache, no cost): s1:it1-c2, ref:it2-c2, s9:it1-c4, s9:it2-c5, s1:it1-c1, s9:it1-c2, s9:it1-c1, ref:it1-c2, s9:it2-c1.

| Structure | Kind | D ± s.e. (cm²/s) | D / D(parent) | Verdict | Conduction | Framework |
|---|---|---|---|---|---|---|
| Li7P3S11 (mp-641703) | parent | 1.30e-05 ± 2.2e-06 | — | — | — | intact |
| Li3PS4 (mp-985583) | parent | 5.94e-06 ± 1.2e-06 | — | — | — | intact |
| Li6P3S10I (it1-c2) | candidate | 1.50e-05 ± 4.1e-06 | 1.15 ± 0.37 | tied | excluded | MOVED |
| Li6P2SeS7 (s1:it1-c2) | candidate | 3.90e-06 ± 9.6e-07 | 0.66 ± 0.21 | tied | passes | intact |
| Li12P4SeS15 (ref:it2-c2) | candidate | 4.87e-06 ± 1.1e-06 | 0.82 ± 0.25 | tied | passes | intact |
| Li7P3SeS10 (s9:it1-c4) | candidate | 1.39e-05 ± 1.8e-06 | 1.07 ± 0.23 | tied | passes | intact |
| Li11P4S15I (s9:it2-c5) | candidate | 5.34e-06 ± 1.7e-06 | 0.90 ± 0.34 | tied | passes | intact |
| Li11P4S15Br (s1:it1-c1) | candidate | 6.80e-06 ± 9.2e-07 | 1.15 ± 0.28 | tied | passes | intact |
| Li6P2S7O (s9:it1-c2) | candidate | 7.86e-06 ± 8.1e-07 | 1.32 ± 0.30 | tied | passes | intact |
| Li11P4S15Cl (s9:it1-c1) | candidate | 5.53e-06 ± 1.2e-06 | 0.93 ± 0.28 | tied | passes | intact |
| Li13P6S21I (ref:it1-c2) | candidate | 1.49e-05 ± 3.4e-06 | 1.15 ± 0.33 | tied | passes | intact |
| Li13P6S21Cl (s9:it2-c1) | candidate | 1.25e-05 ± 1.4e-06 | 0.96 ± 0.20 | tied | excluded | MOVED |

## Final ranking

Order: MD verdict (higher > tied > not_run), then lowest E_hull per substitution; excluded candidates last, with their reason. Candidates are computational predictions, not proven materials.

1. s1:it1-c2 Li6P2SeS7 **finalist**: E_hull per substitution -0.115 eV, E_hull -0.007 eV/atom, gap 2.48 eV, MD tied (D/D(parent) 0.66 ± 0.21); reduced confidence of the window (decomposes via SeS7)
2. ref:it2-c2 Li12P4SeS15 **finalist**: E_hull per substitution -0.113 eV, E_hull -0.004 eV/atom, gap 2.59 eV, MD tied (D/D(parent) 0.82 ± 0.25); reduced confidence of the window (decomposes via SeS7)
3. s9:it1-c4 Li7P3SeS10 **finalist**: E_hull per substitution 0.323 eV, E_hull 0.015 eV/atom, gap 2.35 eV, MD tied (D/D(parent) 1.07 ± 0.23); reduced confidence of the window (decomposes via P2S7)
4. s9:it2-c5 Li11P4S15I: E_hull per substitution 0.362 eV, E_hull 0.023 eV/atom, gap 2.52 eV, MD tied (D/D(parent) 0.90 ± 0.34); reduced confidence of the window (decomposes via P2S7)
5. s1:it1-c1 Li11P4S15Br: E_hull per substitution 0.367 eV, E_hull 0.024 eV/atom, gap 2.66 eV, MD tied (D/D(parent) 1.15 ± 0.28); reduced confidence of the window (decomposes via P2S7)
6. s9:it1-c2 Li6P2S7O: E_hull per substitution 0.384 eV, E_hull 0.024 eV/atom, gap 2.84 eV, MD tied (D/D(parent) 1.32 ± 0.30); reduced confidence of the window (decomposes via LiS4, P2S7)
7. s9:it1-c1 Li11P4S15Cl: E_hull per substitution 0.399 eV, E_hull 0.026 eV/atom, gap 2.67 eV, MD tied (D/D(parent) 0.93 ± 0.28); reduced confidence of the window (decomposes via P2S7)
8. ref:it1-c2 Li13P6S21I: E_hull per substitution 0.489 eV, E_hull 0.024 eV/atom, gap 2.40 eV, MD tied (D/D(parent) 1.15 ± 0.33); reduced confidence of the window (decomposes via P2S7)
9. ref:it1-c3 Li12AsP3S16: E_hull per substitution -0.154 eV, E_hull -0.005 eV/atom, gap 2.54 eV, MD not run; reduced confidence (E_hull via LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
10. ref:it2-c3 Li6AsPS8: E_hull per substitution -0.153 eV, E_hull -0.010 eV/atom, gap 2.37 eV, MD not run; reduced confidence (E_hull via LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
11. it1-c3 Li5P2S7Br: E_hull per substitution 0.334 eV, E_hull 0.044 eV/atom, gap 2.61 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
12. ref:it2-c1 Li12SbP3S16: E_hull per substitution 0.412 eV, E_hull 0.013 eV/atom, gap 2.46 eV, MD not run; reduced confidence of the window (decomposes via LiS4)
13. ref:it1-c1 Li11P4S15F: E_hull per substitution 0.460 eV, E_hull 0.030 eV/atom, gap 2.68 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
14. s9:it2-c2 Li7AsP2S11: E_hull per substitution 0.503 eV, E_hull 0.024 eV/atom, gap 2.20 eV, MD not run; reduced confidence (E_hull via AsS2, LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
15. s1:it1-c3 Li7P3S10O: E_hull per substitution 0.510 eV, E_hull 0.024 eV/atom, gap 2.56 eV, MD not run
16. it1-c1 Li13P6S21Br: E_hull per substitution 0.529 eV, E_hull 0.026 eV/atom, gap 2.38 eV, MD not run
17. s9:it2-c3 Li14SbP5S22: E_hull per substitution 1.381 eV, E_hull 0.033 eV/atom, gap 2.23 eV, MD not run; reduced confidence (E_hull via LiS4)
18. it1-c2 Li6P3S10I: E_hull per substitution 0.413 eV, E_hull 0.041 eV/atom, gap 2.19 eV, MD tied (D/D(parent) 1.15 ± 0.37); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at molecular_dynamics: framework moved: I diffuses at 5% of Li (limit 5%), seed 0, final MSD 1.0 A2
19. s9:it2-c1 Li13P6S21Cl: E_hull per substitution 0.618 eV, E_hull 0.030 eV/atom, gap 2.25 eV, MD tied (D/D(parent) 0.96 ± 0.20) — EXCLUDED at molecular_dynamics: framework moved: Cl diffuses at 40% of Li (limit 5%), seed 0, final MSD 5.4 A2
20. ref:it1-c5 NaLi5(PS4)2: E_hull per substitution 0.055 eV, E_hull 0.003 eV/atom, gap 2.70 eV, MD not run; reduced confidence of the window (decomposes via Na2S5) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.112 eV/atom)
21. s9:it2-c4 NaLi11(PS4)4: E_hull per substitution 0.089 eV, E_hull 0.003 eV/atom, gap 2.71 eV, MD not run; reduced confidence of the window (decomposes via Na2S5) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom)
22. ref:it1-c4 Li10Mg(PS4)4: E_hull per substitution 0.102 eV, E_hull 0.007 eV/atom, gap 2.61 eV, MD not run; reduced confidence (E_hull via P2S7); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.287 eV/atom)
23. s9:it1-c5 NaLi6P3S11: E_hull per substitution 0.347 eV, E_hull 0.017 eV/atom, gap 2.40 eV, MD not run; reduced confidence of the window (decomposes via Na2S5, P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom)
24. ref:it2-c4 Li12Mg(P3S11)2: E_hull per substitution 0.453 eV, E_hull 0.022 eV/atom, gap 2.35 eV, MD not run; reduced confidence (E_hull via P2S7); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.507 eV/atom)

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

### ref:it2-c2 Li12P4SeS15: close family already studied

This search did not return the exact Li12P4SeS15 composition, but a computational phase-stability study lists Li3PSe4 as a predicted stable phase derived from ICSD-Li3PS4, the full-Se analogue of Se-substituted Li3PS4. Se-for-S anion doping in the closely related thiophosphate Li7P3S11 is reported experimentally as a series Li7P3S11-xSex (x=0-0.15), with Se substitution at S sites improving conductivity and moisture stability. The same Li3PS4 parent with a chemically similar anion dopant is reported as O-doped β-Li3PS4, e.g. Li3PS3.8O0.2 with ionic conductivity 1.13 mS cm-1 and suppressed H2S generation.

Sources:
- [Computational Prediction and Evaluation of Solid-State Sodium Superionic Conductors Na7P3X11 (X = O, S, Se)](https://escholarship.org/content/qt7ck260j4/qt7ck260j4.pdf?t=pfrnwl)
- [D. Narsimulu | ScienceDirect](https://www.sciencedirect.com/author/56741441700/d-narsimulu)

_10 web searches, 68 sources considered, ~$0.1726, 2026-10-29_

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

Total: 0 calls, ~$0.0000.


Model ranking (last analysis): ['it1-c3', 'it1-c2', 'it1-c1']

## Usage

- meta: 3 calls, 32676 in / 9014 out tokens, ~$0.0791
- baseten: 0 calls, 0 in / 0 out tokens, ~$0.0000
- candidate analyses (baseten): 30 calls, ~$0.4198
- novelty web search: 0 calls, ~$0.0000
- molecular dynamics: 2 new runs of 24 on Modal A10G, estimate 0.66 $
- UMA relaxations: 24 new / 60 allowed
- events: 89; duration 29.1 min