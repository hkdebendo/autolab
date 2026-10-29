# MD calibration v2: Li7P3S11 vs beta-Li3PS4 at 600 K, 3 seeds of 40 ps (UMA, block D)

Test fixed in SPEC section 7 before these runs (commit 19dca4a). The initial test (600 and 700 K, md_calibration.md) failed and stays failed.

**Truth test v2: PASSED** — framework intact: True; D(Li7P3S11) / D(Li3PS4) = 2.04, difference 3.6 combined standard errors (needed: more than 2).

| Parent | seed | D, blocks ± s.e. (cm²/s) | P MSD final (Å²) | S MSD final (Å²) | Framework | GPU ms/step |
|---|---|---|---|---|---|---|
| Li7P3S11 | 0 | 1.28e-05 ± 2.4e-06 | 0.10 | 0.22 | intact | 24.43 |
| Li7P3S11 | 1 | 1.32e-05 ± 4.2e-06 | 0.07 | 0.17 | intact | 18.53 |
| Li7P3S11 | 2 | 1.24e-05 ± 1.5e-06 | 0.12 | 0.24 | intact | 18.59 |
| Li3PS4 | 0 | 7.89e-06 ± 1.2e-06 | 0.11 | 0.17 | intact | 22.32 |
| Li3PS4 | 1 | 3.99e-06 ± 1.7e-06 | 0.06 | 0.11 | intact | 22.26 |
| Li3PS4 | 2 | 6.90e-06 ± 1.5e-06 | 0.06 | 0.14 | intact | 22.52 |

| Parent | Seeds pooled | Blocks | D pooled ± s.e. (cm²/s) |
|---|---|---|---|
| Li7P3S11 | 0, 1, 2 | 12 | 1.28e-05 ± 1.5e-06 |
| Li3PS4 | 0, 1, 2 | 12 | 6.26e-06 ± 9.3e-07 |