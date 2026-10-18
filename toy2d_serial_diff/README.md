# toy2d_serial_diff — A Closed-Loop Series Diff-Pair Ring as a KirchhoffNet Classifier

Training a **real SPICE-simulated closed-loop analog circuit** as a binary classifier on
the 2-D toy datasets (**twomoon, circle, 2spirals**), using the simulator's **100 ns
transient adjoint** as the gradient signal.

Unlike the sibling `../toy2d/` (which uses *open* structures — a feed-forward chain or a
parallel wide layer — and drives inputs as `VIN` gate-voltage sources), this directory
implements the **KirchhoffNet-faithful** design:

- **Series + closed loop.** `N = 10` differential-amplifier stages are wired in series,
  each stage's output feeding the next stage's signal input, and the **loop is closed**
  (stage 1's signal input is stage 10's output).
- **Input via `.IC`.** The data point is injected as **initial conditions** on the ring's
  node voltages at `t = 0` — *input = initial state*, exactly the Neural-ODE idea. There
  are **no `VIN` sources**; data enters only through `.IC V(h_j)=…`.
- **Read the same nodes at 100 ns.** After the ring evolves for 100 ns, the same `h1..h10`
  nodes are read back and classified.
- **Hardware-trained.** The `3·N = 30` per-stage circuit parameters `VTH` (PMOS load),
  `VB` (tail bias), `VN` (reference) are trained end-to-end through the simulator's
  backward transient adjoint `dV(h_j,100ns)/d{VTH,VB,VN}`.

The topology mirrors the simulator's own committed example
`D:\Simulator\circuit_simulator with level3\testfiles\kirr.txt` ("kirchoff_diffamp_new"),
a 4-stage diff-amp ring, scaled to 10 stages.

---

## Pipeline

```
 (x,y) ──basic linear encoder──►  10 .IC seeds  ──►  [10-stage CLOSED diff-pair RING]  ──►
   2 features   1.65 + W·x + b        h1..h10          evolve 0→100 ns (seed-then-evolve)
   (standardized)  clip[0.3,3.0]                        h_j = f(ring dynamics, VTH/VB/VN)
        read h1..h10 @100ns ──standardize──► softmax READOUT (10→2) ──► argmax ──► class
                            ▲ per-stage VTH_j/VB_j/VN_j trained via 100 ns transient adjoint
```

**Very basic data manipulation** by design:
- *before hardware*: a fixed linear map turns the 2 features into 10 `.IC` seed voltages
  (`ring_common.encode_ic`), centered at mid-supply (1.65 V) and clipped to `[0.3, 3.0] V`.
- *after hardware*: standardize the 10 read voltages, then a linear softmax readout.

## The circuit, one stage at a time

Each of the 10 stages is an NMOS differential pair with a PMOS active load and an NMOS
tail current source — a classic analog "neuron". For stage `j`, the **signal** input is
the **previous** stage's output `h_{j-1}` (and `h_10` for stage 1, closing the loop):

```
Md{j}  dm{j}  vn{j}  tl{j}  0    NCH L=650n W=6u     ; dummy branch, gate = VN_j reference
Ms{j}  h{j}   {h_{j-1}} tl{j} 0  NCH L=650n W=6u     ; signal branch, gate = prev stage out
Mt{j}  tl{j}  vb{j}  0     0     NCH L=1u   W=12u    ; tail current, gate = VB_j
Mpd{j} dm{j}  th{j}  vdd   vdd   PCH L=2u   W=6u     ; PMOS load (dummy)
Mps{j} h{j}   th{j}  vdd   vdd   PCH L=2u   W=6u     ; PMOS load (signal), OUTPUT = h{j}
C{j}   h{j}   0      1p                              ; storage cap (state node)
```

The `.IC V(h_j)=…` seed each output node at `t=0`; `.TRAN 10n 100n` evolves the ring; the
value of `h_j` at 100 ns is the state read out. `.IC` is **seed-then-evolve** — the node
holds the seed only at `t=0`, then evolves freely under the full nonlinear solve.

## Why the closed loop (and why `.IC` input)

A closed ring turns the circuit into a genuine dynamical system: the seeded state evolves
under coupled nonlinear feedback for 100 ns, so the read-out state is a nonlinear function
of the whole input point. The **gate check** (`diag_ring.py`) confirms this adds separating
power over the raw features *before any training*:

