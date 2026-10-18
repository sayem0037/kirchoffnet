# Experiment protocol

## Status and scope

This is the prospective protocol. Completed runs must be linked in the SKY130 results record. No planned experiment is a measured result. The original project scripts remain unchanged.

## Stage 0: model and simulator checks

Record upstream repository, commit, downloaded files and SHA-256 values; simulator version and binary hash; device model; geometry units; corner; temperature; supply; solver settings.

Start with a single NMOS DC sweep and inspect current direction, magnitude, finiteness and voltage dependence. Then inspect a differential pair and a four-transistor synapse. Check compatibility warnings; unresolved model parameters are failures, not harmless log noise. Use supported devices and voltage ranges from official documentation.

## Stage 1: cells and connected layers

1. Sweep input differential voltage and input common mode independently.
2. Sweep differential weight and average gate bias independently.
3. Sweep load resistance and neuron tail bias.
4. For two connected layers, vary fan-in with fan-out fixed, then fan-out with fan-in fixed.
5. Compare direct coupling with isolated stages and with a practical buffer/level-shifter alternative.
6. Verify the proposed operating envelope on configurations excluded from its calibration.

Suggested exploratory widths are 1, 2, 4, 8 and 16; they are a study design, not demonstrated scaling. Begin with two inputs, two hidden neurons and one output. Report exact bias-row inclusion and actual physical loading. Record all connected nodes, including the final array's column readout and any instantiated final neuron.

Observables: row and column common modes; differential voltages; per-device currents, overdrive and drain headroom; total supply current; loading current; numerical residual/status; local input-output sensitivities. Characterize nonlinear multiplication error rather than assuming a perfect bilinear cell.

## Stage 2: numerical validation

For representative inputs and parameters in every layer, compare sensitivities with central finite differences at multiple perturbation sizes. Perturbations must exceed netlist quantization and solver noise. Include directional derivatives and both absolute and normalized errors. Report median, high percentiles, worst cases and near-zero-gradient handling.

Do not select a favorable perturbation after inspecting final results as the sole proof of correctness. Confirm an agreement plateau and repeat on held-out configurations. Missing sensitivity data must raise an explicit error rather than silently becoming zero.

For DC-intended computation compare operating-point solutions and sufficiently settled transients; change maximum timestep, integration method where supported, tolerance and simulation duration. Do not confuse printed output interval with solver internal maximum step. For genuine transient computation, differentiate the intended transient objective and validate that objective separately.

## Stage 3: method comparisons

| ID | Method | Question |
|---|---|---|
| A | Ideal mathematical training then mapping | How large is the mapping gap? |
| B | Per-layer calibration plus circuit weight training, fixed biases | Does ordinary calibration already solve the problem? |
| C | Calibrated hardware-aware surrogate with learned ranges | Does a simpler scalable training method suffice? |
| D | Joint weight/bias optimization without operating constraints | Are constraints responsible for the benefit? |
| E | Proposed constrained joint method | Does the proposed contribution work? |
| F | Buffered/level-shifted network with appropriate training | Is direct coupling worth retaining? |

Match task, preprocessing, splits, input precision and tuning budgets. Match design constraints where possible and disclose differences in device count and power. Compare against tuned baselines, not only intentionally failing settings.

Use a small task for debugging and at least one substantive task for evaluation. Downsampled MNIST is a reasonable first benchmark; document resolution and preprocessing and compare to software using identical inputs. Toy tasks and Iris alone do not demonstrate broad scalability.

Separate training/validation/test data. Select checkpoints and hyperparameters on validation data. Use multiple training seeds. Count failed simulations explicitly and report results both with the prescribed failure policy and the failure rate.

## Stage 4: robustness and physical cost

Use model-supported corners and specified supply/temperature ranges. Hold mismatch fixed across inputs for each simulated chip; resample time-varying noise appropriately. Separate one-model-across-chips evaluation from per-chip calibration and include its cost.

Measure settling from input transitions against a declared score/decision tolerance. Integrate supply power over the stated inference interval; disclose idle/static energy and the handling of programming energy. Include real output sensing and bias-storage assumptions. Core-only estimates must not be compared directly to complete-chip measurements.

For area or parasitic claims, implement representative layout and extraction if available. Without layout, label dimensions/area as estimates and parasitic studies as assumptions.

## Decision gates

- No model or solver errors before device results are used.
- No training claims before gradients/optimization method are validated for the actual model.
- No novelty claim based only on beating A.
- No robustness guarantee inferred from finitely sampled conditions.
- If E does not improve the trade-off over B/C/F, revise the contribution rather than hide the comparison.

## Result record

Each run must save configuration, circuit netlist, model provenance, simulator log, raw measurements and summary metrics. Record status, including failure. Save original data before plotting. Never fill a missing result with a plausible value.
