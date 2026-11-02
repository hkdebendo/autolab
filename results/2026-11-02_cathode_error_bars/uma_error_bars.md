# UMA vs DFT (Materials Project) on known compounds

Each known compound of a system is left out of the hull and its decomposition energy (eV/atom, negative when stable) is computed with UMA + MP2020 and with MP (GGA/GGA+U, MP2020) energies, in separate hulls. The mean absolute difference is the error bar given with the E_hull of a candidate of that system.

| System | Compounds | Mean abs. diff. (eV/atom) | Largest (eV/atom) | Mean signed (eV/atom) | Polysulfides: n / mean abs. / largest |
|---|---|---|---|---|---|
| Li-Mn-Ni-O-Ti | 45 | 0.0071 | 0.0298 | +0.0003 | 0 / — / — |
| Li-Mn-Ni-O-V | 41 | 0.0068 | 0.0298 | +0.0013 | 0 / — / — |
| Li-Mn-Ni-O-Zr | 33 | 0.0101 | 0.0782 | -0.0007 | 0 / — / — |
| Li-Mn-Ni-O | 23 | 0.0076 | 0.0298 | +0.0009 | 0 / — / — |
| Al-Li-Mn-O | 24 | 0.0061 | 0.0298 | +0.0014 | 0 / — / — |
| Li-Mn-O-Ti | 27 | 0.0067 | 0.0298 | +0.0012 | 0 / — / — |
| Li-Mn-O-P-Si | 55 | 0.0047 | 0.0298 | +0.0011 | 0 / — / — |
| Fe-Li-O-P | 34 | 0.0090 | 0.0641 | -0.0020 | 0 / — / — |

## Largest differences

| Compound | MP (eV/atom) | UMA + MP2020 (eV/atom) | Difference | Polysulfide |
|---|---|---|---|---|
| ZrO2 (mp-2858) | -3.1270 | -3.2052 | -0.0782 |  |
| Fe2O3 (mp-19770) | -0.5219 | -0.4578 | +0.0641 |  |
| FeO (mp-1274279) | -0.0589 | -0.1026 | -0.0437 |  |
| LiFeO2 (mp-755709) | -0.0691 | -0.1030 | -0.0339 |  |
| MnO (mp-1232659) | -0.1824 | -0.1526 | +0.0298 |  |
| FePO4 (mp-753395) | -0.0598 | -0.0895 | -0.0297 |  |
| TiO (mp-1071163) | -0.0800 | -0.0565 | +0.0235 |  |
| LiVO2 (mp-19340) | -0.1212 | -0.0990 | +0.0222 |  |
| MnNi3 (mp-11501) | -0.0947 | -0.0747 | +0.0200 |  |
| LiMnP2O7 (mp-31924) | -0.0249 | -0.0057 | +0.0191 |  |
