"""
train.py -- KirchhoffNet feedforward-chain classifier.

Stage 1 (this file's default): freeze the circuit, run each sample through the
open chain ONCE, cache its 100ns state vector [V(h1..hn)], then train a softmax
readout on the cached (standardized) states. This is a convex problem -> the
loss decreases and accuracy increases SMOOTHLY, in seconds, up to the circuit's
linear-readout ceiling (~0.93 train, per diag_structure.py).

Stage 2 (train_stage2.py) then unfreezes the circuit params and fine-tunes them
via the 100ns backward transient adjoint to push past the Stage-1 ceiling.
"""

import os, json, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_writer import (write_chain_netlist, theta_names, vbias_names,
                            input_source_names, output_nodes)
from simulator_api import eval_chain
from dataset import load_dataset
from model import Readout, Adam, softmax, cross_entropy, ce_grad

BASE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(BASE, "tmp_stage1.sp")
LOG_CSV = os.path.join(BASE, "stage1_log.csv")
LOSS_PNG = os.path.join(BASE, "stage1_curve.png")
BEST_JSON = os.path.join(BASE, "stage1_best.json")

N_BLOCKS = 4
EPOCHS   = 200
LR       = 0.05

CIRCUIT_INIT = {**{n: 1.7 for n in theta_names(N_BLOCKS)},
                **{n: 0.8 for n in vbias_names(N_BLOCKS)}}
READ = output_nodes(N_BLOCKS)


def fixed_encoder(x):
    """Fixed (untrained in Stage 1) feature->voltage map, same as diag_structure."""
    return {
        "VIN":   1.65,
        "VREF1": 1.0 + 0.25 * float(x[0]),
        "VREF2": 1.0 + 0.25 * float(x[1]),
        "VREF3": 1.0 + 0.25 * float(x[2]),
        "VREF4": 1.0,
    }


def collect_states(X):
    """Run each sample through the frozen chain once; return (N, n_blocks) states."""
    S = []
    for i in range(len(X)):
        write_chain_netlist(CIRCUIT_INIT, fixed_encoder(X[i]), NETLIST, n_blocks=N_BLOCKS)
        v = eval_chain(NETLIST, READ)
        S.append([v[n] for n in READ])
    return np.array(S)


def accuracy(logits_batch, y):
    return float((logits_batch.argmax(1) == y).mean())


def main():
    Xtr, ytr, Xte, yte = load_dataset()
    print(f"Stage 1 (readout on frozen circuit) | {len(ytr)} train / {len(yte)} test "
          f"| chain={N_BLOCKS} stages, read {READ} @100ns")

    print("Caching circuit states (one sim per sample)...")
    Str = collect_states(Xtr)
    Ste = collect_states(Xte)

    # standardize states using train stats
    mu, sd = Str.mean(0), Str.std(0) + 1e-9
    Str_n = (Str - mu) / sd
    Ste_n = (Ste - mu) / sd

    n_class = int(max(ytr.max(), yte.max())) + 1
    readout = Readout(m_state=N_BLOCKS, n_class=n_class, seed=0)
    params = {"W": readout.W, "b": readout.b}
    opt = Adam(params, lr=LR)

    print(f"{'Ep':>4}  {'loss':>8}  {'train_acc':>9}  {'test_acc':>8}  best")
    print("-" * 46)

    history = {"epoch": [], "loss": [], "train_acc": [], "test_acc": []}
    best_test, best_ep = -1.0, -1

    with open(LOG_CSV, "w", newline="") as f:
        writer = csv.writer(f); writer.writerow(["epoch", "loss", "train_acc", "test_acc"])

        for epoch in range(1, EPOCHS + 1):
            # full-batch forward + grad
            gW = np.zeros_like(readout.W); gb = np.zeros_like(readout.b)
            logits_tr = np.zeros((len(ytr), n_class))
            losses = []
            for i in range(len(ytr)):
                readout.W, readout.b = params["W"], params["b"]
                logit = readout.forward(Str_n[i])
                logits_tr[i] = logit
                losses.append(cross_entropy(softmax(logit[None, :]), ytr[i:i+1]))
                g = ce_grad(logit, ytr[i])
                grads, _ = readout.backward(g)
                gW += grads["W"]; gb += grads["b"]
            gW /= len(ytr); gb /= len(ytr)
            params = opt.step(params, {"W": gW, "b": gb})

            # eval
            readout.W, readout.b = params["W"], params["b"]
            logits_te = np.array([readout.forward(Ste_n[i]) for i in range(len(yte))])
            tr_acc = accuracy(logits_tr, ytr)
            te_acc = accuracy(logits_te, yte)
            loss = float(np.mean(losses))

            history["epoch"].append(epoch); history["loss"].append(loss)
            history["train_acc"].append(tr_acc); history["test_acc"].append(te_acc)
            writer.writerow([epoch, f"{loss:.6f}", f"{tr_acc:.4f}", f"{te_acc:.4f}"]); f.flush()

            flag = ""
            if te_acc > best_test:
                best_test, best_ep = te_acc, epoch
                with open(BEST_JSON, "w") as bf:
                    json.dump({"epoch": epoch, "test_acc": te_acc, "train_acc": tr_acc,
                               "loss": loss, "readout_W": params["W"].tolist(),
                               "readout_b": params["b"].tolist()}, bf, indent=2)
                flag = "  *"
            if epoch % 10 == 0 or epoch == 1:
                print(f"{epoch:>4}  {loss:>8.4f}  {tr_acc:>9.2f}  {te_acc:>8.2f}{flag}")

    print(f"\nStage 1 done. Best test acc = {best_test:.2f} at epoch {best_ep} "
          f"(final train {history['train_acc'][-1]:.2f} / test {history['test_acc'][-1]:.2f})")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(history["epoch"], history["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss")
    ax[0].set_title(f"Loss: {history['loss'][0]:.3f} -> {history['loss'][-1]:.3f}")
    ax[0].grid(alpha=0.3)
    ax[1].plot(history["epoch"], history["train_acc"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(history["epoch"], history["test_acc"], color="#1baf7a", lw=1.6, label="test")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_test:.2f}"); ax[1].legend(frameon=False)
    ax[1].grid(alpha=0.3)
    fig.suptitle("KirchhoffNet chain -- Stage 1 (softmax readout on frozen 100ns circuit state)")
    fig.tight_layout(); fig.savefig(LOSS_PNG, dpi=140)
    print(f"Saved -> {LOSS_PNG}")


if __name__ == "__main__":
    main()
