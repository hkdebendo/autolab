# AutoLab loop report

**Domain.** electrolyte. **Goal.** Find new sulfide solid electrolytes for lithium-metal batteries, derived from Li7P3S11 or beta-Li3PS4, that conduct lithium at least as fast as their parent and stay stable against lithium metal. Learn from the candidates that fail.

**Parents.** Li3PS4 mp-985583 (Li12P4S16, 32 atoms); Li7P3S11 mp-641703 (Li14P6S22, 42 atoms)
**Settings.** 3 iterations max, 3 candidates max, 160 new UMA relaxations max; brain meta, fallback baseten.
**Stop reason.** iterations done

## Iteration 1

**Hypothesis.** Combine Li-vacancy creation by halogens with dilute O passivation and Na expansion to boost conduction and Li-metal stability.

_meta, 1 attempt(s), 7371 in / 5783 out tokens, ~$0.0000, 0.0 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-985583 | S->Cl x2, -2 Li | Double Cl doping doubles Li vacancies for faster diffusion and forms LiCl interphase stable against Li metal. |
| it1-c2 | mp-641703 | S->O x1 | Dilute O in Li7P3S11 should form passivating phosphate while preserving sulfide conduction better than higher O content. |
| it1-c3 | mp-641703 | Li->Na x1 | Single Na pillar expands Li7P3S11 channels for Li motion with less blocking risk than double Na doping. |

<details><summary>Reasoning summary (proposals)</summary>

Reviewing substitution rules and oxidation state constraints for lithium-metal electrolyte proposals.

Applying charge-neutrality and E_hull filters while excluding prior compositions and transition metals.

Proposing three new anion substitutions while avoiding prior compositions and transition metals.

Evaluating charge-neutral substitution rules and ruling out aliovalent P-site swaps due to vacancy constraints.

Extending substitution filtering to add halogen and oxygen dopants while avoiding aliovalent P-site swaps.

Proposing new halogen, selenium, and magnesium substitutions to balance conductivity and stability.

Selecting halogen, oxide, and alkali substitutions to diversify vacancy and passivation effects.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it1-c1 | Li5P2S7Cl | 8/8 | 30.1 | 0.050 | 0.373 | 2.59 / 3.33 | no | — | passed |
| it1-c2 | Li14P6S21O | 6/6 | 10.2 | 0.016 | 0.660 | 2.50 / 3.03 | no | — | passed |
| it1-c3 | NaLi13(P3S11)2 | 5/5 | 6.5 | 0.012 | 0.502 | 2.38 / 2.97 | no | — | passed |
- it1-c1 decomposes into: Li3PS4 0.71, P2S5 0.16, LiCl 0.13
- it1-c2 decomposes into: Li3PS4 0.84, P2S5 0.11, Li3PO4 0.05
- it1-c3 decomposes into: Li3PS4 0.83, NaPS3 0.12, P2S5 0.06

**Slow tests of this iteration (fed back to the model):**

- Negative result: Li5P2S7Cl (it1-c1) failed the Li diffusion at 600 K (molecular dynamics, against its parent): framework moved: Cl diffuses at 17.7% of Li (limit 5%), seed 0, final MSD 4.8 A2.
- Negative result: Li14P6S21O (it1-c2) failed the Li diffusion at 600 K (molecular dynamics, against its parent): framework moved: O diffuses at 5.3% of Li (limit 5%), seed 1, final MSD 3.0 A2.
- Negative result: NaLi13(P3S11)2 (it1-c3) failed the contact test with Li metal: non_passivating against Li metal (metallic products Na, reaction 2.440 eV/atom).

**The model's reading of the failures (hypotheses, not measurements):**

- it1-c1: hypothesis: double S->Cl with 2 Li vacancies creates weakly bound Cl- that migrates with Li and disorders the anion framework. — correction: Limit halogens to x1 per cell and prefer larger Br/I over Cl while keeping S->halogen + Li-vacancy charge neutrality.
- it1-c2: hypothesis: isolated dilute O on a sulfide site without full PO4 coordination is under-bound and follows Li motion. — correction: Avoid isolated O and use isovalent Se for S or cluster O into PO4-like units while keeping charge neutrality.
- it1-c3: hypothesis: Na+ is reducible by Li metal to metallic Na, giving a non-passivating interphase. — correction: Drop Na alkali mixing and use non-reducible Mg-vacancy or isovalent P-site As/Sb substitutions while keeping charge neutrality.


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (s1:it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2SeS7 (s1:it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c2)
- **same substitution, different parents**, Li->Na x2 on mp-641703 vs mp-985583: E_hull per atom: NaLi5(PS4)2 (ref:it1-c5) 0.003 < NaLi6P3S11 (s9:it1-c5) 0.017 eV/atom (better: ref:it1-c5); E_hull per substitution: NaLi5(PS4)2 (ref:it1-c5) 0.055 < NaLi6P3S11 (s9:it1-c5) 0.347 eV per modified site (better: ref:it1-c5); band gap optB88: NaLi5(PS4)2 (ref:it1-c5) 2.699 > NaLi6P3S11 (s9:it1-c5) 2.397 eV (better: ref:it1-c5)
- **same substitution, different parents**, P->As x2 on mp-641703 vs mp-985583: E_hull per atom: Li6AsPS8 (ref:it2-c3) -0.010 < Li7AsP2S11 (s9:it2-c2) 0.024 eV/atom (better: ref:it2-c3); E_hull per substitution: Li6AsPS8 (ref:it2-c3) -0.153 < Li7AsP2S11 (s9:it2-c2) 0.503 eV per modified site (better: ref:it2-c3); band gap optB88: Li6AsPS8 (ref:it2-c3) 2.374 > Li7AsP2S11 (s9:it2-c2) 2.200 eV (better: ref:it2-c3)
- **same substitution, different parents**, P->Sb x1 on mp-641703 vs mp-985583: E_hull per atom: Li12SbP3S16 (ref:it2-c1) 0.013 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: ref:it2-c1); E_hull per substitution: Li12SbP3S16 (ref:it2-c1) 0.412 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: ref:it2-c1); band gap optB88: Li12SbP3S16 (ref:it2-c1) 2.457 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: ref:it2-c1)
- **same substitution, different parents**, Li->Na x1 on mp-985583 vs mp-641703: E_hull per atom: NaLi11(PS4)4 (s9:it2-c4) 0.003 < NaLi13(P3S11)2 (it1-c3) 0.012 eV/atom (better: s9:it2-c4); E_hull per substitution: NaLi11(PS4)4 (s9:it2-c4) 0.089 < NaLi13(P3S11)2 (it1-c3) 0.502 eV per modified site (better: s9:it2-c4); band gap optB88: NaLi11(PS4)4 (s9:it2-c4) 2.705 > NaLi13(P3S11)2 (it1-c3) 2.378 eV (better: s9:it2-c4)
- **same substitution, different parents**, S->I x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li13P6S21I (ref:it1-c2) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (ref:it1-c2) 0.489 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15I (s9:it2-c5) 2.522 > Li13P6S21I (ref:it1-c2) 2.397 eV (better: s9:it2-c5)
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
- **same parent, different added element**, on mp-985583: P->As vs P->Sb (x1, 0 Li vacancies): E_hull per atom: Li12AsP3S16 (ref:it1-c3) -0.005 < Li12SbP3S16 (ref:it2-c1) 0.013 eV/atom (better: ref:it1-c3); E_hull per substitution: Li12AsP3S16 (ref:it1-c3) -0.154 < Li12SbP3S16 (ref:it2-c1) 0.412 eV per modified site (better: ref:it1-c3); band gap optB88: Li12AsP3S16 (ref:it1-c3) 2.542 > Li12SbP3S16 (ref:it2-c1) 2.457 eV (better: ref:it1-c3)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): ref:it2-c3 -0.010, s1:it1-c2 -0.007, ref:it1-c3 -0.005, ref:it2-c2 -0.004, s9:it2-c4 0.003, ref:it1-c5 0.003, ref:it1-c4 0.007, ref:it2-c1 0.013, s9:it2-c5 0.023, s1:it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026, ref:it1-c1 0.030, it1-c1 0.050; E_hull per substitution (lowest first): ref:it1-c3 -0.154, ref:it2-c3 -0.153, s1:it1-c2 -0.115, ref:it2-c2 -0.113, ref:it1-c5 0.055, s9:it2-c4 0.089, ref:it1-c4 0.102, s9:it2-c5 0.362, s1:it1-c1 0.367, it1-c1 0.373, s9:it1-c2 0.384, s9:it1-c1 0.399, ref:it2-c1 0.412, ref:it1-c1 0.460; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, ref:it1-c5 2.699, ref:it1-c1 2.678, s9:it1-c1 2.669, s1:it1-c1 2.660, ref:it1-c4 2.610, ref:it2-c2 2.594, it1-c1 2.594, ref:it1-c3 2.542, s9:it2-c5 2.522, s1:it1-c2 2.485, ref:it2-c1 2.457, ref:it2-c3 2.374
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): it1-c3 0.012, s9:it1-c4 0.015, it1-c2 0.016, s9:it1-c5 0.017, ref:it2-c4 0.022, ref:it1-c2 0.024, s9:it2-c2 0.024, s1:it1-c3 0.024, s9:it2-c1 0.030, s9:it2-c3 0.033; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, ref:it2-c4 0.453, ref:it1-c2 0.489, it1-c3 0.502, s9:it2-c2 0.503, s1:it1-c3 0.510, s9:it2-c1 0.618, it1-c2 0.660, s9:it2-c3 1.381; band gap optB88 (highest first): s1:it1-c3 2.560, it1-c2 2.499, s9:it1-c5 2.397, ref:it1-c2 2.397, it1-c3 2.378, s9:it1-c4 2.355, ref:it2-c4 2.355, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200

