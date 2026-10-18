# Gaps and possible solutions

| Gap | Proposed action | Evidence that closes the gap |
|---|---|---|
| Simplified Level-1 devices | Port a small circuit to authentic SKY130 compact models; redesign voltages and geometries for the selected device family | Single-device and cell curves, model revision and simulator logs |
| Initial layer sizing misses interactions | Characterize two connected stages and independently vary fan-in and fan-out | Predicted versus simulated voltage/current feasibility maps |
| Training can move the circuit outside its usable range | Joint weight/bias updates with connected-state constraint checks | Reduced failures and improved useful signal against tuned baselines |
| Tail bias couples gain and common mode | Evaluate constrained tuning, separate level shifting, and common-mode control | Accuracy, signal swing and physical cost comparisons |
| Adequate headroom does not ensure adequate signal | Monitor gain and output decision margin relative to noise/readout errors | Depth sweeps and noise-aware classification results |
| Gradient correctness is configuration dependent | Finite differences at multiple perturbations, directional checks, convergence tests | Error distributions including worst cases; explain near-zero derivatives and failures |
| Custom simulator may not support PDK models/sensitivities | Use a compatible SPICE engine; validate any surrogate or external gradient calculation against it | Identical-circuit comparisons, not reuse of Level-1 claims |
| Ideal voltage sources stand in for weight memory | Select SRAM/DAC, sampled bias storage, or a documented external-bias prototype | Precision, drift, update cost and area/power accounting |
| Nominal results may fail on other chips | PDK process corners, mismatch Monte Carlo, supply and temperature sweeps | Failure counts and distributions on held-out conditions |
| Unknown physical timing | Include intrinsic/external parasitics; test input transitions and initialization history | Defined settling metric and timestep convergence |
| Incomplete efficiency accounting | Include drivers, bias generation, storage, output sensing and static power | State the measurement boundary; label core-only numbers as such |
| Novelty not established | Compare the exact proposed method against closest prior methods and simpler engineering fixes | Reproducible incremental benefit, not only a new name |

Priority: model/simulator validation -> cell characterization -> two-layer compatibility -> method comparison -> robustness -> layout/system costs.

Avoid claiming statistical manufacturing yield from arbitrary independent parameter perturbations. Use supplied statistical models when available; otherwise call the result a sensitivity study. Separate a single frozen model evaluated across chips from per-chip recalibration or retraining.
