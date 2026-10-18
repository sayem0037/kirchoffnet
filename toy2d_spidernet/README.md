# KirchhoffNet SpiderNet — 4×4 crossbar trained on the toy2d datasets

Port of the Cadence Virtuoso/Spectre export `spidernet_1.txt` (cell
`kirchoff_spidernet`, library `Neur_Sam_350`) into the in-house simulator's SPICE
dialect, plus an adjoint training pipeline on the 2-D toy datasets.

Pipeline, mirroring the validated `../toy2d_serial_diff` recipe:

```
(x,y) --encode_rails--> v1..v4 rail voltages --> [4x4 theta-gated NMOS crossbar]
      --settle 100ns--> read net1..net4 --standardize--> softmax readout --> class
```

The 16 per-edge thetas are trained through the simulator's **100 ns transient
adjoint** (`dV(net_j,100ns)/dVTH_k`); the linear readout is co-trained with
ordinary analytic gradients.

---

## 1. The circuit

A fully-connected crossbar: 4 fixed input rails × 4 capacitive state nodes, one
NMOS per pair (16 edges). Each edge has **drain = rail `v_i`, gate = `theta_k`,
source = `net_j`, bulk = 0**; each state node carries a 100 aF cap to ground.

```
        v1      v2      v3      v4          <- encoder-driven input rails
         |       |       |       |
  net1 --+-------+-------+-------+--        gates: theta1  theta2  theta3  theta4
  net2 --+-------+-------+-------+--        gates: theta5  theta6  theta7  theta8
  net3 --+-------+-------+-------+--        gates: theta9  ...
  net4 --+-------+-------+-------+--        gates: theta13 ...
         |       |       |       |
        C1      C2      C3      C4          (one cap per state node, to ground)
```

### Why it computes something

Level-1 Shichman–Hodges does **not** re-designate source/drain
(`src/models/mosfet_level1_model.py:29-43`). For `vds < 0 < vov` an edge stays on
the triode branch with `Id < 0` and `gds > 0`, so a rail *below* `net_j` pulls it
**down** while a rail above pulls it **up**. Every edge is a theta-gated
bidirectional conductance to its rail, and `net_j` settles at the current balance

```
sum_i [ (theta_ij - VTO - net_j)(v_i - net_j) - 0.5 (v_i - net_j)^2 ] = 0
```

which, with `a_ij = theta_ij - VTO`, solves in closed form:

```
net_j = ( A_j - sqrt( A_j^2 + 4Q - 8 B_j ) ) / 4
A_j = sum_i a_ij      B_j = sum_i a_ij v_i      Q = sum_i v_i^2
```

**This closed form drives every design decision below**, and it is worth reading
carefully — it says exactly what the architecture can and cannot express.

---

## 2. Spectre → SPICE port (`spidernet_1.txt` → `spidernet_1.sp`)

The export cannot be fed to `run_simulation_core` as-is; `NetlistParser`
(`src/utils/parser.py`) reads a Berkeley/HSPICE subset. Every conversion:

