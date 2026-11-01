# Ionic conductivity at 300 K from UMA molecular dynamics

**Truth test: PASSED** (fixed before the runs): Li7P3S11 above beta-Li3PS4 (yes), each within a factor 10 of experiment.

Method: blocks of the cached runs pooled per temperature (runs up to 750 K), weighted Arrhenius fit of ln D against 1/T, extrapolation to 300 K, Nernst-Einstein with the Li density of the relaxed cell (Haven ratio 1). Range: one standard error of the extrapolated ln D.

| Structure | Temperatures (K) | Ea (eV) | σ 300 K (mS/cm) | Range (mS/cm) | Experiment (mS/cm) | Method |
|---|---|---|---|---|---|---|
| Li7P3S11 (mp-641703) | 500, 600, 700 | 0.14 ± 0.03 | 99.9 | 58–1.7e+02 | 3.2–17 | own Arrhenius fit (500, 600, 700 K) |
| Li3PS4 (mp-985583) | 500, 600, 700 | 0.34 ± 0.05 | 1.18 | 0.43–3.2 | 0.16 | own Arrhenius fit (500, 600, 700 K) |
| Li6P2SeS7 (s1:it1-c2) | 500, 600, 700 | 0.42 ± 0.10 | 0.0979 | 0.012–0.8 | — | own Arrhenius fit (500, 600, 700 K) |
| Li12P4SeS15 (ref:it2-c2) | 500, 600, 700 | 0.24 ± 0.07 | 5.66 | 1.5–22 | — | own Arrhenius fit (500, 600, 700 K) |
| Li7P3SeS10 (s9:it1-c4) | 500, 600, 700 | 0.12 ± 0.05 | 134 | 50–3.6e+02 | — | own Arrhenius fit (500, 600, 700 K) |

D per temperature (cm²/s, blocks of all cached runs pooled):

- Li7P3S11 (mp-641703): 500 K: 9.15e-06 ± 1.5e-06 (1 run(s)); 600 K: 1.27e-05 ± 1.7e-06 (3 run(s)); 700 K: 2.14e-05 ± 1.5e-06 (1 run(s))
- Li3PS4 (mp-985583): 500 K: 2.19e-06 ± 6.0e-07 (1 run(s)); 600 K: 5.97e-06 ± 9.9e-07 (3 run(s)); 700 K: 1.97e-05 ± 4.0e-06 (1 run(s))
- Li6P2SeS7 (s1:it1-c2): 500 K: 2.08e-07 ± 1.6e-07 (1 run(s)); 600 K: 3.90e-06 ± 9.6e-07 (2 run(s)); 700 K: 7.79e-06 ± 2.3e-06 (1 run(s))
- Li12P4SeS15 (ref:it2-c2): 500 K: 1.94e-06 ± 6.8e-07 (1 run(s)); 600 K: 4.87e-06 ± 1.1e-06 (2 run(s)); 700 K: 9.30e-06 ± 2.8e-06 (1 run(s))
- Li7P3SeS10 (s9:it1-c4): 500 K: 8.81e-06 ± 2.2e-06 (1 run(s)); 600 K: 1.39e-05 ± 1.8e-06 (2 run(s)); 700 K: 1.96e-05 ± 4.5e-06 (1 run(s))

New runs: 6 on Modal H100, estimate 5.57 $.
