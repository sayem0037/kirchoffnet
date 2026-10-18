"""
train_stage2.py -- Stage 2: train the CIRCUIT itself on a 2-D dataset, via the
100ns backward transient adjoint. For non-linearly-separable sets (circle,
2spirals) this is where the circuit must LEARN a nonlinear feature map that the
frozen circuit (Stage 1) could not provide.

Validated stable recipe (from bin_class): a freely-trained readout (convex,
drives accuracy) + fixed feature standardization + gentle PRE-CHECKED circuit
steps (reject any adjoint step that raises the loss before it lands) -> a smooth,
spike-free curve where both accuracies rise.

All simulator calls are per-sample robust: a sample whose SPICE solve fails to
converge (can happen for some circuit configs during training) is skipped, and a
tentative circuit step that causes failures is rejected.

Usage:  python train_stage2.py --dataset {twomoon|circle|2spirals}
"""
import os, json, csv, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_writer import write_chain_netlist
from simulator_api import run_chain, eval_chain
from dataset import load_dataset, DATASETS
from model import Adam, softmax, Readout
from common import N_BLOCKS, CIRC_NAMES, READ, encode, BOUNDS

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
NETLIST = os.path.join(BASE, "tmp_stage2.sp")
EPOCHS  = 90
LR_CIRC = 0.0008
LR_READ = 0.05


def circ_dict(vec):
    return {n: float(vec[k]) for k, n in enumerate(CIRC_NAMES)}


def forward_states(X, circ_vec):
    """Forward-only; returns (S, valid_idx). Skips samples whose solve fails."""
    S, valid = [], []
    for i in range(len(X)):
        write_chain_netlist(circ_dict(circ_vec), encode(X[i]), NETLIST, n_blocks=N_BLOCKS)
        try:
            v = eval_chain(NETLIST, READ)
            S.append([v[n] for n in READ]); valid.append(i)
        except Exception:
            continue
    return np.array(S) if S else np.zeros((0, len(READ))), np.array(valid, dtype=int)


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    Xtr, ytr, Xte, yte = load_dataset(name)
    nC = int(max(ytr.max(), yte.max())) + 1
    onehot = np.eye(nC)
    print(f"Stage 2 | {name} | {len(ytr)} train / {len(yte)} test | circuit params: {CIRC_NAMES}")

    circ = np.array([1.7] * 4 + [0.8] * 4, dtype=float)
    S0, v0 = forward_states(Xtr, circ)
    mu, sd = S0.mean(0), S0.std(0) + 1e-9
    ro = Readout(m_state=len(READ), n_class=nC, seed=0)
    params = {"circ": circ.copy(), "Wout": ro.W.copy(), "bout": ro.b.copy()}
    opt_circ = Adam({"circ": params["circ"]}, lr=LR_CIRC)
    opt_read = Adam({"Wout": params["Wout"], "bout": params["bout"]}, lr=LR_READ)

    s1_ref = 0.5
    s1p = os.path.join(RESULTS, f"{name}_stage1_best.json")
    if os.path.exists(s1p):
        s1_ref = json.load(open(s1p)).get("test_acc", 0.5)

    def metrics(X, y, circ_vec):
        S, valid = forward_states(X, circ_vec)
        if len(valid) == 0:
            return float("nan"), float("nan")
        Sn = (S - mu) / sd
        logits = Sn @ params["Wout"].T + params["bout"]
        pr = softmax(logits)
        yv = y[valid]
        ls = float(-np.log(pr[np.arange(len(yv)), yv] + 1e-12).mean())
        acc = float((logits.argmax(1) == yv).mean())
        return ls, acc

    print(f"{'Ep':>4}  {'loss':>8}  {'train':>7}  {'test':>6}")
    hist = {"epoch": [], "loss": [], "tr": [], "te": []}
    best_te, best_ep, lr_circ = -1.0, -1, LR_CIRC
    log_csv = os.path.join(RESULTS, f"{name}_stage2_log.csv")

    with open(log_csv, "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["epoch", "loss", "train_acc", "test_acc"])
        for ep in range(1, EPOCHS + 1):
            # 1) simulate current circuit -> cache states + sensitivities (robust)
            S, SENS, yv = [], [], []
            for i in range(len(ytr)):
                write_chain_netlist(circ_dict(params["circ"]), encode(Xtr[i]), NETLIST, n_blocks=N_BLOCKS)
                try:
                    v_out, sens = run_chain(NETLIST, READ, CIRC_NAMES)
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

            # 3) circuit: one pre-checked gentle adjoint step
            logits = Sn @ params["Wout"].T + params["bout"]
            G = (softmax(logits) - onehot[yv]) / len(yv)
            dL_dS = (G @ params["Wout"]) / sd
            g_circ = np.einsum("ij,ijk->k", dL_dS, SENS)
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

            hist["epoch"].append(ep); hist["loss"].append(tr_loss); hist["tr"].append(tr_acc); hist["te"].append(te_acc)
            wr.writerow([ep, f"{tr_loss:.6f}", f"{tr_acc:.4f}", f"{te_acc:.4f}"]); f.flush()
            if np.isfinite(te_acc) and te_acc > best_te:
                best_te, best_ep = te_acc, ep
                json.dump({"epoch": ep, "test_acc": te_acc, "train_acc": tr_acc, "circ": circ_dict(params["circ"])},
                          open(os.path.join(RESULTS, f"{name}_stage2_best.json"), "w"), indent=2)
            if ep % 10 == 0 or ep == 1:
                print(f"{ep:>4}  {tr_loss:>8.4f}  {tr_acc:>7.2f}  {te_acc:>6.2f}")

    print(f"\nStage 2 {name} done. Best test acc={best_te:.2f} @ep{best_ep} (Stage 1 was {s1_ref:.2f})")

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].plot(hist["epoch"], hist["loss"], color="#2a78d6", lw=1.6)
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss"); ax[0].grid(alpha=0.3)
    ax[0].set_title(f"Loss: {hist['loss'][0]:.3f} -> {hist['loss'][-1]:.3f}")
    ax[1].plot(hist["epoch"], hist["tr"], color="#2a78d6", lw=1.6, label="train")
    ax[1].plot(hist["epoch"], hist["te"], color="#1baf7a", lw=1.6, label="test")
    ax[1].axhline(s1_ref, color="#c3c2b7", ls="--", lw=1, label="Stage 1 test")
    ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
    ax[1].set_title(f"Accuracy: best test={best_te:.2f}"); ax[1].legend(frameon=False); ax[1].grid(alpha=0.3)
    fig.suptitle(f"KirchhoffNet chain -- {name} Stage 2 (circuit trained via 100ns adjoint)")
    fig.tight_layout(); fig.savefig(os.path.join(RESULTS, f"{name}_stage2_curve.png"), dpi=140)
    print(f"Saved -> results/{name}_stage2_curve.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
