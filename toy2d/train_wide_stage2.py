"""
train_wide_stage2.py -- train the WIDE analog layer's CIRCUIT parameters
themselves, via the 100ns backward transient adjoint.

This is the "hardware, not software" version of train_wide.py. There, the wide
layer was a FROZEN random reservoir and only the software softmax readout was
trained. Here, the 3*N per-unit circuit parameters

    VTH_j (PMOS-load theta),  VB_j (tail bias),  VN_j (per-unit reference)

are trained end-to-end through the simulator's backward adjoint -- so the
diversity and thresholding are learned in the CIRCUIT. The (random-diverse)
encoder stays fixed; the readout is co-trained (convex) so the accuracy signal
stays clean while the circuit moves.

Recipe (from the validated bin_class / train_stage2 approach):
  - freely-trained readout (convex Adam) drives accuracy,
  - fixed feature standardization (mu,sd from the initial state),
  - a single PRE-CHECKED gentle adjoint step on the circuit each epoch --
    rejected (with LR backoff) if it raises the train loss or breaks convergence,
  - every simulator call is per-sample robust: a sample whose SPICE solve fails
    is skipped; a tentative circuit step that causes failures is rejected.

Gradient path (single sample i, read node u_j):
  dL/dVTH_j = sum_j (dL/du_j) * dV(u_j,100ns)/dVTH_j     [adjoint sensitivity]
The dL/du_j come from the softmax readout; the sensitivities come from run_chain.

Usage:  python train_wide_stage2.py --dataset {twomoon|circle|2spirals}
"""
import os, json, csv, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_wide import write_wide_netlist
from simulator_api import run_chain, eval_chain
from dataset import load_dataset, DATASETS
from model import Adam, softmax, Readout
from wide_common import (N_UNITS, CIRC_NAMES, READ, BOUNDS,
                         init_encoder, encode_wide, circ_dict, circ_init)

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
EPOCHS   = 90
LR_CIRC  = 0.0008
LR_READ  = 0.05


