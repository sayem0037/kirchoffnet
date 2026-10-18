# `compare/` — three architectures, one simulator, one yardstick

This directory answers a question the rest of the repo could not: **how does
KirchhoffNet compare to the analog and digital neural-network hardware that
already exists in the literature, measured the same way?**

Before this, the only baseline anywhere in the project was
`kfabric/run_kfq.py`'s `raw + linear` row — logistic regression on the input
features. That shows the circuit is not trivially beatable. It is not a
hardware comparison, and an ICCAD reviewer will say so. The repo's own
self-review already did: `toy2d_serial_diff/AI_Hardware_Session/
Reviewer_Report_and_Response.md` lists *baselines* and *hardware framing
without energy numbers* among six major faults.

Two gaps are closed here.

1. **Competing architectures.** A differential resistive crossbar (`XBAR`, the
   ISAAC/PUMA lineage) and a quantized digital MLP (`DMLP`), both built in
   house and run through the same in-house simulator as KFQ.
2. **Hardware metrics.** Nothing in `toy2d*/` or `kfabric/` ever computed
   energy, power, area or settling latency — `kfabric/ARCHITECTURE.md` §6 says
   so outright ("No silicon, no measured energy"). `metrics.py` computes all of
   them, identically for every arm.

---

## The three arms

| Arm | What it is | Trained how | Converters |
|---|---|---|---|
| **KFQ** | `kfabric/netlist_kfq.py` — four NMOS per weight, summing into a resistive load | in-situ adjoint | none |
| **XBAR** | four programmable conductances per weight, summing at a virtual ground held by a TIA | ex-situ (primary) and in-situ | 1 DAC/row, 1 ADC/column, per layer |
| **DMLP** | INT-N array multiplier + adder tree | software, quantization-aware | n/a |

The crossbar is deliberately **KFQ with exactly one thing changed**. Same
differential rows about a common mode, same four-quadrant cross-connection,
same bias row, same tail-biased differential-pair neuron feeding the next layer
from both drains, same model cards, same VDD, same readout convention. Only the
synapse and the summing mechanism differ. If the two arms differed in encoding,
neuron and depth as well, a difference in the results table would be
unattributable.

---

## The gates

Each is a go/no-go, in the style of `kfabric/gate_*.py`. All currently pass.

| Gate | File | What it proves | Result |
|---|---|---|---|
| **A** | `verify_xbar.py` | the crossbar computes the MVM it claims, and rejects both common mode and `vref` | 0.004% error; rejection exact |
| **B** | `xbar_train.py --check-grad` | adjoint `dV/dG` matches central finite differences | cosine **1.000000** |
| **C** | `verify_metrics.py` | the energy integrator and settling-time function are right | `E = VDD²/R·T` exact; `t_settle = ln(50)·RC` to 0.2% |
| **D** | `digital_cell.py --gate` | LEVEL=2 switching energy is real and load-dependent | fitted slope 10.66–10.87 vs VDD² = 10.89 (0.2–1.8%) |
| **E** | `run_bench.py` | every arm is scored on a bit-identical split | SHA-256 split fingerprint printed with the table |

---

## Metric definitions

Fixed once, in `metrics.py`, so no arm defines its own yardstick.