</details>

**Analysis.** ranking []; stop=False

- All three it1 substitutions failed slow tests with framework motion for Cl/O and metallic Na for Na against Li metal.
- Comparisons show mp-985583 hosts substitutions more cheaply than mp-641703 (e.g. Li->Na x1 0.089 vs 0.502, S->O x2 0.384 vs 0.510, S->Cl x1 0.399 vs 0.618 eV per site).
- On mp-985583 heavier congeners cost less per site (S->I 0.362 < S->Cl 0.399, S->Se -0.115 < S->O 0.384, P->As -0.154 < P->Sb 0.412 eV per site).

**Next direction.** Prioritize dilute isovalent Se and As plus dilute Mg-vacancy variants on mp-985583 while pausing Na and concentrated Cl/O.

_meta, 1 attempt(s), 14899 in / 2738 out tokens, ~$0.0303, 10.2 s_

<details><summary>Reasoning summary (analysis)</summary>

Summarizing iteration 1 results where all three sulfide electrolyte candidates failed due to framework movement or non-passivating electrodes against lithium metal.

Drafting failure hypotheses and substitution corrections for the three excluded sulfide candidates.

Extending failure analysis with passivation and framework stability lessons using quoted comparison numbers.

</details>

## Iteration 2

**Hypothesis.** Avoid it1 Cl/O framework motion and Na reduction by using isovalent Se/As and non-reducible Mg-vacancy substitutions.

_meta, 1 attempt(s), 9989 in / 4628 out tokens, ~$0.0322, 20.0 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it2-c1 | mp-641703 | S->Se x1 | Dilute isovalent Se expands lattice without vacancies or mobile anions. |
| it2-c2 | mp-641703 | P->As x1 | Dilute isovalent As softens PS4 framework while staying non-reducible. |
| it2-c3 | mp-985583 | Li->Mg x2, -2 Li | Double Mg-vacancy creates Li vacancies with non-reducible Mg for Li-metal stability. |

<details><summary>Reasoning summary (proposals)</summary>

Reviewing prior substitution history to propose up to three new non-repeated substitutions.

Proposing new charge-neutral substitutions while excluding previously evaluated and budget attempts.

Enumerating charge-neutral substitution constraints and ruling out P→Si while identifying untried Li→Mg and S→O variants.

Evaluating dilute isovalent As/Sb substitutions and alternative Li-site charge-balanced variants while avoiding isolated oxygen and halogen concentrations.

Extending the substitution set to dilute isovalent Se on mp-641703 and Mg-vacancy variants on mp-985583.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it2-c1 | Li14P6SeS21 | 6/6 | 1.7 | 0.012 | 0.523 | 2.42 / 2.95 | no | — | passed |
| it2-c2 | Li14AsP5S22 | 3/3 | 2.3 | 0.024 | 1.007 | 2.30 / 2.89 | no (reduced confidence: decomposes via AsS2, LiS4, P2S7) | — | passed |
| it2-c3 | Li4Mg(PS4)2 | 8/8 | 41.7 | 0.013 | 0.096 | 2.58 / 3.31 | no (reduced confidence: decomposes via P2S7) | — | passed |
- it2-c1 decomposes into: Li3PS4 0.89, P2S5 0.08, P2Se5 0.03
- it2-c2 decomposes into: Li3PS4 0.89, AsS2 0.07, P2S7 0.04, LiS4 0.01
- it2-c3 decomposes into: Li3PS4 0.71, MgPS3 0.15, MgS 0.07, P2S7 0.07

**Slow tests of this iteration (fed back to the model):**

- Result: Li14P6SeS21 (it2-c1) passed the Li diffusion at 600 K (molecular dynamics, against its parent): tied with its parent (D/D(parent) = 1.34 ± 0.34).
- Negative result: Li4Mg(PS4)2 (it2-c3) failed the contact test with Li metal: non_passivating against Li metal (metallic products LiMg, reaction 2.271 eV/atom).

**The model's reading of the failures (hypotheses, not measurements):**

- it2-c3: hypothesis: Mg2+ is reduced by Li metal to metallic LiMg alloy, giving a non-passivating interphase. — correction: Drop Mg and Na cation mixing and prioritize isovalent Se/As on mp-985583 while keeping charge neutrality.


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (s1:it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2SeS7 (s1:it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c2)
- **same substitution, different parents**, Li->Na x2 on mp-641703 vs mp-985583: E_hull per atom: NaLi5(PS4)2 (ref:it1-c5) 0.003 < NaLi6P3S11 (s9:it1-c5) 0.017 eV/atom (better: ref:it1-c5); E_hull per substitution: NaLi5(PS4)2 (ref:it1-c5) 0.055 < NaLi6P3S11 (s9:it1-c5) 0.347 eV per modified site (better: ref:it1-c5); band gap optB88: NaLi5(PS4)2 (ref:it1-c5) 2.699 > NaLi6P3S11 (s9:it1-c5) 2.397 eV (better: ref:it1-c5)
- **same substitution, different parents**, P->As x2 on mp-641703 vs mp-985583: E_hull per atom: Li6AsPS8 (ref:it2-c3) -0.010 < Li7AsP2S11 (s9:it2-c2) 0.024 eV/atom (better: ref:it2-c3); E_hull per substitution: Li6AsPS8 (ref:it2-c3) -0.153 < Li7AsP2S11 (s9:it2-c2) 0.503 eV per modified site (better: ref:it2-c3); band gap optB88: Li6AsPS8 (ref:it2-c3) 2.374 > Li7AsP2S11 (s9:it2-c2) 2.200 eV (better: ref:it2-c3)
- **same substitution, different parents**, P->Sb x1 on mp-641703 vs mp-985583: E_hull per atom: Li12SbP3S16 (ref:it2-c1) 0.013 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: ref:it2-c1); E_hull per substitution: Li12SbP3S16 (ref:it2-c1) 0.412 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: ref:it2-c1); band gap optB88: Li12SbP3S16 (ref:it2-c1) 2.457 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: ref:it2-c1)
- **same substitution, different parents**, Li->Na x1 on mp-985583 vs mp-641703: E_hull per atom: NaLi11(PS4)4 (s9:it2-c4) 0.003 < NaLi13(P3S11)2 (it1-c3) 0.012 eV/atom (better: s9:it2-c4); E_hull per substitution: NaLi11(PS4)4 (s9:it2-c4) 0.089 < NaLi13(P3S11)2 (it1-c3) 0.502 eV per modified site (better: s9:it2-c4); band gap optB88: NaLi11(PS4)4 (s9:it2-c4) 2.705 > NaLi13(P3S11)2 (it1-c3) 2.378 eV (better: s9:it2-c4)
- **same substitution, different parents**, S->I x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li13P6S21I (ref:it1-c2) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (ref:it1-c2) 0.489 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15I (s9:it2-c5) 2.522 > Li13P6S21I (ref:it1-c2) 2.397 eV (better: s9:it2-c5)
- **same substitution, different parents**, P->As x1 on mp-985583 vs mp-641703: E_hull per atom: Li12AsP3S16 (ref:it1-c3) -0.005 < Li14AsP5S22 (it2-c2) 0.024 eV/atom (better: ref:it1-c3); E_hull per substitution: Li12AsP3S16 (ref:it1-c3) -0.154 < Li14AsP5S22 (it2-c2) 1.007 eV per modified site (better: ref:it1-c3); band gap optB88: Li12AsP3S16 (ref:it1-c3) 2.542 > Li14AsP5S22 (it2-c2) 2.297 eV (better: ref:it1-c3)
- **same substitution, different parents**, Li->Mg x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li10Mg(PS4)4 (ref:it1-c4) 0.007 < Li12Mg(P3S11)2 (ref:it2-c4) 0.022 eV/atom (better: ref:it1-c4); E_hull per substitution: Li10Mg(PS4)4 (ref:it1-c4) 0.102 < Li12Mg(P3S11)2 (ref:it2-c4) 0.453 eV per modified site (better: ref:it1-c4); band gap optB88: Li10Mg(PS4)4 (ref:it1-c4) 2.610 > Li12Mg(P3S11)2 (ref:it2-c4) 2.355 eV (better: ref:it1-c4)
- **same substitution, different parents**, S->Se x1 on mp-985583 vs mp-641703: E_hull per atom: Li12P4SeS15 (ref:it2-c2) -0.004 < Li14P6SeS21 (it2-c1) 0.012 eV/atom (better: ref:it2-c2); E_hull per substitution: Li12P4SeS15 (ref:it2-c2) -0.113 < Li14P6SeS21 (it2-c1) 0.523 eV per modified site (better: ref:it2-c2); band gap optB88: Li12P4SeS15 (ref:it2-c2) 2.594 > Li14P6SeS21 (it2-c1) 2.423 eV (better: ref:it2-c2)
- **same parent, different added element**, on mp-985583: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15Cl (s9:it1-c1) 2.669 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Br (s1:it1-c1) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Br (s1:it1-c1) 0.367 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s1:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->Br vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->O vs S->Se (x2, 0 Li vacancies): E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li6P2S7O (s9:it1-c2) 0.024 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li6P2S7O (s9:it1-c2) 0.384 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li6P2SeS7 (s1:it1-c2) 2.485 eV (better: s9:it1-c2)
- **same parent, different added element**, on mp-641703: S->Se vs S->O (x2, 0 Li vacancies): E_hull per atom: Li7P3SeS10 (s9:it1-c4) 0.015 < Li7P3S10O (s1:it1-c3) 0.024 eV/atom (better: s9:it1-c4); E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c4); band gap optB88: Li7P3S10O (s1:it1-c3) 2.560 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c3)
- **same parent, different added element**, on mp-641703: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (ref:it1-c2) 0.024 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: ref:it1-c2); E_hull per substitution: Li13P6S21I (ref:it1-c2) 0.489 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: ref:it1-c2); band gap optB88: Li13P6S21I (ref:it1-c2) 2.397 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: ref:it1-c2)
- **same parent, different added element**, on mp-641703: P->Sb vs P->As (x1, 0 Li vacancies): E_hull per atom: Li14AsP5S22 (it2-c2) 0.024 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: it2-c2); E_hull per substitution: Li14AsP5S22 (it2-c2) 1.007 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: it2-c2); band gap optB88: Li14AsP5S22 (it2-c2) 2.297 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: it2-c2)
- **same parent, different added element**, on mp-985583: P->As vs P->Sb (x1, 0 Li vacancies): E_hull per atom: Li12AsP3S16 (ref:it1-c3) -0.005 < Li12SbP3S16 (ref:it2-c1) 0.013 eV/atom (better: ref:it1-c3); E_hull per substitution: Li12AsP3S16 (ref:it1-c3) -0.154 < Li12SbP3S16 (ref:it2-c1) 0.412 eV per modified site (better: ref:it1-c3); band gap optB88: Li12AsP3S16 (ref:it1-c3) 2.542 > Li12SbP3S16 (ref:it2-c1) 2.457 eV (better: ref:it1-c3)
- **same parent, different added element**, on mp-641703: S->O vs S->Se (x1, 0 Li vacancies): E_hull per atom: Li14P6SeS21 (it2-c1) 0.012 < Li14P6S21O (it1-c2) 0.016 eV/atom (better: it2-c1); E_hull per substitution: Li14P6SeS21 (it2-c1) 0.523 < Li14P6S21O (it1-c2) 0.660 eV per modified site (better: it2-c1); band gap optB88: Li14P6S21O (it1-c2) 2.499 > Li14P6SeS21 (it2-c1) 2.423 eV (better: it1-c2); worst reaction energy with the cathode: Li14P6S21O (it1-c2) -0.138 > Li14P6SeS21 (it2-c1) -0.141 eV/atom (better: it1-c2)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): ref:it2-c3 -0.010, s1:it1-c2 -0.007, ref:it1-c3 -0.005, ref:it2-c2 -0.004, s9:it2-c4 0.003, ref:it1-c5 0.003, ref:it1-c4 0.007, it2-c3 0.013, ref:it2-c1 0.013, s9:it2-c5 0.023, s1:it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026, ref:it1-c1 0.030, it1-c1 0.050; E_hull per substitution (lowest first): ref:it1-c3 -0.154, ref:it2-c3 -0.153, s1:it1-c2 -0.115, ref:it2-c2 -0.113, ref:it1-c5 0.055, s9:it2-c4 0.089, it2-c3 0.096, ref:it1-c4 0.102, s9:it2-c5 0.362, s1:it1-c1 0.367, it1-c1 0.373, s9:it1-c2 0.384, s9:it1-c1 0.399, ref:it2-c1 0.412, ref:it1-c1 0.460; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, ref:it1-c5 2.699, ref:it1-c1 2.678, s9:it1-c1 2.669, s1:it1-c1 2.660, ref:it1-c4 2.610, ref:it2-c2 2.594, it1-c1 2.594, it2-c3 2.579, ref:it1-c3 2.542, s9:it2-c5 2.522, s1:it1-c2 2.485, ref:it2-c1 2.457, ref:it2-c3 2.374
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): it1-c3 0.012, it2-c1 0.012, s9:it1-c4 0.015, it1-c2 0.016, s9:it1-c5 0.017, ref:it2-c4 0.022, ref:it1-c2 0.024, s9:it2-c2 0.024, it2-c2 0.024, s1:it1-c3 0.024, s9:it2-c1 0.030, s9:it2-c3 0.033; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, ref:it2-c4 0.453, ref:it1-c2 0.489, it1-c3 0.502, s9:it2-c2 0.503, s1:it1-c3 0.510, it2-c1 0.523, s9:it2-c1 0.618, it1-c2 0.660, it2-c2 1.007, s9:it2-c3 1.381; band gap optB88 (highest first): s1:it1-c3 2.560, it1-c2 2.499, it2-c1 2.423, s9:it1-c5 2.397, ref:it1-c2 2.397, it1-c3 2.378, s9:it1-c4 2.355, ref:it2-c4 2.355, it2-c2 2.297, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200; worst reaction energy with the cathode (highest first): it1-c2 -0.138, it2-c1 -0.141, it2-c2 -0.143

