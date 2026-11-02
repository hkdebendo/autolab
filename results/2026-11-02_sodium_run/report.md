# AutoLab loop report

**Domain.** sodium. **Goal.** Find new sodium solid electrolytes derived from Na3PS4 or Na3SbS4 that stay stable against sodium metal and let Na+ move fast.

**Parents.** Na3PS4 mp-28782 (Na6P2S8, 16 atoms); Na3SbS4 mp-10167 (Na3Sb1S4, 8 atoms); Na3Zr2Si2PO12 mp-532695 (Na12Zr8Si8P4O48, 80 atoms)
**Settings.** 3 iterations max, 3 candidates max, 160 new UMA relaxations max; brain meta, fallback baseten.
**Stop reason.** iterations done

## Iteration 1

**Hypothesis.** Combining softer anions, vacancy-creating aliovalent doping in sulfides and isovalent framework expansion in NASICON can simultaneously maintain stability against Na metal and widen Na+ migration pathways.

_baseten, 1 attempt(s), 1183 in / 5664 out tokens, ~$0.0255, 21.3 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-28782 | S->Se x2 | Isovalent Se for S softens and expands the thio-phosphate lattice, widening Na+ channels and lowering migration barriers while staying charge neutral. |
| it1-c2 | mp-28782 | P->W x1, -1 Li | W6+ for P5+ in Na6P2S8 creates charge-compensating Na vacancies (Na5PWS8) as known in W-doped Na3PS4/Na3SbS4 to enable vacancy-mediated Na+ conduction. |
| it1-c3 | mp-532695 | Si->Ge x4 | Ge4+ for Si4+ in Na12Zr8Si8P4O48 isovalently expands the NASICON bottleneck and lattice, improving Na+ pathway size while oxide framework retains stability vs Na metal. |

<details><summary>Reasoning summary (proposals)</summary>

Need to propose substitutions. We have parents: Na3PS4 Na6P2S8 nsites 16; Na3SbS4 Na3Sb1S4 nsites 8; Na3Zr2Si2PO12 Na12Zr8Si8P4O48 nsites 80.

Goal electrolytes. Must be charge neutral.

We need to propose diverse chemically motivated.

Elements allowed: Na+, Li+, K+, Mg2+, Ca2+, Sr2+, Ba2+, Zn2+, Al3+, Ga3+, In3+, Sc3+, Y3+, La3+, B3+, Si4+, Ge4+, Sn4+, Ti4+, Zr4+, Hf4+, P5+, As5+, Sb5+, Nb5+, Ta5+, W6+, Mo6+, O-2, S-2, Se-2, F-1, Cl-1, Br-1, I-1.

We need to aim for stable against Na metal and conductive.

We have 3 parents. Need propose up to 3 substitutions.

We need to think about compositions not in MP. Must be careful.

General strategies for Na3PS4 type: anion substitution Se, Cl, Br, doping; cation substitution.

Charge neutrality: Example for Na6P2S8.

We can do: replace S with Se is isovalent: no vacancy.

Replace S with Cl need vacancy: S(-2) -> Cl(-1): +1 per substitution, need remove Na+ to compensate.

Replace P with Si need vacancy? P5+ -> Si4+ : -1, need add? But we cannot add Na? li_vacancies field only removes Na. Wait how to compensate aliovalent? Let's see format: substitution {"remove": "S", "add": "Se", "count":2, "li_vacancies":0}. It replaces sites. li_vaca [...]

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it1-c1 | Na3PSeS3 | 3/3 | 1.3 | 0.002 | 0.018 | 2.27 / 2.93 | no | — | passed |
| it1-c2 | Na5PWS8 | 2/2 | 11.7 | 0.015 | 0.115 | 2.09 / 2.51 | no (reduced confidence: decomposes via NaS) | — | passed |
| it1-c3 | Na3Zr2SiGePO12 | 7/7 | 1.0 | 0.002 | 0.046 | 4.20 / 4.88 | no | — | passed |
- it1-c1 decomposes into: Na3PS4 0.75, Na3PSe4 0.25
- it1-c2 decomposes into: Na3PS4 0.53, NaS 0.27, WS2 0.20
- it1-c3 decomposes into: Na3Zr2Si2PO12 0.50, Na4Ge9O20 0.17, Na4P2O7 0.16, ZrO2 0.14

**Slow tests of this iteration (fed back to the model):**

- Result: Na3PSeS3 (it1-c1) passed the Na diffusion at 600 K (molecular dynamics, against its parent): tied with its parent (D/D(parent) = 0.94 ± 0.71).
- Negative result: Na5PWS8 (it1-c2) failed the contact test with Na metal: non_passivating against Na metal (metallic products W, reaction 1.452 eV/atom).

**The model's reading of the failures (hypotheses, not measurements):**

- it1-c2: hypothesis: Aliovalent W-for-P introduces reducible W6+ that is reduced to metallic W on Na contact with large driving force 1.452 eV/atom. — correction: Avoid reducible 5d metals (W, Mo) on P/Sb sites and instead use isovalent p-block substitution or S->Se anion mixing with charge neutrality kept via Na vacancy count.


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **ranking on one parent**, mp-28782: E_hull per atom (lowest first): it1-c1 0.002, it1-c2 0.015; E_hull per substitution (lowest first): it1-c1 0.018, it1-c2 0.115; band gap optB88 (highest first): it1-c1 2.266, it1-c2 2.093

</details>

