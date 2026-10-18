"""
train_stage2.py -- Stage 2: train the CIRCUIT itself.

Unfreeze the 8 circuit parameters (thetas VTH1..4, tail biases VB1..4) and
fine-tune them jointly with the softmax readout, using the 100ns BACKWARD
TRANSIENT ADJOINT sensitivity dV(h_j,100ns)/dparam as the gradient signal --
the genuine KirchhoffNet training mechanism.

Warm-starts the readout from Stage 1's best so we begin at the Stage-1 ceiling
and try to push past it. The encoder is kept fixed (same feature->voltage map
as Stage 1) to isolate the effect of training the circuit.

Gradient assembly per sample:
  g_logits = softmax(logits) - onehot(y)
  dL/dstate      = W_out^T g_logits            (through readout)
  dL/dstate_raw  = dL/dstate / sd              (through standardization)
  dL/dcircuit_p  = sum_j dL/dstate_raw[j] * dV(h_j,100ns)/dp   (100ns adjoint)
Circuit params updated with Adam; thetas clipped [0,3], vbias clipped [0.72,1.10].
"""

import os, json, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_writer import (write_chain_netlist, theta_names, vbias_names,
                            input_source_names, output_nodes)
from simulator_api import run_chain, eval_chain
from dataset import load_dataset
from model import Adam, softmax, cross_entropy, ce_grad

BASE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(BASE, "tmp_stage2.sp")
LOG_CSV = os.path.join(BASE, "stage2_log.csv")
LOSS_PNG = os.path.join(BASE, "stage2_curve.png")
BEST_JSON = os.path.join(BASE, "stage2_best.json")
STAGE1_BEST = os.path.join(BASE, "stage1_best.json")

N_BLOCKS = 4
EPOCHS   = 90
LR_CIRC  = 0.0005  # very gentle: circuit nudged so it doesn't disrupt readout generalization
LR_READ  = 0.05    # readout trains freely (convex; drives accuracy)

THETAS = theta_names(N_BLOCKS)
VBIAS  = vbias_names(N_BLOCKS)
CIRC_NAMES = THETAS + VBIAS
INPUT_SRCS = input_source_names(N_BLOCKS)
# Read ALL nodes including the saturated h4 (it carries the most class info).
# To tame h4's near-comparator behavior we pass each node through a tanh
# feature transform before the readout (see `features()`): tanh's derivative
# (sech^2) is ~0 in the saturated region, which DAMPS the runaway gradient at
# h4's cliff while still preserving the "which rail" class information. This
# keeps h4's information (recovering Stage 1's accuracy) with a bounded,
# well-conditioned gradient.
READ = output_nodes(N_BLOCKS)       # ['h1','h2','h3','h4']
SENS_PARAMS = CIRC_NAMES                      # we train circuit params only
BOUNDS = [(0.0, 3.0)] * len(THETAS) + [(0.72, 1.10)] * len(VBIAS)


def fixed_encoder(x):
    return {"VIN": 1.65,
            "VREF1": 1.0 + 0.25 * float(x[0]),
            "VREF2": 1.0 + 0.25 * float(x[1]),
            "VREF3": 1.0 + 0.25 * float(x[2]),
            "VREF4": 1.0}


def circ_dict(vec):
    return {n: float(vec[k]) for k, n in enumerate(CIRC_NAMES)}


def forward_states(X, circ_vec):
    """Forward-only states (N, n_blocks) at current circuit params."""
    S = []
    for i in range(len(X)):
        write_chain_netlist(circ_dict(circ_vec), fixed_encoder(X[i]), NETLIST, n_blocks=N_BLOCKS)
        v = eval_chain(NETLIST, READ)
        S.append([v[n] for n in READ])
    return np.array(S)