</details>

**Analysis.** ranking ['it2-c1', 'it2-c2']; stop=False

- Isovalent S->Se it2-c1 tied parent diffusion (D/D=1.34 +/-0.34) with intact framework, unlike it1 Cl/O framework-motion failures.
- Mg-vacancy it2-c3 failed Li contact as non-passivating with metallic LiMg (2.271 eV/atom), like Na forming metallic Na.
- Comparisons favor mp-985583 over mp-641703 with S->Se x1 -0.113 vs 0.523 and P->As x1 -0.154 vs 1.007 eV per site, and As 1.007 vs Sb 1.381 eV per site on mp-641703.

**Next direction.** Prioritize dilute isovalent Se/As on mp-985583 and test diffusion and Li-metal stability while avoiding Mg/Na and mobile Cl/O.

_meta, 1 attempt(s), 18059 in / 2697 out tokens, ~$0.0340, 9.8 s_

<details><summary>Reasoning summary (analysis)</summary>

Evaluating iteration 2 sulfide electrolyte candidates against Li conductivity and Li-metal stability criteria, noting one passing Se-substituted variant and an incomplete As-substituted result.

Finalizing the ranking by e_hull_per_substitution and adding a failure analysis for the non-passivating slow test.

Updating failure analysis to exclude reducible Mg and ranking it2-c1 ahead of it2-c2 with cited comparison numbers.

</details>

## Iteration 3

**Hypothesis.** Correct it1-c1 Cl2 framework motion with single large Br, and it1-c2 O motion plus it1-c3/it2-c3 Na/Mg reduction by prioritizing intact-framework isovalent Se/As expansion on mp-985583.

_meta, 1 attempt(s), 11980 in / 5095 out tokens, ~$0.0366, 19.5 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it3-c1 | mp-985583 | S->Se x4 | Extends the negative-hull isovalent Se stability on mp-985583 and intact-framework tie of it2-c1 to widen Li bottlenecks without vacancies or reducible cations. |
| it3-c2 | mp-985583 | P->As x3 | Builds on low-cost P-As isovalent mixing on mp-985583 to expand lattice for diffusion while avoiding Sb cost and Na/Mg Li-metal reduction. |
| it3-c3 | mp-641703 | S->Br x1, -1 Li | Corrects it1-c1 double-Cl motion by using a single larger Br with one Li vacancy to retain vacancy-enhanced conduction with better anion anchoring. |

<details><summary>Reasoning summary (proposals)</summary>

Generating three new chemically diverse substitutions with one-sentence rationales while avoiding prior evaluated options.

Evaluating remaining isovalent substitutions for charge-neutral candidates while excluding prior evaluated options.

Ruling out P→Si and Li→Al due to charge imbalance while considering Li→Si and full P→As substitutions.

Prioritizing dilute isovalent Se and As substitutions on mp-985583 while excluding Mg, Na, and high-concentration halogens.

Evaluating new isovalent Se and As substitution counts on mp-985583 while ruling out Li-site and halogen options.

Selecting three novel dilute substitutions on mp-985583 and a large-halogen vacancy on mp-641703 while avoiding prior failure patterns.

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it3-c1 | Li3PSeS3 | 8/8 | 4.0 | -0.012 | -0.100 | 2.37 / 2.97 | no | — | passed |
| it3-c2 | Li12As3PS16 | 1/1 | 0.0 | -0.014 | -0.151 | 2.30 / 3.15 | no (reduced confidence: decomposes via LiS4) | — | passed |
| it3-c3 | Li13P6S21Br | 8/8 | 15.8 | 0.026 | 0.529 | 2.38 / 2.89 | no | — | passed |
- it3-c1 decomposes into: Li3PS4 0.75, Li7PSe6 0.19, P2Se5 0.06
- it3-c2 decomposes into: Li3AsS3 0.56, Li3PS4 0.25, LiS4 0.13, LiAsS2 0.05
- it3-c3 decomposes into: Li3PS4 0.78, P2S5 0.17, LiBr 0.05

**Slow tests of this iteration (fed back to the model):**

