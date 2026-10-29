# AutoLab loop report

**Domain.** electrolyte. **Goal.** Find new sulfide solid electrolytes for lithium-metal batteries: thermodynamically stable or slightly metastable, electronically insulating, by substitutions in known Li-P-S crystals.

**Parents.** Li3PS4 mp-985583 (Li12P4S16, 32 atoms); Li7P3S11 mp-641703 (Li14P6S22, 42 atoms)
**Settings.** 1 iterations max, 3 candidates max, 80 new UMA relaxations max; brain meta, fallback None.
**Stop reason.** iterations done

## Iteration 1

**Hypothesis.** Dilute anion mixing on S sites balances stability, band gap, and Li vacancies.

_meta, 1 attempt(s), 3616 in / 5382 out tokens, ~$0.0274, 24.0 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-985583 | S->Br x1, -1 Li | Br bridges Cl and I size that both passed, creating Li vacancies like argyrodites for conductivity. |
| it1-c2 | mp-985583 | S->Se x2 | Se isovalent expansion improved hull in Li7P3S11 and should soften lattice in Li3PS4. |
| it1-c3 | mp-641703 | S->O x2 | O oxysulfide mixing passed in Li3PS4 and should stabilize Li7P3S11 against Li metal. |

<details><summary>Reasoning summary (proposals)</summary>

Evaluating substitution rules and filtering criteria for solid electrolyte proposals before simulation.

Applying fixed oxidation-state constraints and charge-neutrality rules while filtering new compositions by E_hull and band gap thresholds.

Proposing three novel aliovalent substitutions with charge-neutrality constraints while avoiding evaluated patterns.

Evaluating aliovalent substitutions for charge neutrality and ruling out P→Si/Ge/Sn while considering Br and O doping.

Prioritizing Br, Se, O, and F dopants for charge-neutral substitutions and excluding P→Si/Ge/Sn.

Selecting Br, Se, and O dopants across the two parents to maximize chemical diversity and prior success.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it1-c1 | Li11P4S15Br | 7/7 | 17.0 | 0.024 | 0.367 | 2.66 / 3.27 | no | — | passed |
| it1-c2 | Li6P2SeS7 | 6/6 | 2.1 | -0.007 | -0.115 | 2.48 / 3.10 | no | — | passed |
| it1-c3 | Li7P3S10O | 8/8 | 13.3 | 0.024 | 0.510 | 2.56 / 3.02 | no | — | passed |
- it1-c1 decomposes into: Li3PS4 0.86, P2S5 0.08, LiBr 0.06
- it1-c2 decomposes into: Li3PS4 0.88, Li7PSe6 0.09, P2Se5 0.03
- it1-c3 decomposes into: Li3PS4 0.79, P2S5 0.11, Li3PO4 0.10

<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: it1-c2); E_hull per substitution: Li6P2SeS7 (it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: it1-c2); band gap optB88: Li6P2SeS7 (it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: it1-c2)
- **same parent, different added element**, on mp-985583: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (it1-c1) 0.024 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: it1-c1); E_hull per substitution: Li11P4S15Br (it1-c1) 0.367 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15Br (it1-c1) 2.660 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Br (it1-c1) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Br (it1-c1) 0.367 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Br (it1-c1) 2.660 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: it1-c1)
- **same parent, different added element**, on mp-985583: S->O vs S->Se (x2, 0 Li vacancies): E_hull per atom: Li6P2SeS7 (it1-c2) -0.007 < Li6P2S7O (s9:it1-c2) 0.024 eV/atom (better: it1-c2); E_hull per substitution: Li6P2SeS7 (it1-c2) -0.115 < Li6P2S7O (s9:it1-c2) 0.384 eV per modified site (better: it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li6P2SeS7 (it1-c2) 2.485 eV (better: s9:it1-c2)
- **same parent, different added element**, on mp-641703: S->Se vs S->O (x2, 0 Li vacancies): E_hull per atom: Li7P3SeS10 (s9:it1-c4) 0.015 < Li7P3S10O (it1-c3) 0.024 eV/atom (better: s9:it1-c4); E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (it1-c3) 0.510 eV per modified site (better: s9:it1-c4); band gap optB88: Li7P3S10O (it1-c3) 2.560 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: it1-c3)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): it1-c2 -0.007, s9:it2-c4 0.003, s9:it2-c5 0.023, it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026; E_hull per substitution (lowest first): it1-c2 -0.115, s9:it2-c4 0.089, s9:it2-c5 0.362, it1-c1 0.367, s9:it1-c2 0.384, s9:it1-c1 0.399; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, s9:it1-c1 2.669, it1-c1 2.660, s9:it2-c5 2.522, it1-c2 2.485
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): s9:it1-c4 0.015, s9:it1-c5 0.017, s9:it2-c2 0.024, it1-c3 0.024, s9:it2-c1 0.030, s9:it2-c3 0.033; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, s9:it2-c2 0.503, it1-c3 0.510, s9:it2-c1 0.618, s9:it2-c3 1.381; band gap optB88 (highest first): it1-c3 2.560, s9:it1-c5 2.397, s9:it1-c4 2.355, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200

