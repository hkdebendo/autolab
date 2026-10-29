# Validation benchmark: known compounds through the funnel, judged blind

Each compound is relaxed by UMA and judged exactly like a candidate: E_hull against UMA + MP2020 references of its system with its own composition removed (as if it were new), ALIGNN band gap, then window and passivation against Li metal. The language model never sees them.

- Good electrolytes passing the funnel (E_hull <= 0.05 eV/atom, gap >= 2.0 eV): **3 / 4**; also passing the Li-metal check: **2 / 4**
- Bad compounds rejected by the funnel: **8 / 8**; after the Li-metal check: **8 / 8**

| Compound | MP id | Expected | E_hull (eV/atom) | Gap optB88 / mBJ (eV) | Against Li metal | Window (V) | Result | Correct |
|---|---|---|---|---|---|---|---|---|
| Li6PS5Cl (argyrodite; ordered MP cell 0.083 eV/atom above the MP hull) | mp-985592 | pass | 0.080 | — | — | — | rejected at hull: E_hull 0.080 > 0.05 eV/atom | **no** |
| Li10GeP2S12 (LGPS; known to react with Li metal) | mp-696138 | pass | 0.019 | 2.63 / 3.31 | non_passivating | 1.74–2.28 | rejected at electrodes: non_passivating against Li metal (metallic products Li15Ge4) | **no** |
| Li7P3S11 | mp-641703 | pass | 0.010 | 2.46 / 2.98 | passivating | 2.28–2.30 | pass | yes |
| beta-Li3PS4 | mp-985583 | pass | -0.033 | 2.69 / 3.21 | passivating | 1.74–2.36 | pass | yes |
| Li3P (semiconductor, MP PBE gap 0.70 eV) | mp-736 | reject | -0.441 | 0.87 / 1.64 | — | — | rejected at bandgap: gap 0.87 < 2.0 eV | yes |
| Li3Sb (semiconductor, MP PBE gap 0.48 eV) | mp-7955 | reject | -0.065 | 0.59 / 0.84 | — | — | rejected at bandgap: gap 0.59 < 2.0 eV | yes |
| LiP (semiconductor, MP PBE gap 0.81 eV) | mp-9588 | reject | -0.012 | 0.89 / 1.30 | — | — | rejected at bandgap: gap 0.89 < 2.0 eV | yes |
| LiGe (metal) | mp-9918 | reject | -0.038 | 0.00 / 0.27 | — | — | rejected at bandgap: gap 0.00 < 2.0 eV | yes |
| LiSi (metal) | mp-795 | reject | 0.011 | 0.13 / 0.47 | — | — | rejected at bandgap: gap 0.13 < 2.0 eV | yes |
| Li15Si4 (metal) | mp-569849 | reject | -0.012 | 0.00 / 0.11 | — | — | rejected at bandgap: gap 0.00 < 2.0 eV | yes |
| Li2PS3 (unstable, 0.121 eV/atom above the MP hull) | mp-38200 | reject | 0.125 | — | — | — | rejected at hull: E_hull 0.125 > 0.05 eV/atom | yes |
| Li2PS3 (unstable, 0.126 eV/atom above the MP hull, metallic) | mp-1222635 | reject | 0.126 | — | — | — | rejected at hull: E_hull 0.126 > 0.05 eV/atom | yes |

New UMA relaxations: 40.

## Reading

- **Bad compounds: 8 / 8 rejected**, but the test is easy for 6 of them: the electronic conductors (Li3P, Li3Sb, LiP, LiGe, LiSi, Li15Si4) are stopped by the band gap alone (ALIGNN optB88 0.00-0.89 eV, MP PBE 0-0.81 eV). Only the two Li2PS3 phases test the stability filter; their UMA E_hull (0.125, 0.126 eV/atom) matches the MP values (0.121, 0.126).
- **Good electrolytes: 3 / 4 pass the funnel, 2 / 4 also pass the Li-metal check.**
  - Li6PS5Cl fails the stability filter (0.080 eV/atom > 0.05): the ordered argyrodite cell of Materials Project is metastable in DFT too (0.083 eV/atom); the real material is stabilised by Cl/S and Li disorder, which a single ordered cell does not capture. A threshold of 0.05 eV/atom would miss it as a new candidate.
  - LGPS passes the funnel (0.019 eV/atom, gap 2.63 eV) but is excluded against Li metal (Li15Ge4, metallic, forms): this is the known experimental behaviour of LGPS, which needs a protective layer on Li metal. The rule excludes it by design (SPEC 5.9); it is a correct prediction of a real weakness, but it means the funnel rejects a famous electrolyte for Li-metal anodes.
  - Li7P3S11 and beta-Li3PS4 pass every step.
- Conductivity is not part of this benchmark (MD calibration, SPEC 7: Li7P3S11 2.0x faster than Li3PS4 at 600 K).
