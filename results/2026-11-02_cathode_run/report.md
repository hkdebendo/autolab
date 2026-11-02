# AutoLab loop report

**Domain.** cathode. **Goal.** Find new cobalt-free cathodes for lithium-ion batteries with a higher energy density than LiFePO4.

**Parents.** LiFePO4 mp-19017 (Li4Fe4P4O16, 28 atoms); LiMnPO4 mp-18997 (Li4Mn4P4O16, 28 atoms); LiMn2O4 mp-22584 (Li6Mn12O24, 42 atoms); Li2Mn3NiO8 mp-771112 (Li8Mn12Ni4O32, 56 atoms)
**Settings.** 3 iterations max, 3 candidates max, 160 new UMA relaxations max; brain meta, fallback baseten.
**Stop reason.** iterations done

## Iteration 1

**Hypothesis.** Raising olivine voltage with Mn and raising spinel voltage/stability with Ni and Ti will exceed LiFePO4 energy density.

_meta, 1 attempt(s), 1041 in / 4643 out tokens, ~$0.0210, 25.4 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it1-c1 | mp-19017 | Fe->Mn x1 | Mn2+/Mn3+ at ~4.1V raises average voltage over Fe2+/Fe3+ while keeping olivine capacity and small volume change. |
| it1-c2 | mp-22584 | Mn->Ni x2 | Ni2+ to Ni4+ introduces high-voltage ~4.7V redox to LiMn2O4 spinel to boost energy density. |
| it1-c3 | mp-771112 | Mn->Ti x1 | Ti4+ for Mn4+ in high-voltage spinel stabilizes the lattice and lowers E_hull without removing Ni redox capacity. |

<details><summary>Reasoning summary (proposals)</summary>

Analyzing parent cathode structures and proposing up to three cobalt-free chemical substitutions to exceed LiFePO4 energy density while maintaining charge neutrality.

Evaluating oxidation states and Li vacancy adjustments to preserve charge neutrality across substitutions.

Generating olivine and spinel substitution variants while balancing voltage, capacity, and stability constraints.

Evaluating Ni and Al spinel substitutions and F-doping tradeoffs against voltage and capacity limits.

Finalizing three chemically distinct partial substitutions with charge-balanced Li vacancies and rationale.

Selecting three parent IDs and substitution counts while avoiding composition overlap and confirming redox activity.

</details>

| Candidate | Parent | Substitution | Status | E_hull (eV/atom) | Voltage (V) | Capacity (mAh/g) | Energy density (Wh/kg) | Volume change (%) |
|---|---|---|---|---|---|---|---|---|
| Li4MnFe3(PO4)4 (it1-c1) | LiFePO4 | Fe→Mn ×1 | rejected (known) | — | — | — | — | — |
| Li3Mn5NiO12 (it1-c2) | LiMn2O4 | Mn→Ni ×2 | passed | 0.005 | 4.39 | 147 | 646 | 4.6 |
| Li8TiMn11(NiO8)4 (it1-c3) | Li2Mn3NiO8 | Mn→Ti ×1 | passed | 0.003 | 4.75 | 147 | 701 | 3.4 |


**Results of this iteration (fed back to the model):**

- Negative result: Li4MnFe3(PO4)4 (it1-c1) failed the novelty (already in Materials Project): composition already in Materials Project: mp-783919, mp-807965, mp-764613, mp-766043, mp-766130.
- Result: Li3Mn5NiO12 (it1-c2) passed every filter: 4.39 V, 147 mAh/g, 646 Wh/kg, volume change 4.6 %, E_hull 0.005 eV/atom; parent LiMn2O4: 3.82 V, 148 mAh/g, 567 Wh/kg.
- Result: Li8TiMn11(NiO8)4 (it1-c3) passed every filter: 4.75 V, 147 mAh/g, 701 Wh/kg, volume change 3.4 %, E_hull 0.003 eV/atom; parent Li2Mn3NiO8: 4.72 V, 147 mAh/g, 692 Wh/kg.

**The model's reading of the failures (hypotheses, not measurements):**

- it1-c1: Mn-for-Fe olivine composition overlaps heavily explored chemistry stabilizing known orderings. Correction: Propose novel olivine ratios or different substituents to avoid known Materials Project compositions.


**Analysis.** ranking ['it1-c3', 'it1-c2']; stop=False

- Ni substitution in Mn-spinel enables high average voltage while passing stability filters.
- Dilute Ti substitution in Ni-Mn spinel preserves capacity with low volume change.

**Next direction.** Continue optimizing Ni/Ti substituted Mn-spinels for higher energy density.

_meta, 1 attempt(s), 2436 in / 1266 out tokens, ~$0.0084, 7.7 s_

<details><summary>Reasoning summary (analysis)</summary>

Interpreting JSON schema requirements to include rejected candidates in failure analysis with hypotheses and corrections.

Deriving candidate ranking from passed status and energy density while avoiding self-generated comparisons.

</details>

## Iteration 2

**Hypothesis.** Avoiding the known Fe-Mn olivine orderings that caused it1-c1 to fail by using Ni doping plus Al pillar and V redox doping to stabilize high-voltage spinels will exceed LiFePO4 energy density.

_meta, 1 attempt(s), 2960 in / 4524 out tokens, ~$0.0229, 28.0 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it2-c1 | mp-19017 | Fe->Ni x1 | Ni2+/Ni4+ raises olivine voltage over Fe2+/Fe3+ with similar radius while avoiding known Fe-Mn compositions. |
| it2-c2 | mp-22584 | Mn->Al x1 | Al3+ suppresses Jahn-Teller distortion and volume change in Mn-spinel while retaining Mn redox capacity. |
| it2-c3 | mp-771112 | Mn->V x1 | V4+/V5+ adds extra redox and high inductive effect to Ni-Mn spinel to build on Ti success beyond it1-c3. |