- **Energy** — `∫ Σ_k v_k(t)·i_k(t) dt` over every independent source, trapezoid
  on the solver's own time grid, charged over the **settling window** `(0,
  t_settle)` rather than over however long the training deck happened to run.
- **Latency** — `t_settle`, the *last* instant any read node is still outside a
  ±2% band around its final value. Last, not first: a node that crosses early
  and comes back would fool the other definition.
- **Area** — Σ drawn device area through `tech.py`, plus periphery as explicit
  line items. First-order, under a stated card.
- **Accuracy** — test accuracy with a Wilson 95% interval (lifted verbatim from
  `kfabric/run_kfq.py` so both directories compute it identically).
- **Convergence** — epochs to reach 95% of the run's *own* best test accuracy,
  so an arm that plateaus low is not credited with converging instantly.

The technology card is `tech.py`: **0.35 µm, VDD = 3.3 V**. That node is not a
choice, it is forced by the circuits that already exist — `SYN_L=1u/W=4u`,
`L=350n..2u`, and a Cadence port from a library literally named `Neur_Sam_350`.
Every constant carries a provenance tag (`geom`, `proc`, `lit`).

---

## The latency caveat, handled rather than buried

Every netlist in this repo uses `C = 0.1 fF`, giving τ ≈ 1e-13 s. That is a
deliberate convenience for *training* — the node settles long before the 100 ns
readout, so the gradient never sees a transient — but a sub-picosecond settling
time is not a publishable latency for silicon, where any node carries wire and
fanout capacitance.

So latency is reported at a **stated load** (`tech.C_LOAD_DEFAULT`, 10 fF) with
the full sweep over C published beside it. `measure_existing.py --sweep`
produces the sweep; it comes out exactly linear, as it should.

---

## Three bugs worth knowing about

All three produced *plausible-looking* numbers, which is why they are recorded
here rather than quietly fixed.

1. **`vref` at mid-supply.** The four-quadrant cell cancels the common mode in
   the column *difference*, but each individual TIA still sinks
   `Σ G_i(v_row − vref)`. With rows at 1.0 V and `vref` at 1.65 V that drove the
   amplifier output past 8 V; both TIAs railed and the difference collapsed.
   The sizing loop read that as "swing too small", raised `Rf`, and ran itself
   into the floor. `vref` is now per layer and solved.
2. **`rd = 200k`.** That drops nearly the whole supply, so the neuron drains
   sat at 0.27 V — below an NMOS input pair's turn-on. The next layer's
   amplifiers were simply off and its column degenerated into a passive
   resistive load. `rd` is now per layer and solved.
3. **Polarity.** The TIA inverts and the neuron inverts again, so inner layers
   are non-inverting and the final layer (read at the columns, no neuron after
   it) inverts. That derivation is correct and *still* produced a wrong answer,
   because it had been calibrated against configuration 2 above, whose dead
   amplifier did not invert. Fixing the bias brought the real inversion back
   and iris went to exactly **0.000** — not noise, but perfectly anti-correct,
   which is what `argmax` over a negated score vector looks like. Polarity is
   now **measured** on a one-weight probe (`xbar_spec.calibrate_signs`) after
   the sizing is solved.

The lesson, which belongs in the paper: an ex-situ arm can score badly for two
completely different reasons, and accuracy alone cannot tell them apart.
`score_fidelity` (Pearson *r* between circuit scores and software logits) does:
**low r** means the circuit is not computing the mapped function, i.e. our bug
and an unfair baseline; **high r with lower accuracy** means the loss is
genuine quantization and device nonlinearity, which is the crossbar's real and
reportable cost.

---

## Running it

```bash
# gates first -- nothing downstream is meaningful until these pass
python verify_metrics.py                  # Gate C
python verify_xbar.py                     # Gate A
python xbar_train.py --check-grad         # Gate B
python digital_cell.py --gate             # Gate D

# characterise the digital cell library (writes results/digital_cell_char.json)
python digital_cell.py

# crossbar: solve the operating point, THEN train
python xbar_spec.py  --dataset iris --hidden 7 --save
python xbar_train.py --mode exsitu --dataset iris --hidden 7 --tag sized
python xbar_train.py --mode insitu --dataset iris --hidden 7 --tag insitu

# digital arm
python digital_mlp.py --dataset iris --hidden 7

# hardware metrics for the analog arms (no retraining)
python measure_existing.py --arm kfq  --dataset iris --sweep
python measure_existing.py --arm xbar --dataset iris --sweep

