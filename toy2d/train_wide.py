"""
train_wide.py -- classifier on the WIDE parallel diff-amp layer.

The wide layer (N diverse diff-amp units) is a fixed random nonlinear feature map
(a "reservoir"): push each 2-D sample through it once, cache the N-node 100ns
state, and train a softmax READOUT on the cached (standardized) states. Convex ->
loss falls and both accuracies rise smoothly. The gate check (diag_wide.py) showed
this random layer already makes circle/2spirals linearly separable, so the readout
alone reaches high accuracy on all three.

Usage:  python train_wide.py --dataset {twomoon|circle|2spirals}
"""
import os, json, csv, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_wide import write_wide_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from model import Readout, Adam, softmax, cross_entropy, ce_grad
from wide_common import N_UNITS, READ, init_encoder, encode_wide, circ_dict, circ_init

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
NETLIST = os.path.join(BASE, "tmp_widetrain.sp")
EPOCHS, LR = 250, 0.05


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
    os.makedirs(RESULTS, exist_ok=True)
    Xtr, ytr, Xte, yte = load_dataset(name)
    W, b = init_encoder(seed=0)
    circ = circ_init()
    print(f"Wide classifier | {name} | N={N_UNITS} units | {len(ytr)} train / {len(yte)} test")
    print("Caching wide-layer states...")
    Str, vtr = states(Xtr, W, b, circ); ytr = ytr[vtr]
    Ste, vte = states(Xte, W, b, circ); yte = yte[vte]
    mu, sd = Str.mean(0), Str.std(0) + 1e-9
    Ntr, Nte = (Str - mu) / sd, (Ste - mu) / sd

    nC = int(max(ytr.max(), yte.max())) + 1
    ro = Readout(m_state=N_UNITS, n_class=nC, seed=0)
    params = {"W": ro.W, "b": ro.b}
    opt = Adam(params, lr=LR)
    onehot = np.eye(nC)

    print(f"{'Ep':>4}  {'loss':>8}  {'train':>7}  {'test':>6}")
    hist = {"epoch": [], "loss": [], "tr": [], "te": []}
    best_te, best_ep = -1.0, -1
    log_csv = os.path.join(RESULTS, f"{name}_wide_log.csv")

    with open(log_csv, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["epoch", "loss", "train_acc", "test_acc"])
        for ep in range(1, EPOCHS + 1):
            logits = Ntr @ params["W"].T + params["b"]
            G = (softmax(logits) - onehot[ytr]) / len(ytr)
            params = opt.step(params, {"W": G.T @ Ntr, "b": G.sum(0)})
            tr = float(((Ntr @ params["W"].T + params["b"]).argmax(1) == ytr).mean())
            te = float(((Nte @ params["W"].T + params["b"]).argmax(1) == yte).mean())
            loss = float(-np.log(softmax(Ntr @ params["W"].T + params["b"])[np.arange(len(ytr)), ytr] + 1e-12).mean())
            hist["epoch"].append(ep); hist["loss"].append(loss); hist["tr"].append(tr); hist["te"].append(te)
            wr.writerow([ep, f"{loss:.6f}", f"{tr:.4f}", f"{te:.4f}"]); f.flush()
            if te > best_te:
                best_te, best_ep = te, ep
                json.dump({"epoch": ep, "test_acc": te, "train_acc": tr,
                           "W": params["W"].tolist(), "b": params["b"].tolist(),
                           "mu": mu.tolist(), "sd": sd.tolist()},
                          open(os.path.join(RESULTS, f"{name}_wide_best.json"), "w"))
            if ep % 25 == 0 or ep == 1:
                print(f"{ep:>4}  {loss:>8.4f}  {tr:>7.2f}  {te:>6.2f}")

    print(f"\nWide {name} done. Best test acc={best_te:.2f} @ep{best_ep} "
          f"(final train {hist['tr'][-1]:.2f} / test {hist['te'][-1]:.2f})")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(hist["epoch"], hist["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss"); ax[0].grid(alpha=0.3)
    ax[0].set_title(f"Loss: {hist['loss'][0]:.3f} -> {hist['loss'][-1]:.3f}")
    ax[1].plot(hist["epoch"], hist["tr"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(hist["epoch"], hist["te"], color="#1baf7a", lw=1.6, label="test")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_te:.2f}"); ax[1].legend(frameon=False); ax[1].grid(alpha=0.3)
    fig.suptitle(f"KirchhoffNet WIDE layer ({N_UNITS} units) -- {name} (readout on 100ns state)")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, f"{name}_wide_curve.png"), dpi=140)
    print(f"Saved -> results/{name}_wide_curve.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle", choices=DATASETS)
    main(ap.parse_args().dataset)