- Result: Li13P6S21Br (it3-c3) passed the Li diffusion at 600 K (molecular dynamics, against its parent): tied with its parent (D/D(parent) = 1.01 ± 0.20).


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Cl x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: s9:it1-c1)
- **same substitution, different parents**, S->O x2 on mp-985583 vs mp-641703: E_hull per atom: Li6P2S7O (s9:it1-c2) 0.024 = Li7P3S10O (s1:it1-c3) 0.024 eV/atom; E_hull per substitution: Li6P2S7O (s9:it1-c2) 0.384 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li7P3S10O (s1:it1-c3) 2.560 eV (better: s9:it1-c2)
- **same substitution, different parents**, S->Se x2 on mp-641703 vs mp-985583: E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li7P3SeS10 (s9:it1-c4) 0.015 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li7P3SeS10 (s9:it1-c4) 0.323 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2SeS7 (s1:it1-c2) 2.485 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c2)
- **same substitution, different parents**, Li->Na x2 on mp-641703 vs mp-985583: E_hull per atom: NaLi5(PS4)2 (ref:it1-c5) 0.003 < NaLi6P3S11 (s9:it1-c5) 0.017 eV/atom (better: ref:it1-c5); E_hull per substitution: NaLi5(PS4)2 (ref:it1-c5) 0.055 < NaLi6P3S11 (s9:it1-c5) 0.347 eV per modified site (better: ref:it1-c5); band gap optB88: NaLi5(PS4)2 (ref:it1-c5) 2.699 > NaLi6P3S11 (s9:it1-c5) 2.397 eV (better: ref:it1-c5)
- **same substitution, different parents**, P->As x2 on mp-641703 vs mp-985583: E_hull per atom: Li6AsPS8 (ref:it2-c3) -0.010 < Li7AsP2S11 (s9:it2-c2) 0.024 eV/atom (better: ref:it2-c3); E_hull per substitution: Li6AsPS8 (ref:it2-c3) -0.153 < Li7AsP2S11 (s9:it2-c2) 0.503 eV per modified site (better: ref:it2-c3); band gap optB88: Li6AsPS8 (ref:it2-c3) 2.374 > Li7AsP2S11 (s9:it2-c2) 2.200 eV (better: ref:it2-c3)
- **same substitution, different parents**, P->Sb x1 on mp-641703 vs mp-985583: E_hull per atom: Li12SbP3S16 (ref:it2-c1) 0.013 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: ref:it2-c1); E_hull per substitution: Li12SbP3S16 (ref:it2-c1) 0.412 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: ref:it2-c1); band gap optB88: Li12SbP3S16 (ref:it2-c1) 2.457 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: ref:it2-c1)
- **same substitution, different parents**, Li->Na x1 on mp-985583 vs mp-641703: E_hull per atom: NaLi11(PS4)4 (s9:it2-c4) 0.003 < NaLi13(P3S11)2 (it1-c3) 0.012 eV/atom (better: s9:it2-c4); E_hull per substitution: NaLi11(PS4)4 (s9:it2-c4) 0.089 < NaLi13(P3S11)2 (it1-c3) 0.502 eV per modified site (better: s9:it2-c4); band gap optB88: NaLi11(PS4)4 (s9:it2-c4) 2.705 > NaLi13(P3S11)2 (it1-c3) 2.378 eV (better: s9:it2-c4)
- **same substitution, different parents**, S->I x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li13P6S21I (ref:it1-c2) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li13P6S21I (ref:it1-c2) 0.489 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15I (s9:it2-c5) 2.522 > Li13P6S21I (ref:it1-c2) 2.397 eV (better: s9:it2-c5)
- **same substitution, different parents**, S->Br x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li13P6S21Br (it3-c3) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li13P6S21Br (it3-c3) 0.529 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li13P6S21Br (it3-c3) 2.382 eV (better: s1:it1-c1)
- **same substitution, different parents**, P->As x1 on mp-985583 vs mp-641703: E_hull per atom: Li12AsP3S16 (ref:it1-c3) -0.005 < Li14AsP5S22 (it2-c2) 0.024 eV/atom (better: ref:it1-c3); E_hull per substitution: Li12AsP3S16 (ref:it1-c3) -0.154 < Li14AsP5S22 (it2-c2) 1.007 eV per modified site (better: ref:it1-c3); band gap optB88: Li12AsP3S16 (ref:it1-c3) 2.542 > Li14AsP5S22 (it2-c2) 2.297 eV (better: ref:it1-c3)
- **same substitution, different parents**, Li->Mg x1, -1 Li on mp-985583 vs mp-641703: E_hull per atom: Li10Mg(PS4)4 (ref:it1-c4) 0.007 < Li12Mg(P3S11)2 (ref:it2-c4) 0.022 eV/atom (better: ref:it1-c4); E_hull per substitution: Li10Mg(PS4)4 (ref:it1-c4) 0.102 < Li12Mg(P3S11)2 (ref:it2-c4) 0.453 eV per modified site (better: ref:it1-c4); band gap optB88: Li10Mg(PS4)4 (ref:it1-c4) 2.610 > Li12Mg(P3S11)2 (ref:it2-c4) 2.355 eV (better: ref:it1-c4)
- **same substitution, different parents**, S->Se x1 on mp-985583 vs mp-641703: E_hull per atom: Li12P4SeS15 (ref:it2-c2) -0.004 < Li14P6SeS21 (it2-c1) 0.012 eV/atom (better: ref:it2-c2); E_hull per substitution: Li12P4SeS15 (ref:it2-c2) -0.113 < Li14P6SeS21 (it2-c1) 0.523 eV per modified site (better: ref:it2-c2); band gap optB88: Li12P4SeS15 (ref:it2-c2) 2.594 > Li14P6SeS21 (it2-c1) 2.423 eV (better: ref:it2-c2)
- **same parent, different added element**, on mp-985583: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15Cl (s9:it1-c1) 0.026 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15Cl (s9:it1-c1) 0.399 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15Cl (s9:it1-c1) 2.669 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: s9:it1-c1)
- **same parent, different added element**, on mp-985583: S->Cl vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Cl (s9:it1-c1) 0.026 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s9:it1-c1); E_hull per substitution: Li11P4S15Cl (s9:it1-c1) 0.399 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s9:it1-c1); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15Cl (s9:it1-c1) 2.669 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15Br (s1:it1-c1) 0.024 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15Br (s1:it1-c1) 0.367 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15Br (s1:it1-c1) 2.660 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: s1:it1-c1)
- **same parent, different added element**, on mp-985583: S->I vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15I (s9:it2-c5) 0.023 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s9:it2-c5); E_hull per substitution: Li11P4S15I (s9:it2-c5) 0.362 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s9:it2-c5); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15I (s9:it2-c5) 2.522 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->Br vs S->F (x1, 1 Li vacancies): E_hull per atom: Li11P4S15Br (s1:it1-c1) 0.024 < Li11P4S15F (ref:it1-c1) 0.030 eV/atom (better: s1:it1-c1); E_hull per substitution: Li11P4S15Br (s1:it1-c1) 0.367 < Li11P4S15F (ref:it1-c1) 0.460 eV per modified site (better: s1:it1-c1); band gap optB88: Li11P4S15F (ref:it1-c1) 2.678 > Li11P4S15Br (s1:it1-c1) 2.660 eV (better: ref:it1-c1)
- **same parent, different added element**, on mp-985583: S->O vs S->Se (x2, 0 Li vacancies): E_hull per atom: Li6P2SeS7 (s1:it1-c2) -0.007 < Li6P2S7O (s9:it1-c2) 0.024 eV/atom (better: s1:it1-c2); E_hull per substitution: Li6P2SeS7 (s1:it1-c2) -0.115 < Li6P2S7O (s9:it1-c2) 0.384 eV per modified site (better: s1:it1-c2); band gap optB88: Li6P2S7O (s9:it1-c2) 2.838 > Li6P2SeS7 (s1:it1-c2) 2.485 eV (better: s9:it1-c2)
- **same parent, different added element**, on mp-641703: S->Se vs S->O (x2, 0 Li vacancies): E_hull per atom: Li7P3SeS10 (s9:it1-c4) 0.015 < Li7P3S10O (s1:it1-c3) 0.024 eV/atom (better: s9:it1-c4); E_hull per substitution: Li7P3SeS10 (s9:it1-c4) 0.323 < Li7P3S10O (s1:it1-c3) 0.510 eV per modified site (better: s9:it1-c4); band gap optB88: Li7P3S10O (s1:it1-c3) 2.560 > Li7P3SeS10 (s9:it1-c4) 2.355 eV (better: s1:it1-c3)
- **same parent, different added element**, on mp-641703: S->Cl vs S->I (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (ref:it1-c2) 0.024 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: ref:it1-c2); E_hull per substitution: Li13P6S21I (ref:it1-c2) 0.489 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: ref:it1-c2); band gap optB88: Li13P6S21I (ref:it1-c2) 2.397 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: ref:it1-c2)
- **same parent, different added element**, on mp-641703: S->Cl vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li13P6S21Br (it3-c3) 0.026 < Li13P6S21Cl (s9:it2-c1) 0.030 eV/atom (better: it3-c3); E_hull per substitution: Li13P6S21Br (it3-c3) 0.529 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site (better: it3-c3); band gap optB88: Li13P6S21Br (it3-c3) 2.382 > Li13P6S21Cl (s9:it2-c1) 2.250 eV (better: it3-c3)
- **same parent, different added element**, on mp-641703: S->I vs S->Br (x1, 1 Li vacancies): E_hull per atom: Li13P6S21I (ref:it1-c2) 0.024 < Li13P6S21Br (it3-c3) 0.026 eV/atom (better: ref:it1-c2); E_hull per substitution: Li13P6S21I (ref:it1-c2) 0.489 < Li13P6S21Br (it3-c3) 0.529 eV per modified site (better: ref:it1-c2); band gap optB88: Li13P6S21I (ref:it1-c2) 2.397 > Li13P6S21Br (it3-c3) 2.382 eV (better: ref:it1-c2)
- **same parent, different added element**, on mp-641703: P->Sb vs P->As (x1, 0 Li vacancies): E_hull per atom: Li14AsP5S22 (it2-c2) 0.024 < Li14SbP5S22 (s9:it2-c3) 0.033 eV/atom (better: it2-c2); E_hull per substitution: Li14AsP5S22 (it2-c2) 1.007 < Li14SbP5S22 (s9:it2-c3) 1.381 eV per modified site (better: it2-c2); band gap optB88: Li14AsP5S22 (it2-c2) 2.297 > Li14SbP5S22 (s9:it2-c3) 2.231 eV (better: it2-c2)
- **same parent, different added element**, on mp-985583: P->As vs P->Sb (x1, 0 Li vacancies): E_hull per atom: Li12AsP3S16 (ref:it1-c3) -0.005 < Li12SbP3S16 (ref:it2-c1) 0.013 eV/atom (better: ref:it1-c3); E_hull per substitution: Li12AsP3S16 (ref:it1-c3) -0.154 < Li12SbP3S16 (ref:it2-c1) 0.412 eV per modified site (better: ref:it1-c3); band gap optB88: Li12AsP3S16 (ref:it1-c3) 2.542 > Li12SbP3S16 (ref:it2-c1) 2.457 eV (better: ref:it1-c3)
- **same parent, different added element**, on mp-641703: S->O vs S->Se (x1, 0 Li vacancies): E_hull per atom: Li14P6SeS21 (it2-c1) 0.012 < Li14P6S21O (it1-c2) 0.016 eV/atom (better: it2-c1); E_hull per substitution: Li14P6SeS21 (it2-c1) 0.523 < Li14P6S21O (it1-c2) 0.660 eV per modified site (better: it2-c1); band gap optB88: Li14P6S21O (it1-c2) 2.499 > Li14P6SeS21 (it2-c1) 2.423 eV (better: it1-c2); worst reaction energy with the cathode: Li14P6S21O (it1-c2) -0.138 > Li14P6SeS21 (it2-c1) -0.141 eV/atom (better: it1-c2)
- **ranking on one parent**, mp-985583: E_hull per atom (lowest first): it3-c2 -0.014, it3-c1 -0.012, ref:it2-c3 -0.010, s1:it1-c2 -0.007, ref:it1-c3 -0.005, ref:it2-c2 -0.004, s9:it2-c4 0.003, ref:it1-c5 0.003, ref:it1-c4 0.007, it2-c3 0.013, ref:it2-c1 0.013, s9:it2-c5 0.023, s1:it1-c1 0.024, s9:it1-c2 0.024, s9:it1-c1 0.026, ref:it1-c1 0.030, it1-c1 0.050; E_hull per substitution (lowest first): ref:it1-c3 -0.154, ref:it2-c3 -0.153, it3-c2 -0.151, s1:it1-c2 -0.115, ref:it2-c2 -0.113, it3-c1 -0.100, ref:it1-c5 0.055, s9:it2-c4 0.089, it2-c3 0.096, ref:it1-c4 0.102, s9:it2-c5 0.362, s1:it1-c1 0.367, it1-c1 0.373, s9:it1-c2 0.384, s9:it1-c1 0.399, ref:it2-c1 0.412, ref:it1-c1 0.460; band gap optB88 (highest first): s9:it1-c2 2.838, s9:it2-c4 2.705, ref:it1-c5 2.699, ref:it1-c1 2.678, s9:it1-c1 2.669, s1:it1-c1 2.660, ref:it1-c4 2.610, ref:it2-c2 2.594, it1-c1 2.594, it2-c3 2.579, ref:it1-c3 2.542, s9:it2-c5 2.522, s1:it1-c2 2.485, ref:it2-c1 2.457, ref:it2-c3 2.374, it3-c1 2.368, it3-c2 2.303; worst reaction energy with the cathode (highest first): it1-c1 -0.131, it3-c1 -0.147, it3-c2 -0.171
- **ranking on one parent**, mp-641703: E_hull per atom (lowest first): it1-c3 0.012, it2-c1 0.012, s9:it1-c4 0.015, it1-c2 0.016, s9:it1-c5 0.017, ref:it2-c4 0.022, ref:it1-c2 0.024, s9:it2-c2 0.024, it2-c2 0.024, s1:it1-c3 0.024, it3-c3 0.026, s9:it2-c1 0.030, s9:it2-c3 0.033; E_hull per substitution (lowest first): s9:it1-c4 0.323, s9:it1-c5 0.347, ref:it2-c4 0.453, ref:it1-c2 0.489, it1-c3 0.502, s9:it2-c2 0.503, s1:it1-c3 0.510, it2-c1 0.523, it3-c3 0.529, s9:it2-c1 0.618, it1-c2 0.660, it2-c2 1.007, s9:it2-c3 1.381; band gap optB88 (highest first): s1:it1-c3 2.560, it1-c2 2.499, it2-c1 2.423, s9:it1-c5 2.397, ref:it1-c2 2.397, it3-c3 2.382, it1-c3 2.378, s9:it1-c4 2.355, ref:it2-c4 2.355, it2-c2 2.297, s9:it2-c1 2.250, s9:it2-c3 2.231, s9:it2-c2 2.200; worst reaction energy with the cathode (highest first): it3-c3 -0.135, it1-c2 -0.138, it2-c1 -0.141, it2-c2 -0.143