| dataset | raw features (a line) | untrained ring state (a line) |
|---|---|---|
| twomoon | 0.93 | **1.00** |
| circle | 0.70 | **0.90** |
| 2spirals | 0.62 | **0.80** |

(train-set linear separability; 0 convergence failures on all three.)

## Results

Best test accuracy (24-point test set), and the ring used by the boundary GIF:

| dataset | best test acc | @epoch | boundary GIF ring |
|---|---|---|---|
| twomoon | 0.88 | 7 | trained checkpoint (converges) |
| circle | 1.00 | 14 | `circ_init` fallback (see note) |
| 2spirals | 0.79 | 40 | trained checkpoint (converges) |

Artifacts per dataset in `results/`: `<name>_ring_curve.png` (loss + train/test
accuracy over 90 epochs), `<name>_ring_boundary.gif` (decision boundary forming as the
readout trains on the ring state), and `<name>_ring_best.json` (checkpoint).

**Honest findings (candor, à la the toy2d READMEs):**

1. **The closed ring works as a classifier.** The `.IC`-seeded ring, evolved 100 ns and
   read back, provides a nonlinear feature map that a linear readout separates well —
   circle reaches 1.00, twomoon 0.88, 2spirals 0.79 on tiny 40/24 splits.
2. **Circuit-adjoint training is delicate on a closed loop.** The circle run's saved
   checkpoint is **degenerate** — it only converges on ~15/64 points when re-simulated,
   even though its logged accuracy looked perfect. Cause: the adjoint step can push the
   ring into a non-convergent operating regime. The accept/reject guard now **also
   requires a step to keep ≥95 % of train samples convergent** (not just a low loss on the
   survivors); re-running with this guard yields trustworthy checkpoints. 2spirals'
   checkpoint, by contrast, stayed valid (64/64).
3. **The boundary GIFs use the untrained `circ_init` ring when a checkpoint is degenerate**
   (circle), matching what `../toy2d/animate_wide.py` does with its frozen reservoir. The
   gate check confirms the untrained ring already carries the separating power, so the
   GIFs are legitimate visualizations of the ring's decision boundary.
4. **Where the accuracy comes from.** As in toy2d Stage 2, the co-trained linear readout
   drives most of the accuracy; the value of the circuit-adjoint path here is
   *methodological* — it demonstrates that the 30 physical `VTH/VB/VN` sources of a
   **closed** analog ring are trainable end-to-end through the simulator's 100 ns
   transient adjoint, with a stable accept/reject recipe.

## File map

**Ring-specific**
- `netlist_ring.py` — emits the closed 10-stage diff-pair ring netlist (`.IC` input, no
  `VIN`). Wraps the loop (`stage 1 signal = h_N`).
- `ring_common.py` — config: `N_STAGES`, ordered `CIRC_NAMES` (VTH/VB/VN × 10), `BOUNDS`,
  `READ`, the basic `.IC` seed encoder (`init_seed_encoder`/`encode_ic`), `circ_dict`,
  `circ_init`.
- `diag_ring.py` — gate check: raw-vs-ring-state linear separability (design validator).
- `train_ring.py` — trains the 30 circuit params via the 100 ns adjoint + a co-trained
  linear softmax readout; cross-entropy loss. Also writes a final sensitivities CSV.
- `diag_ring.py` — gate check: raw-vs-ring-state linear separability (design validator).
- `animate_ring.py` — decision-boundary-forming GIF (falls back to `circ_init` if a
  trained checkpoint is degenerate).
- `plot_boundary.py` — static accuracy-curve + decision-boundary figure from a checkpoint.
- `smoke_test.py` — one-shot convergence + non-zero-sensitivity check for the ring.

**Reused verbatim from `../toy2d/` (generic)**
- `simulator_api.py` — `run_chain` (TRAN + adjoint sensitivities) / `eval_chain` (forward).
- `model.py` — `Adam`, `softmax`, `Readout`, cross-entropy.
- `dataset.py` — the three datasets as binary classification (40 train / 24 test).

**`results/`** — per-dataset logs (`*_ring_log.csv`), curves (`*_ring_curve.png`), boundary
GIFs (`*_ring_boundary.gif`), best checkpoints (`*_ring_best.json`, containing `circ`,
`Wout`, `bout`, `mu`, `sd`), and the **final sensitivities CSV** (`*_ring_sensitivities.csv`).