**Analysis.** ranking ['it1-c1', 'it1-c3']; stop=False

- Within mp-28782, S->Se gives lowest E_hull per substitution (lowest first: it1-c1 0.018, it1-c2 0.115) and retains Na-metal passivation with intact framework.
- Aliovalent W-for-P fails Na-metal contact (metallic W, 1.452 eV/atom) despite gap >2 eV, showing high-valent d-metals drive non-passivating reduction.
- Ge-for-Si NASICON expansion (Na3Zr2SiGePO12, e_hull 0.0023 eV/atom, gap 4.199 eV) stays passivating, supporting isovalent framework expansion strategy.

**Next direction.** Systematically explore S->Se/Te anion mixing in Na3PS4/Na3SbS4 and isovalent Si->Ge expansion in NASICON avoiding reducible cations.

_baseten, 1 attempt(s), 2559 in / 2427 out tokens, ~$0.0135, 9.3 s_

<details><summary>Reasoning summary (analysis)</summary>

Need ranking candidates with status passed and not excluded.

We have:
it1-c1: passed, e_hull 0.002236 per atom, e_hull_per_sub 0.0179, passivating, MD tied -> not excluded.
it1-c2: passed but excluded at electrodes non_passivating -> so excluded, cannot rank? Instruction: Rank only candidates with status "passed" and not excluded, best first... So it1-c2 excluded, so not ranked.
it1-c3: passed, e_hull 0.002305, e_hull_per_sub 0.0461, passivating, no exclusion. Parent is mp-532695 NASICON.

So candidates to rank: it1-c1 and it1-c3.

Best first by e_hull_per_substitution unless comparisons or slow tests give reason otherwise.
e_hull_per_sub: it1-c1 0.0179, it1-c3 0.0461 => it1-c1 better.
Comparisons: for mp-28782, it1-c1 has lowest E_hull per atom and per substitution, highest gap among that parent. So supports ranking.

Slow tests: it1-c1 tied diffusion but calibration failed, so not conclude worse. But still information only. Framework intact.

it1-c2 failure: Need failure_analysis: for EACH failed slow test, its id, hypothesis, correction. Failed is it1-c2 non_passivating against Na metal with W metallic products. Hypothesis: high-valent 5d transition metal W6+ dopant on P site i [...]

</details>

## Iteration 2

**Hypothesis.** Isovalent soft-anion (Se, Sb, Ge) lattice expansion plus halogen-induced Na vacancies widen Na+ pathways while retaining Na-metal passivation, correcting it1-c2 failure by avoiding reducible W6+ that formed metallic W.

_baseten, 1 attempt(s), 3119 in / 7041 out tokens, ~$0.0338, 27.5 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it2-c1 | mp-10167 | S->Se x1 | Isovalent Se for S on Na3SbS4 softens and expands SbS4 tetrahedra to widen Na+ bottlenecks as in passivating Na3PSeS3 (it1-c1) without creating reducible species. |
| it2-c2 | mp-28782 | S->Br x1, -1 Li | Aliovalent Br-for-S with Na vacancy combines vacancy creation and larger anion opening of Na+ channels, a classic halogen-doping route that stays passivating unlike W6+ in it1-c2. |
| it2-c3 | mp-532695 | Si->Ge x8 | Full Si-to-Ge isovalent NASICON framework expansion maximizes bottleneck size building on low-hull half-exchanged it1-c3 while preserving high band gap and Na-metal passivation. |

<details><summary>Reasoning summary (proposals)</summary>

We need to propose at most 3 new substitutions. History shows iteration 1 tried 3 proposals. We need to propose diverse and chemically motivated (Na vacancies, softer or larger anions that widen Na pathways, aliovalent dopants known in sodium conductors), each with one-sentence rationale. Never repeat substitution already evaluated.

Previous substitutions:
- it1-c1: mp-28782 S->Se count2 li_vac 0 => Na3PSeS3 passed, tied diffusion, very low hull. Need to not repeat. So we should not propose same exact remove/add/count/li_vacancies on same parent.
- it1-c2: mp-28782 P->W count1 li_vac1 => failed passivation. Avoid W.
- it1-c3: mp-532695 Si->Ge count4 li_vac0

We must propose new ones. The lessons say lowest E_hull per substitution for it1-c1 etc. Next direction: systematically explore S->Se/Te anion mixing in Na3PS4/Na3SbS4 and isovalent Si->Ge expansion in NASICON avoiding reducible cations.

We need to consider rules: Only elements allowed. Fixed oxidation states. Must stay charge neutral. Counts refer to parent cell.

We have parents:
mp-28782 Na3PS4 cell Na6P2S8 nsites16
mp-10167 Na3SbS4 cell Na3Sb1S4 nsites8
mp-532695 Na3Zr2Si2PO12 cell Na12Zr8Si8P4O48 nsites80

