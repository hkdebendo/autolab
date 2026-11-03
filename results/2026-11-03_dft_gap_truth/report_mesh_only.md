# Truth test: DFT band gap (GPAW, PBE) vs Materials Project (PBE)

Settings: plane waves 400 eV, k-point density 2.5 /Å, 8 CPUs on Modal. Passed when |GPAW - MP| <= 0.3 eV (metals: GPAW <= 0.1 eV).

| Compound | Atoms | MP PBE (eV) | GPAW PBE (eV) | Difference (eV) | Time (s) | Verdict |
|---|---|---|---|---|---|---|
| Li2S (mp-1153) | 3 | 3.39 | 3.66 | +0.28 | 9.7 | passed |
| Li (mp-135) | 1 | 0.00 | 0.00 | +0.00 | 5.5 | passed |
| LiI (mp-570935) | 4 | 4.38 | 4.41 | +0.03 | 21.4 | passed |
| Li3P (mp-736) | 8 | 0.70 | 1.08 | +0.38 | 16.4 | failed |
| Na3SbS4 (mp-10167) | 8 | 1.93 | 2.01 | +0.08 | 177.1 | passed |
| Li3PS4 (mp-985583) | 32 | 2.81 | 2.86 | +0.05 | 109.1 | passed |

**5 / 6 passed.**
