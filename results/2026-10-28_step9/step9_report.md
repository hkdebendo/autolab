# AutoLab step 9 — electrodes and Li diffusion with UMA energies

Energies: UMA + MP2020 corrections (see the method notes at the end).

## Ranking: raw UMA vs UMA + MP2020 (best first, lowest E_hull per substitution)

| Rank (MP2020) | Rank (raw) | Candidate | Formula | E_hull per atom raw → MP2020 (eV/atom) | E_hull per substitution raw → MP2020 (eV per modified site) | Confidence |
|---|---|---|---|---|---|---|
| 1 | 1 | it2-c4 | NaLi11(PS4)4 | 0.003 → 0.003 | 0.089 → 0.089 | normal |
| 2 | 4 | it1-c4 | Li7P3SeS10 | 0.018 → 0.015 | 0.377 → 0.323 | normal |
| 3 | 2 | it1-c5 | NaLi6P3S11 | 0.017 → 0.017 | 0.347 → 0.347 | normal |
| 4 | 3 | it2-c5 | Li11P4S15I | 0.023 → 0.023 | 0.362 → 0.362 | normal |
| 5 | 5 | it1-c2 | Li6P2S7O | 0.024 → 0.024 | 0.384 → 0.384 | normal |
| 6 | 6 | it1-c1 | Li11P4S15Cl | 0.026 → 0.026 | 0.399 → 0.399 | normal |
| 7 | 8 | it2-c2 | Li7AsP2S11 | 0.037 → 0.024 | 0.774 → 0.503 | reduced: decomposes via the polysulfide AsS2, LiS4 |
| 8 | 7 | it2-c1 | Li13P6S21Cl | 0.030 → 0.030 | 0.618 → 0.618 | normal |
| 9 | 9 | it2-c3 | Li14SbP5S22 | 0.040 → 0.033 | 1.680 → 1.381 | reduced: decomposes via the polysulfide LiS4 |

## 9A. Electrochemical window and contact with Li metal (UMA + MP2020 energies, CPU)

Calibration Li3PS4: UMA 1.74–2.36 V vs MP 1.72–2.34 V. Parents (UMA): Li7P3S11 2.28–2.30 V; Li3PS4 1.74–2.36 V

| Candidate | Formula | Window (V) | Against Li metal | Products at 0 V |
|---|---|---|---|---|
| it2-c4 | NaLi11(PS4)4 | 1.94–2.26 | non_passivating (metallic: Na) | Li2S 0.76, Li3P 0.19, Na 0.05 |
| it1-c4 | Li7P3SeS10 | 2.28–2.30 | passivating | Li2S 0.71, Li3P 0.21, Li2Se 0.07 |
| it1-c5 | NaLi6P3S11 | 2.26–2.34 | non_passivating (metallic: Na) | Li2S 0.73, Li3P 0.20, Na 0.07 |
| it2-c5 | Li11P4S15I | 2.28–2.30 | passivating | Li2S 0.75, Li3P 0.20, LiI 0.05 |
| it1-c2 | Li6P2S7O | 1.74–2.36 | passivating | Li2S 0.70, Li3P 0.20, Li2O 0.10 |
| it1-c1 | Li11P4S15Cl | 2.28–2.30 | passivating | Li2S 0.75, Li3P 0.20, LiCl 0.05 |
| it2-c2 | Li7AsP2S11 | zero at the calculation precision (parent Li7P3S11 already at 0.02 V); not rejected | passivating | Li2S 0.79, Li3P 0.14, Li3As 0.07 |
| it2-c1 | Li13P6S21Cl | 2.28–2.30 | passivating | Li2S 0.75, Li3P 0.21, LiCl 0.04 |
| it2-c3 | Li14SbP5S22 | zero at the calculation precision (parent Li7P3S11 already at 0.02 V); not rejected | passivating | Li2S 0.79, Li3P 0.18, Li3Sb 0.04 |

## 9B. Interface with the cathode (UMA + MP2020 energies, on-hull references)

Calibrations (Li3PS4, tolerance 0.05 eV/atom):

- Li3PS4 / LiCoO2: UMA -0.415 vs MP -0.416 eV/atom, diff +0.001 → ok (56 UMA / 952 MP references)
- Li3PS4 / LiFePO4: UMA -0.144 vs MP -0.133 eV/atom, diff -0.011 → ok (57 UMA / 1185 MP references)