We need to des [...]

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it2-c1 | Na3SbSeS3 | 1/1 | 0.0 | 0.016 | 0.124 | 1.77 / 2.75 | — (reduced confidence: decomposes via NaS2) | — | rejected at bandgap: gap 1.77 < 1.8 eV |
| it2-c2 | Na5P2S7Br | 2/2 | 5.9 | 0.061 | 0.460 | — | — (reduced confidence: decomposes via Na2S5) | — | rejected at hull: E_hull 0.061 > 0.05 eV/atom |
| it2-c3 | Na3Zr2Ge2PO12 | 1/1 | 0.0 | 0.003 | 0.025 | 3.98 / 4.78 | no | — | passed |
- it2-c1 decomposes into: Na3SbS3 0.58, NaSe2 0.19, NaSbS2 0.17, NaS2 0.06
- it2-c2 decomposes into: Na2PS3 0.64, NaPS3 0.13, NaBr 0.13, Na2S5 0.09
- it2-c3 decomposes into: Na4Ge9O20 0.33, Na4P2O7 0.33, ZrO2 0.28, Na2ZrGe2O7 0.06


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **ranking on one parent**, mp-28782: E_hull per atom (lowest first): it1-c1 0.002, it1-c2 0.015, it2-c2 0.061; E_hull per substitution (lowest first): it1-c1 0.018, it1-c2 0.115, it2-c2 0.460; band gap optB88 (highest first): it1-c1 2.266, it1-c2 2.093
- **ranking on one parent**, mp-532695: E_hull per atom (lowest first): it1-c3 0.002, it2-c3 0.003; E_hull per substitution (lowest first): it2-c3 0.025, it1-c3 0.046; band gap optB88 (highest first): it1-c3 4.199, it2-c3 3.978

</details>

**Analysis.** ranking ['it1-c1', 'it2-c3', 'it1-c3']; stop=False

- Na3SbSeS3 (it2-c1) rejected with gap 1.77 < 1.8 eV vs Na3PSeS3 (it1-c1) gap 2.266 eV, showing Sb-Se combination lowers gap more than P-Se.
- Br + Na-vacancy Na5P2S7Br (it2-c2) is least stable on mp-28782 (E_hull per substitution highest: it2-c2 0.460 vs it1-c1 0.018, it1-c2 0.115) with E_hull 0.061 >0.05 eV/atom.
- NASICON Ge expansion remains passivating with large gaps and improves per-site stability when fully substituted: E_hull per substitution lowest first it2-c3 0.025 vs it1-c3 0.046 and gaps 3.978 vs 4.199 eV.

**Next direction.** Explore lower-dose Se (1 Se per 8 f.u.) and Br/vacancy (<1 per cell) in Na3PS4/Na3SbS4 to keep E_hull <0.05 and gap >1.8 eV while retaining passivation, avoiding reducible metals.

_baseten, 1 attempt(s), 4021 in / 1843 out tokens, ~$0.0129, 7.0 s_

<details><summary>Reasoning summary (analysis)</summary>

We need to analyze goal: Find new sodium solid electrolytes derived from Na3PS4 or Na3SbS4 that stay stable against sodium metal and let Na+ move fast.

Iteration 2 results:
- it2-c1: Na3SbSeS3 rejected bandgap 1.77 <1.8
- it2-c2: Na5P2S7Br rejected hull 0.061
- it2-c3: Na3Zr2Ge2PO12 passed, e_hull 0.002545, per sub 0.0255, gap 3.978, passivating

Comparisons:
ranking on mp-28782: E hull per atom lowest: it1-c1 0.002, it1-c2 0.015, it2-c2 0.061 ; per sub: it1-c1 0.018, it1-c2 0.115, it2-c2 0.460
ranking on mp-532695: per atom: it1-c3 0.002, it2-c3 0.003 ; per sub: it2-c3 0.025, it1-c3 0.046 ; gap highest: it1-c3 4.199, it2-c3 3.978

Slow tests: none this iteration. Previous: it1-c1 passed diffusion tied, passivating; it1-c2 failed contact non-passivating due W; it1-c3 passivating.

We need to rank only candidates with status passed and not excluded, best first by e_hull_per_substitution unless comparisons or slow tests give reason otherwise.

Passed candidates overall: it1-c1 (0.0179), it1-c3 (0.0461), it2-c3 (0.0255). Also it1-c2 is passed but excluded at electrodes (non_passivating). So excluded. So ranking candidates: it1-c1, it2-c3, it1-c3. Sorted by per substitution: it1-c1 0. [...]

</details>

## Iteration 3

**Hypothesis.** Isovalent soft-anion and pnictogen lattice expansion in Na3PS4 plus Hf framework expansion in NASICON widen Na+ pathways while preserving Na-metal passivation and gaps by avoiding reducible W and vacancy-halogen hull penalties.

_baseten, 1 attempt(s), 4447 in / 7233 out tokens, ~$0.0363, 26.8 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it3-c1 | mp-28782 | S->Se x1 | Low-dose isovalent S->Se softens sulfide sublattice without Na vacancies to keep gap >1.8 eV and passivation, correcting it2-c1 Sb-Se gap collapse (1.77 eV) and it2-c2 Br+vacancy hull penalty (0.061 eV/atom). |
| it3-c2 | mp-28782 | P->Sb x1 | Isovalent P->Sb expands tetrahedra to open Na channels using non-reducible p-block cation, correcting it1-c2 W6+ reduction to metallic W (1.452 eV/atom non-passivating). |
| it3-c3 | mp-532695 | Zr->Hf x4 | Isovalent Zr->Hf in NASICON continues Si->Ge passivating low-hull trend (it1-c3 0.0023, it2-c3 0.0025 eV/atom, gaps ~4 eV) for framework expansion without redox activity. |

<details><summary>Reasoning summary (proposals)</summary>

Need to propose up to 3 new substitutions, diverse, chemically motivated, charge neutral, using allowed elements/oxidation states, not repeat history.

We have parents:
mp-28782 Na3PS4 cell Na6P2S8 (16 sites)
mp-10167 Na3SbS4 cell Na3Sb1S4 (8 sites)
mp-532695 NASICON Na12Zr8Si8P4O48 (80 sites) => Na3Zr2Si2PO12

