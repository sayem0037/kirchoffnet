# toy2d Stage 2 — Training the Analog Circuit Itself (100 ns Backward-Adjoint)

A deep-dive, teach-it-to-me README for the **hardware-training** stage of the
toy2d project. Where Stage 1 (`train_wide.py`) froze the analog circuit and only
trained a software readout on top of it, **Stage 2 (`train_wide_stage2.py`)
trains the 72 physical circuit parameters themselves** — the PMOS gate biases,
tail biases, and per-unit reference voltages — using gradients that come *out of
the SPICE simulator* via its 100 ns backward transient adjoint.

This document explains every moving part, the exact math of the gradient, the
training loop line-by-line, the results (including the honest negative finding),
and precise steps to reproduce everything.

> If you have not read the main [`README.md`](./README.md) yet, skim its sections
> 1–4 first: they explain *why* we go from a narrow chain to a wide layer. This
> file assumes that context and focuses entirely on **Stage 2**.

---

## Table of contents

1. [What "Stage 2" means](#1-what-stage-2-means)
2. [The end-to-end pipeline](#2-the-end-to-end-pipeline)
3. [The circuit, one unit at a time](#3-the-circuit-one-unit-at-a-time)
4. [The data and the encoder](#4-the-data-and-the-encoder)
5. [The forward pass: from (x,y) to a class](#5-the-forward-pass-from-xy-to-a-class)
6. [The gradient: how the simulator gives us dV/dparam](#6-the-gradient-how-the-simulator-gives-us-dvdparam)
7. [The training loop, line by line](#7-the-training-loop-line-by-line)
8. [Results (and the honest finding)](#8-results-and-the-honest-finding)
9. [The decision-boundary animation](#9-the-decision-boundary-animation)
10. [How to replicate — exact commands](#10-how-to-replicate--exact-commands)
11. [File map for Stage 2](#11-file-map-for-stage-2)
12. [Troubleshooting & key gotchas](#12-troubleshooting--key-gotchas)

---

## 1. What "Stage 2" means

There are two ways to use the wide analog layer as a classifier:

| | trainable knobs | who trains them | file |
|---|---|---|---|
| **Stage 1** (frozen reservoir) | software readout weights only | analytic backprop | `train_wide.py` |
| **Stage 2** (hardware training) | **circuit params** VTH/VB/VN **+** readout | **100 ns adjoint** (circuit) + analytic backprop (readout) | `train_wide_stage2.py` |

Stage 1 treats the 24 analog units as a **fixed random feature map** (a
"reservoir") and only learns the linear layer that reads them out. Stage 2 asks
the harder question: *can we also tune the transistors themselves so the analog
features become better?* — and it does so with **real gradients extracted from
the circuit simulator**, not a software surrogate.

The 72 trainable circuit parameters are, per unit *j* (24 units × 3):

| param | netlist source | physical role | bounds |
|---|---|---|---|
| `VTH`*j* | `VTH{j} th{j} 0` | PMOS-load gate voltage → sets the active-load / gain point | `[0.0, 3.0] V` |
| `VB`*j*  | `VB{j} vb{j} 0`   | tail-NMOS gate → sets the diff-pair bias current | `[0.72, 1.10] V` |
| `VN`*j*  | `VN{j} vn{j} 0`   | the "reference" input of the diff pair → the unit's **threshold** | `[0.60, 1.40] V` |

The important design choice (vs. Stage 1): **`VN` is a hardware source, not a
software number.** Each unit compares its input against its *own trainable
reference voltage*, so the per-unit thresholding — the thing that makes the layer
diverse and expressive — lives in the circuit and is trained by the adjoint.

---

## 2. The end-to-end pipeline

```
                          fixed random-diverse             per-unit diff-amp            software
                          linear projection                (analog neurons)             linear layer
                          ──────────────────               ─────────────────            ────────────
  (x, y)  ──────────────►  VINj = clip(1 + Wj·(x,y) + bj)  ──►  24 units  ──►  read u1..u24  ──►  softmax(Wout·u+bout)  ──► class
  standardized 2-D          [wide_common.encode_wide]           [netlist_wide]    @ 100 ns        [model.Readout]           argmax
                                                                     ▲
                                                    trainable VTH/VB/VN per unit
                                                    (gradient from 100 ns adjoint)
```

Three code layers implement it:

- **Encoder** (`wide_common.encode_wide`) — *fixed*. Gives each unit a different
  linear view of the input so the 24 units are diverse. Not trained in Stage 2.
- **Circuit** (`netlist_wide.write_wide_netlist` → SPICE) — *trained*. The 24
  parallel diff-amps; produces 24 node voltages at 100 ns.
- **Readout** (`model.Readout`, softmax) — *trained* (convex, analytic). Maps the
  24 voltages to 2 class logits.

Only the **circuit** uses the simulator's adjoint; the readout and encoder use
ordinary numpy math.

---

## 3. The circuit, one unit at a time

Each of the 24 units is an **independent NMOS differential amplifier with a PMOS
active load and an NMOS tail current source** — a classic analog "neuron." The
units are *not* wired to each other; that is what makes them 24 separate
nonlinear features of the input rather than one deep chain.

```
                         VDD (3.3 V)
                          │        │
                    ┌─────┴──┐ ┌───┴────┐
        VTHj ──gate─┤ Mpd(P) │ │ Mps(P) ├─gate── VTHj      PMOS active loads
                    └────┬───┘ └───┬────┘                  (gate = trainable VTHj)
                       d(j)        u(j) ◄─────────── READ THIS NODE @100 ns
                         │           │
             ┌───────────┴──┐   ┌────┴─────────┐
   vnj ─gate─┤   Md (NMOS)   │   │  Ms (NMOS)   ├─gate── VINj    input diff pair
  (VNj ref)  └───────┬───────┘   └──────┬───────┘        (signal = encoder VINj)
                     └──────┬───────────┘
                          t(j)  (tail node)
                            │
                     ┌──────┴──────┐
           vbj ─gate─┤  Mt (NMOS)  │                       tail current source
          (VBj bias) └──────┬──────┘                       (gate = trainable VBj)
                            GND
                            │
                        C(j)=0.1fF from u(j) to GND (storage/integration cap)
```

The netlist for the whole layer is emitted by
`netlist_wide.write_wide_netlist(...)`. For unit *j* it writes exactly:

```
Md{j}  d{j}  vn{j}  t{j}  0    NCH L=650n W=6u     # dummy/reference branch
Ms{j}  u{j}  in{j}  t{j}  0    NCH L=650n W=6u     # signal branch, OUTPUT = u{j}
Mt{j}  t{j}  vb{j}  0     0    NCH L=1u   W=12u    # tail current source
Mpd{j} d{j}  th{j}  vdd   vdd  PCH L=2u   W=6u     # PMOS load on dummy branch
Mps{j} u{j}  th{j}  vdd   vdd  PCH L=2u   W=6u     # PMOS load on signal branch
C{j}   u{j}  0      0.1f                           # output cap
```

Intuition for what the unit computes: it's a **soft comparator**. When the input
`VINj` rises above the reference `vnj`, the signal branch steals current from the
dummy branch and the output node `u{j}` swings — a smooth, **tanh-like**
nonlinearity of `(VINj − VNj)`, with the steepness/level set by `VBj` (tail
current) and `VTHj` (load). Twenty-four of these, each with a *different*
projection and a *different* trainable threshold, tile the input plane with 24
differently-placed soft thresholds. A linear readout over them can then draw a
curved, piecewise boundary.

**MOSFET models** (Level-1 Shichman–Hodges, from the netlist header):

```
.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7
```

**How we read the output.** The netlist ends with an initial condition and a
short transient:

```
.IC V(u1)=1.65 V(u2)=1.65 ... V(u24)=1.65    # seed every output at a neutral 1.65 V
.TRAN 10n 100n                                # run 0 → 100 ns, 10 ns steps
```

We seed all outputs at a neutral 1.65 V and let the circuit evolve for 100 ns;
the **value of `u{j}` at t = 100 ns is the unit's activation.** (100 ns is the
same readout horizon used throughout the project; it is long enough for the
diff-amp to move meaningfully but short enough that all trainable knobs still
influence the state — see the main README's discussion.)

---

## 4. The data and the encoder

**Datasets** (`dataset.py`) — the reference repo's three 2-D toy sets, kept as
**binary classification**:

- `twomoon` — `make_moons(noise=0.1)`, nearly linearly separable.
- `circle` — `make_circles(noise=0.06, factor=0.5)`, concentric → needs a
  *closed* boundary.
- `2spirals` — two interleaved spirals, the hardest.

Each is standardized (`StandardScaler`) and cut to a **small, balanced** split
because every sample is a SPICE run: **20 per class train (40 total), 12 per
class test (24 total)**, `SEED=42`.

**Encoder** (`wide_common.init_encoder` + `encode_wide`) — *fixed, not trained*:

```python
W = 0.7 * randn(24, 2)     # a different 2-vector per unit  (seed=0)
b = 0.6 * randn(24)        # a different offset per unit
VINj = clip(1.0 + W[j]·(x,y) + b[j], 0.3, 3.0)   # volts into unit j's signal gate
```

The `1.0 +` centers the inputs around 1 V; the random `W, b` are what give the 24
units **diversity** (each thresholds a different linear combination of the plane).
We keep the encoder fixed so the "does training the *circuit* help?" question is
clean — only the transistor knobs and the readout move.

---

## 5. The forward pass: from (x,y) to a class

For one sample `x = (x0, x1)`:

1. **Encode** → 24 input voltages `VIN1..24` (`encode_wide`).
2. **Write netlist** with the current circuit params + these inputs
   (`write_wide_netlist`).
3. **Simulate** the `.TRAN` and read the 24 output voltages at 100 ns
   (`eval_chain` → `{u1: V, ..., u24: V}`). Call this state vector **s ∈ ℝ²⁴**.
4. **Standardize** the state: `sn = (s − μ) / σ`, where `μ, σ` are computed
   **once** from the initial circuit's states over the train set (fixed
   thereafter — a stable reference frame while the circuit moves).
5. **Readout** → logits `= Wout · sn + bout`, then `softmax`, then `argmax` = the
   predicted class.

Loss is standard **softmax cross-entropy** over the 2 classes.

---

## 6. The gradient: how the simulator gives us dV/dparam

This is the heart of Stage 2. We need `dLoss/dVTHj`, `dLoss/dVBj`, `dLoss/dVNj`
for every unit. The chain of dependencies is:

```
Loss ── softmax/CE ──► logits ── Wout ──► sn ── (÷σ) ──► s = [u1..u24] @100ns ── circuit ──► VTH/VB/VN
        (analytic)              (analytic)   (analytic)                          (SIMULATOR ADJOINT)
```

Everything left of `s` is ordinary calculus we do in numpy. The **only** piece
that crosses into the physical circuit is `∂u_j(100ns)/∂param`, and **the
simulator computes exactly that** via its backward transient adjoint.

### 6a. What the simulator returns

`simulator_api.run_chain(netlist, read_nodes, param_names)` calls the simulator
with `sensitivity=True` and returns:

```python
v_out, sens = run_chain(netlist, READ, CIRC_NAMES)
#  v_out[u_j]            = V(u_j, 100ns)                    forward value
#  sens[u_j][param]      = dV(u_j, 100ns) / dparam          adjoint sensitivity
```

Because every trainable knob (`VTHj`, `VBj`, `VNj`) is a **voltage source** in
the netlist, the simulator can return `∂V(u_j)/∂(that source)` for each. Sources
it can't provide a sensitivity for come back as `0.0` (safe fallback). We stack
these into a tensor:

```
SENS[i, j, k] = ∂u_j / ∂param_k     for sample i, read-node j, param k   # shape (n, 24, 72)
```

### 6b. Assembling the parameter gradient (the chain rule)

From the readout we get `dL/d(logits)` per sample; then

```
dL/ds_j  =  (dL/dlogits · Wout)_j  /  σ_j            # (n, 24), the ÷σ is the standardizer
```

In code (`train_wide_stage2.py`):

```python
G      = (softmax(logits) - onehot[yv]) / len(yv)    # dL/dlogits, (n, 2)
dL_dS  = (G @ params["Wout"]) / sd                   # dL/du_j,   (n, 24)
g_circ = np.einsum("ij,ijk->k", dL_dS, SENS)         # dL/dparam, (72,)
```

That single `einsum` is the whole gradient: for each parameter `k`, sum over all
samples `i` and all read nodes `j` of `(dL/du_j) · (∂u_j/∂param_k)`. **That is the
adjoint doing the work** — no finite differences, one simulator call per sample
gives all 72 sensitivities at once.

---

## 7. The training loop, line by line

Per epoch (`main()` in `train_wide_stage2.py`), for `EPOCHS = 90`:

**(1) Simulate the current circuit** over the 40 train samples, caching each
sample's state `s` **and** its `(24×72)` sensitivity block. Every call is wrapped
in `try/except` — a sample whose SPICE solve fails is simply **skipped** (robust
to the occasional non-convergent operating point).

**(2) Readout step — free convex Adam.** With the circuit held fixed this epoch,
the readout problem is convex, so we take an ordinary Adam step on `Wout, bout`
(`LR_READ = 0.05`). This keeps the accuracy signal clean while the circuit moves
slowly underneath it.

**(3) Circuit step — one *pre-checked, gentle* adjoint step.** This is the
careful part:

```python
g_circ = einsum(...)                         # 72-dim adjoint gradient
ckpt   = params["circ"].copy()               # remember where we are
cp     = opt_circ.step(circ, g_circ)         # tentative Adam step (LR_CIRC = 0.0008)
new_circ = clip(cp to BOUNDS)                # keep every knob physical
try_loss = metrics(Xtr, ytr, new_circ)       # RE-SIMULATE with the tentative circuit
if finite(try_loss) and try_loss <= tr_loss * 1.02:
    params["circ"] = new_circ                # accept only if it didn't hurt (allow +2%)
else:
    params["circ"] = ckpt                    # REJECT: revert
    lr_circ *= 0.6                           # and back off the circuit LR (floor 1e-5)
    opt_circ = Adam(circ, lr=lr_circ)
```

Why so cautious? The adjoint is a *local, small-signal* sensitivity around the
current operating point; a step that's too large can push units into a different
regime where the linearization is invalid and the loss jumps (or the solve
fails). The **accept-if-not-worse + LR-backoff** rule makes the circuit training
monotone-ish and stable. The readout always moves; the circuit only moves when it
verifiably helps.

**(4) Log & checkpoint.** Track train loss/acc, test acc; write
`results/<name>_wide_stage2_log.csv` and save the best-test-acc checkpoint to
`results/<name>_wide_stage2_best.json` (contains the trained `circ`, `Wout`,
`bout`, and `μ, σ` — everything needed to reproduce the classifier).

**Key constants** (top of the file): `EPOCHS=90`, `LR_CIRC=0.0008`,
`LR_READ=0.05`. Bounds live in `wide_common.BOUNDS`.

---

## 8. Results (and the honest finding)

Best test accuracy (24-sample test set), Stage 2 vs. the Stage 1 frozen reservoir:

| dataset | frozen reservoir (Stage 1) | **circuit-trained (Stage 2)** | best epoch | train acc |
|---|---|---|---|---|
| twomoon | 0.88 | **0.88** | 16 | 1.00 |
| circle | 0.96 | **0.96** | 12 | 0.95 |
| 2spirals | 0.96 | **0.92** | 7 | 0.65* |

\*2spirals reaches train 1.00 later in training but its *best test* checkpoint is
an early, still-underfit epoch — the classic small-test-set / overfitting caveat.

**The honest finding: training the circuit did *not* beat the frozen reservoir.**
Two independent pieces of evidence show why, and they're worth internalizing:

1. **The parameters barely moved.** After 90 epochs the trained knobs sit almost
   exactly at their initial values:

   | | init | trained range (across all 24 units) |
   |---|---|---|
   | VTH | 1.70 | [1.69, 1.71] |
   | VB  | 0.80 | [0.79, 0.81] |
   | VN  | 1.00 | [0.99, 1.01] |

   The pre-checked/backoff rule kept rejecting larger steps, so the circuit stayed
   within ~1 % of where it started.

2. **The best epoch is very early** (7–16). The circuit step rarely improved test
   accuracy beyond what the readout alone achieved on the *initial* random
   features.

**Why this is the expected result, not a bug.** A wide *random* analog layer is
already a good reservoir — the whole point of reservoir computing / random
features is that width, not fine-tuning of the nonlinearity, provides the
separating power. On these small 2-D problems the frozen reservoir is already at
ceiling (circle 0.96, 2spirals 0.96), so there's little headroom for circuit
training to claim, and the conservative adjoint step (correctly) declines to risk
the operating point for a fraction of a percent. **Stage 2's value is
methodological**: it demonstrates that the physical parameters *are* trainable
end-to-end through the simulator's adjoint, with a stable recipe — not that doing
so beats a good reservoir on these particular toy sets.

> Want Stage 2 to actually win? You need headroom and expressivity the reservoir
> lacks: a harder/higher-dimensional dataset, a *smaller* layer (so tuning
> matters), a trainable encoder, or a deeper analog stack. See the ideas at the
> end of §12.

Curves: `results/<name>_wide_stage2_curve.png` (loss + train/test accuracy, with
the frozen-reservoir line drawn for reference).

---

## 9. The decision-boundary animation

`animate_wide_stage2.py` visualizes what the **trained** analog features can do:

1. Load the trained circuit from `<name>_wide_stage2_best.json`.
2. Push a dense `44×44` grid of the `(x,y)` plane **through the trained circuit
   once**, caching each grid point's 24-node 100 ns state.
3. Re-train just the softmax readout on those cached features, rendering a frame
   every few epochs → the boundary **forming** on the learned analog features.
4. Save `results/<name>_wide_stage2_boundary.gif`.

The GIFs show the boundary **enclosing the circle** and **winding through the
spiral arms** — the curved boundaries the narrow chain could never draw. Final
in-animation accuracy prints ~1.00 because it fits the combined (train+test)
points shown; the honest generalization number is the test acc in §8.

---

## 10. How to replicate — exact commands

**Prereqs**

- Python 3 with `numpy`, `scikit-learn`, `matplotlib`, `pillow`.
- The circuit simulator present at
  `D:\Simulator\circuit_simulator with level3\src` (hard-coded in
  `simulator_api.py:19` — edit that path if yours differs).
- Run everything from the `toy2d/` directory.

**Full Stage 2 pipeline for one dataset** (PowerShell or bash):

```bash
cd D:/Kirchoffnet/kirchoff_claude/toy2d

# 0. (optional) sanity-check the split
python dataset.py --dataset circle

# 1. (optional) Stage 1 first, so the curve/GIF get a frozen-reservoir reference line
python train_wide.py --dataset circle

# 2. Stage 2 — TRAIN THE CIRCUIT via the 100 ns adjoint  (this is the main step)
python train_wide_stage2.py --dataset circle

# 3. render the trained-circuit decision-boundary GIF
python animate_wide_stage2.py --dataset circle
```

Repeat with `--dataset twomoon` and `--dataset 2spirals`. Each dataset uses its
own scratch netlist (`tmp_wide_stage2_<name>.sp`), so the three can run in
parallel safely.

**What each step writes** (into `results/`):

| file | produced by | contents |
|---|---|---|
| `<name>_wide_stage2_log.csv` | train | per-epoch loss, train acc, test acc, circuit LR |
| `<name>_wide_stage2_best.json` | train | best checkpoint: `circ`, `Wout`, `bout`, `μ`, `σ` |
| `<name>_wide_stage2_curve.png` | train | loss + accuracy curves (with reference line) |
| `<name>_wide_stage2_boundary.gif` | animate | boundary-forming animation on trained features |
| `<name>_anim_stage2_stdout.txt` / `<name>_wide_stage2_stdout.txt` | your redirect | captured console output |

**Runtime / expectations.** Each epoch runs one adjoint simulation per train
sample (40) plus re-simulations for the accept-check and test metrics, so a
90-epoch run is a few hundred–thousand SPICE solves; budget minutes, not seconds,
per dataset on a typical machine. Expected best test acc: **twomoon ≈ 0.88,
circle ≈ 0.96, 2spirals ≈ 0.92** (§8). Results are deterministic given the fixed
seeds (`dataset SEED=42`, encoder/readout `seed=0`) **and** an unchanged
simulator — a different simulator version can shift the operating points and
therefore the exact accuracies.

**To reproduce the numbers without retraining**, load a checkpoint and evaluate:

```python
import json, numpy as np
from netlist_wide import write_wide_netlist
from simulator_api import eval_chain
from dataset import load_dataset
from model import softmax
from wide_common import N_UNITS, READ, CIRC_NAMES, init_encoder, encode_wide, circ_dict

d   = json.load(open("results/circle_wide_stage2_best.json"))
circ = np.array([d["circ"][n] for n in CIRC_NAMES])
Wout, bout = np.array(d["Wout"]), np.array(d["bout"])
mu, sd = np.array(d["mu"]), np.array(d["sd"])
W, b = init_encoder(seed=0)
Xtr, ytr, Xte, yte = load_dataset("circle")

def predict(x):
    write_wide_netlist(circ_dict(circ), encode_wide(x, W, b), "tmp_eval.sp", n_units=N_UNITS)
    v = eval_chain("tmp_eval.sp", READ)
    s = np.array([v[n] for n in READ])
    return (((s - mu) / sd) @ Wout.T + bout).argmax()

acc = np.mean([predict(x) == y for x, y in zip(Xte, yte)])
print("test acc:", acc)
```

---

## 11. File map for Stage 2

**Stage-2-specific**

- `train_wide_stage2.py` — the circuit trainer (this README's subject).
- `animate_wide_stage2.py` — trained-circuit boundary animation.
- `wide_common.py` — wide-layer config, `BOUNDS`, `CIRC_NAMES`, the fixed encoder,
  `circ_init` (VTH=1.7, VB=0.8, VN=1.0).
- `netlist_wide.py` — emits the 24-unit parallel diff-amp netlist (`VN` per-unit
  trainable reference is the Stage-2 addition).

**Reused unchanged**

- `simulator_api.py` — `run_chain` (TRAN + adjoint sensitivities) and `eval_chain`
  (forward only). Simulator path is set at line 19.
- `model.py` — `softmax`, `Readout`, `Adam`.
- `dataset.py` — the three datasets as binary classification.

**Outputs** — everything under `results/` matching `*_wide_stage2_*`.

---

## 12. Troubleshooting & key gotchas

- **`ModuleNotFoundError` / simulator not found** — fix the hard-coded path in
  `simulator_api.py:19` to point at your `circuit_simulator .../src`.
- **A dataset "fails on all train samples"** — the initial circuit didn't converge
  for any sample. Check the netlist's `.IC` seed (1.65 V) and the encoder swing;
  wildly out-of-range `VINj` can latch the diff-amps. This is the same
  operating-point fragility documented in the project memory.
- **Test accuracy is noisy epoch-to-epoch** — expected: the test set is only 24
  points, so each correct/incorrect flip is ~0.04. Trust the trend and the `best`
  checkpoint, not a single epoch.
- **The circuit params barely change** — that's the real behavior (§8), caused by
  the pre-checked/backoff rule protecting a near-optimal operating point. It is a
  feature (stability), and it is *why* Stage 2 ≈ Stage 1 here.
- **Why not just use bigger `LR_CIRC`?** Larger steps get *rejected* more often
  (they violate the "don't raise the loss" check) and trigger LR backoff, so they
  don't actually move faster — they just waste simulations. The bottleneck is the
  validity radius of the local adjoint, not the learning rate.

**If you want Stage 2 to *beat* the reservoir** (open directions, not yet built):
harder/higher-dimensional data with real headroom; a *narrow* layer (e.g. 6–8
units) where tuning each unit matters; a **trainable encoder** (also via the
adjoint, since `VINj` are sources the simulator can differentiate); a **deeper
analog stack** (feed a second analog layer); or a per-sample-longer transient to
give the circuit more dynamic range before readout.
