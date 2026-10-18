"""
diag_structure.py -- GATE CHECK for a 2-D dataset before training.

Confirms the open chain read at 100ns is (a) analog/non-latched, (b) has non-zero
backward-adjoint sensitivity for every circuit parameter, and (c) yields a circuit
STATE vector that is linearly separable clearly above chance (compared to the raw
2-feature ceiling). Run:  python diag_structure.py --dataset twomoon
"""
import os, argparse
import numpy as np
from sklearn.linear_model import LogisticRegression

from netlist_writer import write_chain_netlist
from simulator_api import run_chain
from dataset import load_dataset, DATASETS
from common import N_BLOCKS, CIRCUIT_INIT, CIRC_NAMES, ALL_SENS, READ, encode

NETLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_diag.sp")
OUT = READ[-1]


def main(name):
    Xtr, ytr, Xte, yte = load_dataset(name)
    print(f"=== {name} | {len(ytr)} train | chain {N_BLOCKS} stages | read {READ} @100ns ===")
    S, sens_abs, fails = [], {p: [] for p in ALL_SENS}, 0
    for i in range(len(Xtr)):
        write_chain_netlist(CIRCUIT_INIT, encode(Xtr[i]), NETLIST, n_blocks=N_BLOCKS)
        try:
            v, sens = run_chain(NETLIST, READ, ALL_SENS)
        except Exception as e:
            fails += 1; continue
        S.append([v[n] for n in READ])
        for p in ALL_SENS:
            sens_abs[p].append(abs(sens[OUT][p]))
    S = np.array(S)
    print(f"convergence failures: {fails}/{len(Xtr)}")

    print("per-node spread (distinct rounded values):",
          [len(set(np.round(S[:, j], 2))) for j in range(S.shape[1])])
    dead = [p for p in CIRC_NAMES if np.mean(sens_abs[p]) < 1e-6]
    print(f"circuit-param sensitivities (mean|dV({OUT})/dp|):")
    for p in CIRC_NAMES:
        print(f"    {p:5s}: {np.mean(sens_abs[p]):.3e}")

    lr_state = LogisticRegression(max_iter=2000).fit(S, ytr[:len(S)])
    lr_raw = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    acc_state = lr_state.score(S, ytr[:len(S)])
    acc_raw = lr_raw.score(Xtr, ytr)

    analog = sum(1 for j in range(S.shape[1]) if len(set(np.round(S[:, j], 2))) >= max(4, len(S)//3))
    print("\n=== GATE ===")
    print(f"  analog read-nodes: {analog}/{S.shape[1]}   dead params: {dead}")
    print(f"  linear separability -- circuit STATE: {acc_state:.2f}   raw features: {acc_raw:.2f}")
    ok = (fails == 0 and not dead and analog >= 2 and acc_state > 0.6)
    print(f"  --> {'GO' if ok else 'RECONSIDER'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
