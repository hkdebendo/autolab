# Cobalt-free cathodes: live research 590fa5770002 (2026-11-02)

Request: *Find new cobalt-free cathodes for lithium-ion batteries with a higher energy density than LiFePO4.*

The agent searched for cobalt-free cathode candidates with higher energy density than LiFePO4 and proposed nine new compositions. Seven of them passed the initial stability funnel. The three most stable finalists were Li8TiMn11(NiO8)4 with energy above the hull of about 0.00 eV per atom, Li8Mn11V(NiO8)4 with about 0.01 eV per atom, and Li8ZrMn11(NiO8)4 with about 0.02 eV per atom. No band gap or energy density values were reported for the finalists in this run, so a comparative assessment versus LiFePO4 could not be completed. The run stopped after the planned iterations with stable candidates identified but without confirmed electronic or performance metrics.

## Final scientific report

### Executive summary

The search looked for cobalt-free cathodes with higher energy density than LiFePO4. The champion is Li8TiMn11(NiO8)4, derived from Li2Mn3NiO8. It has 701.0 Wh/kg at 4.754 V and 147.4 mAh/g, with 0.003 eV/atom and 3.44% volume change. Its parent computed the same way has 692.0 Wh/kg at 4.718 V and 146.7 mAh/g, with 3.86% volume change. Two backup finalists on the same parent have 690.0 Wh/kg and 676.0 Wh/kg. Two phosphate candidates were rejected as already known. Ionic conductivity, diffusion, voltage profiles, rate capability, cycling, synthesis, cost and experimental data were not computed.

### Comparison of the finalists

| | Li8TiMn11(NiO8)4 | Li8Mn11V(NiO8)4 | Li8ZrMn11(NiO8)4 |
|---|---|---|---|
| Parent cathode | Li2Mn3NiO8 | Li2Mn3NiO8 | Li2Mn3NiO8 |
| Substitution | Mn→Ti ×1 | Mn→V ×1 | Mn→Zr ×1 |
| Space group | C2 | C2 | C2 |
| E_hull (eV/atom) | 0.003 | 0.008 | 0.016 |
| Li removed on charge | 8 of 8 | 8 of 8 | 8 of 8 |
| Average voltage (V) | 4.75 (parent 4.72) | 4.69 (parent 4.72) | 4.72 (parent 4.72) |
| Theoretical capacity (mAh/g) | 147 (parent 147) | 147 (parent 147) | 143 (parent 147) |
| Energy density (Wh/kg) | 701 (parent 692) | 690 (parent 692) | 676 (parent 692) |
| Volume change on charge (%) | 3.4 (parent 3.9) | 3.4 (parent 3.9) | 3.9 (parent 3.9) |

### Champion: Li8TiMn11(NiO8)4

**Why it is preferred.**

- It has the highest energy density among finalists at 701.0 Wh/kg, compared with 690.0 Wh/kg and 676.0 Wh/kg.
- It improves on its parent computed the same way, with 701.0 Wh/kg versus 692.0 Wh/kg, 4.754 V versus 4.718 V, and 147.4 mAh/g versus 146.7 mAh/g.
- Its stability value of 0.003 eV/atom is the lowest among finalists, compared with 0.008 eV/atom and 0.016 eV/atom.
- Its substitution cost of 0.146 eV is lower than 0.462 eV and 0.869 eV for the other finalists on the same parent.
- Its volume change of 3.44% on removal of 8 of 8 Li is small and lower than 3.86% for its parent computed the same way.

**Trade-offs.**

- Its average voltage of 4.754 V is high and may exceed electrolyte stability.
- Its high Mn content risks Jahn-Teller Mn3+ distortion and Mn dissolution during cycling.
- Its Ni-Mn oxide framework may have low electronic conductivity.

**Uncertainties.**

- Energies and voltages use UMA energies instead of DFT, so stability and voltage carry modelling error.
- Only the average voltage over full removal of 8 of 8 Li was computed, not the full voltage profile.
- Only one ordering of the substituted sites was computed, not all possible arrangements.
- Magnetism was not treated explicitly, which can affect transition-metal energies.

**Validation to do.**

- Recalculate stability and average voltage with DFT+U for Mn, Ni and Ti oxides. *(documented)*
- Attempt synthesis and check the structure with X-ray diffraction. *(documented)*
- Test lithium storage with galvanostatic cycling to measure capacity, voltage and volume change. *(documented)*

**Synthesis routes to consider.**

- Try solid-state reaction of lithium, manganese, nickel and titanium precursors with high-temperature firing. *(documented)*
- Try sol-gel mixing of the cations followed by calcination to form the spinel phase. *(documented)*

### Methods

- **Candidate proposals and decisions**: Meta Muse Spark (reasoning model), with comparisons computed by the code
- **Structure relaxation and energies**: Meta FAIR UMA (uma-s-1p2, OMat head), atoms and cell relaxed, MP2020 corrections for the hull; references from Materials Project relaxed with UMA
- **Thermodynamic stability**: energy above the convex hull of the stable known phases of the system; kept if <= 0.08 eV/atom
- **Voltage, capacity, energy density**: the Li that charge neutrality allows removed, delithiated cell relaxed with UMA; average voltage from the UMA energies and Li metal; theoretical capacity from the Li removed (calibrated on four known cathodes)
- **Volume change**: lithiated and delithiated cells, both relaxed with UMA
- **Independent reviews**: Meta Muse Spark Open, one review per passed candidate, in parallel
- **Error-driven loop**: each iteration's failures, with their numbers, go back to the proposing model, which explains them as hypotheses and corrects its next proposals
- **Plain-language summaries**: Meta Muse Glimmer

### Limitations

- Lithium diffusion, ionic conductivity, voltage profiles, rate capability and cycling were not computed.
- Synthesis routes, element cost and experimental data were not computed.
- The candidates are computational predictions, not proven materials.
- Not computed: measured ionic conductivity (room-temperature values are extrapolated estimates from molecular dynamics at 500-700 K, with their range), DFT calculations (UMA energies carry an error bar measured against DFT on known compounds), synthesis routes, cost of the elements, experimental data, for cathodes: voltage profiles and rate capability (only the average voltage over full delithiation), lithium diffusion in the cathode, cycling.
- The candidates are computational predictions, not proven materials.

