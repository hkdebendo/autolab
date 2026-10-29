# Li diffusion screening: 600 K, 2 seeds of 40 ps pooled (UMA, block D, Modal NVIDIA A10)

Verdict rule (config.MD_EXCLUDED_VERDICTS): a candidate slower than its parent by more than 2 combined errors is excluded for conduction but stays listed; tied or faster passes.

| Structure | Kind | Parent | D ± s.e. (cm²/s) | D per seed | D / D(parent) | Verdict | Conduction | Framework |
|---|---|---|---|---|---|---|---|---|
| Li7P3S11 (mp-641703) | parent | — | 1.30e-05 ± 2.2e-06 | 1.28e-05, 1.32e-05 | — | — | — | intact |
| Li7P3SeS10 (it1-c4) | candidate | Li7P3S11 | 1.39e-05 ± 1.8e-06 | 1.56e-05, 1.21e-05 | 1.07 ± 0.23 | tied | passes | intact |
| Li13P6S21Cl (it2-c1) | candidate | Li7P3S11 | 1.25e-05 ± 1.4e-06 | 1.05e-05, 1.45e-05 | 0.96 ± 0.20 | tied | excluded | MOVED |
| Li3PS4 (mp-985583) | parent | — | 5.94e-06 ± 1.2e-06 | 7.89e-06, 3.99e-06 | — | — | — | intact |
| Li11P4S15Cl (it1-c1) | candidate | Li3PS4 | 5.53e-06 ± 1.2e-06 | 6.29e-06, 4.76e-06 | 0.93 ± 0.28 | tied | passes | intact |
| Li6P2S7O (it1-c2) | candidate | Li3PS4 | 7.86e-06 ± 8.1e-07 | 7.96e-06, 7.76e-06 | 1.32 ± 0.30 | tied | passes | intact |
| Li11P4S15I (it2-c5) | candidate | Li3PS4 | 5.34e-06 ± 1.7e-06 | 3.82e-06, 6.87e-06 | 0.90 ± 0.34 | tied | passes | intact |