</details>

**Analysis.** ranking ['it1-c2', 'it1-c1', 'it1-c3']; stop=False

- S->Se x2 favors mp-985583 over mp-641703 (-0.115 vs 0.323 eV per modified site).
- On mp-985583 S->Se x2 beats S->O x2 (-0.115 vs 0.384 eV per modified site).
- On mp-985583 S->Br x1 beats S->Cl x1 (0.367 vs 0.399 eV per modified site) while S->I remains best (0.362 vs 0.367 eV per modified site).

**Next direction.** Prioritize dilute Se and heavy-halide Br/I mixing on mp-985583.

_meta, 1 attempt(s), 6638 in / 2292 out tokens, ~$0.0180, 10.0 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking only candidates with status 'passed' using e_hull_per_substitution while relying on provided comparison statements and clarifying iteration scope.

Applying the e_hull_per_substitution ordering to this iteration's passed candidates while deferring to comparison statements.

Deriving a current-iteration ranking from quoted e_hull per substitution values and drafting brief lessons and next direction.

</details>

**Earlier runs.** 10 candidates given to the model and to the stages: s9:it1-c1, s9:it1-c2, s9:it1-c3, s9:it1-c4, s9:it1-c5, s9:it2-c1, s9:it2-c2, s9:it2-c3, s9:it2-c4, s9:it2-c5.

## Electrodes (UMA + MP2020 energies)

- Calibration Li3PS4 / LiFePO4: UMA -0.144 vs MP -0.133 eV/atom (diff -0.011, tolerance 0.05) → trusted