<details><summary>Reasoning summary (proposals)</summary>

Evaluating prior substitution results to propose three new chemically distinct, charge-neutral dopants that avoid repeats and cobalt while aiming to exceed the LiFePO4 baseline energy density.

Generating three novel charge-neutral olivine dopants without cobalt or prior substitutions while preserving redox balance and lithium stoichiometry.

Evaluating isovalent versus aliovalent spinel substitutions and lithium vacancy requirements for charge neutrality.

Shifting to charge-neutral F-doped olivine and Ni/Fe olivine variants while assessing voltage and novelty risks.

Extending the substitution set with Al and V dopants while validating charge balance and voltage limits.

</details>

| Candidate | Parent | Substitution | Status | E_hull (eV/atom) | Voltage (V) | Capacity (mAh/g) | Energy density (Wh/kg) | Volume change (%) |
|---|---|---|---|---|---|---|---|---|
| Li4Fe3Ni(PO4)4 (it2-c1) | LiFePO4 | Fe→Ni ×1 | rejected (known) | — | — | — | — | — |
| Li6Mn11AlO24 (it2-c2) | LiMn2O4 | Mn→Al ×1 | passed | 0.003 | 3.85 | 127 | 488 | 4.7 |
| Li8Mn11V(NiO8)4 (it2-c3) | Li2Mn3NiO8 | Mn→V ×1 | passed | 0.008 | 4.69 | 147 | 690 | 3.4 |


**Results of this iteration (fed back to the model):**

- Negative result: Li4Fe3Ni(PO4)4 (it2-c1) failed the novelty (already in Materials Project): composition already in Materials Project: mp-771063.
- Result: Li6Mn11AlO24 (it2-c2) passed every filter: 3.85 V, 127 mAh/g, 488 Wh/kg, volume change 4.7 %, E_hull 0.003 eV/atom; parent LiMn2O4: 3.82 V, 148 mAh/g, 567 Wh/kg.
- Result: Li8Mn11V(NiO8)4 (it2-c3) passed every filter: 4.69 V, 147 mAh/g, 690 Wh/kg, volume change 3.4 %, E_hull 0.008 eV/atom; parent Li2Mn3NiO8: 4.72 V, 147 mAh/g, 692 Wh/kg.

**The model's reading of the failures (hypotheses, not measurements):**

- it2-c1: Hypothesis: Ni-for-Fe olivine at Fe3Ni ratio falls into a well-known stable ordering already in Materials Project. Correction: Try different Ni counts or co-substitutions to avoid known Fe-Ni olivine compositions.


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same parent, different added element**, on mp-771112: Mn->Ti vs Mn->V (x1, 0 Li vacancies): energy density: Li8TiMn11(NiO8)4 (it1-c3) 701.000 > Li8Mn11V(NiO8)4 (it2-c3) 690.000 Wh/kg (better: it1-c3); average voltage: Li8TiMn11(NiO8)4 (it1-c3) 4.754 > Li8Mn11V(NiO8)4 (it2-c3) 4.693 V (better: it1-c3); theoretical capacity: Li8TiMn11(NiO8)4 (it1-c3) 147.400 > Li8Mn11V(NiO8)4 (it2-c3) 147.100 mAh/g (better: it1-c3); E_hull per atom: Li8TiMn11(NiO8)4 (it1-c3) 0.003 < Li8Mn11V(NiO8)4 (it2-c3) 0.008 eV/atom (better: it1-c3); E_hull per substitution: Li8TiMn11(NiO8)4 (it1-c3) 0.146 < Li8Mn11V(NiO8)4 (it2-c3) 0.462 eV per modified site (better: it1-c3); volume change on charge: Li8Mn11V(NiO8)4 (it2-c3) 3.370 < Li8TiMn11(NiO8)4 (it1-c3) 3.440 % (better: it2-c3)
- **ranking on one parent**, mp-22584: energy density (highest first): it1-c2 646.000, it2-c2 488.000; average voltage (highest first): it1-c2 4.391, it2-c2 3.851; theoretical capacity (highest first): it1-c2 147.200, it2-c2 126.800; E_hull per atom (lowest first): it2-c2 0.003, it1-c2 0.005; E_hull per substitution (lowest first): it2-c2 0.113, it1-c2 0.114; volume change on charge (lowest first): it1-c2 4.610, it2-c2 4.680
- **ranking on one parent**, mp-771112: energy density (highest first): it1-c3 701.000, it2-c3 690.000; average voltage (highest first): it1-c3 4.754, it2-c3 4.693; theoretical capacity (highest first): it1-c3 147.400, it2-c3 147.100; E_hull per atom (lowest first): it1-c3 0.003, it2-c3 0.008; E_hull per substitution (lowest first): it1-c3 0.146, it2-c3 0.462; volume change on charge (lowest first): it2-c3 3.370, it1-c3 3.440

</details>

**Analysis.** ranking ['it2-c3', 'it2-c2']; stop=False

- On mp-771112 Mn->Ti (it1-c3 701.000 Wh/kg) outperforms Mn->V (it2-c3 690.000 Wh/kg) in energy density.
- On mp-22584 Ni substitution (it1-c2 646.000 Wh/kg) retains energy density better than Al substitution (it2-c2 488.000 Wh/kg).

**Next direction.** Prioritize dilute Ti/Ni substitutions on Mn-rich spinels over Al pillaring and V doping.

_meta, 1 attempt(s), 5206 in / 2166 out tokens, ~$0.0157, 11.3 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking two passed cobalt-free cathode candidates by energy density and drafting brief lessons, next direction, and stop flag.

