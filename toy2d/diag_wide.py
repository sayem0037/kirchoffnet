"""
diag_wide.py -- GATE CHECK for the wide parallel layer (tests the width fix).

Build a random-diverse wide layer (untrained), push each dataset through it, and
compare the circuit-state linear separability to the raw-feature ceiling. If width
adds separating power, the N-dim state should be MORE separable than the 2 raw
features (target: circle > 0.70 -> ~0.9; 2spirals > 0.62).

Usage:  python diag_wide.py --dataset circle
"""
import os, argparse
import numpy as np
from sklearn.linear_model import LogisticRegression

from netlist_wide import write_wide_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from wide_common import N_UNITS, READ, init_encoder, encode_wide, circ_dict, circ_init

NETLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_diagw.sp")


def states(X, W, b, circ):
    S, valid = [], []
    for i in range(len(X)):
        write_wide_netlist(circ_dict(circ), encode_wide(X[i], W, b), NETLIST, n_units=N_UNITS)
        try:
            v = eval_chain(NETLIST, READ)
            S.append([v[n] for n in READ]); valid.append(i)
        except Exception:
            continue
    return np.array(S), np.array(valid, dtype=int)


def main(name):
    Xtr, ytr, Xte, yte = load_dataset(name)
    W, b = init_encoder(seed=0)
    circ = circ_init()
    print(f"=== {name} | wide layer N={N_UNITS} units | read {N_UNITS} nodes @100ns ===")

    Str, vtr = states(Xtr, W, b, circ)
    Ste, vte = states(Xte, W, b, circ)
    print(f"convergence failures: train {len(Xtr)-len(vtr)}/{len(Xtr)}, test {len(Xte)-len(vte)}/{len(Xte)}")

    raw = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    st = LogisticRegression(max_iter=5000).fit(Str, ytr[vtr])
    acc_raw_tr, acc_raw_te = raw.score(Xtr, ytr), raw.score(Xte, yte)
    acc_st_tr = st.score(Str, ytr[vtr])
    acc_st_te = st.score(Ste, yte[vte]) if len(vte) else float("nan")

    print("\n=== GATE (random untrained wide layer) ===")
    print(f"  raw features   : train {acc_raw_tr:.2f}  test {acc_raw_te:.2f}")
    print(f"  circuit STATE  : train {acc_st_tr:.2f}  test {acc_st_te:.2f}")
    gain = acc_st_tr - acc_raw_tr
    print(f"  --> width adds {gain:+.2f} separability on train "
          f"({'GO -- width helps' if gain > 0.03 else 'RECONSIDER -- width did not add power'})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle", choices=DATASETS)
    main(ap.parse_args().dataset)
