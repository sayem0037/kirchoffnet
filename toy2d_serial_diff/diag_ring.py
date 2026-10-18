"""
diag_ring.py -- GATE CHECK for the closed-loop ring (does it add separating power?).

Push each dataset through the untrained ring (seed via .IC, read h1..h10 @100ns) and
compare the 10-D ring-state linear separability to the raw 2-D feature ceiling. If the
ring's nonlinear evolution adds separating power, the 10-D state should be MORE linearly
separable than the 2 raw features -- validating the design BEFORE full adjoint training.

Usage:  python diag_ring.py --dataset {twomoon|circle|2spirals}
"""
import os, argparse
import numpy as np
from sklearn.linear_model import LogisticRegression

from netlist_ring import write_ring_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from ring_common import N_STAGES, READ, init_seed_encoder, encode_ic, circ_dict, circ_init

NETLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_diagring.sp")


def states(X, W, b, circ):
    S, valid = [], []
    for i in range(len(X)):
        write_ring_netlist(circ_dict(circ), encode_ic(X[i], W, b), NETLIST, n_stages=N_STAGES)
        try:
            v = eval_chain(NETLIST, READ)
            S.append([v[n] for n in READ]); valid.append(i)
        except Exception:
            continue
    return np.array(S), np.array(valid, dtype=int)


def main(name):
    Xtr, ytr, Xte, yte = load_dataset(name)
    W, b = init_seed_encoder(seed=0)
    circ = circ_init()
    print(f"=== {name} | closed ring N={N_STAGES} stages | read {N_STAGES} nodes @100ns ===")

    Str, vtr = states(Xtr, W, b, circ)
    Ste, vte = states(Xte, W, b, circ)
    print(f"convergence failures: train {len(Xtr)-len(vtr)}/{len(Xtr)}, test {len(Xte)-len(vte)}/{len(Xte)}")

    raw = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    st = LogisticRegression(max_iter=5000).fit(Str, ytr[vtr])
    acc_raw_tr, acc_raw_te = raw.score(Xtr, ytr), raw.score(Xte, yte)
    acc_st_tr = st.score(Str, ytr[vtr])
    acc_st_te = st.score(Ste, yte[vte]) if len(vte) else float("nan")

    print("\n=== GATE (untrained closed ring) ===")
    print(f"  raw features   : train {acc_raw_tr:.2f}  test {acc_raw_te:.2f}")
    print(f"  ring STATE     : train {acc_st_tr:.2f}  test {acc_st_te:.2f}")
    gain = acc_st_tr - acc_raw_tr
    print(f"  --> ring adds {gain:+.2f} separability on train "
          f"({'GO -- ring helps' if gain > 0.03 else 'MARGINAL -- little added power'})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