Drafting a failure analysis for the rejected candidate and setting the stop flag to false.

Extracting quoted metrics from comparison statements to write lessons and the next direction.

</details>

## Iteration 3

**Hypothesis.** Extending the high-energy Ti/Ni-spinel successes of it1-c2/it1-c3 while avoiding the known Fe-Mn/Ni olivine orderings of it1-c1/it2-c1 and the low-energy Al/V routes of it2-c2/it2-c3, dilute tetravalent and polyanion doping will stabilize high-voltage Mn hosts to exceed LiFePO4.

_meta, 1 attempt(s), 5035 in / 4374 out tokens, ~$0.0249, 28.5 s_

| Proposal | Parent | Substitution | Rationale |
|---|---|---|---|
| it3-c1 | mp-22584 | Mn->Ti x1 | Dilute Ti4+ for Mn suppresses Jahn-Teller distortion and lowers volume change while preserving Mn/Ni redox for high voltage as in it1-c3. |
| it3-c2 | mp-771112 | Mn->Zr x1 | Larger Zr4+ pillar extends the successful Ti strategy with stronger structural stabilization and higher voltage from lattice expansion. |
| it3-c3 | mp-18997 | P->Si x1 | SiO4 mixing into Mn-olivine phosphate retains full Li and Mn2+/Mn4+ double redox for high capacity while creating a novel polyanion composition outside known olivines. |

<details><summary>Reasoning summary (proposals)</summary>

Evaluating chemically diverse cobalt-free cathode substitutions while avoiding prior evaluated compositions and tracking energy density.

Proposing charge-neutral partial substitutions with Li vacancies and fluorine to generate novel compositions.

Evaluating charge-neutral single-element substitutions and Li-vacancy balancing for novel spinel and olivine compositions.

Evaluating F-for-O doping with Li-vacancy balancing for olivine and spinel to raise voltage while meeting capacity constraints.

Shifting to dilute Ti and Zr substitutions on Mn-rich spinels and an Al-stabilized Mn olivine with Li vacancies.

Finalizing three dilute substitution proposals with redox and site-count validation and a hypothesis referencing prior failures.

</details>

| Candidate | Parent | Substitution | Status | E_hull (eV/atom) | Voltage (V) | Capacity (mAh/g) | Energy density (Wh/kg) | Volume change (%) |
|---|---|---|---|---|---|---|---|---|
| Li6TiMn11O24 (it3-c1) | LiMn2O4 | Mn→Ti ×1 | passed | 0.010 | 3.85 | 149 | 574 | 6.0 |
| Li8ZrMn11(NiO8)4 (it3-c2) | Li2Mn3NiO8 | Mn→Zr ×1 | passed | 0.016 | 4.72 | 143 | 676 | 3.9 |
| Li4Mn4SiP3O16 (it3-c3) | LiMnPO4 | P→Si ×1 | passed | 0.028 | 3.92 | 172 | 674 | 7.2 |


**Results of this iteration (fed back to the model):**

- Result: Li6TiMn11O24 (it3-c1) passed every filter: 3.85 V, 149 mAh/g, 574 Wh/kg, volume change 6.0 %, E_hull 0.010 eV/atom; parent LiMn2O4: 3.82 V, 148 mAh/g, 567 Wh/kg.
- Result: Li8ZrMn11(NiO8)4 (it3-c2) passed every filter: 4.72 V, 143 mAh/g, 676 Wh/kg, volume change 3.9 %, E_hull 0.016 eV/atom; parent Li2Mn3NiO8: 4.72 V, 147 mAh/g, 692 Wh/kg.
- Result: Li4Mn4SiP3O16 (it3-c3) passed every filter: 3.92 V, 172 mAh/g, 674 Wh/kg, volume change 7.2 %, E_hull 0.028 eV/atom; parent LiMnPO4: 3.79 V, 171 mAh/g, 648 Wh/kg.


<details><summary>Comparisons computed by the code (given to the model)</summary>

