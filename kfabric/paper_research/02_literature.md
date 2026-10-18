# Literature comparison

Search date: 2026-10-18. Targeted literature review, not an exhaustive systematic review or patent clearance. Search themes included CMOS four-quadrant synapses, circuit-simulation-based training, differential common-mode control, interlayer loading, operating constraints, joint weight/neuron optimization and recent silicon hardware-aware training. Primary papers and author/institutional copies were prioritized; search-engine crawl dates were not treated as publication dates.

| Key and source | Established contribution relevant here | Consequence for KFQ positioning |
|---|---|---|
| `bult1986`, [CMOS four-quadrant multiplier](https://ris.utwente.nl/ws/files/202809452/Bult1986cmos.pdf) | Signed multiplication exploiting MOS square-law behavior | The multiplication principle is prior art; this comparison does not assert transistor-for-transistor identity. |
| `bayraktaroglu1996`, [Circuit-level simulation training thesis](https://ismet.bayraktaroglu.org/education/msthesis.pdf) | Circuit simulation is incorporated into analog-network training | Simulation-based training alone is not new. This is a thesis, not a peer-reviewed journal article. |
| `kendall2020`, [Equilibrium propagation](https://arxiv.org/abs/2006.01981) | End-to-end training of analog resistive networks with circuit-simulation evaluation | Different training mechanism and circuit family; establishes prior end-to-end analog learning. |
| `weller2021`, [Printed neuromorphic computing](https://pmc.ncbi.nlm.nih.gov/articles/PMC8099883/) | Feasible component ranges, coupled weights, output signal separation and variation-aware training | Hardware constraints and voltage separability in training are not new. |
| `kiani2021`, [Fully hardware-based memristive multilayer network](https://pmc.ncbi.nlm.nih.gov/articles/PMC11559551/) | Analog neurons link arrays; buffering isolates stages; inverted signals support signed weights | Analog interlayer operation is prior art; a buffered alternative is a necessary engineering comparison. |
| `zhou2022`, [SPICEprop](https://arxiv.org/abs/2203.01426) | Gradient-based learning on circuit models of memristive spiking networks | Differentiating through circuit dynamics is prior art. Cited version is a preprint. |
| `watfa2023`, [EBANA](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2023.1114651/full) | Explicitly discusses whole-circuit loading and operating-point-dependent nonlinearities | Neither observing loading nor solving the entire circuit is sufficient novelty. Its equilibrium-propagation network differs from KFQ's active CMOS circuit. |
| `rasch2023`, [Hardware-aware AIMC training](https://www.nature.com/articles/s41467-023-40770-4) | Realistic nonidealities, learned input ranges and weight-to-conductance scales | Compare against range-aware, calibrated training, not only naive ideal mapping. |
| `kirchhoffnet2024`, [KirchhoffNet v3](https://arxiv.org/html/2310.15872v3) | Initial state evolves under nonlinear branch-current dynamics | Conceptual background; KFQ's held-input protocol differs. The paper's hardware-speed discussion is not a measured chip result. |
| `ye2025`, [Fully analog computing hardware](https://pmc.ncbi.nlm.nih.gov/articles/PMC12542939/) | Fabricated analog hardware with collaborative adjustment of weights and activation characteristics | Analog-only processing and joint weight/activation adjustment already exist. |
| `filippeschi2026`, [Silicon hardware-aware training](https://doi.org/10.1109/JETCAS.2026.3705439), [author preprint](https://arxiv.org/abs/2601.19905) | Physically informed floating-gate array model, crosstalk and bit-line effects, supported by measurements | A recent close comparison for physical modeling and compensation. Distinguish its time-domain floating-gate arrays from amplitude-driven differential CMOS stages. |

## Narrow contribution to investigate

The combination to evaluate is a predictive, connected-circuit feasibility analysis plus a specific training/design procedure for the KFQ source-connected synapse/neuron topology. It must show value over fixed per-layer calibration, hardware-aware surrogate training, unconstrained joint optimization and a buffered alternative.

## Open literature questions before submission

- Follow citations in historical CMOS multiplier and analog-neuron papers for any matching topology or bias-selection method.
- Compare explicitly with printed-network constraint formulations and EBANA's treatment of loading.
- Recheck 2025-2026 CMOS and floating-gate literature after the algorithm and circuits are finalized.
- Document differences in a claim-by-claim matrix; avoid relying on keyword absence.
- Use final publication metadata where available. The Filippeschi preprint and journal versions may differ in experiment count; do not mix their numbers.
