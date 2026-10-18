"""
train_spider.py -- train the SPIDERNET crossbar's per-edge thetas via the 100 ns
transient adjoint, for binary classification of the 2-D toy datasets.

Data flow (very basic software pre/post-processing):
  (x,y) --encode_rails--> 4 rail voltages v1..v4 --> [4x4 theta-gated crossbar]
  --settle 100ns--> read net1..net4 --standardize--> softmax readout (4->2) --> CE loss.

The n_rails*n_nodes thetas are trained through the simulator's backward adjoint;
the linear readout is co-trained with ordinary analytic gradients (convex).
Recipe mirrors the validated toy2d_serial_diff Stage-2 loop:
  - freely-trained readout (drives accuracy),
  - fixed feature standardization (mu,sd from the initial circuit state),
  - one PRE-CHECKED gentle adjoint step on the circuit each epoch, rejected (with
    LR backoff) if it raises the train loss or breaks convergence,
  - every simulator call is per-sample robust (skip non-convergent samples).

Gradient path (single sample i, read node net_j):
  dL/dVTH_k = sum_j (dL/dnet_j) * dV(net_j,100ns)/dVTH_k     [adjoint sensitivity]

The sensitivity tensor is BLOCK-DIAGONAL -- the crossbar has no node-to-node
coupling, so net_j is only reachable from its own n_rails thetas. Each theta
still receives gradient, just from exactly one read node.

Usage:  python train_spider.py --dataset {twomoon|circle|2spirals}
"""
import os, json, csv, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_spider import write_spider_netlist
from simulator_api import run_chain, eval_chain
from dataset import load_dataset, DATASETS
from model import Adam, softmax, Readout
from spider_common import (N_RAILS, N_NODES, N_EDGES, CIRC_NAMES, READ, BOUNDS,
                           RAIL_CENTER, init_rail_encoder, encode_rails,
                           circ_dict, circ_init)

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
EPOCHS   = 90
LR_CIRC  = 0.01     # thetas live in a ~1.4 V band; Adam steps ~lr per epoch
LR_READ  = 0.05


def _write(circ_vec, x, W, b, netlist):
    write_spider_netlist(circ_dict(circ_vec), encode_rails(x, W, b), netlist,
                         n_rails=N_RAILS, n_nodes=N_NODES, ic_center=RAIL_CENTER)