We need to learn from lessons.

Lessons:
- Within mp-28782, S->Se gives lowest E_hull per substitution (0.018) and retains passivation, tied diffusion.
- W-for-P fails (non-passivating, W metal)
- Ge-for-Si NASICON expansion stays passivating, low E_hull.
- Na3SbSeS3 gap 1.77 <1.8 fails, while Na3PSeS3 gap 2.266 passes, so Sb+Se lowers gap more.
- Br + vacancy Na5P2S7Br highest E_hull per substitution 0.46, failed hull.
- NASICON Ge full substitution better per-site.

We need to propose new substitutions, not repeated:

History substitutions:
- it1-c1: mp-28782 S->Se count2
- it1-c2: mp-28782 P->W count1 +1 vacancy
- it1-c3: mp-532695 Si->Ge count4
- it2-c1: mp-10167 S->Se count1
- it2-c2: mp-28782 S->Br count1 +1 vacancy
- it2-c3: mp-532695 Si->Ge count8

We cannot repeat these exactly.

Need to propose charge-neutral substitutions.

We need to consider allowed elements: Na [...]

</details>

| Candidate | Formula | Arrangements/converged | Spread (meV/at) | E_hull per atom (eV/atom) | E_hull per substitution (eV per modified site) | Gap optB88/mBJ (eV) | S-S | Known in MP | Result |
|---|---|---|---|---|---|---|---|---|---|
| it3-c1 | Na6P2SeS7 | 1/1 | 0.0 | 0.002 | 0.031 | 2.26 / 3.12 | no | — | passed |
| it3-c2 | Na6SbPS8 | 1/1 | 0.0 | 0.008 | 0.130 | 2.24 / 3.01 | no (reduced confidence: decomposes via NaS2) | — | passed |
| it3-c3 | Na3HfZrSi2PO12 | 0/0 | — | — | — | — | — | mp-2715300, mp-2715468 | rejected at known: composition already in Materials Project: mp-2715300, mp-2715468 |
- it3-c1 decomposes into: Na3PS4 0.88, Na3PSe4 0.12
- it3-c2 decomposes into: Na3PS4 0.50, Na3SbS3 0.29, NaS2 0.12, NaSbS2 0.08


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, S->Se x1 on mp-10167 vs mp-28782: E_hull per atom: Na6P2SeS7 (it3-c1) 0.002 < Na3SbSeS3 (it2-c1) 0.016 eV/atom (better: it3-c1); E_hull per substitution: Na6P2SeS7 (it3-c1) 0.031 < Na3SbSeS3 (it2-c1) 0.124 eV per modified site (better: it3-c1); band gap optB88: Na6P2SeS7 (it3-c1) 2.259 > Na3SbSeS3 (it2-c1) 1.768 eV (better: it3-c1)
- **ranking on one parent**, mp-28782: E_hull per atom (lowest first): it3-c1 0.002, it1-c1 0.002, it3-c2 0.008, it1-c2 0.015, it2-c2 0.061; E_hull per substitution (lowest first): it1-c1 0.018, it3-c1 0.031, it1-c2 0.115, it3-c2 0.130, it2-c2 0.460; band gap optB88 (highest first): it1-c1 2.266, it3-c1 2.259, it3-c2 2.237, it1-c2 2.093
- **ranking on one parent**, mp-532695: E_hull per atom (lowest first): it1-c3 0.002, it2-c3 0.003; E_hull per substitution (lowest first): it2-c3 0.025, it1-c3 0.046; band gap optB88 (highest first): it1-c3 4.199, it2-c3 3.978

</details>

**Analysis.** ranking ['it1-c1', 'it3-c1', 'it3-c2']; stop=False

- Low-dose S->Se on Na3PS4 (it3-c1 Na6P2SeS7, 0.002 eV/atom, 0.031 per site, gap 2.259 eV) beats same substitution on Na3SbS3 (it2-c1 0.016 eV/atom, 0.124 per site, gap 1.77 eV) on both hull and gap.
- On mp-28782 per-site hull ranking is it1-c1 0.018 < it3-c1 0.031 < it1-c2 0.115 < it3-c2 0.130 < it2-c2 0.460, showing isovalent S->Se retains passivation while vacancy-halogen Br and reducible W incur large penalties.
- Isovalent P->Sb (it3-c2, gap 2.237 eV, passivating) is viable but per-site hull 0.130 and polysulfide NaS2 decomposition make it less stable than S->Se.

**Next direction.** Test minimal co-doping of 1-2 Se plus 1 Sb in Na3PS4 and single-site Te without Na vacancies to increase lattice expansion while keeping E_hull <0.05 and gap >1.8 eV.

_baseten, 1 attempt(s), 5409 in / 4593 out tokens, ~$0.0263, 15.7 s_

<details><summary>Reasoning summary (analysis)</summary>

We need to output JSON ranking, failure_analysis, lessons, next_direction, stop.

Goal: Find new sodium solid electrolytes derived from Na3PS4 or Na3SbS4 that stay stable against Na metal and let Na+ move fast.

Results iteration 3:

- it3-c1: Na6P2SeS7 (S->Se count1) passed, e_hull 0.001933 eV/atom, per substitution 0.0309, gap 2.259, passivating.
- it3-c2: Na6SbPS8 (P->Sb) passed, e_hull 0.00814, per substitution 0.1303, gap 2.237, passivating, but reduced_confidence true, decomposition includes NaS2 polysulfide.
- it3-c3 rejected known.

