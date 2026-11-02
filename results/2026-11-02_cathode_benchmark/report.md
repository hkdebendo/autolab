# Blind benchmark of the cathode funnel

Known compounds go through the same steps as a candidate (no cobalt, charge neutrality, removable Li, UMA relaxation, E_hull with their own composition removed from the hull, charge), never shown to the model. Expected outcomes fixed before the runs (config.CATHODE_BENCHMARK).

| Compound | Group | Expected | Outcome | E_hull (eV/atom) | Voltage (V) | Capacity (mAh/g) | Volume change (%) | Why |
|---|---|---|---|---|---|---|---|---|
| LiNiO2 (mp-865631) | good | passed | ✅ passed | -0.007 | 3.95 | 274 | -2.4 | layered Ni cathode, about 3.8 V |
| Li3V2(PO4)3 (mp-6396) | good | passed | ✅ passed | -0.010 | 3.73 | 197 | 5.7 | NASICON V cathode, 3.6-4.6 V plateaus |
| LiTiO2 (mp-38280) | hard negative | voltage | ✅ voltage | -0.025 | 1.46 | 309 | 0.5 | Ti3+/Ti4+ couple far below 3 V |
| Li2FeSiO4 (mp-18968) | hard negative | voltage | ❌ passed | -0.036 | 3.29 | 166 | -0.9 | real cathode at 2.8 V after cycling (Nyten 2005): below the 3.0 V window |
| LiCoO2 (mp-22526) | bad | generate | ✅ generate | — | — | — | — | contains cobalt |
| Li2MnO3 (mp-18988) | bad | voltage | ✅ voltage | — | — | — | — | Mn4+: no Li can leave |
| LiFeO2 (mp-19419) | bad | voltage | ✅ voltage | — | — | — | — | Fe3+: no Li can leave |
| Li3PO4 (mp-13725) | bad | voltage | ✅ voltage | — | — | — | — | no redox element |
| LiAlO2 (mp-8001) | bad | voltage | ✅ voltage | — | — | — | — | no redox element |
| Li4Ti5O12 (mp-685194) | bad | voltage | ✅ voltage | — | — | — | — | Ti4+: an anode, no Li can leave |

Agreement: good 2/2, hard negative 1/2, bad 6/6; total 9/10.

New relaxations: 29.