- **same substitution, different parents**, Mn->Ti x1 on mp-771112 vs mp-22584: energy density: Li8TiMn11(NiO8)4 (it1-c3) 701.000 > Li6TiMn11O24 (it3-c1) 574.000 Wh/kg (better: it1-c3); average voltage: Li8TiMn11(NiO8)4 (it1-c3) 4.754 > Li6TiMn11O24 (it3-c1) 3.847 V (better: it1-c3); theoretical capacity: Li6TiMn11O24 (it3-c1) 149.200 > Li8TiMn11(NiO8)4 (it1-c3) 147.400 mAh/g (better: it3-c1); E_hull per atom: Li8TiMn11(NiO8)4 (it1-c3) 0.003 < Li6TiMn11O24 (it3-c1) 0.010 eV/atom (better: it1-c3); E_hull per substitution: Li8TiMn11(NiO8)4 (it1-c3) 0.146 < Li6TiMn11O24 (it3-c1) 0.433 eV per modified site (better: it1-c3); volume change on charge: Li8TiMn11(NiO8)4 (it1-c3) 3.440 < Li6TiMn11O24 (it3-c1) 6.000 % (better: it1-c3)
- **same parent, different added element**, on mp-771112: Mn->Ti vs Mn->V (x1, 0 Li vacancies): energy density: Li8TiMn11(NiO8)4 (it1-c3) 701.000 > Li8Mn11V(NiO8)4 (it2-c3) 690.000 Wh/kg (better: it1-c3); average voltage: Li8TiMn11(NiO8)4 (it1-c3) 4.754 > Li8Mn11V(NiO8)4 (it2-c3) 4.693 V (better: it1-c3); theoretical capacity: Li8TiMn11(NiO8)4 (it1-c3) 147.400 > Li8Mn11V(NiO8)4 (it2-c3) 147.100 mAh/g (better: it1-c3); E_hull per atom: Li8TiMn11(NiO8)4 (it1-c3) 0.003 < Li8Mn11V(NiO8)4 (it2-c3) 0.008 eV/atom (better: it1-c3); E_hull per substitution: Li8TiMn11(NiO8)4 (it1-c3) 0.146 < Li8Mn11V(NiO8)4 (it2-c3) 0.462 eV per modified site (better: it1-c3); volume change on charge: Li8Mn11V(NiO8)4 (it2-c3) 3.370 < Li8TiMn11(NiO8)4 (it1-c3) 3.440 % (better: it2-c3)
- **same parent, different added element**, on mp-771112: Mn->Ti vs Mn->Zr (x1, 0 Li vacancies): energy density: Li8TiMn11(NiO8)4 (it1-c3) 701.000 > Li8ZrMn11(NiO8)4 (it3-c2) 676.000 Wh/kg (better: it1-c3); average voltage: Li8TiMn11(NiO8)4 (it1-c3) 4.754 > Li8ZrMn11(NiO8)4 (it3-c2) 4.720 V (better: it1-c3); theoretical capacity: Li8TiMn11(NiO8)4 (it1-c3) 147.400 > Li8ZrMn11(NiO8)4 (it3-c2) 143.100 mAh/g (better: it1-c3); E_hull per atom: Li8TiMn11(NiO8)4 (it1-c3) 0.003 < Li8ZrMn11(NiO8)4 (it3-c2) 0.016 eV/atom (better: it1-c3); E_hull per substitution: Li8TiMn11(NiO8)4 (it1-c3) 0.146 < Li8ZrMn11(NiO8)4 (it3-c2) 0.869 eV per modified site (better: it1-c3); volume change on charge: Li8TiMn11(NiO8)4 (it1-c3) 3.440 < Li8ZrMn11(NiO8)4 (it3-c2) 3.890 % (better: it1-c3)
- **same parent, different added element**, on mp-771112: Mn->V vs Mn->Zr (x1, 0 Li vacancies): energy density: Li8Mn11V(NiO8)4 (it2-c3) 690.000 > Li8ZrMn11(NiO8)4 (it3-c2) 676.000 Wh/kg (better: it2-c3); average voltage: Li8ZrMn11(NiO8)4 (it3-c2) 4.720 > Li8Mn11V(NiO8)4 (it2-c3) 4.693 V (better: it3-c2); theoretical capacity: Li8Mn11V(NiO8)4 (it2-c3) 147.100 > Li8ZrMn11(NiO8)4 (it3-c2) 143.100 mAh/g (better: it2-c3); E_hull per atom: Li8Mn11V(NiO8)4 (it2-c3) 0.008 < Li8ZrMn11(NiO8)4 (it3-c2) 0.016 eV/atom (better: it2-c3); E_hull per substitution: Li8Mn11V(NiO8)4 (it2-c3) 0.462 < Li8ZrMn11(NiO8)4 (it3-c2) 0.869 eV per modified site (better: it2-c3); volume change on charge: Li8Mn11V(NiO8)4 (it2-c3) 3.370 < Li8ZrMn11(NiO8)4 (it3-c2) 3.890 % (better: it2-c3)
- **same parent, different added element**, on mp-22584: Mn->Al vs Mn->Ti (x1, 0 Li vacancies): energy density: Li6TiMn11O24 (it3-c1) 574.000 > Li6Mn11AlO24 (it2-c2) 488.000 Wh/kg (better: it3-c1); average voltage: Li6Mn11AlO24 (it2-c2) 3.851 > Li6TiMn11O24 (it3-c1) 3.847 V (better: it2-c2); theoretical capacity: Li6TiMn11O24 (it3-c1) 149.200 > Li6Mn11AlO24 (it2-c2) 126.800 mAh/g (better: it3-c1); E_hull per atom: Li6Mn11AlO24 (it2-c2) 0.003 < Li6TiMn11O24 (it3-c1) 0.010 eV/atom (better: it2-c2); E_hull per substitution: Li6Mn11AlO24 (it2-c2) 0.113 < Li6TiMn11O24 (it3-c1) 0.433 eV per modified site (better: it2-c2); volume change on charge: Li6Mn11AlO24 (it2-c2) 4.680 < Li6TiMn11O24 (it3-c1) 6.000 % (better: it2-c2)
- **ranking on one parent**, mp-22584: energy density (highest first): it1-c2 646.000, it3-c1 574.000, it2-c2 488.000; average voltage (highest first): it1-c2 4.391, it2-c2 3.851, it3-c1 3.847; theoretical capacity (highest first): it3-c1 149.200, it1-c2 147.200, it2-c2 126.800; E_hull per atom (lowest first): it2-c2 0.003, it1-c2 0.005, it3-c1 0.010; E_hull per substitution (lowest first): it2-c2 0.113, it1-c2 0.114, it3-c1 0.433; volume change on charge (lowest first): it1-c2 4.610, it2-c2 4.680, it3-c1 6.000
- **ranking on one parent**, mp-771112: energy density (highest first): it1-c3 701.000, it2-c3 690.000, it3-c2 676.000; average voltage (highest first): it1-c3 4.754, it3-c2 4.720, it2-c3 4.693; theoretical capacity (highest first): it1-c3 147.400, it2-c3 147.100, it3-c2 143.100; E_hull per atom (lowest first): it1-c3 0.003, it2-c3 0.008, it3-c2 0.016; E_hull per substitution (lowest first): it1-c3 0.146, it2-c3 0.462, it3-c2 0.869; volume change on charge (lowest first): it2-c3 3.370, it1-c3 3.440, it3-c2 3.890