Need to rank only passed and not excluded. Both passed are passivating, so none excluded. But need to consider lessons? Also previous iterations passed candidates:

We have history: it1-c1 Na3PSeS3 passed, passivating, tied diffusion. it1-c2 passed but non_passivating excluded. it1-c3 Na3Zr2SiGePO12 passed but it's NASICON not relevant? Goal says derived from Na3PS4 or Na3SbS4, but ranking should include? The instruction: Rank only candidates with status "passed" and not excluded, best first by e_hull_per_substitution unless comparisons or slow tests give reason otherwise. Does that mean rank across all iterations? Or just this iteration? Typica [...]

</details>

## Summaries (Muse Glimmer)

**iteration 1.** In iteration 1 the agent tested sulfide/ selenide substitutions and isovalent NASICON expansion for sodium solid electrolytes to keep stability against sodium metal and widen sodium migration pathways. Na3PSeS3 and Na3Zr2SiGePO12 were predicted stable with energy above the hull near 0.00 eV per atom and band gaps of about 2.3 eV and 4.2 eV respectively, and Na3PSeS3 showed sodium diffusion at 600 K tied with its parent. Na5PWS8 was predicted stable with energy above the hull about 0.02 eV per atom and a band gap of about 2.1 eV but failed contact with sodium metal because tungsten is reduced to metallic tungsten with a driving force of about 1.45 eV per atom. The agent concluded that S to Se anion mixing and isovalent Si to Ge NASICON expansion can retain passivation, while aliovalent tungsten for phosphorus introduces reducible d-metal reduction, and will next explore S to Se/Te mixing and isovalent NASICON expansion avoiding reducible cations.

**iteration 2.** In iteration 2 the agent tested isovalent soft-anion expansion with Se, Sb, Ge and a halogen induced sodium vacancy to widen Na+ pathways while keeping sodium metal passivation and avoiding reducible tungsten. Na3SbSeS3 was rejected at the band gap filter with a gap of about 1.8 eV, below the 1.8 eV target, and Na5P2S7Br was rejected at the hull filter with energy above the hull of about 0.06 eV per atom above the 0.05 eV per atom limit. Na3Zr2Ge2PO12 passed both filters with energy above the hull near 0.00 eV per atom and a band gap of about 4.0 eV, suggesting the fully substituted NASICON germanium expansion remains passivating and more stable per substitution than earlier variants.

**iteration 3.** In this iteration the agent tried isovalent soft-anion and pnictogen substitutions in Na3PS4 and Hf-expanded NASICON to widen Na+ pathways while keeping passivation and gaps. Na6P2SeS7 and Na6SbPS8 passed with low energy above the hull of about 0.00 eV per atom and 0.01 eV per atom and band gaps of about 2.3 eV and 2.2 eV, while Na3HfZrSi2PO12 was rejected because the composition is already known. The agent concluded that low-dose sulfur to selenium substitution improves stability and gap relative to other substitutions and that minimal co-doping with selenium and antimony should be tested next.

**run.** The agent proposed nine new sodium solid-electrolyte candidates derived from Na3PS4 or Na3SbS4 and six passed the stability and electronic filtering. Na3PSeS3 was predicted with an energy above the hull of about 0.00 eV per atom and a band gap of about 2.3 eV, and molecular dynamics found its sodium diffusion tied with the parent, about 0.94 times the parent rate. Na3Zr2Ge2PO12 was predicted with an energy above the hull of about 0.00 eV per atom and a band gap of about 4.0 eV, and Na6P2SeS7 was predicted with an energy above the hull of about 0.00 eV per atom and a band gap of about 2.3 eV. One early candidate was excluded because it was not passivating against sodium metal with metallic products and a reaction energy of 1.45 eV per atom. The run ended with three low-energy, insulating finalists, one of which shows diffusion comparable to its parent.

## Final ranking

Order: lowest E_hull per substitution (the Na diffusion verdict is shown as information: its calibration failed, it does not rank); excluded candidates last, with their reason. Candidates are computational predictions, not proven materials.

1. it1-c1 Na3PSeS3 **finalist**: E_hull 0.002 ± 0.002 eV/atom, per substitution 0.018 eV, gap 2.27 eV, Na diffusion tied (D/D(parent) 0.94 ± 0.71)
2. it2-c3 Na3Zr2Ge2PO12 **finalist**: E_hull 0.003 ± 0.008 eV/atom, per substitution 0.025 eV, gap 3.98 eV, Na diffusion not simulated
3. it3-c1 Na6P2SeS7 **finalist**: E_hull 0.002 ± 0.002 eV/atom, per substitution 0.031 eV, gap 2.26 eV, Na diffusion not simulated
4. it1-c3 Na3Zr2SiGePO12: E_hull 0.002 ± 0.007 eV/atom, per substitution 0.046 eV, gap 4.20 eV, Na diffusion not simulated
5. it3-c2 Na6SbPS8: E_hull 0.008 ± 0.002 eV/atom, per substitution 0.130 eV, gap 2.24 eV, Na diffusion not simulated
6. it1-c2 Na5PWS8: E_hull 0.015 ± 0.002 eV/atom, per substitution 0.115 eV, gap 2.09 eV, Na diffusion not simulated — EXCLUDED at electrodes: non_passivating against Na metal (metallic products W, reaction 1.452 eV/atom)