| Candidate | Formula | Window (V) | Against Li metal | Worst reaction with LiFePO4 (eV/atom) | Confidence | Decision |
|---|---|---|---|---|---|---|
| it1-c2 | Li6P2SeS7 | 1.80–2.24 | passivating (2.309) | -0.145 | reduced (electrolyte decomposes via SeS7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c4 | NaLi11(PS4)4 | 1.94–2.26 | non_passivating (2.204) | — | reduced (electrolyte decomposes via Na2S5) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom) |
| s9:it1-c4 | Li7P3SeS10 | 2.28–2.30 | passivating (2.529) | -0.143 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c5 | NaLi6P3S11 | 2.26–2.34 | non_passivating (2.365) | — | reduced (electrolyte decomposes via Na2S5, P2S7) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom) |
| s9:it2-c5 | Li11P4S15I | 2.28–2.30 | passivating (2.368) | -0.139 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| it1-c1 | Li11P4S15Br | 2.28–2.30 | passivating (2.368) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c2 | Li6P2S7O | 1.74–2.36 | passivating (2.197) | -0.138 | reduced (electrolyte decomposes via LiS4, P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c1 | Li11P4S15Cl | 2.28–2.30 | passivating (2.372) | -0.138 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c2 | Li7AsP2S11 | zero width (not a rejection) | passivating (2.598) | -0.149 | reduced (electrolyte decomposes via AsS2, LiS4); cathode reaction forms FeS2 (information) | kept |
| it1-c3 | Li7P3S10O | 2.28–2.30 | passivating (2.442) | -0.136 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c1 | Li13P6S21Cl | 2.28–2.30 | passivating (2.574) | -0.135 | reduced (electrolyte decomposes via P2S7); cathode reaction forms FeS2 (information) | kept |
| s9:it2-c3 | Li14SbP5S22 | zero width (not a rejection) | passivating (2.559) | -0.143 | reduced (electrolyte decomposes via LiS4); cathode reaction forms FeS2 (information) | kept |

Reduced confidence: the decomposition of the electrolyte (window limits, Li metal) goes through a polysulfide, where UMA is least reliable. Interfaces are informative (no threshold); a polysulfide formed with the cathode (FeS2 for almost every sulfide against LiFePO4) is shown as information only.

## Choice of the candidates for molecular dynamics

Not simulated yet (the choice): none. Selected by meta: it1-c2, s9:it2-c5, s9:it1-c4.

Rationale: Diverse soft-anion plus vacancy set pairing Se on both parents with I-vacancy, where rankings give it1-c2 -0.115, s9:it2-c5 0.362 < it1-c1 0.367, and s9:it1-c4 0.323 best on its parent, with two cached free.

## Li diffusion (600 K, 2 seeds of 40 ps pooled, Modal A10G)

Runs computed: 0 of 16 (others from the cache); estimate 0.00 $, about 0 min in parallel.
Not selected but already simulated (verdict from the cache, no cost): s9:it1-c2, s9:it1-c1, s9:it2-c1.

| Structure | Kind | D ± s.e. (cm²/s) | D / D(parent) | Verdict | Conduction | Framework |
|---|---|---|---|---|---|---|
| Li7P3S11 (mp-641703) | parent | 1.30e-05 ± 2.2e-06 | — | — | — | intact |
| Li3PS4 (mp-985583) | parent | 5.94e-06 ± 1.2e-06 | — | — | — | intact |
| Li6P2SeS7 (it1-c2) | candidate | 3.90e-06 ± 9.6e-07 | 0.66 ± 0.21 | tied | passes | intact |
| Li11P4S15I (s9:it2-c5) | candidate | 5.34e-06 ± 1.7e-06 | 0.90 ± 0.34 | tied | passes | intact |
| Li7P3SeS10 (s9:it1-c4) | candidate | 1.39e-05 ± 1.8e-06 | 1.07 ± 0.23 | tied | passes | intact |
| Li6P2S7O (s9:it1-c2) | candidate | 7.86e-06 ± 8.1e-07 | 1.32 ± 0.30 | tied | passes | intact |
| Li11P4S15Cl (s9:it1-c1) | candidate | 5.53e-06 ± 1.2e-06 | 0.93 ± 0.28 | tied | passes | intact |
| Li13P6S21Cl (s9:it2-c1) | candidate | 1.25e-05 ± 1.4e-06 | 0.96 ± 0.20 | tied | excluded | MOVED |

## Final ranking

Order: MD verdict (higher > tied > not_run), then lowest E_hull per substitution; excluded candidates last, with their reason. Candidates are computational predictions, not proven materials.

1. it1-c2 Li6P2SeS7 **finalist**: E_hull per substitution -0.115 eV, E_hull -0.007 eV/atom, gap 2.48 eV, MD tied (D/D(parent) 0.66 ± 0.21); reduced confidence of the window (decomposes via SeS7)
2. s9:it1-c4 Li7P3SeS10 **finalist**: E_hull per substitution 0.323 eV, E_hull 0.015 eV/atom, gap 2.35 eV, MD tied (D/D(parent) 1.07 ± 0.23); reduced confidence of the window (decomposes via P2S7)
3. s9:it2-c5 Li11P4S15I **finalist**: E_hull per substitution 0.362 eV, E_hull 0.023 eV/atom, gap 2.52 eV, MD tied (D/D(parent) 0.90 ± 0.34); reduced confidence of the window (decomposes via P2S7)
4. s9:it1-c2 Li6P2S7O: E_hull per substitution 0.384 eV, E_hull 0.024 eV/atom, gap 2.84 eV, MD tied (D/D(parent) 1.32 ± 0.30); reduced confidence of the window (decomposes via LiS4, P2S7)
5. s9:it1-c1 Li11P4S15Cl: E_hull per substitution 0.399 eV, E_hull 0.026 eV/atom, gap 2.67 eV, MD tied (D/D(parent) 0.93 ± 0.28); reduced confidence of the window (decomposes via P2S7)
6. it1-c1 Li11P4S15Br: E_hull per substitution 0.367 eV, E_hull 0.024 eV/atom, gap 2.66 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
7. s9:it2-c2 Li7AsP2S11: E_hull per substitution 0.503 eV, E_hull 0.024 eV/atom, gap 2.20 eV, MD not run; reduced confidence (E_hull via AsS2, LiS4); reduced confidence of the window (decomposes via AsS2, LiS4)
8. it1-c3 Li7P3S10O: E_hull per substitution 0.510 eV, E_hull 0.024 eV/atom, gap 2.56 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
9. s9:it2-c3 Li14SbP5S22: E_hull per substitution 1.381 eV, E_hull 0.033 eV/atom, gap 2.23 eV, MD not run; reduced confidence (E_hull via LiS4); reduced confidence of the window (decomposes via LiS4)
10. s9:it2-c1 Li13P6S21Cl: E_hull per substitution 0.618 eV, E_hull 0.030 eV/atom, gap 2.25 eV, MD tied (D/D(parent) 0.96 ± 0.20); reduced confidence of the window (decomposes via P2S7) — EXCLUDED at molecular_dynamics: framework moved: Cl diffuses at 40% of Li (limit 5%), seed 0, final MSD 5.4 A2
11. s9:it2-c4 NaLi11(PS4)4: E_hull per substitution 0.089 eV, E_hull 0.003 eV/atom, gap 2.71 eV, MD not run; reduced confidence of the window (decomposes via Na2S5) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom)
12. s9:it1-c5 NaLi6P3S11: E_hull per substitution 0.347 eV, E_hull 0.017 eV/atom, gap 2.40 eV, MD not run; reduced confidence of the window (decomposes via Na2S5, P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom)

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

