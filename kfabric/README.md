# kfabric — the Kirchhoff Recurrent Core (KRC)

A **small, fixed analog core invoked many times** over a streamed input, trained
end-to-end through the SPICE transient adjoint with **exact backpropagation
through time** — and no trained software read-out anywhere in the pipeline.

This is the answer to "how does the serial diff-pair ring in `../toy2d_serial_diff`
become reconfigurable and reach MNIST/CIFAR scale". The full argument, the
literature, and the measured results are in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## The one-line idea

The reference ICCAD KirchhoffNet maps **one pixel to one circuit node**, so
`N_nodes = input_dim` — 834 nodes / 920,272 params for MNIST, 3,122 nodes /
12,324,108 params for CIFAR-10. That is unsimulable in SPICE and, in software, is
just their PyTorch ODE again.

KRC **decouples circuit size from input dimension**. A core of `M` state nodes is
re-used for `T` steps, carrying state on a sample-and-hold between steps. Capacity
comes from **time and configuration**, not from simultaneous node count.

```
         held state  VS1..VSM ->  s1..sM --.
                                            >-[ theta-gated NMOS edges ]-> n1..nM (caps)
         data chunk  VR1..VRk ->  r1..rk --'
                                                   |
   x_0 -> [core] -> v_1 -> [core] -> v_2 -> ... -> v_T -> read last C taps -> class
           ^ same theta, same silicon, T times
```

**The state enters through voltage sources, not `.IC`.** That is what makes exact
BPTT possible: one adjoint call returns the parameter sensitivity `dv/dtheta`
*and* the state-transfer Jacobian `dv_{t+1}/dv_t`.

## Run it

Prereqs: `numpy`, `scikit-learn`, `matplotlib`, `pillow`, the simulator at
`D:\Simulator\circuit_simulator with level3\src`, and (for MNIST) the cached
`~/.keras/datasets/mnist.npz`. Run everything from inside `kfabric/`.

```powershell
cd D:\Kirchoffnet\kirchoff_claude\kfabric

# the mapper -- no simulator needed. Reproduces the reference ICCAD counts exactly.
python core_spec.py --compare

# GATE 1: does the adjoint return the state-transfer Jacobian? (decides everything)
python smoke_test.py --m 8 --k 2

# GATE 2: what does a core step actually cost? Picks M and the schedule.
python scale_probe.py --ms 6,8,12,16 --k 8

# GATE 3: is the BPTT gradient right? (adjoint vs central finite differences)
python check_grad.py --T 4 --m 8 --k 4

# train + plot
python mnist_stream.py                       # inspect the streamed digits
python train_krc.py --task mnist --side 8 --m 12 --n-train 150 --n-test 60 --epochs 8 `
                    --readout mean --tag mnist_mean
python plot_krc.py  --task mnist_mean
```

**Always pass a distinct `--tag` when running two trainings at once.** Each run
writes a scratch netlist `tmp_krc_<tag>.sp` and re-reads it to solve; two runs
sharing a tag will overwrite each other's netlist between the write and the solve
and silently corrupt *both* results (they also share `<tag>_krc_log.csv` and
`<tag>_krc_best.json`). `--tag` is the only thing separating concurrent runs.

Swap `--task mnist` for `twomoon`, `circle`, or `2spirals` to run the 2-D sets
from `../toy2d_serial_diff/dataset.py` through the same core.

## Files

| File | Role |
|---|---|
| `netlist_core.py` | Emits the M-node core. **Why state enters as voltage sources, not `.IC`** — read this docstring first. |
| `core_spec.py` | The dataset-agnostic mapper `(input shape, classes, budget) -> config`, plus the operating-point window. `--compare` checks our reading of the reference topology. |
| `mnist_stream.py` | Real MNIST from the cached npz, downsampled and cut into `T` row-chunks. |
| `recurrent.py` | `rollout` (T-step forward with tape) and `bptt` (exact gradient). The fixed, **diagonal**, untrained read-out lives here. |
| `train_krc.py` | Per-minibatch Adam on the edge thetas, convergence guard, logging. |
| `smoke_test.py` | Gate 1 — convergence, no dead edges, and the Jacobian. |
| `scale_probe.py` | Gate 2 — measured SPICE cost vs core size. |
| `check_grad.py` | Gate 3 — adjoint BPTT vs finite differences. |
| `plot_krc.py` | The six-panel results figure. |

Reused verbatim from `../toy2d_serial_diff/`: `simulator_api.py`, `model.py`
(only `Adam`), `dataset.py`.

Artifacts land in `results/`: `<task>_krc_log.csv`, `<task>_krc_best.json`
(`theta`, `theta0`, `mu`, `sd`, geometry), `<task>_krc_hist.json`, and
`<task>_krc_results.png`.

## What to look at in the output

`max|dtheta|` in the training log. In `../toy2d_serial_diff` the circuit
parameters moved **0.0008 V over 90 epochs** while a co-trained linear read-out
supplied the accuracy — the honest finding of that paper's section VIII-A. Here
there is no read-out to hide behind, so that number is the direct measure of
whether the *circuit* is learning.