## Electrodes (UMA + MP2020 energies)


| Candidate | Formula | Window (V vs Na/Na+) | Against Na metal | Worst reaction with  (eV/atom) | Confidence | Decision |
|---|---|---|---|---|---|---|
| it1-c1 | Na3PSeS3 | 1.52–1.70 | passivating (1.493) | — | normal | kept |
| it2-c3 | Na3Zr2Ge2PO12 | 1.70–3.28 | passivating (0.496) | — | normal | kept |
| it3-c1 | Na6P2SeS7 | 1.52–1.70 | passivating (1.467) | — | normal | kept |
| it1-c3 | Na3Zr2SiGePO12 | 1.70–3.28 | passivating (0.457) | — | normal | kept |
| it1-c2 | Na5PWS8 | 1.56–1.56 | non_passivating (1.452) | — | reduced (electrolyte decomposes via NaS, NaS2; window limits move by — V when the polysulfide energies shift by ±0.025 eV/atom) | excluded: non_passivating against Na metal (metallic products W, reaction 1.452 eV/atom) |
| it3-c2 | Na6SbPS8 | zero width (not a rejection) | passivating (1.599) | — | normal (window via NaS2, robust: limits move by 0.00 V for ±0.025 eV/atom on the polysulfides) | kept |

Reduced confidence: the decomposition of the electrolyte (window limits, Na metal) goes through a polysulfide, where UMA is least reliable, and the window limits move by more than 0.1 V when every polysulfide energy is shifted by ±0.025 eV/atom (twice the largest UMA-vs-DFT difference measured on known polysulfides). No cathode interface is computed in this domain.

## Choice of the candidates for molecular dynamics

Not simulated yet (the choice): it2-c3, it3-c1, it1-c3, it3-c2. Selected by None: none.

Rationale: —

## Candidate analyses (Muse Spark Open, in parallel)

Not run: no new eligible candidate.

## Na diffusion (600 K, 2 seeds of 40 ps pooled, Modal H100)

Runs computed: 0 of 4 (others from the cache); estimate 0.00 $, about 0 min in parallel.
Not selected but already simulated (verdict from the cache, no cost): it1-c1.

| Structure | Kind | D ± s.e. (cm²/s) | D / D(parent) | Verdict | Conduction | Framework |
|---|---|---|---|---|---|---|
| Na3PS4 (mp-28782) | parent | 2.29e-07 ± 8.6e-08 | — | — | — | intact |
| Na3PSeS3 (it1-c1) | candidate | 2.16e-07 ± 1.4e-07 | 0.94 ± 0.71 | tied | passes | intact |

## Novelty check (literature, web search)

Search date: 2026-11-02. Links come only from the API (its citations, or the relevant search results it returned when it gave no citation). "No publication found in this search" does not mean the material was never reported.

### control-Na3PS4 Na3PS4 (control, expected: already published): already published

Na3PS4 is described as one of the most promising Na+ conductors for solid-state battery applications. It is reported as a sodium ion conductor and promising electrolyte for all-solid-state batteries using Na+ charge carriers. Its ambient-temperature ionic conductivity is reported on the order of 10-4 S cm-1, optimizable by doping and processing. Leading sulfide materials such as Na3PS4 are reported to achieve room-temperature conductivities of 0.1-1 mS/cm.