### it1-c2 Li6P2SeS7: close family already studied

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

## Final scientific report

*Ranking complete*.

### Executive summary

The goal was to find sulfide solid electrolytes for lithium metal batteries by substitution in known crystals. The best compromise is Li6P2SeS7 derived from Li3PS4. It has an energy above the hull of -0.007 eV/atom and band gaps of 2.485 eV and 3.102 eV. It is stable from 1.8 V to 2.24 V and shows passivating behavior against lithium metal. Its diffusion coefficient at 600 K is 3.9e-06 cm²/s with a ratio to the parent of 0.657. Ionic conductivity at room temperature was not computed.

### Comparison of the three finalists

| | Li6P2SeS7 | Li7P3SeS10 | Li11P4S15I |
|---|---|---|---|
| Parent crystal | Li3PS4 | Li7P3S11 | Li3PS4 |
| Space group | Pmc2_1 | P1 | P1 |
| Cell a / b / c (Å) | 6.26 / 8.15 / 13.15 | 6.20 / 12.67 / 12.67 | 6.31 / 8.20 / 13.09 |
| E_hull (eV/atom) | -0.007 | 0.015 | 0.023 |
| E_hull per substitution (eV) | -0.115 | 0.323 | 0.362 |
| Band gap optB88 / mBJ (eV) | 2.48 / 3.10 | 2.35 / 2.89 | 2.52 / 3.18 |
| Window (V) | 1.80–2.24 | 2.28–2.30 | 2.28–2.30 |
| Against Li metal | passivating | passivating | passivating |
| Reaction with LiFePO4 (eV/atom) | -0.145 | -0.143 | -0.139 |
| D at 600 K (cm²/s) | 3.90e-06 | 1.39e-05 | 5.34e-06 |
| D / D(parent) | 0.66 ± 0.21 | 1.07 ± 0.23 | 0.90 ± 0.34 |
| Diffusion verdict | tied | tied | tied |
| Ionic conductivity | not computed | not computed | not computed |
| Literature | close family already studied | close family already studied | close family already studied |
| Confidence flags | window via a polysulfide | window via a polysulfide | window via a polysulfide |

### Champion: Li6P2SeS7

**Why it is preferred.**
- Li6P2SeS7 has an energy above the hull of -0.007 eV/atom, lower than 0.015 eV/atom for Li7P3SeS10 and 0.023 eV/atom for Li11P4S15I.
- Li6P2SeS7 is stable from 1.8 V to 2.24 V, covering a broader voltage interval than 2.28 V to 2.3 V for Li7P3SeS10 and 2.28 V to 2.3 V for Li11P4S15I.
- Li6P2SeS7 has an energy of -0.115 eV per substitution, lower than 0.323 eV per substitution for Li7P3SeS10 and 0.362 eV per substitution for Li11P4S15I.

