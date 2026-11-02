# Check of the barrier tolerance (memristor domain)

Rule, fixed before the runs: the largest difference between equivalent hops (noise) and between cell sizes (finite size) must stay within MEMRISTOR_EA_SIGNIFICANT_EV = 0.15 eV; else the tolerance becomes that spread rounded up to 0.05 eV.

| Hop | Barrier (eV) | Equivalent pair (eV) | Difference (eV) |
|---|---|---|---|
| 2.56 Å | 0.632 | 0.632 | 0.000 |
| 2.8 Å | 1.043 | 1.035 | 0.008 |

Lowest hop: 0.632 eV in 96 atoms, 0.651 eV in 270 atoms (finite-size difference 0.019 eV).

**Spread: 0.019 eV → tolerance kept at 0.15 eV.**
