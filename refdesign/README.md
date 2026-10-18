# `refdesign/` — two reference accelerators, built from the literature

Two neural-network accelerators designed from the published architectures, with no
reference to KirchhoffNet anywhere, both run on the in-house simulator, both trained on
the three toy2d datasets.

| | Arm A | Arm B |
|---|---|---|
| **What** | 1T1R resistive crossbar | fixed-point digital MLP |
| **Trained** | **in-situ**, Manhattan rule | software QAT, straight-through estimator |
| **Circuit role** | every forward pass is a SPICE solve | datapath verified gate-by-gate at DC |
| **Activation** | tanh (digital, after the ADC) | ReLU |
| **Weights are** | programmed conductances | INT8 in SRAM |

---

## Arm A — 1T1R crossbar

### The array

One logical weight is a **pair of 1T1R cells** feeding a column pair:

```
row i --[select NMOS]--[ G+ ]--> column+
row i --[select NMOS]--[ G- ]--> column-

col+ - col-  =  -Rf * sum_i (G+ - G-) * (v_i - vref)
```

- **Select transistor per cell.** A bare 1R array has sneak paths — current from a driven
  row reaches a column through unselected cells and the MVM is wrong by a
  state-dependent amount. The simulator has no switch primitive, which is no obstacle: a
  1T1R selector *is* a transistor. Its on-resistance (~150 Ω against a 10 kΩ cell) is
  left in, because that series error is a genuine accuracy limit of 1T1R arrays.
- **Differential pair for signed weights** — a conductance is physically positive.
- **Virtual-ground readout** — a real 5-transistor OTA plus feedback resistor. An ideal
  VCVS exists for closed-form checking only, never for a reported number.
- **No analog neuron.** A layer ends at its columns; that is where the ADC sits.

### The device model

Conductance updates happen in software between samples, which is also where they happen
in hardware — the array is *read* with small voltages and *written* with large pulses.

- 100:1 window, 64 programmable levels, 2% write error on every write
- **Update nonlinearity**: `ΔG` shrinks towards whichever rail it is pushed at, so
  potentiation and depression are not mirror images. Crossing the window takes 37 pulses
  with it and 16 without — that gap is the device's real cost.

### Training: Manhattan rule

One fixed-amplitude pulse per cell, direction from the **sign** of the gradient,
magnitude set by the device. Forward on the circuit; gradient sign computed by a digital
controller from measured activations. **The simulator's adjoint is deliberately not
used** — real crossbar hardware does not have one.

---

## Arm B — fixed-point digital MLP

The published reference flow: train in software with quantization in the loop, export
integer weights, run bit-accurate inference on hardware. Q-format weights and
activations, power-of-two scales (so the rescale is a shift, not a multiplier).

The gate-level netlist is real CMOS built up from NAND/NOR/INV: XOR, full adder,
ripple-carry adder, array multiplier.

---

## Verification

| Gate | What it proves | Result |
|---|---|---|
| **V1** | array computes the MVM | within 2–3% of closed form (the rest is select-transistor series resistance) |
| **V2** | select devices block unselected rows | deselecting a row moves the output 57.8 mV and matches ideal row removal to 3.4% |
| **V3** | gate-level logic is exact | full adder 8/8, 2-bit adder 16/16, 2×2 multiplier 14/14 of the converged cases |
| **V4** | linearity in row drive | half drive gives half output to 0.3% |

### The simulator's limits, measured rather than assumed

```
inverter chain x16     32 MOS   converges
ripple adder 1-bit     44 MOS   converges
array multiplier 2x2  112 MOS   converges
ripple adder 3-bit    132 MOS   converges
ripple adder 4-bit    176 MOS   does NOT converge
array multiplier 3x3  318 MOS   does NOT converge
```

**Ceiling ≈ 132 transistors per DC solve**, and convergence is input-dependent as well
as size-dependent (the 2×2 multiplier converged on 14 of 16 operand pairs). A full INT8
multiplier is ~3800 transistors and is **not** claimed to have been simulated. What is
claimed — and exhaustively verified — is that every primitive it is built from is exact.

Transient is worse: cascaded CMOS stages do not converge in `.TRAN` at any time step
under either integration method, because the transient's initial DC solve seeds nodes at
mid-supply, the maximum-gain point of a chain of inverting stages. Logic correctness is
a DC property, so that is where it is checked.

---

## Six bugs, and what each one looked like

Every one produced plausible output. They are recorded because the symptoms are more
useful than the fixes.

**1. No bias row.** Without it every hidden unit computes `ReLU(w·x)`, which is
positively homogeneous, so the decision boundary can only be rays through the origin —
and `circle` is an inner-vs-outer ring. Not hard but *impossible*. A software twin of
the same network with the same rule sat at exactly the same 0.63, which is what proved
it was the architecture and not the circuit.

**2. Unpulsed cells were still being written.** `write()` ran on every cell including
those receiving no pulse, so each picked up 2% write noise per step — a random walk
across the whole array. Update thresholding, which should have *stabilised* training,
instead drove every dataset to a constant output, because the cells it protected were
the ones being damaged. A cell that receives no pulse must be left untouched.

**3. Random bias initialisation.** Gave every hidden unit an arbitrary offset before it
saw data; with ReLU after it, 6 of 8 units were dead at initialisation and never
recovered. Bias cells now start at `G+ = G−`.