Sources:
- [Enhancing sodium ionic conductivity in tetragonal-Na3PS4 by halogen doping: a first principles investigation. | MediFind](https://www.medifind.com/articles/publication/182341902)
- [Room-Temperature All-solid-state Rechargeable Sodium-ion Batteries with a Cl-doped Na3PS4 Superionic Conductor. - PDF Download Free](https://d.docksci.com/room-temperature-all-solid-state-rechargeable-sodium-ion-batteries-with-a-cl-dop_5a05bb64d64ab204917a5f3d.html)
- [Room-Temperature All-solid-state Rechargeable Sodium-ion Batteries with a Cl-doped Na3PS4 Superionic Conductor (Journal Article)](https://www.osti.gov/pages/biblio/1559138)
- [, James A. Dawsonb,c , François Fauthe , Emmanuelle Suardf ,](https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/60c74149842e65255bdb1e55/original/a-new-phase-of-the-na-ion-conductor-na3ps4.pdf)
- [Room-Temperature All-solid-state Rechargeable Sodium-ion Batteries with a Cl-doped Na3PS4 Superionic Conductor | Scientific Reports](https://www.nature.com/articles/srep33733)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_1 web searches, 12 sources considered, ~$0.0112, 2026-11-02_

### it1-c1 Na3PSeS3: already published

Members of the solid solution Na3PS4-xSex were prepared by high-temperature reaction, with x = 0, 1 reported as tetragonal and x = 2, 3, 4 as cubic. The x = 1 member is Na3PS3Se, the same composition as Na3PSeS3 written differently, with S/Se disorder around P shown by 31P NMR. The Se-substituted family was also developed as cubic Na3PS4-xSex by mechanochemical and high-temperature routes to expand diffusion pathways and enhance conductivity.

Sources:
- [Drop That Activation Energy: Tetragonal to Cubic Transformations in Na3PS4−xSex for Solid State Sodium Ion Battery Materials](https://www.citedrive.com/en/discovery/drop-that-activation-energy-tetragonal-to-cubic-transformations-in-nasub3subpssub4subisubxsubiseisubxsubi-for-solid-state-sodium-ion-battery-materials/)
- [Effective Approaches of Improving the Performance of Chalcogenide Solid Electrolytes for All-Solid-State Sodium-Ion Batteries](https://www.frontiersin.org/journals/energy-research/articles/10.3389/fenrg.2020.00097/full)

_5 web searches, 31 sources considered, ~$0.0516, 2026-11-02_

### it2-c3 Na3Zr2Ge2PO12: close family already studied

Ge addition to NASICON Na3Zr2Si2PO12 is reported as Na3[Zr2-delta Ge delta]Si2PO12 with delta = 0.1, 0.2, reaching 1.4 x 10(-2) S cm(-1) at 150 C. That work describes Ge lowering the phase-transition temperature and increasing rhombohedral phase fraction. Sc and Ge co-doping is also reported, with highest total conductivity 4.64 × 10⁻³ S cm⁻¹ for Na3.125Zr1.75Sc0.125Ge0.125Si2PO12. These reports substitute Ge on the Zr site while retaining Si2, unlike the queried full Si-by-Ge composition Na3Zr2Ge2PO12.

Sources:
- [Stable zero-sodium-excess solid-state batteries enabled by interphase stratification](https://www.newswise.com/pdf_docs/174342583785964_1-s2.0-S2667141724000582-main.pdf)
- [High-Strength 3D-Ordered Ceramic-Gel Composite Electrolytes Enable Highly Stable Sodium Metal Batteries at − 20 to 60 °C | Nano-Micro Letters | Springer Nature Link](https://link.springer.com/article/10.1007/s40820-025-02032-4)
- [A High‐Performance Monolithic Solid‐State Sodium Battery with Ca<sup>2+</sup> Doped Na<sub>3</sub>Zr<sub>2</sub>Si<sub>2</sub>PO<sub>12</sub> Electrolyte](https://scite.ai/reports/a-high-performance-monolithic-solid-state-sodium-2NeL5pL)
- [Researchers develop high-energy, high-efficiency all-solid-state sodium](https://techxplore.com/news/2024-05-high-energy-efficiency-solid-state.amp)
- [US11830985B2 - Solid electrolyte for all-solid sodium battery, method for producing same, and all-solid sodium battery](https://patents.google.com/patent/US11830985B2/en)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_5 web searches, 56 sources considered, ~$0.0405, 2026-11-02_

### it3-c1 Na6P2SeS7: already published

The Na3PS4-xSex system with S replaced by Se was systematically studied as a Na-ion conductor, monitoring lattice softening and transport by X-ray diffraction and impedance spectroscopy. The exact x=0.5 member, Na3PS3.5Se0.5 equivalent to Na6P2SeS7, was prepared by ball-milling and refined by Rietveld analysis. That composition showed cubic structure with small reflections of tetragonal phase, indicating a minor tetragonal mass fraction.

Sources:
- [Influence of Lattice Dynamics on Na  Transport in the Solid Electrolyte - PDF Free Download](https://d.docecity.com/influence-of-lattice-dynamics-on-na-transport-in-the-solid-e-5f0ea1c573a85.html)

_5 web searches, 32 sources considered, ~$0.0469, 2026-11-02_

Total: 0 calls, ~$0.0000.

## Final scientific report

### Executive summary

The search looked for new sodium solid electrolytes from Na3PS4 or Na3SbS4 that resist sodium metal and allow fast Na+ motion. The champion is Na3PSeS3 derived from Na3PS4, with space group Cc. Its energy above the hull is 0.002 eV/atom with an error bar of 0.002 eV/atom from the mean difference against density functional theory on 23 known compounds of Na-P-S-Se. Its computed band gaps are 2.266 eV and 2.931 eV. Its electrochemical window is 1.52 V to 1.7 V and it is passivating against sodium metal, so it is not thermodynamically stable at 0 V vs Na/Na+. Its diffusion coefficient at 600 K is 2.16e-07 cm²/s with an error of 1.42e-07 cm²/s, with a verdict of tied, meaning its range overlaps the parent and it cannot be called faster or slower. Literature shows this composition is already published in the Na3PS4-xSex family. The other finalists are Na3Zr2Ge2PO12 and Na6P2SeS7. One candidate was excluded for being non-passivating against sodium metal. Room-temperature ionic conductivity, density functional theory checks, cathode interface, grain boundaries, synthesis, element cost and experimental data were not computed. The candidates are computational predictions, not proven materials.

### Comparison of the finalists

| | Na3PSeS3 | Na3Zr2Ge2PO12 | Na6P2SeS7 |
|---|---|---|---|
| Parent crystal | Na3PS4 | Na3Zr2Si2PO12 | Na3PS4 |
| Space group | Cc | P1 | P1 |
| E_hull (eV/atom) | 0.002 ± 0.002 | 0.003 ± 0.008 | 0.002 ± 0.002 |
| E_hull per substitution (eV) | 0.018 | 0.025 | 0.031 |
| Band gap optB88 / mBJ (eV) | 2.27 / 2.93 | 3.98 / 4.78 | 2.26 / 3.12 |
| Window (V vs Na/Na+) | 1.52–1.70 | 1.70–3.28 | 1.52–1.70 |
| Against Na metal | passivating | passivating | passivating |
| D at 600 K (cm²/s) | 2.16e-07 | not computed | not computed |
| D / D(parent) | 0.94 ± 0.71 | not simulated | not simulated |
| Diffusion verdict | tied | not simulated | not simulated |
| Literature | already published | close family already studied | already published |

### Champion: Na3PSeS3

**Why it is preferred.**

- The champion has the lowest energy above the hull per substitution at 0.018 eV, compared with 0.025 eV for Na3Zr2Ge2PO12 and 0.031 eV for Na6P2SeS7, so it comes first by the convention of lowest energy per substitution, not by a significant difference, with the three sharing the same ranking level.
- It is the only finalist with a simulated diffusion coefficient at 600 K, at 2.16e-07 cm²/s with an error of 1.42e-07 cm²/s and a verdict of tied, while diffusion for Na3Zr2Ge2PO12 and Na6P2SeS7 was not simulated.
- It derives from Na3PS4 with an electrochemical window of 1.52 V to 1.7 V, closer to 0 V than the 1.7 V to 3.28 V window of Na3Zr2Ge2PO12, and unlike Na3Zr2Ge2PO12 which derives from Na3Zr2Si2PO12 and is an oxide off the sulfide goal.

**Trade-offs.**

- Its window of 1.52 V to 1.7 V is narrow and not stable at 0 V vs Na/Na+, so stability against sodium metal relies on passivation with risk of thick interphase growth.
- It is already published in the Na3PS4-xSex solid solution, so it is not a new composition, and selenide content brings moisture sensitivity and cost concerns.
- It has no added sodium vacancies, leaving carrier concentration unoptimized, and its band gaps of 2.266 eV and 2.931 eV show electronic insulation but do not guarantee low interfacial resistance.

**Uncertainties.**

- Energies are from a universal potential with an error bar of 0.002 eV/atom, not from density functional theory, which was not computed.
- Diffusion was simulated at 600 K, not at 300 K, and calibration failed because ordered Na3SbS4 came out slower than Na3PS4, the reverse of experiment, so the verdict of tied is information only.
- The diffusion error of 1.42e-07 cm²/s is large relative to the value of 2.16e-07 cm²/s, and room-temperature ionic conductivity was not computed with a range and method.

**Validation to do.**

- Check phase purity and lattice by powder X-ray diffraction with Rietveld refinement against the predicted Cc cell. *(documented)*
- Measure Na+ conductivity and activation energy by impedance spectroscopy as a function of temperature. *(documented)*
- Test stability by cycling against sodium metal and analyzing the interphase by microscopy and spectroscopy. *(documented)*
- Recompute the energy above the hull and the band structure with density functional theory. *(documented)*

**Synthesis routes to consider.**

- Ball milling followed by annealing under inert atmosphere could be tried for this sulfide-selenide family, without guarantee of success. *(documented)*

### Methods

- **Candidate proposals and decisions**: Meta Muse Spark (reasoning model), with comparisons computed by the code
- **Structure relaxation and energies**: Meta FAIR UMA (uma-s-1p2, OMat head), MP2020 corrections; references from Materials Project (the stable phases), all relaxed with UMA
- **Thermodynamic stability**: energy above the convex hull of the system; kept if <= 0.05 eV/atom; error bar measured against DFT (Materials Project) on the known compounds of the same system
- **Electronic band gap**: recorded prediction (optB88vdW scale); kept if >= 1.8 eV
- **Electrochemical window and sodium metal**: grand-potential phase diagrams open to sodium (window vs Na/Na+, reaction with sodium metal)
- **Independent reviews**: Meta Muse Spark Open, one review per candidate, in parallel
- **Sodium diffusion**: Langevin molecular dynamics with UMA at 600 K, 2 x 40 ps per structure, compared with the parent crystal; information only, it neither excludes nor ranks: its calibration failed (ordered Na3SbS4 came out slower than tetragonal Na3PS4 at 600 K, the reverse of experiment)
- **Error-driven loop**: the slow tests (reaction with sodium metal, sodium diffusion) run in each round; their failures, with the measured numbers, go back to the proposing model, which explains them as hypotheses and corrects its next proposals
- **Literature check**: Meta Muse Spark with web search; a known sodium electrolyte (Na3PS4) checked first as a control
- **Plain-language summaries**: Meta Muse Glimmer

### Limitations

- Room-temperature ionic conductivity was not computed, and no measured conductivity should be inferred.
- Density functional theory checks, cathode interface, grain boundaries, synthesis, element cost and experimental data were not computed and are still needed.
- Diffusion at 600 K cannot be presented as faster or slower conduction because calibration failed, and all candidates remain computational predictions, not proven materials.
- Not computed: DFT calculations (UMA energies with an error bar measured against DFT on known compounds), ionic conductivity at room temperature, a calibrated Na diffusion (the Na diffusion at 600 K against the parent is information only: its calibration failed, ordered Na3SbS4 came out slower than Na3PS4, the reverse of experiment), the interface with a sodium cathode, grain boundaries, synthesis, cost of the elements, experimental data.
- The candidates are computational predictions, not proven materials.


Model ranking (last analysis): ['it1-c1', 'it3-c1', 'it3-c2']

## Usage

- meta: 10 calls, 0 in / 0 out tokens, ~$0.0000
- baseten: 10 calls, 28484 in / 37573 out tokens, ~$0.1953
- meta (rerun): 1 calls, 3903 in / 5192 out tokens, ~$0.0269
- candidate analyses (analyst): 0 calls, ~$0.0000
- novelty web search: 0 calls, ~$0.0000
- molecular dynamics launched in this research (all iterations): estimate 2.05 $ on Modal H100
- UMA relaxations: 83 new / 160 allowed
- events: 143; duration 32.6 min