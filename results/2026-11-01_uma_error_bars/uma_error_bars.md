# UMA vs DFT (Materials Project) on known compounds

Each known compound of a system is left out of the hull and its decomposition energy (eV/atom, negative when stable) is computed with UMA + MP2020 and with MP (GGA/GGA+U, MP2020) energies, in separate hulls. The mean absolute difference is the error bar given with the E_hull of a candidate of that system.

| System | Compounds | Mean abs. diff. (eV/atom) | Largest (eV/atom) | Mean signed (eV/atom) | Polysulfides: n / mean abs. / largest |
|---|---|---|---|---|---|
| Al-Li-P-S | not available: references not all relaxed by UMA in the cache (21 new relaxations requested, 0 left (MAX_RELAXATIONS_PER_RUN)) | | | | |
| As-Li-P-S | 31 | 0.0044 | 0.0126 | -0.0010 | 3 / 0.0065 / 0.0124 |
| Br-Li-P-S | 23 | 0.0049 | 0.0126 | -0.0016 | 3 / 0.0065 / 0.0124 |
| Cl-Li-P-S | 23 | 0.0048 | 0.0126 | -0.0020 | 3 / 0.0054 / 0.0124 |
| F-Li-P-S | 23 | 0.0056 | 0.0159 | -0.0016 | 2 / 0.0080 / 0.0124 |
| Ge-Li-P-S | 31 | 0.0056 | 0.0126 | -0.0019 | 2 / 0.0080 / 0.0124 |
| Ge-Li | 6 | 0.0054 | 0.0086 | -0.0025 | 0 / — / — |
| I-Li-P-S | 23 | 0.0047 | 0.0126 | -0.0020 | 2 / 0.0080 / 0.0124 |
| Li-Mg-P-S | 34 | 0.0054 | 0.0209 | -0.0011 | 2 / 0.0080 / 0.0124 |
| Li-Na-P-S | 33 | 0.0041 | 0.0126 | -0.0010 | 5 / 0.0039 / 0.0124 |
| Li-O-P-S | 36 | 0.0050 | 0.0166 | -0.0003 | 2 / 0.0080 / 0.0124 |
| Li-P-S-Sb | 30 | 0.0117 | 0.1611 | +0.0022 | 2 / 0.0080 / 0.0124 |
| Li-P-S-Se | 25 | 0.0053 | 0.0126 | -0.0022 | 3 / 0.0066 / 0.0124 |
| Li-P-S | 18 | 0.0054 | 0.0126 | -0.0019 | 2 / 0.0080 / 0.0124 |
| Li-P | 5 | 0.0058 | 0.0126 | +0.0006 | 0 / — / — |
| Li-S-Sb | 13 | 0.0209 | 0.1611 | +0.0064 | 1 / 0.0124 / 0.0124 |
| Li-S | 2 | 0.0096 | 0.0124 | -0.0096 | 1 / 0.0124 / 0.0124 |
| Li-Sb | 4 | 0.0409 | 0.1611 | +0.0398 | 0 / — / — |
| Li-Si | 6 | 0.0022 | 0.0052 | -0.0006 | 0 / — / — |

## Largest differences

| Compound | MP (eV/atom) | UMA + MP2020 (eV/atom) | Difference | Polysulfide |
|---|---|---|---|---|
| LiSb3 (mp-1185416) | +0.0474 | +0.2085 | +0.1611 |  |
| LiSbS (mp-2206511) | +0.0217 | -0.0408 | -0.0625 |  |
| LiMg5 (mp-1094609) | -0.0114 | +0.0095 | +0.0209 |  |
| Li2O (mp-1960) | -0.9615 | -0.9781 | -0.0166 |  |
| LiF (mp-1138) | -3.1644 | -3.1803 | -0.0159 |  |
| LiO8 (mp-1235059) | -0.0604 | -0.0452 | +0.0152 |  |
| LiMg3 (mp-1094603) | +0.0216 | +0.0089 | -0.0127 |  |
| LiP5 (mp-2412) | +0.0104 | +0.0230 | +0.0126 |  |
| LiS4 (mp-995393) | -0.1618 | -0.1742 | -0.0124 | yes |
| GeP3 (mp-7542) | +0.0292 | +0.0403 | +0.0111 |  |

## Polysulfides (S-S bonds)

Largest difference over 9 polysulfides: 0.0124 eV/atom (AsS2 -0.0036, LiS4 -0.0124, Na2S5 -0.0018, NaS +0.0006, NaS2 +0.0011, P2S7 -0.0036, SBr +0.0035, SCl +0.0003, SeS7 -0.0038).