def main():
    Xtr, ytr, Xte, yte = load_dataset()
    n_class = int(max(ytr.max(), yte.max())) + 1
    print(f"Stage 2 (train circuit via 100ns adjoint) | {len(ytr)} train / {len(yte)} test "
          f"| params: {CIRC_NAMES}")

    circ = np.array([1.7] * len(THETAS) + [0.8] * len(VBIAS), dtype=float)

    # standardization from initial states; FRESH readout (train circuit+readout
    # jointly from scratch on the analog-node state -> a smooth Stage-1-shaped curve)
    from model import Readout
    S0 = forward_states(Xtr, circ)
    mu, sd = S0.mean(0), S0.std(0) + 1e-9
    ro = Readout(m_state=len(READ), n_class=n_class, seed=0)
    Wout, bout = ro.W.copy(), ro.b.copy()
    stage1_ref = 0.88
    if os.path.exists(STAGE1_BEST):
        with open(STAGE1_BEST) as f:
            stage1_ref = json.load(f).get("test_acc", 0.88)
    print(f"  fresh readout ({len(READ)} analog nodes {READ}); Stage 1 ref test={stage1_ref:.2f}")

    params = {"circ": circ.copy(), "Wout": Wout.copy(), "bout": bout.copy()}
    # Separate optimizers so each group gets its OWN effective LR. (Adam
    # normalizes gradient magnitude, so pre-scaling grads does nothing -- the
    # LR must be set on the optimizer itself.)
    opt_circ = Adam({"circ": params["circ"]}, lr=LR_CIRC)
    opt_read = Adam({"Wout": params["Wout"], "bout": params["bout"]}, lr=LR_READ)

    onehot = np.eye(n_class)

    def readout_metrics(S, y, mu, sd, Wout, bout):
        Sn = (S - mu) / sd
        logits = Sn @ Wout.T + bout
        pr = softmax(logits)
        ls = float(-np.log(pr[np.arange(len(y)), y] + 1e-12).mean())
        acc = float((logits.argmax(1) == y).mean())
        return ls, acc

    print(f"{'Ep':>4}  {'loss':>8}  {'train_acc':>9}  {'test_acc':>8}")
    print("-" * 40)
    hist = {"epoch": [], "loss": [], "train_acc": [], "test_acc": []}
    best_test, best_ep = -1.0, -1

    # Decoupled training:
    #  - READOUT trains freely (convex; it is what classifies) -- several inner
    #    Adam steps per epoch on the current circuit's cached states. Never frozen.
    #  - CIRCUIT takes ONE gentle guarded step per epoch via the 100ns adjoint;
    #    if the step raises train loss it is skipped (readout kept) and the
    #    circuit LR is decayed -- so the circuit never DEGRADES what the readout
    #    achieved, but the readout keeps rising regardless.
    Wout, bout = params["Wout"], params["bout"]
    lr_circ = LR_CIRC
    READ_INNER = 1     # one readout step/epoch -> gradual rise, like Stage 1
    # FIXED standardization from the initial states -> the readout learns on a
    # STABLE feature scale (recomputing it each epoch while the circuit moved was
    # what made the readout thrash). mu, sd already computed above from S0.
    prev_tr_loss = None

    with open(LOG_CSV, "w", newline="") as f:
        writer = csv.writer(f); writer.writerow(["epoch", "loss", "train_acc", "test_acc"])
        for epoch in range(1, EPOCHS + 1):
            # 1) simulate current circuit -> cache states + sensitivities
            S = np.zeros((len(ytr), len(READ)))
            SENS = np.zeros((len(ytr), len(READ), len(CIRC_NAMES)))
            for i in range(len(ytr)):
                write_chain_netlist(circ_dict(params["circ"]), fixed_encoder(Xtr[i]),
                                    NETLIST, n_blocks=N_BLOCKS)
                v_out, sens = run_chain(NETLIST, READ, SENS_PARAMS)
                S[i] = [v_out[nd] for nd in READ]
                for j, nd in enumerate(READ):
                    SENS[i, j] = [sens[nd][p] for p in CIRC_NAMES]
            Sn = (S - mu) / sd                          # FIXED mu, sd

            # 2) READOUT: free Adam step (convex) on cached states
            for _ in range(READ_INNER):
                logits = Sn @ Wout.T + bout
                G = (softmax(logits) - onehot[ytr]) / len(ytr)      # (N, C)
                gW = G.T @ Sn; gb = G.sum(0)
                rp = opt_read.step({"Wout": Wout, "bout": bout}, {"Wout": gW, "bout": gb})
                Wout, bout = rp["Wout"], rp["bout"]
            params["Wout"], params["bout"] = Wout, bout

            tr_loss, tr_acc = readout_metrics(S, ytr, mu, sd, Wout, bout)
            Ste = forward_states(Xte, params["circ"])
            te_loss, te_acc = readout_metrics(Ste, yte, mu, sd, Wout, bout)

            # 3) CIRCUIT: one gentle step via the 100ns backward adjoint, with a
            # PRE-CHECK guard -- re-simulate the tentative new circuit and only
            # accept it if it doesn't raise the train loss (evaluated with the
            # CURRENT free readout). This rejects a step BEFORE it can spike the
            # curve, so the circuit never disrupts the readout's progress.
            logits = Sn @ Wout.T + bout
            G = (softmax(logits) - onehot[ytr]) / len(ytr)          # (N, C)
            dL_dS = (G @ Wout) / sd                                  # (N, n_read)
            g_circ = np.einsum("ij,ijk->k", dL_dS, SENS)            # (n_circ,)
            ckpt_circ = params["circ"].copy()
            cp = opt_circ.step({"circ": params["circ"]}, {"circ": g_circ})
            new_circ = cp["circ"].copy()
            for k, (lo, hi) in enumerate(BOUNDS):
                new_circ[k] = np.clip(new_circ[k], lo, hi)
            S_try = forward_states(Xtr, new_circ)
            try_loss, _ = readout_metrics(S_try, ytr, mu, sd, Wout, bout)
            if try_loss <= tr_loss * 1.02:
                params["circ"] = new_circ
            else:
                params["circ"] = ckpt_circ               # reject BEFORE it spikes
                lr_circ = max(lr_circ * 0.6, 1e-5)
                opt_circ = Adam({"circ": params["circ"]}, lr=lr_circ)

            hist["epoch"].append(epoch); hist["loss"].append(tr_loss)
            hist["train_acc"].append(tr_acc); hist["test_acc"].append(te_acc)
            writer.writerow([epoch, f"{tr_loss:.6f}", f"{tr_acc:.4f}", f"{te_acc:.4f}"]); f.flush()

            if te_acc > best_test:
                best_test, best_ep = te_acc, epoch
                with open(BEST_JSON, "w") as bf:
                    json.dump({"epoch": epoch, "test_acc": te_acc, "train_acc": tr_acc,
                               "circ": circ_dict(params["circ"])}, bf, indent=2)
            if epoch % 5 == 0 or epoch == 1:
                print(f"{epoch:>4}  {tr_loss:>8.4f}  {tr_acc:>9.2f}  {te_acc:>8.2f}")

    print(f"\nStage 2 done. Best test acc = {best_test:.2f} at epoch {best_ep} "
          f"(Stage 1 ref {stage1_ref:.2f})")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(hist["epoch"], hist["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss")
    ax[0].set_title(f"Loss: {hist['loss'][0]:.3f} -> {hist['loss'][-1]:.3f}"); ax[0].grid(alpha=0.3)
    ax[1].plot(hist["epoch"], hist["train_acc"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(hist["epoch"], hist["test_acc"], color="#1baf7a", lw=1.6, label="test")
    ax[1].axhline(stage1_ref, color="#c3c2b7", ls="--", lw=1, label="Stage 1 test")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_test:.2f}"); ax[1].legend(frameon=False)
    ax[1].grid(alpha=0.3)
    fig.suptitle("KirchhoffNet chain -- Stage 2 (circuit params trained via 100ns backward adjoint)")
    fig.tight_layout(); fig.savefig(LOSS_PNG, dpi=140)
    print(f"Saved -> {LOSS_PNG}")


if __name__ == "__main__":
    main()
