# Paper approach

## Positioning in simple terms

KirchhoffNet initializes capacitor voltages with the sample and reads the evolved state later. KFQ holds external input voltages and computes through cascaded MOS synaptic arrays and differential-pair neurons. The serial ring is a separate initial-state-driven architecture. Keep it in related work or a separate study.

The proposed paper concerns **electrical compatibility during learning**. Connecting two nominally functional blocks can change their operating points enough to destroy their intended computation.

## Why this topology needs a connected-circuit analysis

Each four-NMOS synapse connects its source terminals to the preceding neuron's output pair. The next layer therefore exchanges current with that neuron. There are two coupled limits:

- Fan-in increases column current and the voltage drop across the column load.
- Fan-out changes the total downstream current injected into the preceding output pair.

At DC, under the intended device current directions and neglecting leakage, the sum of the two output-node KCL equations gives:

`I_tail = I_load_plus + I_load_minus + I_next_plus + I_next_minus`.

This is a circuit derivation, not a new physical law. Verify current signs and leakage when evaluating PDK models. A large tail current alone is not a solution: it changes gain, common mode, power and required headroom.

## Contribution candidates

1. Derive and validate an operating-range model covering fan-in, fan-out, common mode and signal swing for this topology.
2. Develop joint weight/bias optimization that accounts for connected-circuit operating conditions throughout training.
3. Quantify when this approach is preferable to well-tuned calibration or explicit buffers/level shifters.

General constrained optimization, common-mode control and hardware-aware training are existing techniques. Novelty must reside in a specific nontrivial formulation, implementation, predictive result or demonstrated trade-off beyond the closest sources in the literature table. An empty search result does not establish priority.

## Proposed parameterization and optimization

Represent each synapse as `VA = b + d/2`, `VB = b - d/2`. The difference `d` controls its signed weight; `b` controls its average gate bias. A shared per-layer `b` is a useful first implementation, but compare against a fair fixed-bias baseline.

Use complete-circuit states to evaluate constraints. For a long-channel intuition, the multiplier devices need positive overdrive and adequate drain headroom. With the PDK use the model's reported threshold, saturation voltage and measured transfer behavior, not a universal Level-1 threshold rule.

Illustrative objective: minimize classification loss plus a normalized power penalty, subject to circuit equations, multiplier operating margins and a specified output noise/readout margin. These generic optimization ingredients are not a novelty claim. Penalties alone do not guarantee feasibility; re-solve and check each accepted update.

Distinguish design-time resistor/device sizing from programmable biases and stored weights. Do not assume all optimized parameters can be changed on a fabricated chip. Allow intended nonlinear behavior in the neuron; do not impose multiplier linearity requirements on the activation circuit.

## Decision criteria

- If per-layer calibration performs as well, constrained training has not established an advantage.
- If buffers outperform direct coupling under matched constraints, revise the architecture or report the limitation.
- If only an ideal mathematical baseline is beaten, the novelty evidence is weak.
- If no feasible region exists, change circuitry, dimensions, fan-out or supply/device choice; optimization cannot supply unavailable headroom.
- If numerical validation fails, repair the simulator interface/gradients before training claims.

## Wording for a future manuscript

"We investigate directly coupled differential CMOS neural networks and derive operating constraints that capture the interaction between synaptic loading and neuron bias. We incorporate these constraints into joint weight-bias optimization and evaluate the resulting designs with SKY130 compact models."

Only add "improves", numerical gains, robustness guarantees or novelty priority after the corresponding evidence exists. State simulation-based evaluation explicitly.