# the table
python run_bench.py --dataset iris
```

`xbar_spec.py` must be run before `xbar_train.py` for any new dataset or
topology. `Rf` scales with fan-in, so one value cannot be right for two layers
— the same problem `netlist_kfq.py`'s `load_r` docstring records for KFQ
(fan-in 8 wants ~2.5k, fan-in 64 wants ~200). Running the trainer with the
scalar defaults is a diagnostic mode, not a reportable one.

---

## Known limits

- **`LEVEL=1` has no intrinsic capacitance**, so the analog arms' *dynamic*
  energy is not modelled; their reported energy is static bias current over the
  settling window, and that is what dominates. The digital arm uses `LEVEL=2`
  precisely because switching energy is its whole story. This asymmetry favours
  neither arm uniformly and is stated rather than corrected.
- **Ideal op-amps are free.** `ideal_tia=True` uses a VCVS that draws no
  current; it exists for Gate A and for the readout-cost ablation. Reported
  energy always uses the 5-transistor OTA.
- **Nothing here is laid-out silicon.** Area is a first-order Σ(W·L) + periphery
  estimate under a stated card.
- **Converter energy and area are literature-derived** (`FOM_ADC`, `FOM_DAC`,
  `A_ADC_8B` in `tech.py`), because simulating an ADC is out of scope. They are
  a separate line in every table, never folded into a total.
- **The digital datapath is counted, not simulated end to end.** Per-gate
  constants are measured; the gate counts are a stated architectural
  assumption (array multiplier + ripple-carry accumulation) and can be argued
  with directly in `digital_mlp.gate_counts`.
- **MNIST 8×8 has no stable KFQ operating point** (the sizing fixed point
  oscillates at fan-in 64). It should be reported as a limitation row, not
  dropped.

---

## Where the crossbar's mapping loss actually comes from

Isolating the two halves of the network on iris, with `score_fidelity`:

| network | fidelity *r* | circuit | software |
|---|---|---|---|
| `4 → 3`, crossbar only, no neuron in path | **0.9992** | 0.983 | 0.983 |
| `4 → 7 → 3`, crossbar + neuron + crossbar | 0.8628 | 0.900 | 0.983 |

The matrix-vector multiply is essentially exact — which is the check that the
crossbar arm is implemented fairly. **All** of the mapping loss enters with the
neuron: the tail-biased differential pair does not have the same transfer shape
as the ideal `tanh` the software model was trained against.

That matters for how the paper frames the result. It is a genuine analog
effect, not a setup fault, and it is a *fair* one — KFQ uses the identical
neuron and pays the identical price. The crossbar's disadvantage in the results
table is therefore attributable to its readout and conversion cost, not to a
hobbled implementation of its core operation.

---

## Protocol check against the literature

The implementation was audited against published practice for analog
crossbar and digital accelerators. Four things matched; two did not, and both
were fixed or flagged.

### What already matched

| Our choice | Literature |
|---|---|
| Weight = `G⁺ − G⁻` conductance pair, one side at minimum | The standard differential mapping — gives a full signed range, cancels common-mode drift to first order, and puts a robust zero at `G⁺ = G⁻` |
| Crossbar trained **ex-situ** in software, then programmed; accuracy measured **on the circuit** | Standard: the device is a memory, not a learner. Reporting the software accuracy would be the error |
| Digital arm: quantization-aware training with a straight-through estimator | The universal QAT recipe |
| 8-bit ADC | ISAAC's choice |

### Fixed: ADC instance count (this changed the numbers)

ADCs are **not** one-per-column in any real design — an 8-bit ADC is ~12× the
area of a 128×128 crossbar array, so ISAAC time-multiplexes **one ADC across
128 bitlines** within the array's read window; PUMA follows the same scheme.

The first version charged one ADC *instance* per column. That overstated the
crossbar's area by **160,000 µm² on iris — 45% of its reported total**:

| | before | after |
|---|---|---|
| XBAR area | 358,088 µm² | **198,088 µm²** |

Energy is unchanged and was always right: every column still needs one
conversion, so *conversions per inference* and *converter instances* are
different quantities. Conflating them is what caused the error;
`converter_counts()` now returns both.

### Flagged: hardware-aware training and device non-idealities

The literature standard (e.g. IBM's AIHWKit) is to inject weight noise during
the software forward pass so the network learns to tolerate the spread the
devices will actually have, and to evaluate against programming error, drift
and read noise. The original implementation did **neither** — which cuts both
ways: the crossbar was never hardened (unfairly weak) but also never degraded
(unfairly strong).

Both are now implemented — `--hwa-sigma` (training) and `--prog-sigma`
(programming error, applied **once** at mapping, since the array is programmed
once and read many times). Measured on iris:

| HWA σ | programming σ | circuit test |
|---|---|---|
| 0 | 0 | 0.900 |
| 0 | 0.05 | 0.867 |
| 0.05 | 0.05 | 0.800 |
| 0 | 0.10 | 0.800 |
| 0.10 | 0.10 | 0.917 |

**These differences are not resolvable.** At n = 60 the Wilson interval is
roughly ±10 points, and one test sample is 1.7 points — the whole spread above
sits inside the noise. The mechanism is implemented and the sweep runs; drawing
a conclusion from it needs multiple seeds and a larger test set, and the paper
should not claim one until then.

### A node-specific caveat worth stating

Published digital accelerators are **memory-access dominated**. Our digital arm
is **logic dominated** (95–97% logic, 3–4% SRAM). That is not a contradiction:
the usual claim concerns modern nodes with DRAM traffic and heavy data reuse,
where logic energy has collapsed while memory energy has not. At 0.35 µm and
3.3 V, `CV²` is roughly an order of magnitude larger, and the workload is a
59-weight MLP read once from on-chip SRAM with no reuse to exploit. The
conclusion is correct *for this technology*, and the paper should say so rather
than let it read as a general claim.

---

## Correction: the crossbar had a neuron it should not have had

The crossbar arm in `xbar_train.py` keeps the signal analog end to end, reusing
KFQ's tail-biased differential pair as its activation. That made the comparison
controlled — same nonlinearity, so any difference traces to the synapse.

It is **not** what a resistive-crossbar accelerator does. ISAAC and PUMA go:

```
analog MVM → ADC → digital shift-and-add → digital ReLU → DAC → next tile
```

The activation is exact digital arithmetic; there is no analog neuron in the
signal path. Measured on iris:

| crossbar configuration | test | mapping loss |
|---|---|---|
| analog neuron (`xbar_train.py`) | 0.900 | +0.083 |
| **digital activation (`xbar_faithful.py`, 8-bit ADC)** | **0.983** | **0.000** |
| software reference | 0.983 | — |

The analog neuron was costing the baseline **8.3 accuracy points** for a
component a real crossbar would not have. The isolation test had already
pointed at it — MVM alone tracks the mapped function at r = 0.9992, adding the
analog neuron drops it to r = 0.863 — but the implication was not acted on
until the two configurations were run side by side.

It also removes an internal inconsistency: the energy and area model was
already charging this arm for an ADC per column and a DAC per row at every
layer boundary, i.e. for exactly the digital round trip the analog-neuron
version never performed. The faithful configuration pays for the converters
**and** gets the exact activation they buy.

### What this changes in the paper

Report `xbar_faithful` as the primary crossbar row. The crossbar then **ties on
accuracy** (0.983 vs KFQ's 0.983) and the entire KFQ advantage sits in energy,
area and avoided conversion. That is a narrower claim and a much stronger one —
"we match accuracy at 17× less energy and 24× less area, because we never leave
the analog domain" beats "we win on everything", which invites the reviewer to
look for the handicap.

`xbar_train.py`'s analog-neuron version stays as the controlled-comparison
ablation: it isolates the synapse, and the 0.983 → 0.900 gap between the two
configurations is itself the measured cost of an analog activation.
