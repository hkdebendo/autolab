# Validation benchmark: known compounds through the funnel, judged blind

Each compound is relaxed by UMA and judged exactly like a candidate: E_hull against UMA + MP2020 references of its system with its own composition removed (as if it were new), band gap (recorded prediction), then window and passivation against Li metal. The language model never sees them.

- Good electrolytes passing the funnel (E_hull <= 0.05 eV/atom, gap >= 2.0 eV): **3 / 4**; also passing the Li-metal check: **2 / 4**
- Bad compounds rejected by the funnel: **8 / 8**; after the Li-metal check: **8 / 8**
- Hard negatives (stable insulators, poor Li conductors) rejected by the funnel: **0 / 5**; after the Li-metal check and the diffusion test against beta-Li3PS4: **5 / 5**
- Rejected by step: bad {'bandgap': 6, 'hull': 2}; hard {'electrodes': 1, 'molecular_dynamics': 4}

| Compound | Group | MP id | Expected | E_hull (eV/atom) | Gap optB88 / mBJ (eV) | Against Li metal | Window (V) | D at 600 K / D(beta-Li3PS4) | Result | Correct |
|---|---|---|---|---|---|---|---|---|---|---|
| Li6PS5Cl (argyrodite; ordered MP cell 0.083 eV/atom above the MP hull) | good | mp-985592 | pass | 0.080 | — | — | — | — | rejected at hull: E_hull 0.080 > 0.05 eV/atom | **no** |
| Li10GeP2S12 (LGPS; known to react with Li metal) | good | mp-696138 | pass | 0.019 | 2.63 / 3.31 | non_passivating | 1.74–2.28 | — | rejected at electrodes: non_passivating against Li metal (metallic products Li15Ge4) | **no** |
| Li7P3S11 | good | mp-641703 | pass | 0.010 | 2.46 / 2.98 | passivating | 2.28–2.30 | 2.18 ± 0.59 (higher) | pass | yes |
| beta-Li3PS4 | good | mp-985583 | pass | -0.033 | 2.69 / 3.21 | passivating | 1.74–2.36 | 1.00 ± 0.29 (tied) | pass | yes |
| Li3P (semiconductor, MP PBE gap 0.70 eV) | bad | mp-736 | reject | -0.441 | 0.87 / 1.64 | — | — | — | rejected at bandgap: gap 0.87 < 2.0 eV | yes |
| Li3Sb (semiconductor, MP PBE gap 0.48 eV) | bad | mp-7955 | reject | -0.065 | 0.59 / 0.84 | — | — | — | rejected at bandgap: gap 0.59 < 2.0 eV | yes |
| LiP (semiconductor, MP PBE gap 0.81 eV) | bad | mp-9588 | reject | -0.012 | 0.89 / 1.30 | — | — | — | rejected at bandgap: gap 0.89 < 2.0 eV | yes |
| LiGe (metal) | bad | mp-9918 | reject | -0.038 | 0.00 / 0.27 | — | — | — | rejected at bandgap: gap 0.00 < 2.0 eV | yes |
| LiSi (metal) | bad | mp-795 | reject | 0.011 | 0.13 / 0.47 | — | — | — | rejected at bandgap: gap 0.13 < 2.0 eV | yes |
| Li15Si4 (metal) | bad | mp-569849 | reject | -0.012 | 0.00 / 0.11 | — | — | — | rejected at bandgap: gap 0.00 < 2.0 eV | yes |
| Li2PS3 (unstable, 0.121 eV/atom above the MP hull) | bad | mp-38200 | reject | 0.125 | — | — | — | — | rejected at hull: E_hull 0.125 > 0.05 eV/atom | yes |
| Li2PS3 (unstable, 0.126 eV/atom above the MP hull, metallic) | bad | mp-1222635 | reject | 0.126 | — | — | — | — | rejected at hull: E_hull 0.126 > 0.05 eV/atom | yes |
| Li2S (stable insulator, poor Li conductor) | hard | mp-1153 | reject | -1.255 | 3.53 / 4.58 | stable | 0.00–2.14 | no Li hop | rejected at molecular_dynamics: no Li diffusion seen | yes |
| LiCl (stable insulator, poor Li conductor) | hard | mp-22905 | reject | -2.124 | 6.57 / 6.85 | stable | 0.00–4.28 | 0.00 ± 0.00 (lower) | rejected at molecular_dynamics: slower than Li3PS4 by more than 2 combined errors | yes |
| LiI (stable insulator, poor Li conductor) | hard | mp-570935 | reject | -1.427 | 4.25 / 5.80 | stable | 0.00–2.84 | 0.53 ± 0.28 (tied) | rejected at molecular_dynamics: framework moved: I diffuses at 8.5% of Li (limit 5%), seed 0, final MSD 0.3 A2 | yes |
| Li3PO4 (stable insulator, poor Li conductor) | hard | mp-13725 | reject | -0.137 | 6.39 / 7.76 | passivating | 0.74–4.22 | no Li hop | rejected at molecular_dynamics: no Li diffusion seen | yes |
| Li4GeS4 (stable insulator, poor Li conductor) | hard | mp-1222529 | reject | -0.055 | 2.67 / 3.55 | non_passivating | 1.66–2.28 | — | rejected at electrodes: non_passivating against Li metal (metallic products Li15Ge4) | yes |

New UMA relaxations: 0. MD: 8 new runs on Modal H100, estimate 6.86 $.
