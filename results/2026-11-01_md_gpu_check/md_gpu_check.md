# Same D on H100 and A10G? (600 K, 40 ps)

**Result: SAME** — criterion fixed before the runs: |D(H100, seed 0) - D(A10G, calibration v2 pooled)| <= 2 combined standard errors, framework intact, for both parents.

| Parent | D H100 (cm²/s) | D A10G pooled (cm²/s) | D A10G seed 0 | Difference (σ) | Framework | ms/step H100 / A10G |
|---|---|---|---|---|---|---|
| Li7P3S11 | 1.27e-05 ± 3.18e-06 | 1.28e-05 ± 1.53e-06 | 1.28e-05 ± 2.36e-06 | -0.0 | intact | 14.35 / 24.43 (1.7x) |
| Li3PS4 | 7.01e-06 ± 1.88e-06 | 6.26e-06 ± 9.26e-07 | 7.89e-06 ± 1.22e-06 | +0.4 | intact | 16.64 / 22.32 (1.3x) |

Device reported by the runs: H100.