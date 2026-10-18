"""
train.py -- Stage 1 classifier on a 2-D toy dataset, using the frozen chain.

Run each 2-D sample through the open diff-amp chain, read the 100ns state
[V(h1..h4)], and fit a softmax readout on the cached (standardized) states.
Convex -> loss falls and both accuracies rise smoothly.

Usage:  python train.py --dataset {twomoon|circle|2spirals}
"""
import os, json, csv, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_writer import write_chain_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from model import Readout, Adam, softmax, cross_entropy, ce_grad
from common import N_BLOCKS, CIRCUIT_INIT, READ, encode

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
NETLIST = os.path.join(BASE, "tmp_stage1.sp")
EPOCHS, LR = 200, 0.05


def states(X):
    S = []
    for i in range(len(X)):
        write_chain_netlist(CIRCUIT_INIT, encode(X[i]), NETLIST, n_blocks=N_BLOCKS)
        v = eval_chain(NETLIST, READ)
        S.append([v[n] for n in READ])
    return np.array(S)


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    Xtr, ytr, Xte, yte = load_dataset(name)
    print(f"Stage 1 | {name} | {len(ytr)} train / {len(yte)} test")
    print("Caching circuit states...")
    Str, Ste = states(Xtr), states(Xte)
    mu, sd = Str.mean(0), Str.std(0) + 1e-9
    Ntr, Nte = (Str - mu) / sd, (Ste - mu) / sd

    nC = int(max(ytr.max(), yte.max())) + 1
    ro = Readout(m_state=N_BLOCKS, n_class=nC, seed=0)
    params = {"W": ro.W, "b": ro.b}
    opt = Adam(params, lr=LR)

    print(f"{'Ep':>4}  {'loss':>8}  {'train_acc':>9}  {'test_acc':>8}")
    print("-" * 40)
    hist = {"epoch": [], "loss": [], "tr": [], "te": []}
    best_te, best_ep = -1.0, -1
    log_csv = os.path.join(RESULTS, f"{name}_stage1_log.csv")

    with open(log_csv, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["epoch", "loss", "train_acc", "test_acc"])
        for ep in range(1, EPOCHS + 1):
            gW = np.zeros_like(ro.W); gb = np.zeros_like(ro.b)
            logits_tr = np.zeros((len(ytr), nC)); losses = []
            for i in range(len(ytr)):
                ro.W, ro.b = params["W"], params["b"]
                lg = ro.forward(Ntr[i]); logits_tr[i] = lg
                losses.append(cross_entropy(softmax(lg[None, :]), ytr[i:i+1]))
                g, _ = ro.backward(ce_grad(lg, ytr[i]))
                gW += g["W"]; gb += g["b"]
            params = opt.step(params, {"W": gW / len(ytr), "b": gb / len(ytr)})
            ro.W, ro.b = params["W"], params["b"]
            logits_te = np.array([ro.forward(Nte[i]) for i in range(len(yte))])
            tr = float((logits_tr.argmax(1) == ytr).mean())
            te = float((logits_te.argmax(1) == yte).mean())
            loss = float(np.mean(losses))
            hist["epoch"].append(ep); hist["loss"].append(loss); hist["tr"].append(tr); hist["te"].append(te)
            wr.writerow([ep, f"{loss:.6f}", f"{tr:.4f}", f"{te:.4f}"]); f.flush()
            if te > best_te:
                best_te, best_ep = te, ep
                with open(os.path.join(RESULTS, f"{name}_stage1_best.json"), "w") as bf:
                    json.dump({"epoch": ep, "test_acc": te, "train_acc": tr}, bf, indent=2)
            if ep % 20 == 0 or ep == 1:
                print(f"{ep:>4}  {loss:>8.4f}  {tr:>9.2f}  {te:>8.2f}")

    print(f"\nStage 1 {name} done. Best test acc={best_te:.2f} @ep{best_ep} "
          f"(final train {hist['tr'][-1]:.2f} / test {hist['te'][-1]:.2f})")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(hist["epoch"], hist["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss")
    ax[0].set_title(f"Loss: {hist['loss'][0]:.3f} -> {hist['loss'][-1]:.3f}"); ax[0].grid(alpha=0.3)
    ax[1].plot(hist["epoch"], hist["tr"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(hist["epoch"], hist["te"], color="#1baf7a", lw=1.6, label="test")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_te:.2f}"); ax[1].legend(frameon=False); ax[1].grid(alpha=0.3)
    fig.suptitle(f"KirchhoffNet chain -- {name} Stage 1 (softmax readout on frozen 100ns state)")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, f"{name}_stage1_curve.png"), dpi=140)
    print(f"Saved -> results/{name}_stage1_curve.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