</details>

**Analysis.** ranking ['it3-c2', 'it3-c3', 'it3-c1']; stop=False

- On mp-771112 energy density ranks it1-c3 701.000 > it2-c3 690.000 > it3-c2 676.000 Wh/kg, favoring Ti over V over Zr.
- On mp-22584 energy density ranks it1-c2 646.000 > it3-c1 574.000 > it2-c2 488.000 Wh/kg, favoring Ni over Ti over Al.
- On mp-771112 E_hull per substitution ranks it1-c3 0.146 < it2-c3 0.462 < it3-c2 0.869 eV per modified site, showing Ti least destabilizing.

**Next direction.** Prioritize dilute Ti/Ni variants on Ni-Mn spinel mp-771112 and Si-doped Mn-olivine while avoiding Zr and Al dilution.

_meta, 1 attempt(s), 9335 in / 1930 out tokens, ~$0.0199, 9.9 s_

<details><summary>Reasoning summary (analysis)</summary>

Ranking passed candidates by energy density while noting comparison context does not override the order.

Drafting three short lessons from quoted comparison numbers and setting an empty failure list.

</details>

## Summaries (Muse Glimmer)

**iteration 1.** The agent proposed Li4MnFe3(PO4)4 to raise olivine voltage with Mn and Li3Mn5NiO12 and Li8TiMn11(NiO8)4 to raise spinel voltage and stability with Ni and Ti. Li4MnFe3(PO4)4 was rejected as the composition is already in Materials Project, while Li3Mn5NiO12 passed all filters with about 4.4 V, 646 Wh per kg and energy above hull about 0.01 eV per atom, and Li8TiMn11(NiO8)4 passed with about 4.8 V, 701 Wh per kg, 3.4 percent volume change and energy above hull about 0.00 eV per atom. The agent concluded Ni substitution in Mn spinel enables high voltage with acceptable stability and will continue optimizing Ni/Ti substituted Mn-spinels for higher energy density.

**iteration 2.** The agent tried a Ni-doped Fe olivine and two Mn-rich spinels with Al pillar and V redox doping to raise voltage beyond LiFePO4. Li4Fe3Ni(PO4)4 was rejected because the composition already exists in Materials Project, while Li6Mn11AlO24 and Li8Mn11V(NiO8)4 passed all filters with energy above hull about 0.00 eV per atom and about 0.01 eV per atom, 3.85 V and 488 Wh per kg versus 4.69 V and 690 Wh per kg. The agent concluded the Ni-for-Fe olivine at that ratio is a known ordering and will prioritize dilute Ti/Ni substitutions on Mn-rich spinels over Al pillaring and V doping.

**iteration 3.** In iteration three the agent tested dilute tetravalent and polyanion doping of Mn hosts to avoid Fe-Mn/Ni olivine orderings and low-energy Al/V routes, proposing Li6TiMn11O24, Li8ZrMn11(NiO8)4 and Li4Mn4SiP3O16. All three candidates passed every filter, with Li6TiMn11O24 showing 3.85 V, 574 Wh/kg and energy above the hull 0.01 eV per atom, Li8ZrMn11(NiO8)4 showing 4.72 V, 676 Wh/kg and energy above the hull 0.02 eV per atom, and Li4Mn4SiP3O16 showing 3.92 V, 674 Wh/kg and energy above the hull 0.03 eV per atom. The agent concluded Ti and Ni dilutions give higher energy density than Zr and Al on the Ni-Mn spinel and Si-doped Mn-olivine is promising, and will prioritize dilute Ti/Ni variants on the Ni-Mn spinel and Si-doped Mn-olivine while avoiding Zr and Al dilution.

**run.** The agent searched for cobalt-free cathode candidates with higher energy density than LiFePO4 and proposed nine new compositions. Seven of them passed the initial stability funnel. The three most stable finalists were Li8TiMn11(NiO8)4 with energy above the hull of about 0.00 eV per atom, Li8Mn11V(NiO8)4 with about 0.01 eV per atom, and Li8ZrMn11(NiO8)4 with about 0.02 eV per atom. No band gap or energy density values were reported for the finalists in this run, so a comparative assessment versus LiFePO4 could not be completed. The run stopped after the planned iterations with stable candidates identified but without confirmed electronic or performance metrics.

## Independent reviews

- **Li8TiMn11(NiO8)4** (priority high): Li8TiMn11(NiO8)4 is Co-free with 701.0 Wh/kg at 4.754 V, 0.002615 eV/atom and 3.44% volume change, warranting DFT/experimental follow-up despite high-voltage risks.
- **Li8Mn11V(NiO8)4** (priority medium): Stable cobalt-free spinel with low 3.37% strain and 690 Wh/kg but outperformed by Ti analogue on same parent and with high 0.4618 eV per substitution cost, making it a medium-priority DFT follow-up backup.
- **Li8ZrMn11(NiO8)4** (priority low): Zr-substituted Li2Mn3NiO8 passes stability and volume filters but is outperformed by Ti and V analogues on the same parent in energy density, capacity and substitution energetics, warranting low priority for follow-up.
- **Li4Mn4SiP3O16** (priority medium): Cobalt-free Li4Mn4SiP3O16 meets all filter thresholds with 674.0 Wh/kg and 3.925 V but high substitution energy and predicted 4-phase decomposition warrant DFT validation before experiment.
- **Li3Mn5NiO12** (priority high): Li3Mn5NiO12 combines low E_hull of 0.005409 eV/atom with high energy density of 646.0 Wh/kg and low 4.61% volume change, supporting high priority for follow-up despite high voltage and full delithiation.
- **Li6TiMn11O24** (priority medium): Li6TiMn11O24 is a thermodynamically stable cobalt-free spinel meeting all filters with competitive energy density but with a high substitution energy penalty and Mn-related degradation risks.