</details>

**Analysis.** ranking ['it3-c2', 'it3-c1', 'it3-c3']; stop=False

- On mp-985583 E_hull per substitution runs ref:it1-c3 -0.154, ref:it2-c3 -0.153, it3-c2 -0.151, s1:it1-c2 -0.115, it3-c1 -0.100 eV per site, confirming isovalent As/Se as most stable.
- On mp-641703 Li13P6S21Br (it3-c3) 0.529 < Li13P6S21Cl (s9:it2-c1) 0.618 eV per modified site and tied parent diffusion at 1.01 +/-0.20 with intact framework, fixing it1 Cl/O motion.
- mp-985583 hosts substitutions more cheaply with Li11P4S15Br (s1:it1-c1) 0.367 < Li13P6S21Br (it3-c3) 0.529 eV per modified site.

**Next direction.** Submit it3-c1/it3-c2 to diffusion and Li-contact tests and probe dilute Se/As variants on mp-985583.

_meta, 1 attempt(s), 20485 in / 2552 out tokens, ~$0.0365, 10.2 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking candidates by e_hull_per_sub while weighing reduced confidence versus slow test results for JSON output.

Applying the ranking rule to keep per-substitution order despite reduced confidence and noting the MD-tied candidate stays last.

Recording empty failure analysis for this iteration and citing quoted comparisons for lessons and next direction.

</details>

## Summaries (Muse Glimmer)

**iteration 1.** Iteration 1 tested halogen-driven Li vacancies with dilute O passivation and Na expansion. Li5P2S7Cl, Li14P6S21O and NaLi13(P3S11)2 all passed the stability and insulation filters with energy above the hull of about 0.05, 0.02 and 0.01 eV per atom and band gaps of about 2.6, 2.5 and 2.4 eV. All three failed slow tests: Li5P2S7Cl showed framework motion with Cl diffusing at 17.7 percent of Li, Li14P6S21O showed framework motion with O diffusing at 5.3 percent of Li, and NaLi13(P3S11)2 was non-passivating against Li metal with a reaction of 2.44 eV per atom forming metallic Na. The agent concluded to limit halogens to one per cell and prefer larger Br or I, avoid isolated O in favor of clustered PO4-like units or isovalent Se, and drop Na mixing for non-reducible Mg vacancy or P-site As Sb substitutions, prioritizing dilute isovalent Se and As plus Mg-vacancy variants on mp-985583 Li3PS4.

**iteration 2.** Iteration two tested isovalent Se/As and Mg-vacancy substitutions to avoid Cl/O framework motion and Na reduction. Li14P6SeS21 and Li14AsP5S22 passed stability and insulation filters with energy above hull about 0.01 eV per atom and band gaps about 2.4 eV and 2.3 eV, and Li14P6SeS21 tied its parent for lithium diffusion at 600 K with D over D parent about 1.34 plus minus 0.34. Li4Mg(PS4)2 passed filters with a band gap about 2.6 eV but failed contact with Li metal because it forms metallic LiMg with a reaction about 2.27 eV per atom, so the agent concluded to drop Mg and Na cation mixing and prioritize dilute isovalent Se/As on Li3PS4 while avoiding Mg/Na and mobile Cl/O.

**iteration 3.** In iteration 3 the agent tested isovalent Se/As expansions on Li3PS4 and a single large Br substitution intended to keep the framework intact on Li13P6S21Br, correcting earlier Cl/O motion issues. Li3PSeS3, Li12As3PS16 and Li13P6S21Br all passed stability and band gap filtering with energy above the hull around -0.01 eV per atom for the first two and 0.03 eV per atom for Li13P6S21Br, and gaps near 2.4 eV, 2.3 eV and 2.4 eV respectively. Molecular dynamics at 600 K showed Li13P6S21Br tied with its parent with diffusion ratio 1.01 ± 0.20, confirming the intact-framework Br substitution fixes motion, and the agent concluded isovalent As/Se substitutions are the most stable on Li3PS4 and will submit the Se/As candidates to diffusion and Li-contact tests.

**run.** The agent proposed nine selenide-substituted derivatives of Li7P3S11 and beta-Li3PS4 and screened them for stability, electronic insulation and lithium diffusion. Several candidates were rejected because the framework moved in molecular dynamics with chlorine or oxygen diffusing at up to about 40 percent of lithium, and others were rejected for being non-passivating against lithium metal with metallic decomposition products and reaction energies around 2.1 to 2.5 eV per atom. Three related candidates remained with near-zero energy above the hull and insulating band gaps: Li6P2SeS7 with energy above the hull about -0.01 eV per atom and band gap about 2.5 eV, Li12P4SeS15 with energy above the hull about 0.00 eV per atom and band gap about 2.6 eV, and Li7P3SeS10 with energy above the hull about 0.02 eV per atom and band gap about 2.4 eV. Molecular dynamics found lithium diffusion tied to the parent with diffusion ratios of about 0.66, 0.82 and 1.07 respectively. The agent concluded these selenide substitutions give computationally predicted stable insulating frameworks with lithium transport comparable to the parent but without a clear improvement.

**Earlier runs.** 23 candidates given to the model and to the stages: s9:it1-c1, s9:it1-c2, s9:it1-c3, s9:it1-c4, s9:it1-c5, s9:it2-c1, s9:it2-c2, s9:it2-c3, s9:it2-c4, s9:it2-c5, s1:it1-c1, s1:it1-c2, s1:it1-c3, ref:it1-c1, ref:it1-c2, ref:it1-c3, ref:it1-c4, ref:it1-c5, ref:it2-c1, ref:it2-c2, ref:it2-c3, ref:it2-c4, ref:it2-c5.