**Trade-offs.**
- Its diffusion coefficient at 600 K of 3.9e-06 cm²/s is lower than 1.39e-05 cm²/s for Li7P3SeS10 and 5.34e-06 cm²/s for Li11P4S15I, with a ratio to the parent of 0.657.
- Its reaction energy with LiFePO4 is -0.145 eV/atom, slightly more negative than -0.143 eV/atom for Li7P3SeS10 and -0.139 eV/atom for Li11P4S15I.
- Its band gap of 3.102 eV is higher than 2.886 eV for Li7P3SeS10 but lower than 3.178 eV for Li11P4S15I.
- Its novelty is listed as close family already studied, so Se substitution in this sulfide family is not fully new.

**Uncertainties.**
- Diffusion was evaluated only at 600 K, not at room temperature, with an error of 9.6e-07 cm²/s and a ratio error of 0.211 leading to a tied verdict.
- The electrochemical window carries a reduced confidence flag because it was determined via a polysulfide.
- The energy above the hull of -0.007 eV/atom is close to zero and method accuracy limits confidence in exact stability.
- Ionic conductivity at room temperature was not computed and no experimental data were available.

**Validation.**
- Powder diffraction can test whether the predicted orthorhombic structure forms. *(documented)*
- Impedance spectroscopy can measure ionic conductivity and electronic leakage. *(documented)*
- Cycling against lithium metal can test whether passivation holds in practice. *(documented)*
- Higher accuracy density functional calculations can recheck stability and band gap. *(documented)*

**Synthesis routes to consider.**
- Ball milling followed by annealing under inert atmosphere could be tried as a route to Li6P2SeS7. *(documented)*
- Solid state reaction of lithium sulfide with phosphorus and selenium precursors in sealed tubes could be explored. *(hypothesis)*

### Methods

- **Candidate proposals and decisions**: Meta Muse Spark (reasoning model), with comparisons computed by the code
- **Structure relaxation and energies**: Meta FAIR UMA (uma-s-1p2, OMat head), MP2020 corrections; references from Materials Project, all relaxed with UMA (no mixing of energy sources)
- **Thermodynamic stability**: energy above the convex hull of the chemical system; kept if <= 0.05 eV/atom
- **Electronic band gap**: ALIGNN graph neural network (optB88vdW scale for the filter, mBJ shown); kept if >= 2 eV
- **Electrochemical window and electrodes**: grand-potential phase diagrams (window, reaction with Li metal), interface reactivity with LiFePO4 (calibrated against MP)
- **Independent reviews**: Meta Muse Spark Open, one review per candidate, in parallel
- **Lithium diffusion**: Langevin molecular dynamics with UMA at 600 K, 2 x 40 ps per structure, diffusion coefficient by blocks, compared with the parent crystal (calibrated: Li7P3S11 2.0x faster than beta-Li3PS4)
- **Literature check**: Meta Muse Spark with web search; a known electrolyte (LGPS) checked first as a control
- **Plain-language summaries**: Meta Muse Glimmer

### Limitations

- Ionic conductivity at room temperature was not computed.
- Synthesis routes, cost of the elements, and experimental performance were not studied.
- Long term cycling, moisture stability, and compatibility beyond LiFePO4 still need validation.
- The candidates are computational predictions and are not proven materials.
- Not computed: ionic conductivity at room temperature (only the diffusion coefficient at 600 K, relative to the parent), DFT-level energies, synthesis routes, cost of the elements, experimental data.
- The candidates are computational predictions, not proven materials.


Model ranking (last analysis): ['it1-c2', 'it1-c1', 'it1-c3']

## Usage

- meta: 3 calls, 16195 in / 10048 out tokens, ~$0.0630
- meta (rerun): 1 calls, 2742 in / 4727 out tokens, ~$0.0235
- novelty web search: 0 calls, ~$0.0000
- molecular dynamics: 0 new runs of 16 on Modal A10G, estimate 0.00 $
- UMA relaxations: 55 new / 80 allowed
- events: 53; duration 33.0 min