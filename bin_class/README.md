# KirchhoffNet — Feedforward Analog-Circuit Classifier

Training a **real SPICE-simulated analog circuit** as a binary classifier, using
the simulator's own **backward transient adjoint sensitivity** as the gradient
signal — no PyTorch autograd, no surrogate model. The circuit is trained in two
stages, both of which produce clean, gradual learning curves where training and
test accuracy rise together.

- **Dataset:** Breast Cancer Wisconsin (569 samples, 30 features) → PCA-reduced
  to **3 features** → binary target (malignant / benign).
- **Readout time:** transient output at **t = 100 ns**.
- **Gradient:** `dV(node, 100 ns)/dparam` via the backward-in-time transient adjoint.
- **Result:** Stage 1 → train 1.00 / **test 0.88**; Stage 2 → train 1.00 /
  **test ≈ 0.81–0.88**, both stages smooth and spike-free.

---

## Table of Contents
1. [Theory](#1-theory)
2. [System Architecture](#2-system-architecture)
3. [The Two Training Stages](#3-the-two-training-stages)
4. [Results](#4-results)
5. [File-by-File](#5-file-by-file)
6. [How to Run](#6-how-to-run)
7. [Why It Works — the Key Lessons](#7-why-it-works--the-key-lessons)

---

## 1. Theory

### 1.1 A circuit as a neural network
Each **differential-amplifier stage** is an analog "neuron": it compares a signal
input against a reference and produces a nonlinear (roughly tanh-like) output. Its
**gate biases are trainable weights**. Chaining stages gives a nonlinear feature
map `f(x; θ)` from inputs `x` to node voltages, parameterized by the circuit's
DC source values `θ`. Reading node voltages and mapping them to class logits makes
it a classifier.

### 1.2 The decisive fact: open chain vs. closed ring
The original KirchhoffNet topology is a **closed 4-stage ring**. Four inverting
stages in a loop = **positive feedback = a bistable latch**: by ~5–20 ns the ring
snaps to a supply rail and *stays* there. Read at 100 ns, its output is therefore
a **discrete step function** of the inputs/parameters, and the adjoint sensitivity
of a saturated node is ≈ 0 → **dead gradients, collapsing/flat training**.

The fix is structural: **open the loop into a feedforward chain.** With no
feedback there is no bistability; the 100 ns transient settles to a **smooth
analog value**, and every parameter keeps a **non-zero backward-adjoint
sensitivity**. This is the single change that makes gradient training possible.

```
   CLOSED RING (bistable, latches -> dead gradient)      OPEN CHAIN (analog, trainable)
   net4 -> A -> net6 -> B -> net2 -> C -> net3 -> D          nin -> A -> h1 -> B -> h2 -> C -> h3 -> D -> h4
    ^__________________________________________|            (no loop closure)
```

### 1.3 Backward transient adjoint sensitivity
For a transient solve to `T = 100 ns`, the simulator computes
`dV(node, T)/dθ` by propagating an **adjoint system backward in time** from `T`
to `0`, reusing the forward solve's factorizations. One call
(`run_simulation_core(..., sensitivity=True)`) returns both the forward voltages
*and* their sensitivities at every time step — we read the value at the final
(100 ns) step. This is the exact, physics-consistent gradient used to train the
circuit parameters (the "100 ns backward transient adjoint").

### 1.4 Reservoir-computing framing
An untrained analog circuit is already a **rich nonlinear feature map** ("a
reservoir"). Two things can be trained:
- a **software readout** on top of the circuit's state (convex, robust), and
- the **circuit parameters themselves**, via the adjoint (non-convex, the
  genuine "KirchhoffNet" training).

This project does both, in two stages.

---

## 2. System Architecture

End-to-end pipeline (all differentiable):

```
x  (3 PCA features, standardized)
 └─ ENCODER  (software)          v = W_enc · x + b_enc,  clipped to a safe voltage range
      │                          -> 5 held DC input-source voltages: VIN, VREF1..VREF4
      └─ CIRCUIT  (open feedforward chain, 4 diff-amp stages)      [trained via 100ns adjoint]
           nin driven by VIN; each stage i compares its signal input to reference vref_i
           A -> h1 -> B -> h2 -> C -> h3 -> D -> h4   (NO loop closure)
           read the 4-node state  s = [V(h1),V(h2),V(h3),V(h4)]  at t = 100 ns
           trainable params:  VTH1..4 (PMOS thetas),  VB1..4 (tail biases)   = 8
              └─ READOUT  (software)   logits = W_out · standardize(s) + b_out   -> 2 logits
                   └─ softmax -> cross-entropy(label)
```

**Feature injection.** The 3 dataset features enter as the per-stage **reference
voltages** `vref_i` (the diff-amp comparison points) via the encoder; the chain's
front input `nin` and any unused references are held at fixed encoder outputs.
Inputs are **held DC sources** (not initial conditions), so the 100 ns output
reflects the input rather than a decayed initial condition.

**Node saturation note.** In a 4-stage chain the final node `h4` still saturates
(too much cascaded gain) — it is a near-comparator. The readout reads the **full
state** `[h1..h4]`: h1–h3 are analog and carry smooth gradients; h4 carries sharp
class information. Stage 2 handles h4's discontinuity with a monotonic guard
(§3.2).

**Gradients.**
- `dL/dW_out, dL/db_out` — analytic (standard softmax + linear layer).
- `dL/dθ_circuit = Σ_nodes (dL/dV_node) · dV(node,100ns)/dθ` — the **100 ns
  backward transient adjoint** (this is what trains the circuit).
- `dL/dW_enc, dL/db_enc` — analytic, chained through `dV(node,100ns)/dV(input source)`
  (also available from the same adjoint call).

---

## 3. The Two Training Stages

### 3.1 Stage 1 — readout on a frozen circuit (`train.py`)
Freeze the circuit; it is a fixed feature map. Run each sample through the chain
**once**, cache its 100 ns state vector, then train the softmax **readout** on the
cached (standardized) states. This is a **convex** problem → the loss decreases and
both accuracies rise **smoothly and monotonically**, in seconds (no re-simulation,
no adjoint). It establishes the circuit's linear-readout ceiling.

### 3.2 Stage 2 — training the circuit via the 100 ns adjoint (`train_stage2.py`)
Now train the **circuit parameters** themselves (plus a co-trained readout), using
the backward transient adjoint. The subtle part is keeping it *smooth* and making
*both* accuracies rise — training the circuit is **non-convex** and can disrupt the
classifier. The design that achieves it:

1. **Decoupled learners.** The readout trains **freely every epoch** (it is what
   classifies — convex, always helps). Earlier designs let a guard freeze the
   readout, which pinned test accuracy; here the readout is never frozen.
2. **Stable feature standardization.** `mu/sd` are computed **once** from the
   initial states and held fixed, so the readout learns on a stable feature scale
   (recomputing them while the circuit moved caused thrashing).
3. **Gentle, pre-checked circuit steps.** The circuit takes one small adjoint step
   per epoch; the tentative step is **re-simulated and rejected before it is
   applied** if it would raise the loss (and the circuit LR decays). This prevents
   the circuit from ever spiking the curve or hurting generalization — the source
   of the earlier single-epoch loss spikes.

The result is a smooth, spike-free curve where **train and test accuracy rise
together** while the circuit is genuinely trained via the 100 ns adjoint.

---

## 4. Results

| | Stage 1 (frozen circuit + readout) | Stage 2 (circuit trained via 100 ns adjoint) |
|---|---|---|
| Loss | 0.59 → 0.08 (monotone) | 0.57 → ~0.13 (monotone, no spikes) |
| Train acc | 0.63 → **1.00** | 0.63 → **1.00** |
| Test acc | 0.62 → **0.88** | 0.62 → **~0.81–0.88** |
| Epochs | 200 (seconds; states cached) | ~90 (re-simulates each epoch) |
| Curve | smooth, both rise | smooth, both rise, spike-free |

Curves: `stage1_curve.png`, `stage2_curve.png`.
Best checkpoints: `stage1_best.json`, `stage2_best.json`.

**Honest note.** On this small dataset (30 train / 16 test) the frozen-circuit
readout (Stage 1) already reaches the useful ceiling; training the circuit
(Stage 2) matches it with a clean curve but does not dramatically exceed it —
expected for reservoir-style systems on small data. The value of Stage 2 is
demonstrating stable, gradual circuit training through the physical adjoint.

---

## 5. File-by-File

| File | Purpose |
|------|---------|
| `netlist_writer.py` | Generates the **open feedforward chain** SPICE netlist (parameterizable stage count); defines param/source/node names. |
| `simulator_api.py` | `run_chain()` (TRAN forward + backward adjoint → node voltages *and* `dV/dparam` at 100 ns) and `eval_chain()` (forward-only). |
| `dataset.py` | Breast Cancer Wisconsin → standardize → PCA-3 → standardize → balanced train/test split. |
| `model.py` | Software `Encoder`, `Readout`, `softmax`/cross-entropy, and a numpy `Adam`. |
| `diag_structure.py` | **Gate check** — verifies the 100 ns outputs are analog/non-latched and all params have non-zero sensitivity, and reports linear separability of the circuit state. Run this first. |
| `train.py` | **Stage 1** — cache states, train softmax readout on the frozen circuit. |
| `train_stage2.py` | **Stage 2** — train circuit params via the 100 ns adjoint + free readout, stable standardization, pre-checked gentle circuit steps. |
| `plot_stage2.py` | Re-plots `stage2_curve.png` from `stage2_log.csv`. |
| `params_init.json` | Initial circuit parameter values. |
| `stage{1,2}_log.csv`, `stage{1,2}_curve.png`, `stage{1,2}_best.json` | Per-epoch logs, curves, best checkpoints. |

---

## 6. How to Run

### Prerequisites
- Python with `numpy`, `scikit-learn`, `matplotlib`, `pyyaml`.
- The circuit simulator available at
  `D:\Simulator\circuit_simulator with level3\src` (imported by `simulator_api.py`).

### Step 0 — inspect the data
```bash
cd bin_class
python dataset.py            # prints train/test split sizes and feature stats
```

### Step 1 — structure gate check (run this first)
```bash
python diag_structure.py
```
Confirms the open chain at 100 ns is **analog and non-latched**, that every
parameter has **non-zero backward-adjoint sensitivity**, and prints the linear
separability of the circuit state (should be clearly above chance). Only proceed
if this passes.

### Step 2 — Stage 1 (fast, seconds)
```bash
python train.py
```
Trains the readout on the frozen circuit. Outputs `stage1_log.csv`,
`stage1_curve.png`, `stage1_best.json`. Expect train → 1.00, test → ~0.88 with a
smooth curve.

### Step 3 — Stage 2 (trains the circuit; minutes)
```bash
python train_stage2.py
```
Trains the circuit parameters via the 100 ns backward adjoint (plus a co-trained
readout). Outputs `stage2_log.csv`, `stage2_curve.png`, `stage2_best.json`. Expect
both accuracies to rise smoothly with no spikes. Re-plot anytime with
`python plot_stage2.py`.

### Key knobs
- `netlist_writer.py`: `n_blocks` (chain length), storage caps / device sizing
  (time constant, per-stage gain).
- `train_stage2.py`: `LR_CIRC` (circuit step size — keep small), `LR_READ`,
  `EPOCHS`, the pre-check tolerance, and `READ` (which nodes to read).
- `dataset.py`: `N_PER_CLASS_TRAIN/TEST` and the PCA component count.

---

## 7. Why It Works — the Key Lessons

1. **Open the loop.** A closed inverting ring is bistable; read latched, its output
   is discrete and its gradients die. A feedforward chain is a smooth analog
   function at 100 ns → trainable.
2. **Read at a time where the output is smooth.** 100 ns on the open chain is
   analog; the same 100 ns on the closed ring is fully latched — the readout *time*
   was never the problem, the *topology* was.
3. **Let the classifier (readout) train freely.** It is convex and drives accuracy;
   coupling its fate to the non-convex circuit optimization is what froze test
   accuracy.
4. **Keep the circuit's influence smooth and gentle.** Stable standardization plus
   small, pre-checked adjoint steps stop the circuit from spiking the curve or
   hurting generalization.
5. **Reservoir first, then fine-tune.** The frozen circuit + trained readout
   (Stage 1) is a strong, robust baseline; training the circuit (Stage 2) is the
   genuine physical-learning step layered on top.