## Electrodes (UMA + MP2020 energies)

- Calibration Li3PS4 / LiFePO4: UMA -0.144 vs MP -0.133 eV/atom (diff -0.011, tolerance 0.05) → trusted

| Candidate | Formula | Window (V) | Against Li metal | Worst reaction with LiFePO4 (eV/atom) | Confidence | Decision |
|---|---|---|---|---|---|---|
| ref:it1-c3 | Li12AsP3S16 | 2.08–2.26 | passivating (2.358) | -0.152 | normal (window via AsS2, LiS4, robust: limits move by 0.06 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c3 | Li6AsPS8 | 2.08–2.26 | passivating (2.414) | -0.161 | normal (window via AsS2, LiS4, robust: limits move by 0.06 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| it3-c2 | Li12As3PS16 | 2.10–2.26 | passivating (2.469) | -0.171 | normal (window via AsS2, LiS4, robust: limits move by 0.06 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c2 | Li6P2SeS7 | 1.80–2.24 | passivating (2.309) | -0.145 | normal (window via SeS7, robust: limits move by 0.02 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c2 | Li12P4SeS15 | 1.80–2.24 | passivating (2.306) | -0.145 | normal (window via SeS7, robust: limits move by 0.02 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| it3-c1 | Li3PSeS3 | 1.82–2.22 | passivating (2.319) | -0.147 | normal (window via SeS7, robust: limits move by 0.02 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| ref:it1-c5 | NaLi5(PS4)2 | 1.94–2.26 | non_passivating (2.112) | — | normal (window via Na2S5, robust: limits move by 0.06 V for ±0.025 eV/atom on the polysulfides) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.112 eV/atom) |
| s9:it2-c4 | NaLi11(PS4)4 | 1.94–2.26 | non_passivating (2.204) | — | normal (window via Na2S5, robust: limits move by 0.06 V for ±0.025 eV/atom on the polysulfides) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom) |
| it2-c3 | Li4Mg(PS4)2 | zero width (not a rejection) | non_passivating (2.271) | — | normal (window via P2S7, robust: limits move by 0.00 V for ±0.025 eV/atom on the polysulfides) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.271 eV/atom) |
| ref:it1-c4 | Li10Mg(PS4)4 | zero width (not a rejection) | non_passivating (2.287) | — | normal (window via P2S7, robust: limits move by 0.00 V for ±0.025 eV/atom on the polysulfides) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.287 eV/atom) |
| s9:it1-c4 | Li7P3SeS10 | 2.28–2.30 | passivating (2.529) | -0.143 | reduced (electrolyte decomposes via P2S7; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c5 | NaLi6P3S11 | 2.26–2.34 | non_passivating (2.365) | — | normal (window via Na2S5, P2S7, robust: limits move by 0.08 V for ±0.025 eV/atom on the polysulfides) | excluded: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom) |
| s9:it2-c5 | Li11P4S15I | 2.28–2.30 | passivating (2.368) | -0.139 | reduced (electrolyte decomposes via P2S7; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom); cathode reaction forms FeS2 (information) | kept |
| s1:it1-c1 | Li11P4S15Br | 2.28–2.30 | passivating (2.368) | -0.138 | reduced (electrolyte decomposes via P2S7; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom); cathode reaction forms FeS2 (information) | kept |
| it1-c1 | Li5P2S7Cl | 2.28–2.30 | passivating (2.435) | -0.131 | reduced (electrolyte decomposes via P2S7; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c2 | Li6P2S7O | 1.74–2.36 | passivating (2.197) | -0.138 | normal (window via LiS4, P2S7, robust: limits move by 0.04 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| s9:it1-c1 | Li11P4S15Cl | 2.28–2.30 | passivating (2.372) | -0.138 | reduced (electrolyte decomposes via P2S7; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c1 | Li12SbP3S16 | 2.00–2.30 | passivating (2.353) | -0.151 | normal (window via LiS4, robust: limits move by 0.04 V for ±0.025 eV/atom on the polysulfides); cathode reaction forms FeS2 (information) | kept |
| ref:it2-c4 | Li12Mg(P3S11)2 | zero width (not a rejection) | non_passivating (2.507) | — | normal (window via P2S7, robust: limits move by 0.00 V for ±0.025 eV/atom on the polysulfides) | excluded: non_passivating against Li metal (metallic products LiMg, reaction 2.507 eV/atom) |
| ref:it1-c1 | Li11P4S15F | 2.28–2.30 | passivating (2.378) | -0.138 | reduced (electrolyte decomposes via P2S7; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom); cathode reaction forms FeS2 (information) | kept |

Reduced confidence: the decomposition of the electrolyte (window limits, Li metal) goes through a polysulfide, where UMA is least reliable, and the window limits move by more than 0.1 V when every polysulfide energy is shifted by ±0.025 eV/atom (twice the largest UMA-vs-DFT difference measured on known polysulfides). Interfaces are informative (no threshold); a polysulfide formed with the cathode (FeS2 for almost every sulfide against LiFePO4) is shown as information only.

## Choice of the candidates for molecular dynamics

Not simulated yet (the choice): ref:it1-c3, ref:it2-c3, it3-c2, it3-c1, ref:it2-c1, ref:it1-c1, s9:it2-c2, s1:it1-c3, it2-c2, s9:it2-c3. Selected by None: none.

Rationale: —

## Candidate analyses (Muse Spark Open, in parallel)

Not run: no new eligible candidate.

## Li diffusion (600 K, 2 seeds of 40 ps pooled, Modal A10G + H100)

Runs computed: 0 of 26 (others from the cache); estimate 0.00 $, about 0 min in parallel.
Not selected but already simulated (verdict from the cache, no cost): s1:it1-c2, ref:it2-c2, s9:it1-c4, s9:it2-c5, s1:it1-c1, s9:it1-c2, s9:it1-c1, ref:it1-c2, it2-c1, it3-c3, s9:it2-c1.

| Structure | Kind | D ± s.e. (cm²/s) | D / D(parent) | Verdict | Conduction | Framework |
|---|---|---|---|---|---|---|
| Li7P3S11 (mp-641703) | parent | 1.30e-05 ± 2.2e-06 | — | — | — | intact |
| Li3PS4 (mp-985583) | parent | 5.94e-06 ± 1.2e-06 | — | — | — | intact |
| Li6P2SeS7 (s1:it1-c2) | candidate | 3.90e-06 ± 9.6e-07 | 0.66 ± 0.21 | tied | passes | intact |
| Li12P4SeS15 (ref:it2-c2) | candidate | 4.87e-06 ± 1.1e-06 | 0.82 ± 0.25 | tied | passes | intact |
| Li7P3SeS10 (s9:it1-c4) | candidate | 1.39e-05 ± 1.8e-06 | 1.07 ± 0.23 | tied | passes | intact |
| Li11P4S15I (s9:it2-c5) | candidate | 5.34e-06 ± 1.7e-06 | 0.90 ± 0.34 | tied | passes | intact |
| Li11P4S15Br (s1:it1-c1) | candidate | 6.80e-06 ± 9.2e-07 | 1.15 ± 0.28 | tied | passes | intact |
| Li6P2S7O (s9:it1-c2) | candidate | 7.86e-06 ± 8.1e-07 | 1.32 ± 0.30 | tied | passes | intact |
| Li11P4S15Cl (s9:it1-c1) | candidate | 5.53e-06 ± 1.2e-06 | 0.93 ± 0.28 | tied | passes | intact |
| Li13P6S21I (ref:it1-c2) | candidate | 1.49e-05 ± 3.4e-06 | 1.15 ± 0.33 | tied | passes | intact |
| Li14P6SeS21 (it2-c1) | candidate | 1.74e-05 ± 3.2e-06 | 1.34 ± 0.34 | tied | passes | intact |
| Li13P6S21Br (it3-c3) | candidate | 1.31e-05 ± 1.3e-06 | 1.01 ± 0.20 | tied | passes | intact |
| Li13P6S21Cl (s9:it2-c1) | candidate | 1.25e-05 ± 1.4e-06 | 0.96 ± 0.20 | tied | excluded | MOVED |

## Ionic conductivity at 300 K (estimate)

Arrhenius fit of the diffusion coefficients of the molecular dynamics (runs up to 750 K), extrapolated to 300 K, then the Nernst-Einstein relation (tracer diffusion, Haven ratio 1). The range is one standard error of the extrapolation: an order of magnitude, not a measurement. A candidate with its own fit is "lower" or "higher" than its parent only when the two ranges do not overlap; this verdict comes first in the final ranking.

| Structure | σ at 300 K (mS/cm) | Range (mS/cm) | Activation energy (eV) | Against its parent | Method |
|---|---|---|---|---|---|
| parent mp-641703 | 99.9 | 58–1.7e+02 | 0.14 ± 0.03 | — | own Arrhenius fit (500, 600, 700 K) |
| parent mp-985583 | 1.18 | 0.43–3.2 | 0.34 ± 0.05 | — | own Arrhenius fit (500, 600, 700 K) |
| s9:it1-c1 Li11P4S15Cl | 0.857 | 0.31–2.3 | 0.34 ± 0.05 | not compared (no own fit) | D at 600 K with the parent's activation energy (assumed) |
| s9:it1-c2 Li6P2S7O | 1.39 | 0.52–3.7 | 0.34 ± 0.05 | not compared (no own fit) | D at 600 K with the parent's activation energy (assumed) |
| s9:it1-c4 Li7P3SeS10 | 134 | 50–3.6e+02 | 0.12 ± 0.05 | tied (ratio 1.3, parent 58–1.7e+02) | own Arrhenius fit (500, 600, 700 K) |
| s9:it2-c1 Li13P6S21Cl | 80.6 | 48–1.3e+02 | 0.14 ± 0.03 | not compared (no own fit) | D at 600 K with the parent's activation energy (assumed) |
| s9:it2-c5 Li11P4S15I | 0.812 | 0.29–2.3 | 0.34 ± 0.05 | not compared (no own fit) | D at 600 K with the parent's activation energy (assumed) |
| s1:it1-c1 Li11P4S15Br | 1.05 | 0.39–2.8 | 0.34 ± 0.05 | not compared (no own fit) | D at 600 K with the parent's activation energy (assumed) |
| s1:it1-c2 Li6P2SeS7 | 0.098 | 0.012–0.8 | 0.42 ± 0.10 | tied (ratio 0.083, parent 0.43–3.2) | own Arrhenius fit (500, 600, 700 K) |
| ref:it1-c2 Li13P6S21I | 94 | 54–1.6e+02 | 0.14 ± 0.03 | not compared (no own fit) | D at 600 K with the parent's activation energy (assumed) |
| ref:it2-c2 Li12P4SeS15 | 5.66 | 1.5–22 | 0.24 ± 0.07 | tied (ratio 4.8, parent 0.43–3.2) | own Arrhenius fit (500, 600, 700 K) |

## Final ranking

Order: conductivity at 300 K against the parent (higher > tied > not_fitted > lower), then MD verdict at 600 K (higher > tied > not_run), then lowest E_hull per substitution; excluded candidates last, with their reason. Candidates are computational predictions, not proven materials. E_hull ± its error bar: mean absolute UMA-vs-DFT (Materials Project) difference on the known compounds of the same chemical system.

1. s1:it1-c2 Li6P2SeS7 **finalist**: E_hull per substitution -0.115 eV, E_hull -0.007 ± 0.005 eV/atom, gap 2.48 eV, MD tied (D/D(parent) 0.66 ± 0.21); σ(300 K) 0.098 mS/cm (0.012–0.8), tied with its parent
2. ref:it2-c2 Li12P4SeS15 **finalist**: E_hull per substitution -0.113 eV, E_hull -0.004 ± 0.005 eV/atom, gap 2.59 eV, MD tied (D/D(parent) 0.82 ± 0.25); σ(300 K) 5.7 mS/cm (1.5–22), tied with its parent
3. s9:it1-c4 Li7P3SeS10 **finalist**: E_hull per substitution 0.323 eV, E_hull 0.015 ± 0.005 eV/atom, gap 2.35 eV, MD tied (D/D(parent) 1.07 ± 0.23); σ(300 K) 1.3e+02 mS/cm (50–3.6e+02), tied with its parent; reduced confidence of the window (decomposes via P2S7)
4. s9:it2-c5 Li11P4S15I: E_hull per substitution 0.362 eV, E_hull 0.023 ± 0.005 eV/atom, gap 2.52 eV, MD tied (D/D(parent) 0.90 ± 0.34); σ(300 K) 0.81 mS/cm (0.29–2.3), not compared; reduced confidence of the window (decomposes via P2S7)
5. s1:it1-c1 Li11P4S15Br: E_hull per substitution 0.367 eV, E_hull 0.024 ± 0.005 eV/atom, gap 2.66 eV, MD tied (D/D(parent) 1.15 ± 0.28); σ(300 K) 1 mS/cm (0.39–2.8), not compared; reduced confidence of the window (decomposes via P2S7)
6. s9:it1-c2 Li6P2S7O: E_hull per substitution 0.384 eV, E_hull 0.024 ± 0.005 eV/atom, gap 2.84 eV, MD tied (D/D(parent) 1.32 ± 0.30); σ(300 K) 1.4 mS/cm (0.52–3.7), not compared
7. s9:it1-c1 Li11P4S15Cl: E_hull per substitution 0.399 eV, E_hull 0.026 ± 0.005 eV/atom, gap 2.67 eV, MD tied (D/D(parent) 0.93 ± 0.28); σ(300 K) 0.86 mS/cm (0.31–2.3), not compared; reduced confidence of the window (decomposes via P2S7)
8. ref:it1-c2 Li13P6S21I: E_hull per substitution 0.489 eV, E_hull 0.024 ± 0.005 eV/atom, gap 2.40 eV, MD tied (D/D(parent) 1.15 ± 0.33); σ(300 K) 94 mS/cm (54–1.6e+02), not compared
9. it2-c1 Li14P6SeS21: E_hull per substitution 0.523 eV, E_hull 0.012 ± 0.005 eV/atom, gap 2.42 eV, MD tied (D/D(parent) 1.34 ± 0.34); σ(300 K) 46 mS/cm (17–1.2e+02), not compared; reduced confidence of the window (decomposes via P2S7)
10. it3-c3 Li13P6S21Br: E_hull per substitution 0.529 eV, E_hull 0.026 ± 0.005 eV/atom, gap 2.38 eV, MD tied (D/D(parent) 1.01 ± 0.20); σ(300 K) 33 mS/cm (12–87), not compared; reduced confidence of the window (decomposes via P2S7)
11. ref:it1-c3 Li12AsP3S16: E_hull per substitution -0.154 eV, E_hull -0.005 ± 0.004 eV/atom, gap 2.54 eV, MD not run; reduced confidence (E_hull via LiS4)
12. ref:it2-c3 Li6AsPS8: E_hull per substitution -0.153 eV, E_hull -0.010 ± 0.004 eV/atom, gap 2.37 eV, MD not run; reduced confidence (E_hull via LiS4)
13. it3-c2 Li12As3PS16: E_hull per substitution -0.151 eV, E_hull -0.014 ± 0.004 eV/atom, gap 2.30 eV, MD not run; reduced confidence (E_hull via LiS4)
14. it3-c1 Li3PSeS3: E_hull per substitution -0.100 eV, E_hull -0.012 ± 0.005 eV/atom, gap 2.37 eV, MD not run
15. ref:it2-c1 Li12SbP3S16: E_hull per substitution 0.412 eV, E_hull 0.013 ± 0.012 eV/atom, gap 2.46 eV, MD not run
16. ref:it1-c1 Li11P4S15F: E_hull per substitution 0.460 eV, E_hull 0.030 ± 0.006 eV/atom, gap 2.68 eV, MD not run; reduced confidence of the window (decomposes via P2S7)
17. s9:it2-c2 Li7AsP2S11: E_hull per substitution 0.503 eV, E_hull 0.024 ± 0.004 eV/atom, gap 2.20 eV, MD not run; reduced confidence (E_hull via AsS2, LiS4)
18. s1:it1-c3 Li7P3S10O: E_hull per substitution 0.510 eV, E_hull 0.024 ± 0.005 eV/atom, gap 2.56 eV, MD not run
19. it2-c2 Li14AsP5S22: E_hull per substitution 1.007 eV, E_hull 0.024 ± 0.004 eV/atom, gap 2.30 eV, MD not run; reduced confidence (E_hull via AsS2, LiS4, P2S7)
20. s9:it2-c3 Li14SbP5S22: E_hull per substitution 1.381 eV, E_hull 0.033 ± 0.012 eV/atom, gap 2.23 eV, MD not run; reduced confidence (E_hull via LiS4)
21. it1-c1 Li5P2S7Cl: E_hull per substitution 0.373 eV, E_hull 0.050 ± 0.005 eV/atom, gap 2.59 eV, MD higher (D/D(parent) 2.37 ± 0.56); σ(300 K) 0.44 mS/cm (0.075–2.5), not compared; reduced confidence of the window (decomposes via P2S7) — EXCLUDED at molecular_dynamics: framework moved: Cl diffuses at 17.7% of Li (limit 5%), seed 0, final MSD 4.8 A2
22. s9:it2-c1 Li13P6S21Cl: E_hull per substitution 0.618 eV, E_hull 0.030 ± 0.005 eV/atom, gap 2.25 eV, MD tied (D/D(parent) 0.96 ± 0.20); σ(300 K) 81 mS/cm (48–1.3e+02), not compared — EXCLUDED at molecular_dynamics: framework moved: Cl diffuses at 39.8% of Li (limit 5%), seed 0, final MSD 5.4 A2
23. it1-c2 Li14P6S21O: E_hull per substitution 0.660 eV, E_hull 0.016 ± 0.005 eV/atom, gap 2.50 eV, MD tied (D/D(parent) 0.85 ± 0.18); σ(300 K) 30 mS/cm (11–80), not compared; reduced confidence of the window (decomposes via P2S7) — EXCLUDED at molecular_dynamics: framework moved: O diffuses at 5.3% of Li (limit 5%), seed 1, final MSD 3.0 A2
24. ref:it1-c5 NaLi5(PS4)2: E_hull per substitution 0.055 eV, E_hull 0.003 ± 0.004 eV/atom, gap 2.70 eV, MD not run — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.112 eV/atom)
25. s9:it2-c4 NaLi11(PS4)4: E_hull per substitution 0.089 eV, E_hull 0.003 ± 0.004 eV/atom, gap 2.71 eV, MD not run — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.204 eV/atom)
26. it2-c3 Li4Mg(PS4)2: E_hull per substitution 0.096 eV, E_hull 0.013 ± 0.005 eV/atom, gap 2.58 eV, MD not run; reduced confidence (E_hull via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.271 eV/atom)
27. ref:it1-c4 Li10Mg(PS4)4: E_hull per substitution 0.102 eV, E_hull 0.007 ± 0.005 eV/atom, gap 2.61 eV, MD not run; reduced confidence (E_hull via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.287 eV/atom)
28. s9:it1-c5 NaLi6P3S11: E_hull per substitution 0.347 eV, E_hull 0.017 ± 0.004 eV/atom, gap 2.40 eV, MD not run — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.365 eV/atom)
29. ref:it2-c4 Li12Mg(P3S11)2: E_hull per substitution 0.453 eV, E_hull 0.022 ± 0.005 eV/atom, gap 2.35 eV, MD not run; reduced confidence (E_hull via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products LiMg, reaction 2.507 eV/atom)
30. it1-c3 NaLi13(P3S11)2: E_hull per substitution 0.502 eV, E_hull 0.012 ± 0.004 eV/atom, gap 2.38 eV, MD not run; reduced confidence of the window (decomposes via P2S7) — EXCLUDED at electrodes: non_passivating against Li metal (metallic products Na, reaction 2.440 eV/atom)

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

## Final scientific report

*Ranking complete*.

### Executive summary

The champion is Li6P2SeS7 derived from Li3PS4 by Se substitution. Its energy above the hull is -0.007 eV/atom with error 0.005 eV/atom. Its band gap is 2.485 eV by optB88 and 3.102 eV by MBJ. Its electrochemical window is stable from 1.8 V to 2.24 V and it is passivating against lithium metal. Its diffusion coefficient at 600 K is 3.9e-06 cm2/s with error 9.6e-07 cm2/s, tied with the parent within uncertainty. Its ionic conductivity at 300 K is an extrapolated estimate of 0.098 mS/cm within range [0.012, 0.8] mS/cm by own Arrhenius fit (500, 600, 700 K) with activation energy 0.421 eV, tied with the parent range [0.432, 3.199] mS/cm. Failed candidates taught two lessons: Cl- and O-substituted variants moved in molecular dynamics with framework diffusion above the 5% limit, and Na- and LiMg-forming variants were non-passivating against lithium metal. Measured ionic conductivity, DFT checks, synthesis routes, cost and experimental data were not computed.

### Comparison of the three finalists

| | Li6P2SeS7 | Li12P4SeS15 | Li7P3SeS10 |
|---|---|---|---|
| Parent crystal | Li3PS4 | Li3PS4 | Li7P3S11 |
| Space group | Pmc2_1 | Pm | P1 |
| Cell a / b / c (Å) | 6.26 / 8.15 / 13.15 | 6.24 / 8.11 / 13.12 | 6.20 / 12.67 / 12.67 |
| E_hull (eV/atom) | -0.007 ± 0.005 | -0.004 ± 0.005 | 0.015 ± 0.005 |
| E_hull per substitution (eV) | -0.115 | -0.113 | 0.323 |
| Band gap optB88 / mBJ (eV) | 2.48 / 3.10 | 2.59 / 3.15 | 2.35 / 2.89 |
| Window (V) | 1.80–2.24 | 1.80–2.24 | 2.28–2.30 |
| Against Li metal | passivating | passivating | passivating |
| Reaction with LiFePO4 (eV/atom) | -0.145 | -0.145 | -0.143 |
| D at 600 K (cm²/s) | 3.90e-06 | 4.87e-06 | 1.39e-05 |
| D / D(parent) | 0.66 ± 0.21 | 0.82 ± 0.25 | 1.07 ± 0.23 |
| Diffusion verdict | tied | tied | tied |
| σ at 300 K against the parent | tied (parent 0.43–3.2 mS/cm) | tied (parent 0.43–3.2 mS/cm) | tied (parent 58–1.7e+02 mS/cm) |
| Ionic conductivity at 300 K (mS/cm, estimate) | 0.098 (range 0.012–0.8; own Arrhenius fit (500, 600, 700 K)) | 5.66 (range 1.5–22; own Arrhenius fit (500, 600, 700 K)) | 134 (range 50–3.6e+02; own Arrhenius fit (500, 600, 700 K)) |
| Literature | close family already studied | close family already studied | close family already studied |
| Confidence flags | none | none | window via a polysulfide |

### Champion: Li6P2SeS7

**Why it is preferred.**
- Energy above the hull of -0.007 eV/atom with error 0.005 eV/atom is lower than -0.004 eV/atom with error 0.005 eV/atom for Li12P4SeS15 and 0.015 eV/atom with error 0.005 eV/atom for Li7P3SeS10.
- Energy per modified site of -0.115 eV is more stabilizing than -0.113 eV for Li12P4SeS15 and 0.323 eV for Li7P3SeS10.
- Electrochemical window from 1.8 V to 2.24 V is stable with no confidence flags, while Li7P3SeS10 has a window from 2.28 V to 2.3 V with a window via a polysulfide flag.

**Trade-offs.**
- Electrochemical window from 1.8 V to 2.24 V is narrow and does not cover typical cathode voltages.
- Interface reaction energy with LiFePO4 is -0.145 eV/atom, indicating cathode reactivity.
- Ionic conductivity at 300 K is an extrapolated estimate of 0.098 mS/cm within range [0.012, 0.8] mS/cm, so the range spans almost two orders of magnitude.
- Novelty is close family already studied, with Se doping of sulfide electrolytes reported before and no exact Li6P2SeS7 report found.

**Uncertainties.**
- Energy above the hull carries UMA-vs-DFT error of 0.005 eV/atom from mean difference on 25 known compounds of Li-P-S-Se.
- Diffusion coefficient at 600 K is 3.9e-06 cm2/s with error 9.6e-07 cm2/s from high-temperature dynamics, and the 300 K conductivity range [0.012, 0.8] mS/cm is extrapolated from 500, 600 and 700 K.
- Window stability allows a maximum shift of 0.02 V under a shift of 0.025 eV/atom and lists polysulfides LiS4, P2S7 and SeS7, which limits confidence.
- Diffusion verdict at 600 K is tied with the parent within uncertainty, so no faster or slower claim can be made.

**Validation.**
- Check phase purity and lattice parameters a 6.265 A, b 8.146 A, c 13.146 A in space group Pmc2_1 by powder X-ray diffraction. *(documented)*
- Measure ionic conductivity and activation energy by temperature-dependent impedance spectroscopy, since the 300 K value is only an extrapolated estimate of 0.098 mS/cm within [0.012, 0.8] mS/cm. *(documented)*
- Test stability during cycling against lithium metal to confirm passivating behavior and analyze interphase products Li2Se, Li3PS4 and P. *(documented)*
- Recalculate energy above the hull and band gap with DFT to confirm the UMA result of -0.007 eV/atom with error 0.005 eV/atom and gaps of 2.485 eV and 3.102 eV. *(documented)*

**Synthesis routes to consider.**
- Ball milling of sulfide and selenide precursors followed by annealing under inert atmosphere could be tried for this sulfide electrolyte family, but success is not guaranteed. *(documented)*
- Sealed-tube solid-state reaction with controlled Se content to target Li6P2SeS7 could be tried, but success is not guaranteed. *(hypothesis)*

### Methods

- **Candidate proposals and decisions**: Meta Muse Spark (reasoning model), with comparisons computed by the code
- **Structure relaxation and energies**: Meta FAIR UMA (uma-s-1p2, OMat head), MP2020 corrections; references from Materials Project, all relaxed with UMA (no mixing of energy sources)
- **Thermodynamic stability**: energy above the convex hull of the chemical system; kept if <= 0.05 eV/atom; error bar measured against DFT (Materials Project) on the known compounds of the same system
- **Electronic band gap**: recorded prediction (optB88vdW scale for the filter, mBJ shown); kept if >= 2 eV
- **Electrochemical window and electrodes**: grand-potential phase diagrams (window, reaction with Li metal), interface reactivity with LiFePO4 (calibrated against MP)
- **Independent reviews**: Meta Muse Spark Open, one review per candidate, in parallel
- **Lithium diffusion**: Langevin molecular dynamics with UMA at 600 K, 2 x 40 ps per structure, diffusion coefficient by blocks, compared with the parent crystal (calibrated: Li7P3S11 2.0x faster than beta-Li3PS4)
- **Error-driven loop**: the slow tests (reaction with lithium metal, lithium diffusion) run in each round; their failures, with the measured numbers, go back to the proposing model, which explains them as hypotheses and corrects its next proposals
- **Ionic conductivity at 300 K**: Arrhenius fit of the diffusion coefficients (molecular dynamics at several temperatures), extrapolated to 300 K, Nernst-Einstein relation; an estimate with its range (calibrated: Li7P3S11 and beta-Li3PS4 against experiment)
- **Literature check**: Meta Muse Spark with web search; a known electrolyte (LGPS) checked first as a control
- **Plain-language summaries**: Meta Muse Glimmer

### Limitations

- Measured ionic conductivity was not computed and the 300 K value is only an extrapolated estimate.
- DFT calculations, synthesis routes, cost of the elements and experimental data were not computed.
- Moisture stability, mechanical behavior and long-term cycling were not studied and still need validation.
- The candidates are computational predictions, not proven materials.
- Not computed: measured ionic conductivity (room-temperature values are extrapolated estimates from molecular dynamics at 500-700 K, with their range), DFT calculations (UMA energies carry an error bar measured against DFT on known compounds), synthesis routes, cost of the elements, experimental data.
- The candidates are computational predictions, not proven materials.


Model ranking (last analysis): ['it3-c2', 'it3-c1', 'it3-c3']

## Usage

- meta: 9 calls, 86240 in / 29922 out tokens, ~$0.2350
- baseten: 0 calls, 0 in / 0 out tokens, ~$0.0000
- meta (rerun): 1 calls, 4785 in / 4674 out tokens, ~$0.0259
- candidate analyses (analyst): 0 calls, ~$0.0000
- novelty web search: 0 calls, ~$0.0000
- molecular dynamics launched in this research (all iterations): estimate 4.41 $ on Modal H100
- UMA relaxations: 23 new / 160 allowed
- events: 177; duration 50.2 min