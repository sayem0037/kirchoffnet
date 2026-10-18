# KFQ paper research and SKY130 study

Working title: **Joint Weight and Bias Optimization for Directly Coupled CMOS Analog Neural Networks**

Prepared 2026-10-18. This folder separates established literature, evidence from the existing implementation, proposed methods, and experiments actually performed. The proposed contribution is not yet established as novel or effective.

## Research question

Can joint selection of differential weights and circuit operating biases keep directly connected CMOS neural-network layers functional as fan-in, fan-out, depth and process conditions change, with a useful accuracy/power/area trade-off against calibrated and buffered alternatives?

The user selected the open SkyWater SKY130 PDK. The existing KFQ Level-1 models and custom simulator are historical baselines, not SKY130 validation. Setup and new experiment results belong here rather than in the original training output directory.

## Contents

- [Paper approach](01_paper_approach.md): scope, contribution candidates and claim boundaries.
- [Literature comparison](02_literature.md): primary sources and their implications for novelty.
- [Gaps and solutions](03_gaps_and_solutions.md): implementation gaps and proposed remedies.
- [Experiment protocol](04_experiment_protocol.md): staged experiments, baselines and reporting rules.
- [Manuscript outline](05_manuscript_outline.md): structure and required figures.
- [Evidence record](06_evidence.md): existing code and reports, separated from new results.
- [SKY130 setup](sky130/README.md): model provenance, simulator and reproducibility.
- [References](references.bib): citation metadata; check final publisher metadata before submission.

## Claim status

| Claim | Status |
|---|---|
| Four-quadrant CMOS multiplication, analog current summation and analog interlayer signals | Established prior art |
| Circuit-aware training, learned ranges and compensation for loading | Established prior art |
| Current KFQ implements the specific KirchhoffNet initial-state architecture | Unsupported; its inputs are held voltage sources |
| A useful joint feasibility analysis and constrained training method for this connected topology | Proposed; requires implementation and comparative evidence |
| Superior energy, area, precision or scalability | Not established |
| Fabricated silicon or on-chip learning | Not demonstrated |

## First milestone

Use authentic SKY130 models to characterize one transistor, one synapse, one neuron, and two connected layers. Determine whether usable operating regions exist before making classification or efficiency claims. The final classifier should preserve the current column-difference readout unless an explicitly documented architecture variant is tested.

Do not reinterpret setup tests as a trained-network benchmark. New result files must record their exact circuit, model revision and simulator version.
