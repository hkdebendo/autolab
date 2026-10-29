# MD calibration: Li7P3S11 vs beta-Li3PS4 (UMA, block D)

**Truth test: FAILED** — framework intact at 600, 700 K: True; Li7P3S11 faster than Li3PS4 by more than 2 combined standard errors: False.

## Diffusion coefficients

| Parent | T (K) | ps | seed | Atoms / Li | D, blocks ± s.e. (cm²/s) | D, one origin (cm²/s) | P MSD final (Å²) | S MSD final (Å²) | Framework | ms/step |
|---|---|---|---|---|---|---|---|---|---|---|
| Li7P3S11 | 600 | 40 | 0 | 84 / 28 | 1.28e-05 ± 2.4e-06 | 1.59e-05 | 0.10 | 0.22 | intact | 24.43 |
| Li7P3S11 | 700 | 30 | 0 | 84 / 28 | 2.14e-05 ± 1.5e-06 | 8.20e-06 | 0.14 | 0.29 | intact | 19.43 |
| Li7P3S11 | 1000 | 20 | 1 | 84 / 28 | 4.89e-05 ± 6.8e-06 | 7.42e-05 | 0.22 | 0.55 | intact | 20.39 |
| Li3PS4 | 600 | 40 | 0 | 128 / 48 | 7.89e-06 ± 1.2e-06 | 7.13e-06 | 0.11 | 0.17 | intact | 22.32 |
| Li3PS4 | 700 | 30 | 0 | 128 / 48 | 1.97e-05 ± 4.0e-06 | 1.04e-05 | 0.15 | 0.23 | intact | 22.79 |
| Li3PS4 | 1000 | 20 | 1 | 128 / 48 | 5.09e-05 ± 6.1e-06 | 4.88e-05 | 0.27 | 1.11 | intact | 24.22 |

## Order of the parents (expected: Li7P3S11 faster)

| T (K) | D(Li7P3S11) / D(Li3PS4) | Difference in standard errors | Test |
|---|---|---|---|
| 600 | 1.62 | 1.9 | FAILED |
| 700 | 1.09 | 0.4 | FAILED |

## Activation energies (Arrhenius fit of the block D)

| Parent | Ea, test temperatures (eV) | Ea, all temperatures (eV) | Literature MD (eV) |
|---|---|---|---|
| Li7P3S11 | 0.19 ± 0.07 | 0.17 ± 0.03 | 0.19 |
| Li3PS4 | 0.33 ± 0.09 | 0.23 ± 0.02 | 0.35–0.41 |

Framework: every element other than Li must diffuse at less than 5% of Li (a bounded MSD of P and S is vibration or PS4 rotation; a growing one means the structure melted or disordered). beta-Li3PS4 turns into its alpha phase near 746 K, so the order is tested below it and 1000 K is shown for information.