def forward_states(X, circ_vec, W, b, netlist):
    """Forward-only; returns (S, valid_idx). Skips samples whose solve fails."""
    S, valid = [], []
    for i in range(len(X)):
        write_wide_netlist(circ_dict(circ_vec), encode_wide(X[i], W, b),
                           netlist, n_units=N_UNITS)
        try:
            v = eval_chain(netlist, READ)
            S.append([v[n] for n in READ]); valid.append(i)
        except Exception:
            continue
    return (np.array(S) if S else np.zeros((0, len(READ)))), np.array(valid, dtype=int)


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    netlist = os.path.join(BASE, f"tmp_wide_stage2_{name}.sp")  # per-dataset (parallel-safe)
    Xtr, ytr, Xte, yte = load_dataset(name)
    nC = int(max(ytr.max(), yte.max())) + 1
    onehot = np.eye(nC)
    W, b = init_encoder(seed=0)          # fixed random-diverse encoder
    print(f"Wide Stage 2 | {name} | {len(ytr)} train / {len(yte)} test | "
          f"N={N_UNITS} units | trainable circuit params: {len(CIRC_NAMES)} "
          f"(VTH/VB/VN x {N_UNITS})")

    circ = circ_init()
    S0, v0 = forward_states(Xtr, circ, W, b, netlist)
    if len(v0) == 0:
        raise RuntimeError("initial circuit failed on all train samples")
    mu, sd = S0.mean(0), S0.std(0) + 1e-9
    ro = Readout(m_state=len(READ), n_class=nC, seed=0)
    params = {"circ": circ.copy(), "Wout": ro.W.copy(), "bout": ro.b.copy()}
    opt_circ = Adam({"circ": params["circ"]}, lr=LR_CIRC)
    opt_read = Adam({"Wout": params["Wout"], "bout": params["bout"]}, lr=LR_READ)

    # reference: the frozen-reservoir readout-only result, if train_wide.py ran
    ref_te = -1.0
    refp = os.path.join(RESULTS, f"{name}_wide_best.json")
    if os.path.exists(refp):
        ref_te = json.load(open(refp)).get("test_acc", -1.0)

    def metrics(X, y, circ_vec):
        S, valid = forward_states(X, circ_vec, W, b, netlist)
        if len(valid) == 0:
            return float("nan"), float("nan")
        Sn = (S - mu) / sd
        logits = Sn @ params["Wout"].T + params["bout"]
        yv = y[valid]
        ls = float(-np.log(softmax(logits)[np.arange(len(yv)), yv] + 1e-12).mean())
        acc = float((logits.argmax(1) == yv).mean())
        return ls, acc

    print(f"{'Ep':>4}  {'loss':>8}  {'train':>7}  {'test':>6}  {'lr_c':>8}")
    hist = {"epoch": [], "loss": [], "tr": [], "te": []}
    best_te, best_ep, lr_circ = -1.0, -1, LR_CIRC
    log_csv = os.path.join(RESULTS, f"{name}_wide_stage2_log.csv")

    with open(log_csv, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["epoch", "loss", "train_acc", "test_acc", "lr_circ"])
        for ep in range(1, EPOCHS + 1):
            # 1) simulate current circuit -> cache states + sensitivities (robust)
            S, SENS, yv = [], [], []
            for i in range(len(ytr)):
                write_wide_netlist(circ_dict(params["circ"]), encode_wide(Xtr[i], W, b),
                                   netlist, n_units=N_UNITS)
                try:
                    v_out, sens = run_chain(netlist, READ, CIRC_NAMES)
                except Exception:
                    continue
                S.append([v_out[nd] for nd in READ])
                SENS.append([[sens[nd][p] for p in CIRC_NAMES] for nd in READ])
                yv.append(ytr[i])
            if not S:
                print(f"{ep:>4}  all train samples failed; stopping."); break
            S = np.array(S); SENS = np.array(SENS); yv = np.array(yv)
            Sn = (S - mu) / sd

            # 2) readout: free Adam step (convex)
            logits = Sn @ params["Wout"].T + params["bout"]
            G = (softmax(logits) - onehot[yv]) / len(yv)
            rp = opt_read.step({"Wout": params["Wout"], "bout": params["bout"]},
                               {"Wout": G.T @ Sn, "bout": G.sum(0)})
            params["Wout"], params["bout"] = rp["Wout"], rp["bout"]

            tr_loss = float(-np.log(softmax(Sn @ params["Wout"].T + params["bout"])[np.arange(len(yv)), yv] + 1e-12).mean())
            tr_acc = float(((Sn @ params["Wout"].T + params["bout"]).argmax(1) == yv).mean())
            te_loss, te_acc = metrics(Xte, yte, params["circ"])

            # 3) circuit: one pre-checked gentle adjoint step over all 3N params
            logits = Sn @ params["Wout"].T + params["bout"]
            G = (softmax(logits) - onehot[yv]) / len(yv)
            dL_dS = (G @ params["Wout"]) / sd            # (n, N) dL/d(state u_j)
            g_circ = np.einsum("ij,ijk->k", dL_dS, SENS) # (3N,) via adjoint
            ckpt = params["circ"].copy()
            cp = opt_circ.step({"circ": params["circ"]}, {"circ": g_circ})
            new_circ = cp["circ"].copy()
            for k, (lo, hi) in enumerate(BOUNDS):
                new_circ[k] = np.clip(new_circ[k], lo, hi)
            try_loss, _ = metrics(Xtr, ytr, new_circ)
            if np.isfinite(try_loss) and try_loss <= tr_loss * 1.02:
                params["circ"] = new_circ
            else:
                params["circ"] = ckpt                    # reject bad/failing step
                lr_circ = max(lr_circ * 0.6, 1e-5)
                opt_circ = Adam({"circ": params["circ"]}, lr=lr_circ)

            hist["epoch"].append(ep); hist["loss"].append(tr_loss)
            hist["tr"].append(tr_acc); hist["te"].append(te_acc)
            wr.writerow([ep, f"{tr_loss:.6f}", f"{tr_acc:.4f}", f"{te_acc:.4f}", f"{lr_circ:.2e}"]); f.flush()
            if np.isfinite(te_acc) and te_acc > best_te:
                best_te, best_ep = te_acc, ep
                json.dump({"epoch": ep, "test_acc": te_acc, "train_acc": tr_acc,
                           "circ": circ_dict(params["circ"]),
                           "Wout": params["Wout"].tolist(), "bout": params["bout"].tolist(),
                           "mu": mu.tolist(), "sd": sd.tolist()},
                          open(os.path.join(RESULTS, f"{name}_wide_stage2_best.json"), "w"), indent=2)
            if ep % 10 == 0 or ep == 1:
                print(f"{ep:>4}  {tr_loss:>8.4f}  {tr_acc:>7.2f}  {te_acc:>6.2f}  {lr_circ:>8.2e}")

    ref_txt = f" (frozen-reservoir readout-only was {ref_te:.2f})" if ref_te >= 0 else ""
    print(f"\nWide Stage 2 {name} done. Best test acc={best_te:.2f} @ep{best_ep}{ref_txt}")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(hist["epoch"], hist["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss"); ax[0].grid(alpha=0.3)
    ax[0].set_title(f"Loss: {hist['loss'][0]:.3f} -> {hist['loss'][-1]:.3f}")
    ax[1].plot(hist["epoch"], hist["tr"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(hist["epoch"], hist["te"], color="#1baf7a", lw=1.6, label="test")
    if ref_te >= 0:
        ax[1].axhline(ref_te, color="#c3c2b7", ls="--", lw=1, label="frozen reservoir")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_te:.2f}"); ax[1].legend(frameon=False); ax[1].grid(alpha=0.3)
    fig.suptitle(f"KirchhoffNet WIDE layer ({N_UNITS} units) -- {name} "
                 f"(circuit VTH/VB/VN trained via 100ns adjoint)")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, f"{name}_wide_stage2_curve.png"), dpi=140)
    print(f"Saved -> results/{name}_wide_stage2_curve.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle", choices=DATASETS)
    main(ap.parse_args().dataset)