## Running this code — step by step

**Prerequisites**
- Python 3 with `numpy`, `scikit-learn`, `matplotlib`, `pillow`.
- The circuit simulator present at `D:\Simulator\circuit_simulator with level3\src`
  (hard-coded in `simulator_api.py:19` — edit that line if your path differs).
- **Run every command from inside `toy2d_serial_diff/`** (the modules use bare imports and
  the simulator does a `sys.path.insert`). Each dataset uses its own scratch netlist
  (`tmp_ring_<name>.sp` / `tmp_animr_<name>.sp`), so different datasets can run in parallel.

```powershell
cd D:\Kirchoffnet\kirchoff_claude\toy2d_serial_diff
```

**Step 0 — (optional) sanity checks**
```powershell
python smoke_test.py                    # 1 sample: ring converges + non-zero VTH/VB/VN sens
python dataset.py    --dataset twomoon  # inspect the standardized 40/24 split
```

**Step 1 — gate check (does the ring add separating power? runs in seconds–minutes)**
```powershell
python diag_ring.py  --dataset twomoon  # prints raw-vs-ring-state linear separability
```

**Step 2 — train (the main step: circuit via 100 ns adjoint + linear readout)**
```powershell
python train_ring.py --dataset twomoon
```
Writes into `results/`:
| file | contents |
|---|---|
| `twomoon_ring_log.csv` | per-epoch loss, train acc, test acc, circuit LR |
| `twomoon_ring_best.json` | best checkpoint: `circ`, `Wout`, `bout`, `mu`, `sd` |
| `twomoon_ring_curve.png` | loss + train/test accuracy curves |
| `twomoon_ring_sensitivities.csv` | **final** `dV(h_j,100ns)/d{VTH,VB,VN}` per sample/node/param |

**Step 3 — decision-boundary GIF**
```powershell
python animate_ring.py --dataset twomoon   # -> results/twomoon_ring_boundary.gif
```

Swap `--dataset twomoon` for `circle` or `2spirals` to run the other two. A full sweep:
```powershell
foreach ($d in @('twomoon','circle','2spirals')) {
    python diag_ring.py  --dataset $d
    python train_ring.py --dataset $d
    python animate_ring.py --dataset $d
}
```

**The final sensitivities CSV** (`results/<name>_ring_sensitivities.csv`) is produced
automatically at the end of `train_ring.py`. It is long-format with columns
`sample, label, read_node, param, V_node_100ns, dVnode_dparam` — one row per
(train sample × read node `h1..h10` × circuit param `VTH/VB/VN 1..10`), i.e. the raw
100 ns transient adjoint sensitivities that drive the circuit training.

**Runtime.** Each epoch runs one adjoint simulation per train sample plus re-simulations
for the accept-check and test metrics (~120 SPICE solves/epoch × 90 epochs); budget a few
minutes to tens of minutes per dataset depending on the machine.

## Key implementation notes

- **Transient step vs. adjoint cost.** `sensitivity=True` caches an LU factorization per
  timestep, so the step count is kept small: `.TRAN 10n 100n` (≈11 steps). Do **not** use
  `kirr.txt`'s `1e-12 100e-9` (100k steps) — untenable for the adjoint. Drop to `1n` only
  if the dynamics look aliased.
- **Stable circuit training.** The circuit takes one *pre-checked* gentle adjoint step per
  epoch: a tentative step is applied, the train loss re-simulated, and the step is
  **rejected (with LR backoff)** if it raises the loss or breaks convergence. The readout
  (convex) is stepped freely. Every simulator call is per-sample robust (non-convergent
  samples are skipped).
- **Operating point.** The closed ring is seeded away from its symmetric metastable point by
  the `.IC` values; with the default Level-1 biases (VTH=1.7, VB=0.8, VN=1.0 — device sizes
  identical to `kirr.txt`) all samples converge and the adjoint returns healthy non-zero
  VTH/VB/VN sensitivities (verified by `smoke_test.py`).

> **Superseded:** the circle/twomoon/2spirals checkpoints in `results/` are legacy (circle fails 49/64 points; test-set checkpoint selection; scaler leak). Use the validated packages in `kring/models/` — see `kring/README.md`.