**4. ADC full scale too small** (calibrated from the initial swing, before weights grew
~10×): the converter saturated. Score standard deviation pinned at exactly 1.000, loss
frozen at 4.0003 — confidently wrong on every sample.

**5. ADC full scale too large** (the array's absolute physical maximum, a state training
never reaches): 0.53 V of range for a 0.02 V signal, about 4 of 256 codes carrying
everything. Scores barely varied, loss sat at `ln 2`, and a tiny offset made every
sample class 0. Full scale is now the measured signal with headroom.

**6. ReLU on a differential array.** The column output is signed and zero-centred; ReLU
killed half the units immediately and the rest drifted off, active fraction 0.54 → 0.00
within 25 epochs on every dataset. tanh is symmetric, has no dead region, and is what
the 1T1R MLP literature uses.

### And one that is not a bug

**Manhattan without pulse decay reaches a good accuracy and then walks away from it.**
Measured: twomoon peaked at 0.867 and ended at exactly 0.500 — a constant output — on
*every* device setting, including a perfectly linear, symmetric, noiseless one. A
fixed-amplitude rule discards gradient magnitude, so its step never shrinks near a
solution. Annealing the pulse count fixes it, and that is a controller-side schedule,
not a device property.

---

## Running it

```bash
# verification first
python verify_xbar1t1r.py        # V1, V2, V4
python digital_verify.py         # V3 + the convergence ceiling

# training (crossbar is ~0.75 min/epoch at 120 train / 120 test with 8 workers)
python xbar1t1r_train.py --dataset circle --epochs 50 --workers 8 --tag run
python digital_train.py  --dataset circle --epochs 60 --tag run

# figures
python make_plots.py
```

Outputs: `results/<arm>_<dataset>_<tag>_log.csv` (per-epoch accuracy **and one column
per weight**) plus a `_meta.json`, and `figs/acc_*.png` / `figs/weights_*.png`.

Per-epoch weight logging did not exist anywhere in this repo and is what the convergence
plots need. For the analog arm the logged values are the **measured conductances** — the
actual programmed state of the array, not a software shadow of it.

---

## Honest limits

- The crossbar's accuracy is well below the digital arm's. That is the real cost of
  fixed-amplitude in-situ updates into a bounded, nonlinear, 64-level device, and it is
  what the in-situ literature reports. A float-SGD control on the identical architecture
  reaches 1.000 on twomoon and circle, which bounds how much of the gap is the training
  rule rather than the network.
- Single seed. Multiple seeds are needed before any of these numbers is quoted.
- 120 test samples gives roughly a ±8-point Wilson interval; the bands on the accuracy
  plots show it.
- `2spirals` is genuinely hard — the repo's own prior best is ~0.79–0.92.

---

## Results (single seed, 120 train / 120 test, chance = 0.50)

| dataset | arm | best | @ epoch | last | mean(last 10) |
|---|---|---|---|---|---|
| twomoon | **1T1R crossbar** | **0.867** | 25 | 0.850 | 0.839 |
| twomoon | fixed-point MLP | 1.000 | 18 | 1.000 | 1.000 |
| circle | **1T1R crossbar** | 0.708 | 16 | 0.442 | **0.519** |
| circle | fixed-point MLP | 1.000 | 6 | 1.000 | 1.000 |
| 2spirals | **1T1R crossbar** | 0.683 | 3 | 0.667 | 0.608 |
| 2spirals | fixed-point MLP | 0.817 | 42 | 0.783 | 0.780 |

### Read these carefully

**twomoon is the only clean crossbar success.** It converges by epoch ~25 and holds —
train and test track each other, the weight traces calm as the pulse amplitude decays.

**circle did not train at all.** Its "best 0.708" is a fluctuation, not learning: the
*train* accuracy sits at chance for all 50 epochs alongside the test accuracy, and the
mean over the last ten epochs is 0.519 against a chance level of 0.500. Quoting 0.708
from this run would be reporting the maximum of a noise process. The weight plot shows
why — the cells are still swinging across the full device window at epoch 50, with only
4% railed and the mean pinned at the device's nonlinear fixed point. Pulse decay from
0.3 at 0.95/epoch was not enough to let this task settle.

**2spirals is marginal**: 0.608 over the last ten epochs against 0.500 chance, so there
is some signal, but well under the digital arm's 0.780.

### What this says

The digital arm solves twomoon and circle exactly and reaches 0.78 on 2spirals, which is
roughly the ceiling for a 2-8-2 network on that task. The crossbar matches it nowhere.

The gap is **not** the array and **not** the simulator. A float-SGD control on the
identical architecture -- same layer sizes, same bias row, same tanh, same backprop --
reaches 1.000 on twomoon and circle. The architecture is capable; the loss is in the
training rule meeting the device:

* fixed-amplitude updates discard gradient magnitude, so the array never settles on its
  own and depends entirely on an annealing schedule;
* the nonlinear update has a stable fixed point near mid-window, so every pulsed cell is
  pulled back toward zero weight -- the array forgets while it learns;
* the conductance window bounds |w| to 1, where float SGD grows weights past 2.

All three are genuine properties of in-situ training on resistive hardware rather than
artefacts of this implementation, and they are the reason the published on-chip
demonstrations use small networks and easy tasks. What is not established here is how
much of the circle failure is fundamental and how much is tuning: a wider pulse-decay
and threshold sweep, and more than one seed, would be needed before claiming the former.
