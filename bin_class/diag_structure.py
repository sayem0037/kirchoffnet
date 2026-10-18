"""
diag_structure.py -- GATED verification step 1.

Confirm the open feedforward chain, read at 100ns, has left the dead-latched
regime BEFORE building the training loop:
  (a) outputs are distinct across samples and non-latched (a spread of values,
      not 2-3 discrete rails), and
  (b) dV(output,100ns)/dparam is non-zero for every trainable circuit param
      AND every input source.

Uses init circuit params and a simple FIXED feature->voltage mapping (a stand-in
for the trainable encoder): VREF1..3 <- the 3 features (centered ~1.0V), VIN and
VREF4 held constant.
"""

import os
import numpy as np

from netlist_writer import (write_chain_netlist, theta_names, vbias_names,
                            input_source_names, output_nodes)
from simulator_api import run_chain
from dataset import load_dataset

BASE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(BASE, "tmp_diag.sp")
N_BLOCKS = 4

CIRCUIT_INIT = {**{n: 1.7 for n in theta_names(N_BLOCKS)},
                **{n: 0.8 for n in vbias_names(N_BLOCKS)}}
ALL_PARAMS = theta_names(N_BLOCKS) + vbias_names(N_BLOCKS) + input_source_names(N_BLOCKS)
READ = output_nodes(N_BLOCKS)          # h1..h4
OUT = READ[-1]                          # h4 = final output


def encode_fixed(x):
    """Fixed stand-in encoder: 3 standardized features -> input source voltages."""
    return {
        "VIN":   1.65,
        "VREF1": 1.0 + 0.25 * float(x[0]),
        "VREF2": 1.0 + 0.25 * float(x[1]),
        "VREF3": 1.0 + 0.25 * float(x[2]),
        "VREF4": 1.0,
    }


def main():
    Xtr, ytr, Xte, yte = load_dataset()
    print(f"Chain: {N_BLOCKS} stages, read at 100ns, output node {OUT}")
    print(f"Samples: {len(ytr)} train\n")

    rows = []
    sens_accum = {p: [] for p in ALL_PARAMS}
    fails = 0
    for i in range(len(Xtr)):
        write_chain_netlist(CIRCUIT_INIT, encode_fixed(Xtr[i]), NETLIST, n_blocks=N_BLOCKS)
        try:
            v_out, sens = run_chain(NETLIST, READ, ALL_PARAMS)
        except Exception as e:
            fails += 1
            print(f"  sample {i}: FAILED ({type(e).__name__})")
            continue
        rows.append([v_out[n] for n in READ])
        for p in ALL_PARAMS:
            sens_accum[p].append(abs(sens[OUT][p]))

    rows = np.array(rows)
    print(f"Convergence failures: {fails}/{len(Xtr)}\n")

    print("Per-node output spread at 100ns (across samples):")
    print(f"  {'node':>4}  {'min':>8}  {'max':>8}  {'std':>8}  {'n_distinct(0.01V)':>18}")
    for j, n in enumerate(READ):
        col = rows[:, j]
        ndist = len(set(np.round(col, 2)))
        print(f"  {n:>4}  {col.min():>8.4f}  {col.max():>8.4f}  {col.std():>8.4f}  {ndist:>18}")

    print(f"\nBackward-adjoint sensitivity of {OUT} at 100ns (mean |dV/dparam|):")
    dead = []
    for p in ALL_PARAMS:
        m = np.mean(sens_accum[p]) if sens_accum[p] else 0.0
        tag = "  <-- ~zero" if m < 1e-6 else ""
        if m < 1e-6:
            dead.append(p)
        print(f"    {p:>6}: {m:.3e}{tag}")

    # Separability of the full circuit STATE VECTOR [h1..h4] (what the readout sees)
    from sklearn.linear_model import LogisticRegression
    state = rows  # (N, n_blocks)
    lr_state = LogisticRegression(max_iter=1000).fit(state, ytr[:len(state)])
    acc_state = lr_state.score(state, ytr[:len(state)])
    lr_raw = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    acc_raw = lr_raw.score(Xtr, ytr)

    print("\n=== GATE ===")
    sens_ok = len(dead) == 0
    # non-latched: the STATE VECTOR (not just h4) must be analog/spread
    state_distinct = [len(set(np.round(rows[:, j], 2))) for j in range(rows.shape[1])]
    analog_nodes = sum(1 for d in state_distinct if d >= max(4, len(rows) // 3))
    print(f"  analog (non-latched) read-nodes: {analog_nodes}/{rows.shape[1]}  "
          f"(distinct per node: {state_distinct})")
    print(f"  all params have non-zero sensitivity: {'PASS' if sens_ok else 'FAIL'} (dead: {dead})")
    print(f"  linear separability of circuit STATE vector (train): {acc_state:.2f}")
    print(f"  linear separability of raw features (ceiling):       {acc_raw:.2f}")
    print(f"  --> {'GO' if (sens_ok and analog_nodes >= 2 and acc_state > 0.6) else 'RECONSIDER'}: "
          f"state is separable and gradients live." if (sens_ok and analog_nodes >= 2)
          else "  --> RECONSIDER structure.")


if __name__ == "__main__":
    main()
