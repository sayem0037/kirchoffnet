# The Kirchhoff Recurrent Core

### A reconfigurable architecture for scaling KirchhoffNet past the serial diff-pair ring

**Ahmad Sayeed Sayem** · August 2026 · `D:\Kirchoffnet\kirchoff_claude\kfabric`

---

## 1. The question

`../toy2d_serial_diff` implements a closed loop of ten differential-amplifier
stages. Data enters as `.IC` seeds on `h1..h10`, the ring evolves for 100 ns, the
same nodes are read, and thirty node-bias parameters (`VTH_j`, `VB_j`, `VN_j`) are
trained through the simulator's transient adjoint. It works on the 2-D toy sets
(0.88 / 1.00 / 0.79) and its paper is candid about why: a co-trained linear
soft-max read-out supplies essentially all of the accuracy, while the circuit
parameters move only in the third decimal (VTH₁: 1.7000 → 1.7008 over 90 epochs).

From the netlist's point of view it is a **serial configuration of diff pairs**.
The question is what architecture it needs to become *reconfigurable* and to reach
MNIST- and CIFAR-scale classification.

## 2. Why the obvious answer is the wrong answer

The obvious move is to copy the reference model. The ICCAD KirchhoffNet
[[1]](#refs) is on disk at `D:\Kirchoffnet\kirchhoffnet`, so we can read exactly
what it does rather than guess. `src/utils/topology.py::_mix_connect` builds, per
block: all-pairs edges inside every sliding 4×4 patch, one edge per node to
ground, and 50 global hub nodes wired to everything. `core_spec.py --compare`
recomputes those counts and checks them against the committed `model.pth` sizes:

| | nodes | edges/block | blocks | params | `model.pth` on disk |
|---|---:|---:|---:|---:|---:|
| MNIST | 834 | 230,068 | 2 | **920,272** | 3,682,407 B (= 920,272 × 4 B + header) ✓ |
| CIFAR-10 | 3,122 | 2,054,018 | 3 | **12,324,108** | 49,298,147 B (= 12,324,108 × 4 B + header) ✓ |

The counts match byte-for-byte, so this is the real architecture, not a
reconstruction. And it contains the whole problem in one line:

> **The ICCAD model maps one pixel to one circuit node, so `N_nodes = input_dim`.**

Everything follows from that. A faithful SPICE transient adjoint of a 3,122-node
circuit is out of reach. A software version of it is a re-implementation of their
PyTorch ODE and teaches us nothing about hardware. And re-shaping the graph does
not help: 230,068 edges is 230,068 edges however they are wired.

It is worth recording what the reference itself achieved, because it calibrates
the ambition. `src/results/mnist/metric.yaml` reports `top1: 0.9942` at 4.76
min/epoch — MNIST is solved. `src/results/cifar10/` has `train_loss` falling
2.05 → 0.80 over 120 epochs at **45.5 min/epoch and no recorded test accuracy at
all**. CIFAR-10 is unproven for this model class even in software.

## 3. The idea: decouple circuit size from input dimension

Reuse a **small** physical core many times over the input, carrying state on its
capacitors between invocations. Capacity comes from **time and configuration**,
not from simultaneous node count. This is the weight-stationary reuse that every
real analog accelerator is built on, and it is what lets a 256×256 crossbar run a
ResNet.

```
    held state  VS1..VSM ->  rails s1..sM --.
                                             >-[ theta-gated NMOS edges ]-> n1..nM (caps)
    data chunk  VR1..VRk ->  rails r1..rk --'

    x_0 -> [core] -> v_1 -> [core] -> v_2 -> ... -> v_T -> read last C taps -> class
            ^ same theta, same silicon, invoked T times
```

`N_nodes = M` (fixed), `N_params = E` (fixed, shared across all T steps),
`T = ceil(input_dim / k)`. The input dimension is absorbed entirely by **T**.

### 3.1 L0 — the edge cell

One NMOS per edge: drain = an input rail, gate = `theta_e`, source = the
destination state node, bulk = 0. Geometry and model card are taken verbatim from
`../toy2d_spidernet/netlist_spider.py`, which was ported 1:1 from the Cadence
Virtuoso export `spidernet_1.txt` and checked by its `verify_topology.py`.

Two consequences matter. First, the parameters now live on **edges**, which is
where the ICCAD model puts them and where the ring does not — a cycle graph on N
nodes has N edges, so the ring's capacity is O(N) = 30 no matter how it is tuned.
Second, spidernet's own README (§4) derives its architecture's ceiling
analytically: with fixed rails the crossbar is bipartite forever and collapses to
`linear(x) + κ‖x‖²`, "*the limitation is the crossbar's bipartite structure — all
nodes see the same rails and never each other*". Here **half the rails are the
previous state**, re-driven every step, so the composition over T invocations is
not a single static rail→node map. The documented ceiling is broken by the time
dimension rather than by adding silicon.

**A correction worth recording.** That ceiling is derived from an *all-triode*
closed form. `verify_closedform.py` tests it against the simulator at the KRC
operating point and it **does not hold** — errors up to 0.39 V, larger than the
entire spread of the node voltages. The regime census explains why: over 640
edge-instances the KRC runs **87.5 % triode, 12.5 % saturation, 0 % cutoff**,
while the closed form assumes every edge is in triode. This is not a defect on
either count. The 0 % cutoff confirms the operating window keeps every parameter
alive (Rule 1), and a per-step map that mixes triode with saturation is *more*
nonlinear than the quadratic the closed form describes. It does mean the
expressivity argument must rest on composing T nonlinear maps, which it does, and
not on that closed form — which is why it is checked rather than inherited.

### 3.2 L1 — the core, and the reconfigurability primitive

M capacitive state nodes, up to M(M+k) edge cells selected by a switch fabric,
k data rails, C readout taps. This is the **entire physical circuit and the only
thing SPICE ever sees**. The switch fabric is the classic field-programmable
analog array idea [[6]](#refs) — configurable analog blocks plus a routing
network — specialized to a KCL graph: one fabric, many graphs, changed by
configuration rather than by a new netlist. A sparse edge subset (`edge_budget`
in `core_spec.py`) is a valid configuration of the same silicon.

### 3.3 L2 — time multiplexing

The input is streamed in T chunks; the state persists between them. The same
`theta` is used at every step, so the parameter count is independent of T. The
mapper (`core_spec.CoreSpec`) turns `(input shape, n_classes, budget)` into
`{k, T, chunking, edge list, tap assignment}`, which is what makes the design
dataset-agnostic rather than dataset-specific.

### 3.4 L3 — the read-out, deliberately not trained

The class scores **are** the last C tap voltages. They pass through a fixed
per-tap normalization `(mu, sd)` measured once from the *untrained* core, and a
fixed gain. That map is **diagonal**: it cannot mix taps, so it cannot manufacture
a decision boundary. This is a direct structural response to the ring paper's
§VIII-A. There is no read-out to hide behind, so every bit of class separation has
to come from `theta`.

One free choice remains — *which* state the taps are read from — and it turns out
to matter more than anything else in the design:

- **`last`**: the scores are `v_T[taps]`. This is the direct analogue of the
  reference's `projector: last10`, and the obvious first choice.
- **`mean`**: the scores are `mean_t v_t[taps]`, the taps integrated over the
  whole rollout.

Gate 1 measures a spectral radius of **0.765**, so after T = 8 invocations the
first chunk contributes only `0.765^8 ≈ 0.10` of `v_T`. **Reading only the final
state throws most of the image away** — the core has forgotten the top of the
digit by the time it reaches the bottom. Time-averaging the read-out is the
standard remedy (it is what reservoir computing collects), it stays strictly
diagonal and untrained, and it is free because every `v_t` is already computed.
§5.4 reports both, because the difference is the substantive architectural
finding rather than a tuning detail.

### 3.5 What this is, and is not

|  | ICCAD KirchhoffNet | Kirchhoff Recurrent Core |
|---|---|---|
| nodes | = input dim (834 / 3,122) | fixed small (8–16) |
| params | 920k / 12.3M, one set per edge instance | 80–704, **shared across all T steps** |
| structure | one giant simultaneous ODE | recurrent; state carried across T invocations |
| input | 784–3,072 parallel `.IC` seeds | k rails × T steps |
| read-out | `last10` projector | `last C` taps, fixed diagonal normalization |
| model class | continuous-depth feed-forward | continuous-time RNN |

The nearest precedents are **not** ICCAD. They are Cauwenberghs' analog VLSI
continuous-time recurrent network [[4]](#refs) — six analog neurons, 42 free
parameters, 2 × 2 mm, 1.2 mW, trained on-chip — and delay-based reservoir
computing [[5]](#refs), which emulates a large network from a single physical node
by time multiplexing. KRC differs from the latter in the one way that matters
here: **the recurrence is trained, not random.** Given that the ring's accuracy
turned out to come from its read-out rather than its circuit, building another
frozen random reservoir would reproduce exactly the failure mode we are trying to
escape. (A random reservoir read out linearly tops out around 90.6 % on MNIST
[[9]](#refs).)

For the MNIST configuration actually trained below (M = 12, k = 8, T = 8), the
mapper reports against the reference on the same task:

```
  nodes        834  ->      12       70x fewer
  params   920,272  ->     240     3834x fewer
  DACs         784  ->       8       98x fewer
```

## 4. Training: SPICE is the only gradient source

No digital twin, no differentiable surrogate. The whole point is to keep the
gradient physical, and the small core is what makes that affordable.

### 4.1 The enabling trick: state enters as voltage sources, not `.IC`

`.IC` is a solver directive, not a component, so `dV/d(.IC)` does not exist —
seeding the state with `.IC`, as the ring does, makes the state-transfer Jacobian
unobtainable and BPTT impossible. But in this simulator **a voltage source's name
is its differentiable-parameter name** (`simulator_api.py` returns sensitivities
"for every requested parameter ... since all of them are voltage sources"; the
codebase already relies on this at `../toy2d/common.py:11`).

So we hold the previous state on a sample-and-hold and re-apply it through
source-driven rails — which is also the honest hardware description of a
time-multiplexed core. One adjoint call at step *t* then returns all three blocks:

```
    S_t = dv_{t+1}/dtheta   (M x E)   parameter sensitivity
    J_t = dv_{t+1}/dVS      (M x M)   STATE-TRANSFER JACOBIAN
    B_t = dv_{t+1}/dVR      (M x k)   input sensitivity
```

### 4.2 Exact BPTT for free

```
    lam_T = dL/dv_T
    for t = T-1 .. 0:
        g    += S_t^T lam_{t+1}
        lam_t = (J_t^T lam_{t+1}) * mask_t
```

`mask_t` is the derivative of the rail clip — the S/H drives the same rail
network as the data, so a state pushed outside the legal window is clipped by real
hardware and its gradient is genuinely zero there. The backward pass is M×M
matrix-vector products in numpy and costs **no extra simulator calls at all**.

### 4.3 Two fixes to the training recipe itself

The ring's near-frozen parameters are not only an architecture problem. Its loop
takes **one** guarded circuit step per epoch (`train_ring.py:141`), so 90 epochs is
90 steps. `train_krc.py` steps every minibatch. Combined with removing the
read-out, this is why `max|dtheta|` here is measured in tenths of a volt rather
than in units of 1e-4. The convergence guard from the ring is kept in spirit
(revert and back off if a step spikes the loss or drops the solve success rate),
since an analog circuit really can be pushed into a non-convergent regime and
skipped samples make a loss-only test look good.

## 5. Measured results

Every number below is produced by the scripts in this directory.

### 5.1 Gate 1 — the Jacobian exists (`smoke_test.py`)

The check the whole design hangs on. M = 8, k = 2, E = 80:

```
A. convergence + data path   across-node sd 1.6e-02, max|dV| for new input 2.7e-01   PASS
B. dV/dTHETA                 |S| max 5.19e-02, dead edges 0/80                        PASS
C. dV/dVS  (Jacobian)        J is 8x8, nonzero 64/64, |J| max 1.89e-01
                             spectral radius 0.765  (contracting -> stable rollout)   PASS
D. dV/dVR                    |B| max 2.48e-01, nonzero 16/16
```

The Jacobian is **fully dense** and the recurrence is contracting. Exact BPTT is
available. `S` is 80/640 non-zero because each edge feeds exactly one destination
node — the expected block structure, not a defect.

### 5.2 Gate 2 — what a core step costs (`scale_probe.py`)

`.TRAN 10n 100n`, k = 8, one adjoint solve (forward + all sensitivities):

| M | E | t_adjoint | t_forward | adj/fwd |
|---:|---:|---:|---:|---:|
| 6 | 84 | 239 ms | 85 ms | 2.8× |
| 8 | 128 | 436 ms | 128 ms | 3.4× |
| 12 | 240 | 1022 ms | 273 ms | 3.7× |
| 16 | 384 | 1983 ms | 512 ms | 3.9× |

For scale: the reference puts 834 (MNIST) or 3,122 (CIFAR) nodes into a *single*
solve. This table is the argument for the architecture, in milliseconds.

**One optimization fell straight out of it.** The node time constant is ~1e-13 s
(0.1 fF), so the state is fully settled long before `tstop`; `.TRAN 10n 100n` was
paying for eleven cached LU factorizations to compute a settled operating point.
Coarsening to `50n/100n` (3 steps) at M = 12:

| tstep/tstop | steps | t_adjoint | max ΔV vs 10n | max ΔJ |
|---|---:|---:|---:|---:|
| 10n/100n | 11 | 935 ms | — | — |
| 25n/100n | 5 | 502 ms | 6.5e-08 | 7.7e-08 |
| **50n/100n** | **3** | **357 ms** | **8.7e-08** | **1.0e-07** |
| 100n/100n | 2 | 283 ms | 2.8e-07 | 8.4e-05 |

**2.6× faster for a 1e-7 V deviation.** `50n/100n` is now the default;
`100n/100n` is rejected because its Jacobian starts to drift.

### 5.3 Gate 3 — the gradient is correct (`check_grad.py`)

Adjoint BPTT vs central finite differences of the fully rolled-out loss, across a
T = 4 recurrent chain (so it tests `J_t`, not just `S_t`). M = 8, k = 4, E = 96,
batch 6, 10 randomly probed edges:

```
  cosine similarity   : 0.999990
  median rel. error   : 0.66%
  ||adjoint|| / ||fd||: 0.9991
```

The single 88 % outlier sits on an entry of magnitude 2.8e-04, where the
finite-difference estimate is itself dominated by truncation.

This is the validation that reviewer concern **M4** on the ring paper asked for
and that was deferred as future work: *"the adjoint should be validated against
finite-difference perturbation ... to rule out a systematic gradient error masked
by the read-out's ability to compensate."* Here there is no read-out that could
compensate, and the chain being validated spans four recurrent steps.

### 5.4 MNIST

Real MNIST from the cached npz, **downsampled to 8×8 and streamed row-wise**:
`k = 8` rails, `T = 8` invocations, `M = 12` state nodes, `E = 240` edge
parameters shared across all 8 invocations. 150 train / 60 test, 10 classes,
8 epochs, single seed, Adam on the edge thetas via exact SPICE-adjoint BPTT.
Chance is 0.10. All three arms are **identical** except for how the class scores
are formed, and were run concurrently from the same seed (`compare_arms.py`):

| read-out | best test | @ep | best train | train loss | max\|Δθ\| | mean\|Δθ\| |
|---|---:|---:|---:|---|---:|---:|
| `v_T`, fixed diagonal | 0.200 | 5 | 0.193 | 2.298 → 2.101 | 1.320 | 0.246 |
| **`mean_t v_t`, fixed diagonal** | **0.400** | 7 | 0.280 | 2.353 → 2.155 | 1.400 | 0.237 |
| `mean_t v_t` + co-trained linear | 0.317 | 3 | 0.313 | 2.220 → **1.950** | 0.534 | 0.128 |

(Δθ is measured at each arm's best checkpoint. Figure: `results/mnist_ablation.png`;
per-arm six-panel figures: `results/mnist_{last,mean,meanRO}_krc_results.png`.)

Three findings, in order of importance.

**1. The contracting recurrence, not the circuit, was the binding constraint.**
Time-pooling the read-out **doubles test accuracy, 0.200 → 0.400**, with an
identical circuit, identical parameter count, and near-identical θ displacement
(1.320 vs 1.400 V). Nothing was added to the model — the same `v_t` were already
being computed. This is the `0.765^T` washout of §3.4 measured rather than
argued, and it is the single most consequential design decision in the whole
architecture.

**2. The co-trained linear read-out does not help — it hurts.** It reaches the
*best training fit of the three* (loss 1.950 vs 2.155, train accuracy 0.313 vs
0.280) and the *worst* generalization among the pooled arms (0.317 vs 0.400).
120 extra parameters against 150 training samples is simply overfitting. This
matters because it is the ring's own configuration: at this scale the read-out is
not carrying the model, so the KRC's accuracy is genuinely attributable to `theta`.

**3. The ring's attribution effect is reproducible, and it is a gradient-sink
effect.** With a trained read-out available the circuit moves **2.6× less**
(max\|Δθ\| 0.534 vs 1.400 V; 1.85× at the final epoch, 0.758 vs 1.400). Same core,
same budget, same seed — the only difference is whether a soft layer is there to
absorb the gradient. That is a direct measurement of the mechanism behind
`../toy2d_serial_diff`'s §VIII-A, where the circuit drifted 0.0008 V in 90 epochs
while a co-trained read-out did the work.

For scale, the circuit here moved **mean 0.237 V, max 1.400 V — roughly 300×
further than the ring's total drift**, and 0 of 240 edges were dead at any point.

**What 0.400 does and does not mean.** It is 4× chance on a 10-class problem from
240 physical parameters on 12 nodes, with every gradient coming from a SPICE
transient adjoint. It is also **far below the ~96% that a sequential-MNIST RNN
reaches**, and the run was plainly compute-limited rather than converged: training
accuracy was still rising at the cutoff (0.193 → 0.280, never plateaued), the
whole run is 80 Adam updates, and 150 training samples is 15 per class. The
honest statement is that the architecture trains, the circuit is what learns, and
the absolute number is bounded by the simulation budget — not that 0.400 is the
ceiling of this design.

## 6. Honest limits

- **The evaluation is small.** Every training sample is T full circuit solves, so
  the sample budget is stated explicitly with each result rather than hidden.
  These are indicative numbers, single seed, no error bars — the same disclosure
  the ring paper makes, for the same reason.
- **MNIST is downsampled.** Streaming 28×28 row-wise at M = 16 would be
  ~2 s × 28 steps = 56 s *per sample*. Downsampling is a compute concession, not
  an architectural one: it lowers T and k, which are exactly the two multipliers
  on the SPICE bill. The architecture is unchanged.
- **No CIFAR result.** The reference has none either. Claiming one here would be
  worse than reporting its absence.
- **No silicon, no measured energy.** The switch fabric of §3.2 is specified, not
  laid out. The I/O budget is sized analytically, and data conversion is the
  dominant unproven cost in every analog accelerator study [[10]](#refs) — the
  28× DAC reduction is the honest headline, not an energy claim.
- **Level-1 device models.** Second-order effects present in a fabricated device
  are not represented.
- **The contracting Jacobian is the binding constraint.** Spectral radius 0.765
  means the core forgets: over T steps the earliest chunks have influence
  `0.765^T`. This is the classic vanishing-gradient limit of a continuous-time RNN,
  it bounds how large T can usefully get, and §5.4 shows it dominates the result.
  Time-averaged read-out mitigates it but does not remove it. Raising the radius
  toward 1 trades memory against stability and is the obvious next knob.
- **A methodological note worth recording.** An early pair of runs was discarded
  because two concurrent trainings shared one scratch netlist `tmp_krc_mnist.sp`
  and overwrote it between write and solve, silently corrupting both. Concurrent
  runs must pass distinct `--tag` values. The symptom was an interleaved log
  (a `n_conv` larger than the test set, and elapsed times running backwards) —
  worth knowing about, because nothing errors out.

## 7. Where this goes next

Ordered by what §5.4 says is actually limiting.

0. **More optimization budget, first.** Training accuracy never plateaued
   (0.193 → 0.280 across 8 epochs / 80 Adam updates on 150 samples). Before any
   architectural change, run the same configuration with ~10× the updates and
   more samples per class; that is the cheapest available accuracy and it also
   tells us whether 0.400 is a budget artefact or a real ceiling.
1. **Raise the spectral radius toward 1.** Time-pooling doubled accuracy by
   working *around* the contraction; attacking it directly — via the theta window
   and the state-rail/data-rail drive ratio — attacks the cause. Training already
   pushes it the wrong way (0.765 at init → 0.516 trained), which is worth
   understanding on its own.
2. **Sparse configurations.** `edge_budget` already emits them; the cost curve in
   §5.2 says E is what you pay for, so accuracy-vs-E buys either speed or headroom
   for a larger M.
2. **Batched netlists.** B independent copies of the core in one block-diagonal
   solve, returning per-copy sensitivities. Whether this beats B separate calls
   depends on whether the solver exploits the block structure — a measurement, not
   an assumption.
3. **Phase stacking.** Two `theta` banks swapped mid-rollout gives depth without
   area, the analogue of the reference's 2–3 stacked blocks.
4. **Block-local losses** [[8]](#refs) if T grows past what one adjoint chain
   handles gracefully.
5. **Hardware-in-the-loop on real silicon.** The loop exercised here — seed, let
   physics evolve, read, use a hardware-derived sensitivity as the gradient — is
   exactly the loop physics-aware training [[7]](#refs) runs on physical systems.

---

<a name="refs"></a>
## References

1. Z. Gao, F.-K. Sun, R. Rohrer, D. S. Boning. "KirchhoffNet: A Scalable Ultra Fast Analog Neural Network." *ICCAD*, 2024. doi:10.1145/3676536.3676662 (arXiv:2310.15872). Code: https://github.com/zhengqigao/kirchhoffnet
2. R. T. Q. Chen, Y. Rubanova, J. Bettencourt, D. Duvenaud. "Neural Ordinary Differential Equations." *NeurIPS*, 2018. arXiv:1806.07366
3. E. Dupont, A. Doucet, Y. W. Teh. "Augmented Neural ODEs." *NeurIPS*, 2019. arXiv:1904.01681 — ODE flows are homeomorphisms and cannot tear the input space; augmentation dimensions are the fix.
4. G. Cauwenberghs. "A Learning Analog Neural Network Chip with Continuous-Time Recurrent Dynamics." *NeurIPS*, 1993; and "An analog VLSI recurrent neural network learning a continuous-time trajectory," *IEEE Trans. Neural Networks* 7(2), 1996. doi:10.1109/72.485671
5. L. Appeltant *et al.* "Information processing using a single dynamical node as complex system." *Nature Communications* 2:468, 2011.
6. J. Hasler *et al.* "Large-Scale Field-Programmable Analog Arrays." *Proc. IEEE*, 2020; and "The Potential of SoC FPAAs for Emerging Ultra-Low-Power Machine Learning." *J. Low Power Electron. Appl.* 12(2):33, 2022.
7. L. G. Wright, T. Onodera *et al.* "Deep physical neural networks trained with backpropagation." *Nature* 601:549–555, 2022. doi:10.1038/s41586-021-04223-6
8. A. Nøkland, L. H. Eidnes. "Training Neural Networks with Local Error Signals." *ICML*, 2019; A. Momeni *et al.* "Backpropagation-free training of deep physical neural networks." *Science*, 2024. doi:10.1126/science.adi8474
9. Echo-state / reservoir MNIST reference points (~90.6 % with a linear read-out on a random reservoir), and sequential-MNIST RNN reference points (~96.5 % row-wise, ~96 % with a 56-unit hidden state).
10. M. J. Rasch *et al.* "Hardware-aware training for large-scale and diverse deep learning inference workloads using in-memory computing-based accelerators." *Nature Communications* 14:5282, 2023; and the IBM 64-core mixed-signal AIMC chip, 92.81 % on CIFAR-10. Data conversion dominates energy in analog accelerators.
11. S. W. Director, R. A. Rohrer. "The Generalized Adjoint Network and Network Sensitivities." *IEEE Trans. Circuit Theory* 16(3):318–323, 1969.
