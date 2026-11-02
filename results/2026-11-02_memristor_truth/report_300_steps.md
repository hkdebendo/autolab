# Truth test of the oxygen-vacancy migration barriers (NEB with UMA)

Criterion, fixed before the runs: CeO2 <= 1.1 eV and MgO at least 0.5 eV higher, every band converged (fixed before the runs).

| Material | Role | Atoms | Hops (Å) | Barriers (eV) | Lowest (eV) |
|---|---|---|---|---|---|
| CeO2 (mp-20194) | fast reference | 81 | 2.73 | 0.45 | 0.45 |
| MgO (mp-1265) | slow reference | 128 | 3.01 | 4.29 | 4.29 |
| HfO2 (mp-352) | parent of the domain | 96 | 2.54, 2.58 | 2.02 (not converged), 2.42 | 2.42 |
| TiO2 (mp-2657) | parent of the domain | 96 | 2.56, 2.8 | 0.63, 1.04 | 0.63 |
| SrTiO3 (mp-5229) | parent of the domain | 135 | 2.79 | 0.34 | 0.34 |

Tests: {'fast_low': True, 'slow_above_fast': True, 'converged': False}.
**Verdict: FAILED.**