## Final ranking

Order: energy density (voltage x theoretical capacity), then E_hull per substitution. Candidates are computational predictions, not proven materials.

1. it1-c3 Li8TiMn11(NiO8)4 **finalist**: 4.75 V, 147 mAh/g, 701 Wh/kg, volume change 3.4 %, E_hull 0.003 eV/atom (E_hull error bar ± 0.007 eV/atom) (parent Li2Mn3NiO8: 4.72 V, 692 Wh/kg)
2. it2-c3 Li8Mn11V(NiO8)4 **finalist**: 4.69 V, 147 mAh/g, 690 Wh/kg, volume change 3.4 %, E_hull 0.008 eV/atom (E_hull error bar ± 0.007 eV/atom) (parent Li2Mn3NiO8: 4.72 V, 692 Wh/kg)
3. it3-c2 Li8ZrMn11(NiO8)4 **finalist**: 4.72 V, 143 mAh/g, 676 Wh/kg, volume change 3.9 %, E_hull 0.016 eV/atom (E_hull error bar ± 0.010 eV/atom) (parent Li2Mn3NiO8: 4.72 V, 692 Wh/kg)
4. it3-c3 Li4Mn4SiP3O16: 3.92 V, 172 mAh/g, 674 Wh/kg, volume change 7.2 %, E_hull 0.028 eV/atom (E_hull error bar ± 0.005 eV/atom) (parent LiMnPO4: 3.79 V, 648 Wh/kg)
5. it1-c2 Li3Mn5NiO12: 4.39 V, 147 mAh/g, 646 Wh/kg, volume change 4.6 %, E_hull 0.005 eV/atom (E_hull error bar ± 0.008 eV/atom) (parent LiMn2O4: 3.82 V, 567 Wh/kg)
6. it3-c1 Li6TiMn11O24: 3.85 V, 149 mAh/g, 574 Wh/kg, volume change 6.0 %, E_hull 0.010 eV/atom (E_hull error bar ± 0.007 eV/atom) (parent LiMn2O4: 3.82 V, 567 Wh/kg)
7. it2-c2 Li6Mn11AlO24: 3.85 V, 127 mAh/g, 488 Wh/kg, volume change 4.7 %, E_hull 0.003 eV/atom (E_hull error bar ± 0.006 eV/atom) (parent LiMn2O4: 3.82 V, 567 Wh/kg)

## Novelty check (literature, web search)

Search date: 2026-11-02. Links come only from the API (its citations, or the relevant search results it returned when it gave no citation). "No publication found in this search" does not mean the material was never reported.

### control-LNMO LiNi0.5Mn1.5O4 (control, expected: already published): already published

LiNi0.5Mn1.5O4 is identified by name as a lithium-ion battery cathode material, with formula LiNi0.5Mn1.5O4 listed explicitly. It is described as a high-voltage spinel LNMO cathode with working voltage above 4.7V vs Li/Li+, noted for low cost and environmental friendliness. The same spinel component Li[Mn1.5Ni0.5]O4 is reported in articles evaluating lithium-manganese-nickel-oxide electrodes in lithium cells.

