# Manuscript outline

Working title: Joint Weight and Bias Optimization for Directly Coupled CMOS Analog Neural Networks.

## Abstract

State the interlayer compatibility problem, proposed specific method, evaluation technology and actual comparative results. Until experiments exist, keep this section as an outline; do not invent percentages, energy or speed claims.

## 1. Introduction

Explain why functional individual cells may fail when connected and when biases change during training. Distinguish current KFQ from KirchhoffNet's initial-state dynamics. Present only contributions supported by the final evidence.

## 2. Related work

Organize by CMOS multiplication; analog interlayer processing; physical/circuit-aware learning; constrained hardware-aware training. Use the literature matrix to identify what is already known and the specific remaining problem.

## 3. Circuit and problem formulation

Show all devices in one four-transistor synapse and one differential-pair neuron, then their actual source-connected interface. Define differential and common-mode signals, fan-in, fan-out, weight biases and class-score readout. Separate ideal algebra from PDK behavior.

## 4. Operating-range analysis and proposed method

Derive voltage/current constraints and specify their assumptions. Explain joint optimization, accepted/rejected updates, design-time versus programmable variables and computational cost. Identify conditions where the topology has no usable operating region.

## 5. Experimental methodology

Report PDK revision, simulator, geometries, corners, solver tolerances, data splits, seeds, baselines, numerical checks and failure policy. Describe input/bias/readout circuits and which physical costs are included.

## 6. Results

Present cell checks, predicted versus observed feasibility, method ablations, depth/width behavior, robustness and cost trade-offs. Report unsuccessful configurations. Treat simulator elapsed time separately from circuit inference time.

## 7. Limitations and conclusion

Explain simulation-to-silicon limitations, bias storage and layout status, finite coverage of robustness tests, training cost and scope of datasets. Do not generalize beyond tested conditions.

## Planned figures

1. Actual synapse-neuron schematic and comparison of computational protocols.
2. Single-cell transfer surfaces and multiplication error.
3. Two-layer feasibility versus fan-in/fan-out and common mode.
4. Training trajectories including constraint violations and signal margin.
5. Ablations and buffered-baseline comparisons with variation across seeds.
6. Accuracy/power/settling trade-offs and PVT/mismatch distributions.

## Tables and supplementary material

- Literature/claim matrix.
- Circuit/model and test conditions.
- Baseline definitions and all result metrics.
- Numerical validation and failed-run accounting.
- Reproducible configurations, model hashes, netlists and raw results.