def forward_states(X, circ_vec, W, b, netlist):
    """Forward-only; returns (S, valid_idx). Skips samples whose solve fails."""
    S, valid = [], []
    for i in range(len(X)):
        _write(circ_vec, X[i], W, b, netlist)
        try:
            v = eval_chain(netlist, READ)
            S.append([v[n] for n in READ]); valid.append(i)
        except Exception:
            continue
    return (np.array(S) if S else np.zeros((0, len(READ)))), np.array(valid, dtype=int)


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    netlist = os.path.join(BASE, f"tmp_spider_{name}.sp")   # per-dataset (parallel-safe)
    Xtr, ytr, Xte, yte = load_dataset(name)
    nC = int(max(ytr.max(), yte.max())) + 1
    onehot = np.eye(nC)
    W, b = init_rail_encoder(seed=0)          # fixed basic rail encoder
    print(f"Spider | {name} | {len(ytr)} train / {len(yte)} test | "
          f"{N_RAILS} rails x {N_NODES} nodes | trainable thetas: {N_EDGES}")

    circ = circ_init(seed=0)
    S0, v0 = forward_states(Xtr, circ, W, b, netlist)
    if len(v0) == 0:
        raise RuntimeError("initial spidernet failed on all train samples")
    mu, sd = S0.mean(0), S0.std(0) + 1e-9
    ro = Readout(m_state=len(READ), n_class=nC, seed=0)
    params = {"circ": circ.copy(), "Wout": ro.W.copy(), "bout": ro.b.copy()}
    opt_circ = Adam({"circ": params["circ"]}, lr=LR_CIRC)
    opt_read = Adam({"Wout": params["Wout"], "bout": params["bout"]}, lr=LR_READ)

    def metrics(X, y, circ_vec):
        S, valid = forward_states(X, circ_vec, W, b, netlist)
        if len(valid) == 0:
            return float("nan"), float("nan"), 0
        Sn = (S - mu) / sd
        logits = Sn @ params["Wout"].T + params["bout"]
        yv = y[valid]
        ls = float(-np.log(softmax(logits)[np.arange(len(yv)), yv] + 1e-12).mean())
        acc = float((logits.argmax(1) == yv).mean())
        return ls, acc, len(valid)

    print(f"{'Ep':>4}  {'loss':>8}  {'train':>7}  {'test':>6}  {'lr_c':>8}")
    hist = {"epoch": [], "loss": [], "tr": [], "te": []}
    best_te, best_ep, lr_circ = -1.0, -1, LR_CIRC
    log_csv = os.path.join(RESULTS, f"{name}_spider_log.csv")

    with open(log_csv, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["epoch", "loss", "train_acc", "test_acc", "lr_circ"])
        for ep in range(1, EPOCHS + 1):
            # 1) simulate current crossbar -> cache states + sensitivities (robust)
            S, SENS, yv = [], [], []
            for i in range(len(ytr)):
                _write(params["circ"], Xtr[i], W, b, netlist)
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
            te_loss, te_acc, _ = metrics(Xte, yte, params["circ"])

            # 3) circuit: one pre-checked gentle adjoint step over all thetas
            logits = Sn @ params["Wout"].T + params["bout"]
            G = (softmax(logits) - onehot[yv]) / len(yv)
            dL_dS = (G @ params["Wout"]) / sd            # (n, N_NODES) dL/d(state net_j)
            g_circ = np.einsum("ij,ijk->k", dL_dS, SENS) # (N_EDGES,) via adjoint
            ckpt = params["circ"].copy()
            cp = opt_circ.step({"circ": params["circ"]}, {"circ": g_circ})
            new_circ = cp["circ"].copy()
            for k, (lo, hi) in enumerate(BOUNDS):
                new_circ[k] = np.clip(new_circ[k], lo, hi)
            try_loss, _, try_nv = metrics(Xtr, ytr, new_circ)
            # accept only if the step (a) doesn't raise the loss AND (b) doesn't break
            # convergence -- the tentative circuit must still solve >=95% of train samples.
            # (Guarding on the valid count is essential: metrics() skips non-convergent
            #  samples, so a loss check alone would happily accept a degenerate circuit.)
            if np.isfinite(try_loss) and try_loss <= tr_loss * 1.02 and try_nv >= 0.95 * len(ytr):
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
                          open(os.path.join(RESULTS, f"{name}_spider_best.json"), "w"), indent=2)
            if ep % 10 == 0 or ep == 1:
                print(f"{ep:>4}  {tr_loss:>8.4f}  {tr_acc:>7.2f}  {te_acc:>6.2f}  {lr_circ:>8.2e}")

    print(f"\nSpider {name} done. Best test acc={best_te:.2f} @ep{best_ep}")

    # --- final sensitivity dump: dV(net_j,100ns)/dVTH_k for every train sample,
    #     read node, and theta, using the FINAL trained circuit ---
    sens_csv = os.path.join(RESULTS, f"{name}_spider_sensitivities.csv")
    n_written = 0
    with open(sens_csv, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["sample", "label", "read_node", "param", "V_node_100ns", "dVnode_dparam"])
        for i in range(len(ytr)):
            _write(params["circ"], Xtr[i], W, b, netlist)
            try:
                v_out, sens = run_chain(netlist, READ, CIRC_NAMES)
            except Exception:
                continue
            for nd in READ:
                for p in CIRC_NAMES:
                    wr.writerow([i, int(ytr[i]), nd, p, f"{v_out[nd]:.6f}", f"{sens[nd][p]:.6e}"])
            n_written += 1
    print(f"Saved -> results/{name}_spider_sensitivities.csv "
          f"({n_written} samples x {len(READ)} nodes x {len(CIRC_NAMES)} params)")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(hist["epoch"], hist["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss"); ax[0].grid(alpha=0.3)
    ax[0].set_title(f"Loss: {hist['loss'][0]:.3f} -> {hist['loss'][-1]:.3f}")
    ax[1].plot(hist["epoch"], hist["tr"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(hist["epoch"], hist["te"], color="#1baf7a", lw=1.6, label="test")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_te:.2f}"); ax[1].legend(frameon=False); ax[1].grid(alpha=0.3)
    fig.suptitle(f"KirchhoffNet SPIDERNET ({N_RAILS}x{N_NODES} crossbar) -- {name} "
                 f"(rail input, {N_EDGES} thetas trained via 100ns adjoint)")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, f"{name}_spider_curve.png"), dpi=140)
    print(f"Saved -> results/{name}_spider_curve.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