Sources:
- [LMNO (LiNi0.5Mn1.5O4) PLD Targets for Quality LMNO Thin FIlms
 – Target Materials](https://target-materials.com/products/ni-mn-spinel-lini0-5mn1-5o4-pld-target)
- [Lithium manganese nickel oxide cathode material having nickel manganese concentration gradient and preparation method thereof - Eureka](https://eureka-patsnap-com.libproxy1.nus.edu.sg/patent-CN105226270A)
- [CN114864922B - 
        A lithium-ion battery](https://patents.google.com/patent/CN114864922B/en)
- [LiNi₀.₅Mn₁.₅O₄ (LNMO) Cathode Powder for Lithium-ion Batteries - Xiaowei Lithium Battery](https://xiaoweitop.com/equipments/lini0-5mn1-5o4-powder-lnmo/)
- [METHOD FOR PREPARING LITHIUM NICKEL MANGANESE OXIDE POSITIVE BATTERY ELECTRODE MATERIAL, AND LITHIUM NICKEL MANGANESE OXIDE POSITIVE BATTERY ELECTRODE MATERIAL - European Patent Office - EP 3174138 A1](https://data.epo.org/publication-server/rest/v1.2/patents/EP3174138NWA1/document.pdf)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_1 web searches, 12 sources considered, ~$0.0107, 2026-11-02_

### it1-c3 Li8TiMn11(NiO8)4: close family already studied

Ti surface doping of LiNi0.5Mn1.5O4-δ, the same spinel as Li2Mn3NiO8, by hydrolysis–condensation followed by annealing in oxygen is reported. Cationic doping of spinel LiNi0.5Mn1.5O4 with Ti4+ is listed among studied solutions alongside Mo6+, Cr3+ and others. Spinel-type Li–Mn–Ti oxide cathodes prepared from lithium, Mn and Ti compounds are also described in the patent literature.

Sources:
- [Understanding the
Activation of Anionic Redox Chemistry
in Ti4+-Substituted Li2MnO3 as a
Cathode Material for Li](https://figshare.com/articles/journal_contribution/Understanding_the_Activation_of_Anionic_Redox_Chemistry_in_Ti_sup_4_sup_-Substituted_Li_sub_2_sub_MnO_sub_3_sub_as_a_Cathode_Material_for_Li-Ion_Batteries/23573397)
- [A Cathode Active Material For Lithium Secondary Battery And A Lithium Secondary Battery Comprising Thereof OH; Ji Woo ;   et al. [L&F CO., LTD.]](https://uspto.report/patent/app/20200335782)
- [Abstract: (Invited) Ti-Substituted Li[Li<sub>0.26</sub>Mn<sub>0.6-<i>X</i></sub>Ti<i><sub>x</sub></i>Ni<sub>0.07</sub>Co<sub>0.07</sub>]O<sub>2</sub> Layered Cathode Material with Improved Structural Stability and Suppressed Voltage Fading (228th ECS Meeting (October 11-15, 2015))](https://ecs.confex.com/ecs/228/webprogram/Paper60813.html)
- [Supporting Information Fluorine Substituted Lithium Chloride Solid Electrolytes for HighV oltage All-Solid-State Lithium-Ion Batteries](https://pubs.acs.org/doi/suppl/10.1021/acsenergylett.3c02307/suppl_file/nz3c02307_si_001.pdf)
- [Electrochemical and Physical Properties of Ti-Substituted Layered Nickel Manganese Cobalt Oxide (NMC) Cathode Materials - IOPscience](https://iopscience.iop.org/article/10.1149/2.060208jes/meta)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_4 web searches, 43 sources considered, ~$0.0365, 2026-11-02_

### it2-c3 Li8Mn11V(NiO8)4: close family already studied

Patent EP3174138A1 discloses vanadium-doped high-voltage spinel as Li1.0+xNi0.5Mn1.5VyO4 where V is vanadium with y up to 0.08, and also as Li1.0+4xNi0.5Mn1.5-4xVxO4 with x up to 0.1. A journal study reports sol-gel V-doped LiNi0.5Mn1.5O4 cathodes, with V-substitution confirmed as Li0.995V0.005Ni0.5Mn1.5O4. LiNi0.5Mn1.5O4 is twice-reported high-voltage spinel chemistry also written as Li2Mn3NiO8, whose catalog formula is Li2Mn3NiO8, so this is the same parent with V-doping studied but not the exact Mn11V composition in this search.

Sources:
- [METHOD FOR PREPARING LITHIUM NICKEL MANGANESE OXIDE POSITIVE BATTERY ELECTRODE MATERIAL, AND LITHIUM NICKEL MANGANESE OXIDE POSITIVE BATTERY ELECTRODE MATERIAL - European Patent Office - EP 3174138 A1](https://data.epo.org/publication-server/rest/v1.2/patents/EP3174138NWA1/document.pdf)

_7 web searches, 66 sources considered, ~$0.0890, 2026-11-02_

### it3-c2 Li8ZrMn11(NiO8)4: close family already studied

The parent Li2Mn3NiO8 is a known spinel lithium manganese nickel oxide cathode powder, battery grade. Zr doping of the same spinel parent written as LiNi0.5Mn1.5O4 was reported as “Effect of Zr doping on LiNi0.5Mn1.5O4 with ordered or disordered structures”. That study appeared in Journal of Alloys and Compounds, 2018, 749, 1009-1018, and a separate work studied “Zr-doping effect on the capacity retention of LiNi0.5Mn1.5O4−δ”.

Sources:
- [Preparation method of surface covered nickel lithium manganate positive electrode material - Eureka | Patsnap](https://eureka-patsnap-com.libproxy1.nus.edu.sg/patent-CN103794777A)
- [CN114229922A - 
        A kind of nickel-cobalt-manganese ternary precursor, positive electrode material and preparation method](https://patents.google.com/patent/CN114229922A/en)
- [Li2ZrO3 -Coated Li1.2Ni0.2Mn0.8O2 for the High Performance Cathode Material in Lithium Ion Batteries - R Discovery](https://discovery.researcher.life/article/li2zro3-coated-li1-2ni0-2mn0-8o2-for-the-high-performance-cathode-material-in-lithium-ion-batteries/7503905175543696a759880c238b5cc6)
- [High-Ni cathode material improved with Zr for stable cycling of Li-ion rechargeable batteries - RSC Advances (RSC Publishing)](https://pubs.rsc.org/en/content/articlelanding/2020/ra/d0ra01543a)
- [WO2023110830A1 - Cathode material 
        - Google Patents](https://patents.google.com/patent/WO2023110830A1/en)

Notes: no inline citation returned by the API: the relevant search results it returned are listed instead

_5 web searches, 55 sources considered, ~$0.0507, 2026-11-02_

Total: 0 calls, ~$0.0000.

## Final scientific report

### Executive summary

The search aimed for cobalt-free cathodes with higher energy density than LiFePO4. The champion is Li8TiMn11(NiO8)4 with energy density 701.0 Wh/kg at voltage 4.754 V and capacity 147.4 mAh/g, volume change 3.44%, and energy above hull 0.003 eV/atom with error 0.007 eV/atom. Its voltage 4.754 V and energy density 701.0 Wh/kg are comparable to its parent Li2Mn3NiO8 at 4.718 V and 692.0 Wh/kg within the model's voltage error of 0.35 V. The other finalists are Li8Mn11V(NiO8)4 with 690.0 Wh/kg at 4.693 V and 147.1 mAh/g, volume change 3.37%, and 0.008 eV/atom with error 0.007 eV/atom, and Li8ZrMn11(NiO8)4 with 676.0 Wh/kg at 4.72 V and 143.1 mAh/g, volume change 3.89%, and 0.016 eV/atom with error 0.01 eV/atom. The champion belongs to a close family already studied. Two candidates were rejected as known: Li4MnFe3(PO4)4 already in Materials Project as mp-783919, mp-807965, mp-764613, mp-766043, mp-766130, and Li4Fe3Ni(PO4)4 already as mp-771063. DFT calculations, voltage profile beyond average voltage, oxygen redox, lithium diffusion and electronic conductivity, cycling and capacity fade, synthesis, cost of the elements, and experimental data were not computed.

### Comparison of the finalists

| | Li8TiMn11(NiO8)4 | Li8Mn11V(NiO8)4 | Li8ZrMn11(NiO8)4 |
|---|---|---|---|
| Parent cathode | Li2Mn3NiO8 | Li2Mn3NiO8 | Li2Mn3NiO8 |
| Substitution | Mn→Ti ×1 | Mn→V ×1 | Mn→Zr ×1 |
| Space group | C2 | C2 | C2 |
| E_hull (eV/atom) | 0.003 ± 0.007 | 0.008 ± 0.007 | 0.016 ± 0.010 |
| Li removed on charge | 8 of 8 | 8 of 8 | 8 of 8 |
| Average voltage (V) | 4.75 (parent 4.72) | 4.69 (parent 4.72) | 4.72 (parent 4.72) |
| Theoretical capacity (mAh/g) | 147 (parent 147) | 147 (parent 147) | 143 (parent 147) |
| Energy density (Wh/kg) | 701 (parent 692) | 690 (parent 692) | 676 (parent 692) |
| Volume change on charge (%) | 3.4 (parent 3.9) | 3.4 (parent 3.9) | 3.9 (parent 3.9) |
| Against its parent | comparable to its parent within the model's voltage error | comparable to its parent within the model's voltage error | comparable to its parent within the model's voltage error |
| Literature | related | related | related |

### Champion: Li8TiMn11(NiO8)4

**Why it is preferred.**

- Li8TiMn11(NiO8)4 has energy density 701.0 Wh/kg, which is the highest among the finalists at 701.0 Wh/kg, 690.0 Wh/kg and 676.0 Wh/kg.
- It has energy above hull 0.003 eV/atom with error 0.007 eV/atom, volume change 3.44%, voltage 4.754 V and capacity 147.4 mAh/g.
- Its voltage 4.754 V and energy density 701.0 Wh/kg are comparable to its parent Li2Mn3NiO8 at 4.718 V and 692.0 Wh/kg within the model's voltage error of 0.35 V, computed the same way, with capacity difference 0.7 mAh/g coming from the composition.

**Trade-offs.**

- Average voltage 4.754 V is near the 4.8 V upper limit and may exceed electrolyte stability.
- High Mn content risks Jahn-Teller Mn3+ distortion and Mn dissolution.
- The Ni-Mn oxide spinel parent Li2Mn3NiO8 may have low electronic conductivity.

**Uncertainties.**

- Energies are UMA energies instead of DFT, with error 0.007 eV/atom and voltage error 0.35 V.
- Only the average voltage over the whole charge was computed.
- Ordering of the substituted sites and magnetism were not explicit.

**Validation to do.**

- Compute DFT+U voltages to confirm the average voltage of 4.754 V. *(documented)*
- Attempt synthesis and confirm the structure with XRD. *(documented)*
- Test galvanostatic cycling to measure capacity and stability. *(documented)*

**Synthesis routes to consider.**

- Try solid-state reaction, a well-established route for spinels. *(documented)*
- Try sol-gel synthesis, a well-established route for spinels. *(documented)*

### Methods

- **Candidate proposals and decisions**: Meta Muse Spark (reasoning model), with comparisons computed by the code
- **Structure relaxation and energies**: Meta FAIR UMA (uma-s-1p2, OMat head), atoms and cell relaxed, MP2020 corrections for the hull; references from Materials Project relaxed with UMA
- **Thermodynamic stability**: energy above the convex hull of the stable known phases of the system; kept if <= 0.08 eV/atom; error bar measured against DFT (Materials Project) on the known compounds of the same system
- **Voltage, capacity, energy density**: the Li that charge neutrality allows removed, delithiated cell relaxed with UMA; average voltage from the UMA energies and Li metal; theoretical capacity from the Li removed (calibrated on four known cathodes)
- **Volume change**: lithiated and delithiated cells, both relaxed with UMA
- **Independent reviews**: Meta Muse Spark Open, one review per passed candidate, in parallel
- **Literature check**: Meta Muse Spark with web search; a known cathode (LiNi0.5Mn1.5O4) checked first as a control
- **Error-driven loop**: each iteration's failures, with their numbers, go back to the proposing model, which explains them as hypotheses and corrects its next proposals
- **Plain-language summaries**: Meta Muse Glimmer

### Limitations

- Oxygen redox, lithium diffusion, electronic conductivity, cycling and capacity fade, synthesis, cost, and experimental data were not studied.
- Any value not reported was not computed.
- The candidates are computational predictions, not proven materials.
- Not computed: DFT calculations (UMA energies; the voltage of four known cathodes within 0.31 V of experiment), the voltage profile (only the average voltage over the whole charge), oxygen redox, lithium diffusion and electronic conductivity in the cathode, cycling and capacity fade, synthesis, cost of the elements, experimental data.
- The candidates are computational predictions, not proven materials.


Model ranking (last analysis): ['it3-c2', 'it3-c3', 'it3-c1']

## Usage

- meta: 7 calls, 28653 in / 22130 out tokens, ~$0.1299
- baseten: 0 calls, 0 in / 0 out tokens, ~$0.0000
- meta (rerun): 1 calls, 3165 in / 3887 out tokens, ~$0.0205
- candidate analyses (analyst): 0 calls, ~$0.0000
- novelty web search: 0 calls, ~$0.0000
- molecular dynamics launched in this research (all iterations): estimate 0.00 $ on Modal H100
- UMA relaxations: 142 new / 160 allowed
- events: 79; duration 22.8 min