| Candidate | Formula | Reaction energy with LiFePO4 (eV/atom) | Mixing ratio | Reaction |
|---|---|---|---|---|
| it1-c2 | Li6P2S7O | -0.138 | 0.36 | 0.2182 Li6P2S7O + 0.8909 LiFePO4 -> 0.2545 FePS + 0.5091 Li4P2O7 + 0.6364 FeS2 + 0.05455 Li3PO4 |
| it2-c5 | Li11P4S15I | -0.139 | 0.34 | 0.1032 Li11P4S15I + 0.8968 LiFePO4 -> 0.5014 Li4P2O7 + 0.03438 PI3 + 0.2464 FePS + 0.02579 LiPO3 + 0.6504 FeS2 |
| it1-c1 | Li11P4S15Cl | -0.138 | 0.34 | 0.8974 LiFePO4 + 0.1026 Li11P4S15Cl -> 0.4359 Li4P2O7 + 0.1795 LiPO3 + 0.2564 FePS + 0.641 FeS2 + 0.1026 LiCl |
| it2-c1 | Li13P6S21Cl | -0.135 | 0.32 | 0.9245 LiFePO4 + 0.07547 Li13P6S21Cl -> 0.3585 Li4P2O7 + 0.3962 LiPO3 + 0.2642 FePS + 0.6604 FeS2 + 0.07547 LiCl |
| it2-c2 | Li7AsP2S11 | -0.149 | 0.36 | 0.1682 Li7AsP2S11 + 0.9159 LiFePO4 -> 0.1522 AsS + 0.008011 As2P2S7 + 0.5234 Li4P2O7 + 0.1896 FePS + 0.7263 FeS2 |
| it1-c4 | Li7P3SeS10 | -0.143 | 0.32 | 0.1446 Li7P3SeS10 + 0.9277 LiFePO4 -> 0.4217 Li4P2O7 + 0.07229 FeSe2 + 0.253 LiPO3 + 0.2651 FePS + 0.5904 FeS2 |

New UMA relaxations: 0 / 80

## 9C. Li diffusion (molecular dynamics, UMA normal precision)

| Structure | Formula | Kind | Atoms / Li | T (K) | ps | D (cm²/s) | D / D(parent) | MSD final (Å²) | ms/step |
|---|---|---|---|---|---|---|---|---|---|
| mp-985583 | Li3PS4 | parent | 128 / 48 | 1000 | 20 | 9.51e-05 | — | 93.5 | 72.11 |
| mp-641703 | Li7P3S11 | parent | 84 / 28 | 1000 | 20 | 4.81e-05 | — | 43.7 | 94.54 |
| it1-c4 | Li7P3SeS10 | candidate | 84 / 28 | 1000 | 20 | 3.79e-05 | 0.79 | 45.5 | 97.81 |
| it2-c5 | Li11P4S15I | candidate | 124 / 44 | 1000 | 20 | 5.74e-05 | 0.60 | 71.1 | 121.14 |
| it1-c2 | Li6P2S7O | candidate | 128 / 48 | 1000 | 20 | 5.05e-05 | 0.53 | 61.7 | 79.16 |
| it1-c1 | Li11P4S15Cl | candidate | 124 / 44 | 1000 | 20 | 8.21e-05 | 0.86 | 76.1 | 128.37 |

One temperature and one seed per structure: a first screening, not a conductivity value. Cells of ~84 atoms hold only ~24-28 Li, so D is noisy.

## Method notes

- Energies: UMA (uma-s-1p2, omat head) with the MP2020 correction scheme of Materials Project (anion corrections, GGA/GGA+U mixing), as MP's own energies. Each entry carries its structure and oxidation states, so the corrected anion atoms are the same on both sides of every reaction (checked by a test for every candidate and every phase of its hull).
- E_hull per atom is in eV/atom; E_hull per substitution = E_hull per atom x atoms / modified sites (replaced sites + Li vacancies), in eV per modified site.
- As and Sb candidates move with MP2020 because of a known approximation of the scheme, not an inconsistency: polysulfides (e.g. LiS4, AsS2) get the sulfide correction while elemental S gets none, so the excess sulfur of the decomposition goes to polysulfides instead of S8. MP treats its own data the same way.
- Reduced confidence: a decomposition through a polysulfide (S-S bonds) relies on the chemistry where UMA is least reliable: LiS4 is 0.178 eV/atom above the hull with raw UMA, 0.174 below it with UMA + MP2020, on the hull in MP.
- One reference is left out of the conservation check by design: LiSb3 (Sb formally -1/3), an alloy whose Sb the scheme does not correct (anion corrections only for oxidation states of -1 or lower), unlike Sb in Li3Sb.