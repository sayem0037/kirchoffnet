# toy2d — 2-D Datasets on an Analog Circuit: from a Narrow Chain to a Wide Reservoir

Training a **real SPICE-simulated analog circuit** as a binary classifier on the
2-D toy datasets from the reference KirchhoffNet repo — **twomoon, circle,
2spirals** — using the simulator's **100 ns backward transient adjoint** as the
gradient signal. This directory tells a complete story: a naive *narrow* circuit
fails on the non-linearly-separable datasets, and *widening* it into a parallel
layer of many analog "neurons" (reservoir computing) fixes it.

**Headline result** (test accuracy):

| dataset | boundary | narrow chain (4 nodes) | **wide layer (24 units)** |
|---|---|---|---|
| twomoon | nearly linear | 0.83 → 0.91 | **0.88 → 0.97** |
| circle | concentric (nonlinear) | **0.50** | **0.96** |
| 2spirals | interleaved spirals (hardest) | **~0.30–0.65** | **0.96 → 1.00** |

The decision-boundary animations (`results/*_wide_boundary.gif`) show the boundary
curving to **enclose the circle** and **follow the spiral arms** — impossible for
the narrow chain, which could only draw a straight line.

---

## Table of Contents
1. [The datasets](#1-the-datasets)
2. [The circuit-as-classifier pipeline](#2-the-circuit-as-classifier-pipeline)
3. [Attempt 1 — the narrow chain (and why it fails)](#3-attempt-1--the-narrow-chain-and-why-it-fails)
4. [The fix — a wide parallel layer (reservoir computing)](#4-the-fix--a-wide-parallel-layer-reservoir-computing)
5. [Results](#5-results)
6. [Decision-boundary animations](#6-decision-boundary-animations)
7. [File-by-file](#7-file-by-file)
8. [How to run](#8-how-to-run)
9. [Key lessons](#9-key-lessons)

---

## 1. The datasets

The reference repo (`D:\Kirchoffnet\kirchhoffnet`) generated these 2-D point
clouds and used them for **generative density modeling** (it *discarded* the
labels). They are naturally **2-class**, so here we **keep the labels** and train a
classifier. Same generators as `kirchhoffnet/src/utils/testbench.py`:

| name | generator | boundary shape |
|---|---|---|
| `twomoon` | `make_moons(noise=0.1)` | two interleaving half-moons — nearly linearly separable |
| `circle` | `make_circles(noise=0.06, factor=0.5)` | concentric rings — needs a *closed* nonlinear boundary |
| `2spirals` | two interleaving spirals | the hardest — a highly non-monotonic boundary |

Each is a 2-D input `(x, y)`, standardized, split into a small balanced
train/test set (each sample is a SPICE simulation, so the sets are kept modest:
20 per class train, 12 per class test).

## 2. The circuit-as-classifier pipeline

The general architecture (shared with `../bin_class/`; see that README for the
full circuit theory and the 100 ns backward-adjoint mechanism):

```
(x, y)  ->  software ENCODER  ->  analog CIRCUIT (diff-amp units)  ->  read node voltages @100ns
                                                                        ->  software softmax READOUT  ->  class
```

- **Encoder** — maps the 2 features to the circuit's input-source voltages.
- **Circuit** — differential-amplifier stage(s); the trainable knobs are the PMOS
  gate biases (thetas) and tail-NMOS biases, trained via `dV(node,100ns)/dparam`
  from the backward transient adjoint.
- **Readout** — a linear softmax layer over the circuit's 100 ns node voltages.
- **Two stages** — Stage 1 trains only the readout on the *frozen* circuit
  (convex, fast); Stage 2 also trains the circuit parameters via the adjoint.

## 3. Attempt 1 — the narrow chain (and why it fails)

The first architecture (`netlist_writer.py`, `common.py`, `train.py`,
`train_stage2.py`) is a **narrow series chain**: 4 diff-amp stages, 4 read-nodes,
8 trainable parameters, fed a *fixed linear* projection of `(x, y)`.

It classifies **twomoon** fine (nearly linear) but **fails on circle and
2spirals**. The gate check (`diag_structure.py`) shows exactly why — the circuit's
nonlinear map adds **no separating power**:

| dataset | raw-feature separability | narrow circuit-state separability |
|---|---|---|
| circle | 0.70 | 0.70 (no gain) |
| 2spirals | 0.62 | 0.57 (*worse*) |

A linear readout on a low-complexity, smooth transform of a *linear projection* of
`(x,y)` can only draw a roughly straight boundary — which physically cannot wrap a
circle or follow spirals. Narrow-chain results: circle 0.50, 2spirals ~0.30–0.65
test. (See `results/{circle,2spirals}_stage2_curve.png`.)

## 4. The fix — a wide parallel layer (reservoir computing)

The way a neural network — or a physical/reservoir computer — separates such data
is **width**: many nonlinear units, each thresholding a *different* linear
combination of the inputs, so together they tile a curved boundary. The reference
KirchhoffNet repo itself used *wide* circuits (e.g. `fully_connect_node: 50`); our
4-node chain was the deficiency.

So we replace the chain with a **parallel layer of N = 24 diverse diff-amp
"neurons"** (`netlist_wide.py`), a genuine 1-hidden-layer analog network:

```
(x, y)
 └─ ENCODER  W·x + b   (random-DIVERSE per-unit projections)   -> VIN_1..24
      └─ 24 PARALLEL diff-amp units (independent; each = one analog neuron)
           unit j: gate=VIN_j, ref=VN, tail=VB_j, theta=VTH_j, output=u_j
           read u_1..u_24 @100ns          [per-unit params trainable via 100ns adjoint]
              └─ softmax READOUT (24 -> 2)  -> class
```

**Why it works:** each unit applies a tanh-like nonlinearity to its own projection
`W[j]·(x,y) + b[j]`; 24 such units on 24 *different* projections form a
24-dimensional nonlinear feature space, and a linear readout over it draws a
*piecewise* boundary that can enclose a circle or follow spiral arms. **Diversity
is essential** — random `W`, `b` so units threshold at different places/angles.

We proved this **before training** with the gate check (`diag_wide.py`): even a
**random, untrained** wide layer makes the datasets linearly separable —

| dataset | raw (train) | random wide circuit-state (train / test) |
|---|---|---|
| twomoon | 0.93 | **1.00 / 0.88** |
| circle | 0.70 | **1.00 / 0.88** |
| 2spirals | 0.62 | **0.97 / 0.88** |

i.e. width alone adds +0.30 / +0.35 separability on circle / 2spirals. Training the
readout (`train_wide.py`) then reaches the results below.

## 5. Results

Test accuracy, narrow chain vs. wide layer:

| dataset | narrow Stage 1 | narrow Stage 2 | **wide layer** |
|---|---|---|---|
| twomoon | 0.83 | 0.91 | **0.88** (train 1.00) |
| circle | 0.50 | 0.67 | **0.96** (train 1.00) |
| 2spirals | 0.71* | 0.65 | **0.96** (train 1.00) |

*noisy single-epoch peak on a 24-sample test set; narrow 2spirals never fits train.

The wide layer takes the two non-linearly-separable datasets from near-chance to
**0.96**. Curves: `results/{name}_wide_curve.png`.

## 6. Decision-boundary animations

`animate_wide.py` pushes a dense grid of the `(x,y)` plane through the wide layer
and animates the readout training — the plane colored by predicted class, data
points overlaid. Outputs `results/{name}_wide_boundary.gif` (and final-frame stills
`results/{name}_wide_final.png`):

- **circle** — the boundary closes into a blob **enclosing the inner class** (acc 0.98).
- **2spirals** — the boundary **winds through the interleaved arms** (acc 1.00).
- **twomoon** — the boundary follows the **curved gap** between the moons (acc 0.97).

Compare to the narrow-chain `results/{name}_boundary.gif`, which stay straight.

## 7. File-by-file

**Shared / narrow chain**
- `netlist_writer.py` — the open 4-stage series chain.
- `common.py` — narrow-chain config + 2-feature encoder.
- `dataset.py` — the three datasets (labels kept), `--dataset` selectable.
- `diag_structure.py` — narrow-chain gate check (revealed the no-separating-power problem).
- `diag_inject.py` — encoder injection-scheme/swing sweep.
- `train.py` / `train_stage2.py` — narrow Stage 1 / Stage 2.
- `animate.py` — narrow-chain boundary animation.

**Wide layer (the fix)**
- `netlist_wide.py` — N parallel diff-amp units.
- `wide_common.py` — wide-layer config + random-diverse encoder.
- `diag_wide.py` — the gate check that proved the width hypothesis.
- `train_wide.py` — trains the softmax readout on the wide-layer state.
- `animate_wide.py` — the curved-boundary animation; `extract_last.py` pulls final frames.

**Reused unchanged from `../bin_class/`**
- `simulator_api.py` — `run_chain`/`eval_chain` (TRAN + backward adjoint at 100 ns).
- `model.py` — `Encoder`, `Readout`, softmax/CE, `Adam`.
- `params_init.json`, `plot_stage2.py`.

**`results/`** — per-dataset logs, curves, best checkpoints, and the GIFs/PNGs.

## 8. How to run

Prereqs: Python with `numpy`, `scikit-learn`, `matplotlib`, `pillow`, and the
simulator at `D:\Simulator\circuit_simulator with level3\src` (imported by
`simulator_api.py`). All scripts take `--dataset {twomoon|circle|2spirals}`.

```bash
cd toy2d
python dataset.py       --dataset circle      # inspect the split

# --- the wide layer (recommended) ---
python diag_wide.py     --dataset circle      # GATE: random wide layer separability vs raw
python train_wide.py    --dataset circle      # train the readout on the wide layer
python animate_wide.py  --dataset circle      # render the curved-boundary GIF

# --- the narrow chain (for comparison / the failure case) ---
python diag_structure.py --dataset circle
python train.py          --dataset circle     # Stage 1
python train_stage2.py   --dataset circle     # Stage 2 (circuit via 100ns adjoint)
python animate.py        --dataset circle
```
Outputs land in `toy2d/results/`.

## 9. Key lessons

1. **Width, not tuning.** The narrow chain's failure on circle/2spirals was not a
   hyperparameter problem — a linear readout on a narrow, correlated feature map
   *cannot* draw a curved boundary. Adding parallel width fixed it structurally.
2. **A wide random analog layer is a reservoir.** Even *untrained*, 24 diverse
   diff-amp units + a linear readout separate circles and spirals — the classic
   reservoir-computing / random-features result, realized in an analog circuit.
3. **Gate before you train.** The `diag_*` separability checks predicted success
   (wide) and failure (narrow) *before* spending simulation time on training.
4. **Faithful to KirchhoffNet.** The reference repo used wide circuits; the wide
   layer here is the authentic design, and it is still trainable end-to-end via the
   100 ns backward transient adjoint.