| Spectre construct | This dialect | Why |
|---|---|---|
| `//` comments | `*` | `_preprocess_lines:342` only skips `*` |
| trailing `\` continuation | joined onto one line | `_preprocess_lines:343` honours a leading `+` only |
| `parameters theta1=2 ...` | deleted, values inlined | no `.PARAM`, no expression evaluator |
| `include "...mm0355v.scs"` | `.MODEL NCH NMOS LEVEL=1 VTO=0.55 KP=170e-6` | no `.INCLUDE`/`.LIB`; matches the simulator's own `testfiles/kirchoffnet.txt` for this topology family |
| `M15 (v2 theta16 net3 0) nch l=350n w=2u ...` | `M15 v2 theta16 net3 0 NCH L=350n W=2u` | `_parse_mosfet:170` is strictly positional; `(v2` and `0)` become phantom nodes, and **`0)` does not map to ground** |
| `V9 (v1 0) vsource dc=v1 type=dc` | `V9 v1 0 DC 3.0` | `_parse_source_def:288` wants `DC <val>`; as-is the DC value silently becomes 0.0 |
| `C3 (net3 0) capacitor c=100.0a` | `C3 net3 0 0.1f` | **`_parse_value:256` has no atto suffix — `100.0a` would parse as 100 farads** |
| `ic net1=.5` | `.IC V(net1)=0.5 ...` | needs the dot and the `V(node)=` form (`parser.py:127`); as-is it throws `Malformed source` |
| `tran tran stop=1u ...` | `.TRAN 10n 100n` | needs `.TRAN TSTEP TSTOP`; with no recognised analysis card the parser **silently falls back to `.OP`** |
| `simulatorOptions`, `saveOptions`, `finalTimeOP`, `dc dc param=theta1 ...`, `*_info` | deleted | no equivalents. `sensfile=` is irrelevant: **there is no `.SENS` card** — sensitivity is the Python kwarg `run_simulation_core(..., sensitivity=True)` |
| `simulator lang=spectre`, `global 0` | deleted | parsed as components; warn or throw |

Two schematic quirks preserved as comments rather than silently "fixed":
`V4/V3` are cross-wired (`dc=theta3` / `dc=theta2`), and `theta5..theta16` are
never defined in the `parameters` line. Both are moot once each theta becomes an
independent trainable literal. Instance params `m/ad/as/pd/ps/nrd/nrs` are
dropped — they parse fine but LEVEL=1 ignores them, and they would add noise
entries (`M15:AD`, …) to the component's `differentiable_params`.

`verify_topology.py` proves the generator reproduces the schematic as a *circuit*
(identical 16-edge set, 4 distinct gates per node, 16 distinct thetas, same
geometry, same caps), independent of theta numbering.

---

## 3. The two operating-point rules

Both are hard failures, and the schematic's own default values violate the first.

**Rule 1 — edges must be ON.** An edge with `theta_k <= V(net_j) + VTO` is cut
off: `gds` floors at `1e-12` and `dId/dtheta` is **exactly zero**, a dead
parameter Adam can never revive.

**Rule 2 — edges must be in TRIODE** (`v_i < theta_k - VTO`). In saturation the
edge becomes a current source that ignores `v_i`, destroying data dependence.

Simulating the faithful port at the schematic's defaults (rails 2.5–3.1 V, thetas
1.0–2.4 V) shows Rule 1 violated on **all 16 edges** at once:

```
V(net) [2.875 2.875 2.875 2.875]   across-node std = 5.5e-15
|dV/dtheta| max = 0.000e+00        nonzero entries = 0/64
```

Every node sits at the leakage-weighted rail mean and the entire sensitivity
matrix is zero. `spider_common.py` therefore places rails **low** (centre 1.0 V)
and thetas **high** (≈2.4 V, bounded `[1.9, 3.3]`), which satisfies both rules.

---

## 4. What the architecture can express (and its ceiling)

Expanding the closed form to first order:

```
net_j ~= B_j/A_j - Q/(2 A_j)
```

so a **linear readout over the nodes is `linear(x) + kappa * Q(x)`** — a quadratic
classifier whose quadratic *shape* is `W.T @ W`, fixed by the encoder and **not
trainable**. The thetas only tune `kappa` and the linear part.

Three consequences, all measured:

1. **The read features are inherently near-collinear** (max |corr| ≈ 0.99 in every
   configuration tried). `Q` is shared by every node; only the scalars `A_j, B_j`
   differ. This is structural, not a tuning failure.
2. **The encoder matters more than the thetas for concentric data.** With a random
   `W`, `W.T @ W` is a lopsided ellipse. `init_rail_encoder(mode="frame")` lays
   the rail directions on evenly spaced angles, giving `W.T @ W = (swing^2 *
   n_rails/2) * I` so `Q ∝ ||x||^2`.
3. **The quadratic term is weak.** Its coefficient is `~swing^2/(2 A_j)` against a
   linear `~swing/A_j`. A sweep over `swing ∈ [0.22, 0.65]`, `theta_mu ∈ [1.95,
   2.6]`, both encoder modes and two rail windows never moved `circle` above 0.68
   untrained — the quadratic signal is real but too small for a linear readout to
   isolate cleanly.

**Adding more state nodes does not fix this.** Every extra node contributes
another `B_j/A_j - Q/(2A_j)`; the linear parts collapse into one direction and the
quadratic parts share the same `Q`. The limitation is the crossbar's bipartite
structure — all nodes see the same rails and never each other — not the node count.

---

## 5. Results

40 train / 24 test per dataset, 90 epochs, 16 thetas trained through the adjoint.

| dataset | untrained gate (train/test) | **best test** | train @ best | epoch | verdict |
|---|---|---|---|---|---|
| `twomoon`  | 0.85 / 0.67 | **0.83** | 0.93 | 43 | works |
| `circle`   | 0.68 / 0.62 | **1.00** | 0.98 | 52 | works — training does all the work |
| `2spirals` | 0.65 / 0.75 | **0.79** | 0.65 | 42 | fails (train acc stalls at 0.65) |

Zero convergence failures across every run; 0% rail clipping; no dead edges.

**The pre-training gate check badly under-predicts `circle`.** Untrained it scores
0.68, yet training reaches a perfect 1.00. Section 4 explains why: the quadratic
coefficient is `kappa = -sum_j c_j/(2 A_j)`, and `A_j = sum_i (theta_ij - VTO)` is
*trainable*. Adam drives the thetas apart until they pin against **both** bounds
(the trained range is exactly `[1.900, 3.300]` for twomoon and circle), which
spreads `A_j` across nodes, gives each node a different quadratic weight, and lets
the linear readout isolate `Q ∝ ||x||^2` — precisely the boundary `circle` needs.
So the untrained state's separability is the wrong gate for this architecture: the
value lives in the thetas, not in the frozen feature map.

Because the bounds are *binding* at convergence, widening `BOUNDS` in
`spider_common.py` is the first thing to try for more headroom — but keep the
floor above `V(net_j) + VTO` or edges cut off and their gradients go to zero.

`2spirals` behaves as Section 4 predicts: train accuracy stalls at 0.65, i.e. the
model cannot even fit the training set. A `linear(x) + kappa*||x||^2` decision
function has no way to express a boundary that winds repeatedly. (Its test score
of 0.79 above its 0.65 train score is small-sample noise on 24 points, not
generalization.)

## 6. Files

| File | Role |
|---|---|
| `spidernet_1.txt` | original Cadence Spectre export (unmodified) |
| `spidernet_1.sp` | **1:1 static port**, annotated with the conversion notes `[P1]`–`[P10]` |
| `netlist_spider.py` | parameterized generator, `write_spider_netlist(...)`, `n_rails`/`n_nodes` |
| `spider_common.py` | config, bounds, the fixed rail encoder, theta init |
| `simulator_api.py`, `model.py`, `dataset.py` | copied verbatim from `../toy2d_serial_diff` |
| `verify_topology.py` | proves the generator matches the schematic as a circuit |
| `smoke_test.py` | one sample; prints the 4×16 sensitivity matrix, flags dead edges |
| `diag_spider.py` | pre-training gate check + `--sweep` over encoder/theta constants |
| `train_spider.py` | the adjoint training loop |
| `plot_boundary.py` | accuracy curve + decision boundary from the checkpoint |
| `animate_spider.py` | boundary-forming GIF (circuit frozen, readout training) |

## 7. How to run

```
python verify_topology.py                    # generator == schematic
python smoke_test.py  --dataset twomoon      # gradients alive, no dead edges
python diag_spider.py --dataset twomoon      # gate check
python diag_spider.py --sweep                # tune encoder/theta constants
python train_spider.py   --dataset twomoon   # {twomoon|circle|2spirals}
python plot_boundary.py  --dataset twomoon
python animate_spider.py --dataset twomoon   # -> results/<name>_spider_boundary.gif
```

Artifacts land in `results/`: `<name>_spider_log.csv`, `<name>_spider_best.json`
(`circ`, `Wout`, `bout`, `mu`, `sd`), `<name>_spider_curve.png`,
`<name>_spider_boundary.png`, and the long-format `<name>_spider_sensitivities.csv`
(`sample,label,read_node,param,V_node_100ns,dVnode_dparam`).

## 8. Implementation notes

- **The sensitivity tensor is block-diagonal.** The crossbar has no node-to-node
  coupling, so `net_j` is reachable only from its own 4 thetas: 16 of 64 entries
  are nonzero. Every theta still receives gradient, just from exactly one read
  node. `smoke_test.py` asserts this.
- **`.IC` is a solver seed, not data.** With 100 aF caps the node time constant is
  ~1e-13 s, so the state is fully settled long before `tstop` and the readout is a
  clean operating point. Data enters through the rails. This also means prediction
  and sensitivity share the *same* operating point, so the `.OP`-proxy mismatch
  documented in the repo-root README does not apply here.
- **Theta init must be jittered.** With all thetas equal, every node solves an
  identical current balance and returns an identical voltage — a rank-1 read
  vector with nothing to separate.
- **Step count is kept small** (`.TRAN 10n 100n`, ≈11 steps): `sensitivity=True`
  caches an LU factorization per timestep.
- The circuit step is **pre-checked**: a tentative Adam step is clipped to
  `BOUNDS`, re-simulated over the whole train set, and accepted only if it does
  not raise the loss and still solves ≥95% of samples; otherwise it is reverted and
  `lr_circ` backs off by 0.6×.
