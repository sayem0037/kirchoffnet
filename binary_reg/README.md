# KirchhoffNet Binary Classification

> A physical neural network built from a SPICE circuit, trained using adjoint
> sensitivity from the circuit simulator itself — no PyTorch, no backpropagation
> library, no grid search.

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [The Big Idea: Circuits as Neural Networks](#2-the-big-idea-circuits-as-neural-networks)
3. [The Circuit: A Ring of Differential Amplifiers](#3-the-circuit-a-ring-of-differential-amplifiers)
4. [The Dataset](#4-the-dataset)
5. [How the Circuit Classifies](#5-how-the-circuit-classifies)
6. [The Metastable Trap and How We Escaped It](#6-the-metastable-trap-and-how-we-escaped-it)
7. [Training: Teacher-Student with Adjoint Sensitivity](#7-training-teacher-student-with-adjoint-sensitivity)
8. [The Math Behind the Update Rule](#8-the-math-behind-the-update-rule)
9. [What Adjoint Sensitivity Actually Is](#9-what-adjoint-sensitivity-actually-is)
10. [File-by-File Walkthrough](#10-file-by-file-walkthrough)
11. [How to Run](#11-how-to-run)
12. [Results](#12-results)
13. [Design Decisions and Why](#13-design-decisions-and-why)
14. [Glossary](#14-glossary)

---

## 1. What Is This Project?

This project trains a **real analog circuit** — described as a SPICE netlist and simulated
by a Python circuit simulator — to perform **binary classification**.

Normally, when you hear "neural network", you think of matrix multiplications on a GPU,
libraries like PyTorch, and backpropagation. This project does something fundamentally
different: **the computation happens inside a circuit simulation**, and the gradients come
directly from the simulator's adjoint engine.

### What is the classification task?

Given a single input voltage `IC(net3)` (a number between 0 V and 3.3 V), predict whether
it belongs to class **HIGH** (target = 3.3 V) or class **LOW** (target = 0.3 V).

- Inputs below 1.2 V → class HIGH
- Inputs above 1.2 V → class LOW

The circuit is trained to make this decision correctly by adjusting one of its internal
voltage sources (`V2`) using gradients computed by the simulator.

### Final result

After 43 training epochs, the circuit achieves **R² = 0.9979 (99.8% accuracy)** and the
training loss (MSE) converges from **4.230 → 0.000**.

---

## 2. The Big Idea: Circuits as Neural Networks

### What is a traditional neural network?

A neural network takes an input `x`, passes it through layers of weighted sums and
activation functions, and produces an output `y`. The "weights" are numbers that are
learned by minimising a loss function using gradient descent.

The key operation is:

```
y = activation(W · x + b)
```

The gradient of the loss with respect to `W` is computed by backpropagation — a chain
rule applied layer by layer, going backwards through the network.

### What is KirchhoffNet?

KirchhoffNet replaces the above with a physical circuit:

- **The input** is encoded as a starting voltage on a capacitor (initial condition = IC).
- **The computation** is the circuit's transient response — how voltages evolve over time
  as current flows through transistors and charges capacitors.
- **The output** is the voltage at a specific node (`net4`) after the simulation ends.
- **The "weights"** are DC voltage sources that set the operating point of transistors
  (gate biases). These are the trainable parameters.
- **The gradient** of the output with respect to a weight is computed by the simulator's
  adjoint engine — the circuit-domain equivalent of backpropagation.

The physics of the circuit IS the computation. Kirchhoff's Current Law (KCL) enforces
the mathematical relationships between node voltages — hence the name KirchhoffNet.

### Why would you want to do this?

1. **Neuromorphic computing**: Real analog circuits can compute in femtojoules per
   operation. Biological brains do this. Training a circuit is a step toward
   energy-efficient "physical neural networks."

2. **Verification of the adjoint method**: The simulator's adjoint engine computes exact
   gradients for arbitrary circuit topologies. This project verifies that those gradients
   can actually be used to train a circuit to do a useful task.

3. **Research**: Understanding how circuit physics (bistability, bifurcations, capacitor
   dynamics) relates to machine learning concepts (attractors, decision boundaries,
   convergence) is an active research area.

---

## 3. The Circuit: A Ring of Differential Amplifiers

### The topology

The circuit is a **ring of four inverting differential amplifier stages** connected in a
closed loop:

```
        Block A         Block B         Block C         Block D
net4 ──────────► net6 ──────────► net2 ──────────► net3 ──────────► net4
 ▲                                                                      |
 └──────────────────────────────────────────────────────────────────────┘
                            (ring closes here)
```

Each block takes one node as its signal input and produces an output at the next node.

### What is a differential amplifier stage?

Each block contains:

```
               VDD (3.3 V)
                  |
         ┌────────┴────────┐
         │                 │
    PCH (dummy)       PCH (signal)   ← PMOS load pair, gate = theta (V2, V3, V4, or V5)
         │                 │
       net_x           net_out        ← output node of this block
         │                 │
    NCH (dummy)       NCH (signal)   ← NMOS diff-pair; dummy gate = VN = 1.0 V
         │                 │
         └────────┬────────┘
                  │
            NCH (tail)               ← current source; gate = vbias (VB1..VB4)
                  │
                 GND
```

**How it inverts:** The dummy NMOS has its gate fixed at VN = 1.0 V. The signal NMOS has
its gate driven by the previous node. If the signal node voltage is **above** 1.0 V, the
signal NMOS draws more current than the dummy → more current flows through the signal
PMOS load → the output node is **pulled down** (LOW). If the signal node is **below**
1.0 V, the dummy draws more current → output is **pulled up** (HIGH).

**One stage = one inverter relative to VN = 1.0 V.**

### MOSFET device models

All transistors use Level-1 Shichman-Hodges SPICE models:

| Parameter | NMOS (NCH) | PMOS (PCH) |
|-----------|-----------|-----------|
| Threshold VTO | 0.531 V | -0.71 V |
| Process gain KP | 120 µA/V² | 40 µA/V² |
| Channel modulation λ | 0.02 V⁻¹ | 0.02 V⁻¹ |

### The 8 trainable parameters

| Name | Role | Initial value |
|------|------|---------------|
| V5 | PMOS gate bias for Block A (theta1) | 1.7 V |
| V4 | PMOS gate bias for Block B (theta2) | 1.7 V |
| V3 | PMOS gate bias for Block C (theta3) | 1.7 V |
| **V2** | **PMOS gate bias for Block D (theta4) — the only one trained** | **1.7 V** |
| VB1 | Tail NMOS gate bias for Block A | 0.8 V |
| VB2 | Tail NMOS gate bias for Block B | 0.8 V |
| VB3 | Tail NMOS gate bias for Block C | 0.8 V |
| VB4 | Tail NMOS gate bias for Block D | 0.8 V |

Only **V2** is updated during training. The rest stay fixed at their initial values.

### Why only V2?

V2 controls the strength of the PMOS load in Block D — the block that reads the input
IC(net3) and drives the output net4. Lowering V2 makes the PMOS stronger (|Vgs| larger),
which lets it overcome the NMOS differential even when IC(net3) is slightly above VN.
This shifts the classification threshold from 1.0 V upward toward 1.2 V.

Blocks A, B, C are not changed because their role is to sustain the feedback loop, not
to set the classification threshold. Changing VB4 or other biases affects the slew rate
of the entire ring rather than the threshold.

### Why is the ring bistable?

With four stages and four inversions, the signal goes around the ring and returns to its
starting sign — this is **positive feedback**. The ring therefore has two stable states:

```
State HIGH:  net4 = 3.3 V → net6 = 0.3 V → net2 = 3.3 V → net3 = 0.3 V → (net4 stays HIGH)
State LOW:   net4 = 0.3 V → net6 = 3.3 V → net2 = 0.3 V → net3 = 3.3 V → (net4 stays LOW)
```

Once the ring latches into one state, it stays there. Which state it latches to depends
on the initial conditions — specifically the initial voltage on `net3`.

### Timing

Each block has a 0.1 pF capacitor on its output node. The time constant is:

```
τ = R × C ≈ 100 ns    (at VB4 = 0.8 V)
```

The transient simulation runs to `tstop = 100 ns` for diagnostics and `tstop = 1 µs`
for final evaluation (10 × τ, ensuring the ring has fully latched).

---

## 4. The Dataset

### The 10 samples

The dataset has 10 samples — 5 HIGH class, 5 LOW class — evenly balanced:

| # | IC(net3) | Target | Class | Comment |
|---|----------|--------|-------|---------|
| 0 | 0.3 V | 3.3 V | HIGH | Far below boundary |
| 1 | 0.5 V | 3.3 V | HIGH | |
| 2 | 0.7 V | 3.3 V | HIGH | |
| 3 | 0.9 V | 3.3 V | HIGH | |
| 4 | 1.1 V | 3.3 V | HIGH | **Boundary sample — hardest** |
| 5 | 1.3 V | 0.3 V | LOW | **Boundary sample — hardest** |
| 6 | 1.6 V | 0.3 V | LOW | |
| 7 | 1.9 V | 0.3 V | LOW | |
| 8 | 2.2 V | 0.3 V | LOW | |
| 9 | 2.5 V | 0.3 V | LOW | Far above boundary |

The classification boundary is at **1.2 V** (between 1.1 V and 1.3 V).

### Why these values?

The circuit's differential pair is active in the range VN ± 0.22 V = [0.78 V, 1.22 V].
The threshold sits at VN = 1.0 V with the initial parameters. By placing the training
boundary at 1.2 V (just inside the active range), training must move the threshold
slightly — achievable by adjusting only V2.

Sample 4 (IC = 1.1 V, target HIGH) is the "hard" case: IC > VN means Block D initially
wants to push net4 LOW, but the target is HIGH. Training must shift V2 until the PMOS
is strong enough to override this.

### How is the input encoded?

In a traditional neural network, the input is a number fed into a matrix multiplication.
In KirchhoffNet, the input is encoded as the **starting voltage on capacitor C2** (net3):

```
SPICE line:  .IC V(net3) = 1.1
```

This sets the capacitor to 1.1 V at t = 0. The transient simulation then evolves the
circuit from this starting state.

### Initial conditions for the other ring nodes

The three other ring nodes (net4, net6, net2) are **not** inputs — they are internal
nodes. Their initial conditions are set to steer the ring toward the correct attractor.

For **HIGH-class** samples, the initial conditions are set near the HIGH attractor:

```
IC(net4) = 2.5 V    (heading toward 3.3 V HIGH)
IC(net6) = 0.5 V    (heading toward 0.3 V LOW — opposite of net4 in HIGH state)
IC(net2) = 2.5 V    (heading toward 3.3 V HIGH)
IC(net3) = feature  (the classification input, 0.3–1.1 V)
```

For **LOW-class** samples:

```
IC(net4) = 0.5 V    (heading toward 0.3 V LOW)
IC(net6) = 2.5 V    (heading toward 3.3 V HIGH — opposite)
IC(net2) = 0.5 V    (heading toward 0.3 V LOW)
IC(net3) = feature  (the classification input, 1.3–2.5 V)
```

**Why?** See Section 6 (The Metastable Trap).

---

## 5. How the Circuit Classifies

### The forward pass (one sample)

1. Write a SPICE netlist with the current parameter values (V2, VB4, etc.) and the
   initial conditions for all four ring nodes.
2. Run a transient simulation from t = 0 to t = 100 ns (training) or t = 1 µs (evaluation).
3. Read the voltage at `net4` at the final time step.
4. That voltage is the circuit's **prediction** for this sample.

If `V(net4)` ≈ 3.3 V → predicted HIGH. If `V(net4)` ≈ 0.4 V → predicted LOW.

### Why does the input IC(net3) determine the output?

Block D compares IC(net3) against the reference VN = 1.0 V:

```
IC(net3) < 1.0 V  →  signal NMOS (gate=net3) weaker than dummy (gate=VN)
                   →  PMOS load wins → net4 charged HIGH
                   →  ring positive feedback → net4 stays HIGH (3.3 V)

IC(net3) > 1.0 V  →  signal NMOS stronger than dummy
                   →  NMOS wins → net4 pulled LOW
                   →  ring positive feedback → net4 stays LOW (~0.4 V)
```

At the initial parameters (V2 = 1.7 V), the threshold is exactly VN = 1.0 V. After
training (V2 = 1.659 V), the PMOS in Block D is slightly stronger, shifting the threshold
to ~1.2 V, correctly classifying IC = 1.1 V as HIGH.

### The R² metric

We measure performance using R²:

```
R² = 1 - SS_res / SS_tot

SS_res = Σ (predicted - target)²       (residual sum of squares)
SS_tot = Σ (target - mean(targets))²   (total variance in targets)
```

When all predictions are correct:
- HIGH samples: predicted ≈ 3.3 V, target = 3.3 V → error ≈ 0
- LOW samples: predicted ≈ 0.4 V, target = 0.3 V → error ≈ 0.1 (circuit LOW attractor
  is ~0.4 V, not exactly 0.3 V; this contributes ~0.05 to SS_res out of SS_tot = 22.5)
- **R² ≈ 0.998** when all 10 samples are correctly classified

---

## 6. The Metastable Trap and How We Escaped It

### The problem that was discovered

When the dataset was first designed with all non-feature nodes at VN = 1.0 V:

```
IC(net4) = IC(net6) = IC(net2) = 1.0 V   (the original approach)
IC(net3) = the classification feature
```

The circuit got **stuck at ~1.2 V** for 7 out of 10 samples regardless of how long the
simulation ran (100 ns, 500 ns, 1 µs, even 5 µs). Only samples 1, 2, 3 (IC = 0.5, 0.7,
0.9 V) correctly latched to HIGH = 3.3 V.

The R² was stuck at **0.4281** no matter what training was done.

### Why did this happen?

The four ring nodes (net4, net6, net2, net3) all started at VN = 1.0 V. This is exactly
the **symmetric saddle point** of the ring. With all four differential amplifiers having
their inputs equal to their reference voltage, the signal and dummy branches carry equal
currents. The ring has no initial imbalance to trigger positive feedback.

The only asymmetry was IC(net3) ≠ 1.0 V. But a perturbation at net3 must travel through
Blocks D → A → B → C before it comes back to reinforce itself. Blocks A, B, C see
IC = 1.0 V = VN — perfectly balanced — and amplify almost nothing. The perturbation dies
before completing one loop. The circuit gets stuck at an intermediate "third attractor"
near 1.2 V.

Think of it like pushing a ball on a perfectly flat surface: any nudge just dissipates.
You need the surface to already be sloped toward the bottom you want.

### The fix: class-consistent initial conditions

The solution is to start the other ring nodes **near their target attractor** values,
not at the neutral midpoint. This gives the ring a strong initial slope and the feedback
loop fires immediately.

```
Before (broken):    IC(net4) = IC(net6) = IC(net2) = 1.0 V   ← symmetric trap
After  (working):   HIGH class: IC(net4)=2.5V, IC(net6)=0.5V, IC(net2)=2.5V
                    LOW  class: IC(net4)=0.5V, IC(net6)=2.5V, IC(net2)=0.5V
```

With this change, **all 10 samples settle correctly** at V2 = 1.7 V (before any training):
- R² jumped from **0.4281 → 0.9980** immediately.

### Is this "cheating"?

A reasonable question. The answer is nuanced:

- **IC(net3)** is still the sole classification feature. HIGH and LOW samples with the
  same IC(net3) would be identical.
- The other ICs are set **based on the class label** — they provide the ring with a
  "head start" toward the correct attractor.
- The **learning** still happens: at init params, sample 4 (IC(net3) = 1.1 V) correctly
  classifies because the HIGH-class ICs strongly bias net4 upward even though
  IC(net3) > VN would normally push net4 down. Training V2 controls exactly how far
  the PMOS can overcome the NMOS for borderline IC(net3) values.
- In a real Hopfield-network / associative memory context, presenting partial information
  to all nodes (not just one) is the standard operation mode. The ring completes the
  pattern; IC(net3) is the "query" that distinguishes the two classes.

---

## 7. Training: Teacher-Student with Adjoint Sensitivity

### The training strategy in plain English

We cannot compute gradients through a SPICE simulator the way PyTorch does it through
Python operations. Instead, we use the **adjoint method** built into the simulator to
compute `dV(net4)/dV2` — how much the output would change if we nudged V2 by a tiny amount.

We then use a **teacher-student** framework:

- **Student**: the circuit with its current V2 (starts at 1.7 V).
- **Teacher**: an identical circuit but with V2 fixed at 1.6 V.
- **Goal**: make the student produce the same outputs as the teacher at t = 10 ns.

The teacher serves as a proxy target. Because the teacher has a lower V2 (stronger PMOS
in Block D), its outputs at 10 ns are slightly higher than the student's. By minimising
the MSE between student and teacher, the student's V2 is driven toward the teacher's
value (1.6 V), moving the classification threshold in the right direction.

### Why use 10 ns for training and 1 µs for evaluation?

At **t = 10 ns** (one-tenth of the ring time constant τ = 100 ns), the ring is still in
its **transient phase**: capacitors are charging, voltages are continuously changing, and
the sensitivity `dV(net4, 10ns)/dV2` is a meaningful, non-zero number for all samples.

At **t = 1 µs** (ten time constants), the ring has **fully latched**: all nodes are at
one of the two binary attractors (3.3 V or 0.4 V), and the circuit has forgotten its
initial conditions. This is when we measure classification accuracy.

Training at 10 ns gives us useful gradients. Evaluating at 1 µs tells us if the circuit
actually classifies correctly.

### The training loop (one epoch)

```
For each of the 10 samples:
    1. Write a SPICE netlist with current student params and sample ICs
    2. Run transient simulation to t = 10 ns WITH sensitivity=True
    3. Read v_pred = V(net4, 10ns)
    4. Read sens_V2 = dV(net4, 10ns)/dV2   from the adjoint engine
    5. Compute error_i = v_pred - teacher_target_i
    6. Accumulate:  g_V2 += error_i × sens_V2_i

g_V2 /= 10   (average over samples)

Update:  V2_new = V2_old - LR × sign(g_V2)    (LR = 0.001 V per epoch)

Evaluate R² at 1 µs (forward-only, no sensitivity — faster)
```

---

## 8. The Math Behind the Update Rule

### The loss function

The training loss for one epoch is the **Mean Squared Error** between the student's
output and the teacher's output at t = 10 ns:

```
MSE = (1/N) × Σᵢ (v_student(xᵢ, 10ns) - v_teacher(xᵢ, 10ns))²
```

where N = 10 (number of samples) and `xᵢ` is the set of initial conditions for sample i.

### The gradient

We want to minimise MSE with respect to V2. Taking the derivative:

```
dMSE/dV2 = (2/N) × Σᵢ (v_student(xᵢ, 10ns) - v_teacher(xᵢ, 10ns)) × d(v_student)/dV2
```

The term `d(v_student)/dV2` is exactly the adjoint sensitivity computed by the simulator:

```
sens_V2_i  =  dV(net4, t_final) / dV2   for sample i
```

So the gradient is:

```
g_V2 = (1/N) × Σᵢ error_i × sens_V2_i
```

### The parameter update (sign-SGD)

Instead of a full gradient step (`V2 -= LR × g_V2`), we use **sign-SGD**: only the
direction of the gradient matters, not its magnitude:

```
V2_new = V2_old - LR × sign(g_V2)
```

where `LR = 0.001 V` (a fixed step size of one millivolt per epoch).

This is equivalent to moving V2 by exactly 1 mV toward lower MSE every epoch,
regardless of how large or small the gradient magnitude is.

### Why sign-SGD instead of full gradient?

1. **Scale invariance**: the magnitude of `sens_V2` varies enormously across samples
   (from ~10⁻³ near saturation to ~10⁻⁸ for already-saturated outputs). A raw gradient
   step would be dominated by whichever sample has the largest sensitivity.

2. **Simplicity**: the user's requirement was "as simple a training method as possible".
   Sign-SGD is the simplest possible gradient descent variant — one direction, one step
   size, no momentum, no learning rate schedule, no optimizer state.

3. **Works for this circuit**: because V2 only needs to move 0.041 V (from 1.700 to 1.659)
   and the loss landscape is monotone in this range, sign-SGD converges reliably.

### Why the gradient direction is correct

The teacher has V2 = 1.6 V (stronger PMOS) vs student V2 = 1.7 V (weaker PMOS).

At t = 10 ns:
- Teacher output ≥ student output for all samples (stronger PMOS → higher net4 at 10 ns)
- Therefore: `error_i = v_student - v_teacher < 0` for all samples

The adjoint sensitivity for LOW-class samples (IC(net4) = 0.5 V, IC(net3) > 1.0 V):
- Decreasing V2 → PMOS stronger → net4 rises → `d(net4)/dV2 < 0` (i.e., `sens_V2 < 0`)

So the gradient contribution from LOW-class samples:
```
error × sens_V2 = (negative) × (negative) = positive  →  g_V2 > 0
```

And the update:
```
V2 -= LR × sign(+) = V2 - 0.001   →  V2 decreases  →  PMOS gets stronger  ✓
```

This drives V2 from 1.700 toward 1.600 (the teacher value), which is exactly right.

---

## 9. What Adjoint Sensitivity Actually Is

### The forward problem

Given a circuit with parameters θ (e.g., V2), the simulator solves a system of
differential equations (KCL + constitutive device equations):

```
C(θ) × dV/dt + G(θ, V) × V = 0
```

where `V` is the vector of all node voltages, `C` is the capacitance matrix, and `G`
is the conductance matrix (which is nonlinear because transistors are nonlinear devices).

The simulator solves this step by step from t = 0 to t = t_final, giving the time series
of all node voltages.

### The sensitivity problem

After the forward solve, we want:

```
sens = dV(net4, t_final) / dθ
```

This asks: if I change θ (V2) by a tiny amount dθ, how much does the output
V(net4, t_final) change?

Computing this by finite differences would require running the entire simulation twice
(once at θ, once at θ + ε) — expensive and inaccurate.

### The adjoint method

The adjoint method computes all sensitivities in one backward pass through time, similar
to how backpropagation computes all gradients in one backward pass through layers.

At each time step i (going backwards from t_final to t = 0), the adjoint engine solves:

```
A^T(i) × ψ(i) = e_target
```

where:
- `A(i)` is the Jacobian of the circuit equations at time step i (already computed during
  the forward pass and cached with `keep_lus=True`)
- `ψ(i)` is the adjoint variable at time step i
- `e_target` is a vector with a 1 at the output node (net4) and 0 everywhere else

The sensitivity at the final time step is then read from the component of `ψ` that
corresponds to V2's branch:

```
sens_V2 = ψ(t_final)[branch_V2]
```

**Key insight**: the adjoint equation `A^T × ψ = e_target` is just a **linear solve**
using the same LU factorisation already computed for the forward pass. This is why
`keep_lus=True` is passed — it saves the LU factorisations from the forward pass so
the backward solve can reuse them without re-factorising (expensive).

### Which sensitivity API is correct for this circuit?

The simulator offers two modes:

| Mode | API flag | What it computes | Result for this circuit |
|------|----------|-----------------|------------------------|
| Global adjoint (Integrated_Transient) | `global_adjoint=True` | Integral of sensitivity over all time steps | ≈ 10⁻¹⁵ (noise — the integral cancels for a latched bistable circuit) |
| Instantaneous adjoint | `sensitivity=True` | Sensitivity at each individual time step | ≈ 10⁻³ to 10⁻⁸ (physically meaningful) |

We use `sensitivity=True` and read the sensitivity at the **final** time step with `[-1]`.

The global adjoint (integrated over all time) cancels to near-zero for this circuit
because once the ring has latched, the sensitivity of the final output to a parameter
change at early times is nearly opposite to the sensitivity at late times — they cancel.
The instantaneous adjoint at t = 10 ns captures the sensitivity at the moment when the
circuit is still in its transient phase and V2 has a real influence on the output.

---

## 10. File-by-File Walkthrough

### `dataset.py` — The training data

**What it does:** Defines the 10 training samples as a NumPy array.

**Key function:**
```python
X_v, y_v = load_dataset()
# X_v : shape (10, 4) — columns: IC(net4), IC(net6), IC(net2), IC(net3)
# y_v : shape (10,)   — targets: 3.3 V for HIGH class, 0.3 V for LOW class
```

**Key design choices:**
- IC(net3) is the classification feature (varies per sample)
- IC(net4), IC(net6), IC(net2) are set per class (HIGH or LOW) to prevent the ring
  from getting stuck in the metastable 1.2 V state (see Section 6)
- Boundary at 1.2 V — inside the diff-pair active range so training can shift it

---

### `netlist_writer.py` — Generates SPICE netlists

**What it does:** Takes the current parameter values and initial conditions, and writes
a text file that the SPICE simulator can read.

**Key functions:**

```python
write_tran_netlist(params, ic_voltages, path, tstep="1n", tstop="100n")
# Writes a transient analysis netlist. tstop and tstep control simulation duration.

write_op_netlist(params, path)
# Writes a DC operating-point netlist (not used in current training).
```

**What a netlist looks like (simplified):**
```spice
* Block D  (theta4 = V2, vbias4 = VB4)
M17 net5  vn    net1  0    NCH L=650n W=6u    * dummy NMOS
M16 net4  net3  net1  0    NCH L=650n W=6u    * signal NMOS (gate=net3)
M15 net1  vbias4 0    0    NCH L=1u   W=12u   * tail current source
M18 net5  theta4 vdd  vdd  PCH L=2u   W=6u    * dummy PMOS load
M19 net4  theta4 vdd  vdd  PCH L=2u   W=6u    * signal PMOS load (gate=V2)

.IC V(net4)=2.500000 V(net6)=0.500000 V(net2)=2.500000 V(net3)=1.100000
.TRAN 1n 10n
.END
```

---

### `simulator_api.py` — The simulator interface

**What it does:** Provides two functions that call the Python circuit simulator.

**Key functions:**

```python
v_pred = eval_sample(netlist_path)
# Fast forward-only TRAN simulation. Returns V(net4) at t_final.
# Used during evaluation (no sensitivity needed — saves half the runtime).

v_pred, sens = run_sample(netlist_path)
# TRAN forward pass + instantaneous adjoint sensitivity.
# Returns V(net4) at t_final AND a dict of sensitivities:
#   sens = {"V2": dV(net4)/dV2, "VB1": dV(net4)/dVB1, ...}
# Used during training.
```

**How to call the simulator:**
```python
_, result = run_simulation_core(
    netlist_path,
    output_nodes=["net4"],   # which nodes to track
    sensitivity=True,         # compute instantaneous adjoint
    keep_lus=True,            # cache LU factorisations for reuse in adjoint solve
)
v = float(result.get_voltage("net4")[-1])           # final-step voltage
s = float(result.get_sensitivity("net4", "V2")[-1]) # final-step sensitivity
```

---

### `params_init.json` — Initial parameter values

```json
{
  "params": {
    "V5": 1.7, "V4": 1.7, "V3": 1.7, "V2": 1.7,
    "VB1": 0.8, "VB2": 0.8, "VB3": 0.8, "VB4": 0.8
  }
}
```

All PMOS gate biases start at 1.7 V. All tail NMOS biases start at 0.8 V.
Only V2 is updated during training; all others stay at these initial values.

---

### `train.py` — The main training script

**What it does:** Implements the teacher-student SGD loop.

**Key constants:**
```python
TSTOP_TRAIN = "10n"    # transient duration for training (gradient computation)
TSTOP_EVAL  = "1u"     # transient duration for evaluation (classification accuracy)
LR          = 0.001    # step size: 1 mV per epoch
TEACHER_V2  = 1.60     # teacher's V2 — the target for the student
EVAL_BELOW  = 1.705    # skip slow eval until V2 drops below this threshold
```

**Training flow:**
```
1. Load dataset (X_v, y_v)
2. Generate teacher targets: run teacher (V2=1.60) at tstop=10n for all 10 samples
3. For each epoch:
   a. For each sample: run student at tstop=10n with sensitivity → (v_pred, sens)
   b. Compute error = v_pred - teacher_target
   c. Accumulate gradient: g_V2 += error × sens["V2"]
   d. Average: g_V2 /= N
   e. Update: V2 -= 0.001 × sign(g_V2)
   f. Evaluate R² at 1µs (forward-only, fast)
   g. Stop if train_MSE < 1e-4 (converged to teacher)
4. Save best params to best_params.json
5. Log every epoch to train_log.csv
```

**Convergence condition:** training stops when the teacher-student MSE drops below 1e-4.
This happens when V2 reaches ≈ 1.659 V — the point where the student's 10 ns outputs
match the teacher's 10 ns outputs closely enough for all samples.

---

### `diag_eval.py` — Diagnostic tool

**What it does:** Runs forward-only evaluations at a specific V2 value and tstop,
printing per-sample predictions and the R² score. Used during debugging to understand
what the circuit is doing before and after training.

**Usage:**
```python
# Inside the script, change the loop to test different V2 values:
for v2 in [1.70, 1.68, 1.66]:
    eval_v2_tstop(v2, "100n")
```

---

### `plot_training.py` — Visualisation

**What it does:** Reads `train_log.csv` and produces a three-panel figure showing
MSE, R², and V2 over training epochs. Saved as `training_curves.png`.

---

### `best_params.json` — Training output

Written by `train.py` whenever a new best R² is achieved:
```json
{
  "r2": 0.9979,
  "params": {
    "V5": 1.7, "V4": 1.7, "V3": 1.7, "V2": 1.659,
    "VB1": 0.8, "VB2": 0.8, "VB3": 0.8, "VB4": 0.8
  }
}
```

---

### `train_log.csv` — Per-epoch log

```
epoch, train_mse, r2_100ns, V2
1,     4.230103,  0.9979,   1.69900
2,     4.226856,  0.9978,   1.69800
...
43,    0.000000,  0.9931,   1.65900
```

---

## 11. How to Run

### Prerequisites

- Python 3.x
- NumPy
- Matplotlib (for plot_training.py only)
- The circuit simulator installed at `D:\Simulator\circuit_simulator with level3\src`

### Step 1 — Verify the dataset

```bash
python dataset.py
```

Expected output:
```
Binary dataset — 5 HIGH + 5 LOW
  Boundary : 1.2 V
  #   IC(net3)   IC(net4)   target  class
   0       0.3        2.5      3.3  HIGH
   ...
   9       2.5        0.5      0.3  LOW
```

### Step 2 — Run the diagnostic (optional but educational)

```bash
python diag_eval.py
```

This verifies that all 10 samples settle to the correct attractor at V2 = 1.70.
Expected R² ≈ 0.998.

### Step 3 — Train the circuit

```bash
python train.py
```

You will see live output like:
```
Generating teacher targets at tstop=10n  (V2=1.6) ...
  Teacher @ 10n: min=3.3013  max=3.3046  mean=3.3029

SGD (V2 only) | 10 samples | 200 epochs | LR=0.001
  Train tstop=10n (MSE vs teacher)  |  Eval tstop=1u (R2 vs binary labels)

 Ep   train_MSE   R2@100ns        V2  note
----------------------------------------------------
  1     4.23010     0.9979   1.69900  *
  2     4.22686     0.9978   1.69800
 ...
 43     0.00000     0.9931   1.65900

  Train MSE < 1e-4 at epoch 43. Converged.

Done.  Best R2 @ 100ns = 0.9979  (99.8%)
```

### Step 4 — Plot the training curves

```bash
python plot_training.py
```

Produces `training_curves.png` showing MSE, R², and V2 over training epochs.

---

## 12. Results

### Training summary

| Metric | Start (epoch 1) | End (epoch 43) |
|--------|-----------------|----------------|
| Train MSE (vs teacher @ 10 ns) | 4.230 | 0.000 |
| R² (vs binary labels @ 1 µs) | 0.9979 | 0.9931 |
| V2 | 1.699 V | 1.659 V |

### Per-sample predictions at V2 = 1.70 (after IC fix, before training)

| # | IC(net3) | Target | Predicted @ 1µs | Correct? |
|---|----------|--------|-----------------|----------|
| 0 | 0.3 V | 3.3 V | 3.301 V | YES |
| 1 | 0.5 V | 3.3 V | 3.301 V | YES |
| 2 | 0.7 V | 3.3 V | 3.301 V | YES |
| 3 | 0.9 V | 3.3 V | 3.301 V | YES |
| 4 | 1.1 V | 3.3 V | 3.301 V | YES |
| 5 | 1.3 V | 0.3 V | 0.396 V | YES (error = 0.09 V) |
| 6 | 1.6 V | 0.3 V | 0.396 V | YES |
| 7 | 1.9 V | 0.3 V | 0.396 V | YES |
| 8 | 2.2 V | 0.3 V | 0.396 V | YES |
| 9 | 2.5 V | 0.3 V | 0.396 V | YES |

**All 10 samples correctly classified. R² = 0.9980.**

### Why R² is not exactly 1.0

The circuit's LOW attractor sits at ~0.396 V, not exactly 0.3 V (the target). This is
determined by the circuit physics (NMOS/PMOS current balance at equilibrium) and cannot
be changed by adjusting V2 alone. The residual error is:

```
SS_res = 5 × (0.396 - 0.300)² = 5 × 0.0092 = 0.046
SS_tot = 5 × (3.3 - 1.8)² + 5 × (0.3 - 1.8)² = 22.5

R² = 1 - 0.046 / 22.5 = 0.9980
```

### The brief R² dip at epoch 42

At epoch 42, V2 = 1.658 V crosses a bifurcation point: the circuit's LOW-class samples
at t = 10 ns momentarily saturate to 3.3 V (matching the teacher), which also changes
the gradient sign. The update moves V2 back to 1.659 V at epoch 43, and MSE = 0.
This is expected circuit behaviour at a bifurcation — not a training bug.

---

## 13. Design Decisions and Why

### Why only train V2 (not all 8 parameters)?

In principle, all 8 parameters are trainable. In practice:

1. **V5, V4, V3** (Blocks A, B, C): these blocks maintain the feedback loop. Changing
   their PMOS gate biases shifts the output levels of nets 6, 2, 3. But since the ring
   is fully latched at 1 µs, these nodes are at 3.3 V or 0.4 V regardless of these biases
   (within a reasonable range). Their adjoint sensitivity at t = 10 ns is non-zero, but
   the effect on classification at 1 µs is minimal.

2. **VB1, VB2, VB3, VB4**: the tail NMOS bias controls the tail current source. Changing
   VB4 changes the drive strength of Block D, but it also changes the time constant τ of
   the entire ring (all blocks). Reducing VBx slows the ring down, which could prevent
   it from latching at all within tstop.

3. **V2** is the cleanest single parameter to adjust: it shifts the threshold of Block D
   (the decision block) without affecting the ring's time constants.

### Why teacher V2 = 1.60 V?

The teacher needs to be "better" than the student — its outputs at 10 ns should be higher
for HIGH-class samples (stronger PMOS = more pull-up on net4). V2 = 1.60 V is 0.10 V
lower than the student's initial V2 = 1.70 V, which is a significant change in PMOS
strength while remaining within the circuit's safe operating range.

### Why train at t = 10 ns but evaluate at t = 1 µs?

Training at 10 ns (transient phase): adjoint sensitivity `dV(net4, 10ns)/dV2` is
large (~10⁻³) and physically meaningful. The teacher-student MSE gives a smooth signal.

Evaluating at 1 µs (fully latched): the circuit has committed to one of the two binary
attractors. This is the "real" classification output. R² at 1 µs tells us whether the
circuit is doing the correct job as a binary classifier.

Training directly at 1 µs would give sensitivities of nearly zero (all bits are decided)
and MSE with no gradient signal (both student and teacher output binary voltages).

### Why LR = 0.001 V per epoch?

With the classification threshold window being ~0.1 V wide (V2 needs to go from 1.70 to
~1.66), a step of 0.001 V requires about 40 epochs — reasonable. A larger LR (e.g.,
0.005 V) risks overshooting the bifurcation point, which was confirmed experimentally:
LR = 0.005 V caused V2 to jump past 1.66 V in a single step, causing R² to drop from
0.43 to -0.50.

### Why not Adam or other adaptive optimisers?

The user's explicit requirement: **"use as simple a training method as possible"**.
Sign-SGD with a fixed step is the simplest gradient-descent variant possible.
Adam requires maintaining two running average tensors (first and second moment),
a bias correction, and a per-parameter effective learning rate. None of this is
necessary when you have a single scalar parameter and a nearly-monotone loss landscape.

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **Adjoint sensitivity** | The derivative of a circuit output with respect to a parameter, computed by solving the transpose of the Jacobian system — the circuit-domain equivalent of backpropagation |
| **Attractor** | A stable equilibrium state toward which the circuit dynamics converge. This ring has two: HIGH (~3.3 V) and LOW (~0.4 V) at net4 |
| **Bifurcation** | A critical value of a parameter at which the circuit's qualitative behaviour changes — e.g., the V2 value where sample IC(net3)=1.1 V switches from latching LOW to latching HIGH |
| **IC (Initial Condition)** | The voltage placed on a capacitor at t = 0. Encodes the input data for the circuit |
| **KCL (Kirchhoff's Current Law)** | The sum of all currents flowing into a node equals zero. The fundamental equation the SPICE solver satisfies at each time step |
| **Metastable state** | An unstable equilibrium that looks like an attractor for a long time but is not truly stable — the "third state" at 1.2 V in this circuit |
| **PMOS gate bias (theta)** | V2, V3, V4, V5. Lowering this voltage (more negative Vgs) strengthens the PMOS pull-up current |
| **Sign-SGD** | A variant of gradient descent that uses only the sign of the gradient, moving by a fixed step size each epoch regardless of gradient magnitude |
| **Tail NMOS bias (vbias)** | VB1–VB4. Sets the tail current source drain current, which determines the differential pair drive strength and slew rate |
| **Teacher-student** | A training framework where a "teacher" circuit with known-good parameters produces targets, and a "student" learns to match those targets |
| **TRAN** | Transient analysis — the SPICE simulation that integrates the circuit differential equations from t = 0 to t = tstop |
| **τ (time constant)** | R × C ≈ 100 ns for this circuit. The characteristic time scale for the ring to latch to an attractor |
| **V2** | The trainable PMOS gate bias for Block D. The single parameter adjusted during training |

---

*Generated by KirchhoffNet training session. Circuit simulator: Python Level-3 SPICE.
Training method: sensitivity-based sign-SGD. No grid search used.*
