"""
plot_boundary.py -- decision-boundary + accuracy visualization for the trained
closed-loop ring. Loads results/<name>_ring_best.json, pushes a dense grid of the
(x,y) plane through the TRAINED ring (seed via .IC -> read h1..h10 @100ns ->
standardize -> softmax readout), and plots:
  (left)  the accuracy curve over epochs (from results/<name>_ring_log.csv)
  (right) the decision boundary (plane colored by predicted class) with the
          train/test points overlaid.
Saves results/<name>_ring_boundary.png.

Usage:  python plot_boundary.py --dataset {twomoon|circle|2spirals} [--grid 36]
"""
import os, json, csv, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from netlist_ring import write_ring_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from model import softmax
from ring_common import (N_STAGES, CIRC_NAMES, READ,
                         init_seed_encoder, encode_ic, circ_dict)

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
NETLIST = os.path.join(BASE, "tmp_boundary.sp")


def ring_state(x, circ_vec, W, b):
    write_ring_netlist(circ_dict(circ_vec), encode_ic(x, W, b), NETLIST, n_stages=N_STAGES)
    v = eval_chain(NETLIST, READ)
    return np.array([v[n] for n in READ])


def main(name, grid):
    ck = os.path.join(RESULTS, f"{name}_ring_best.json")
    if not os.path.exists(ck):
        raise FileNotFoundError(f"{ck} not found -- train first with train_ring.py --dataset {name}")
    d = json.load(open(ck))
    circ = np.array([d["circ"][n] for n in CIRC_NAMES])
    Wout, bout = np.array(d["Wout"]), np.array(d["bout"])
    mu, sd = np.array(d["mu"]), np.array(d["sd"])
    W, b = init_seed_encoder(seed=0)
    Xtr, ytr, Xte, yte = load_dataset(name)

    def predict(x):
        s = ring_state(x, circ, W, b)
        logits = ((s - mu) / sd) @ Wout.T + bout
        return int(np.argmax(logits))

    # --- dense grid over the plane ---
    allX = np.vstack([Xtr, Xte])
    x0min, x0max = allX[:, 0].min() - 0.5, allX[:, 0].max() + 0.5
    x1min, x1max = allX[:, 1].min() - 0.5, allX[:, 1].max() + 0.5
    gx = np.linspace(x0min, x0max, grid)
    gy = np.linspace(x1min, x1max, grid)
    Z = np.full((grid, grid), np.nan)
    print(f"Rendering {grid}x{grid}={grid*grid} grid points through the trained ring...")
    for iy, yv in enumerate(gy):
        for ix, xv in enumerate(gx):
            try:
                Z[iy, ix] = predict([gx[ix], yv])
            except Exception:
                Z[iy, ix] = np.nan
        if (iy + 1) % max(1, grid // 6) == 0:
            print(f"  row {iy+1}/{grid}")

    # --- accuracy curve from the training log ---
    ep, tr, te = [], [], []
    logp = os.path.join(RESULTS, f"{name}_ring_log.csv")
    if os.path.exists(logp):
        with open(logp) as f:
            for row in csv.DictReader(f):
                ep.append(int(row["epoch"])); tr.append(float(row["train_acc"])); te.append(float(row["test_acc"]))
    best_te = max(te) if te else float("nan")

    fig, ax = plt.subplots(1, 2, figsize=(12, 5))

    # (left) accuracy curve
    if ep:
        ax[0].plot(ep, tr, color="#2a78d6", lw=1.8, label="train")
        ax[0].plot(ep, te, color="#1baf7a", lw=1.8, label="test")
        ax[0].axhline(best_te, color="#c3c2b7", ls="--", lw=1, label=f"best test={best_te:.2f}")
    ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Accuracy"); ax[0].set_ylim(0, 1.02)
    ax[0].set_title(f"{name}: accuracy over epochs"); ax[0].legend(frameon=False); ax[0].grid(alpha=0.3)

    # (right) decision boundary
    ax[1].contourf(gx, gy, Z, levels=[-0.5, 0.5, 1.5], colors=["#cfe3f7", "#ffe0cc"], alpha=0.9)
    ax[1].contour(gx, gy, Z, levels=[0.5], colors=["#333333"], linewidths=1.2)
    for cls, mk, col in [(0, "o", "#1f4e8f"), (1, "^", "#b8471f")]:
        m = ytr == cls
        ax[1].scatter(Xtr[m, 0], Xtr[m, 1], c=col, marker=mk, s=28, edgecolors="white", linewidths=0.5, label=f"train c{cls}")
        m = yte == cls
        ax[1].scatter(Xte[m, 0], Xte[m, 1], c=col, marker=mk, s=60, edgecolors="black", linewidths=0.9, label=f"test c{cls}")
    ax[1].set_xlabel("x0"); ax[1].set_ylabel("x1")
    ax[1].set_title(f"{name}: decision boundary (trained 10-stage ring)")
    ax[1].legend(frameon=False, fontsize=8, loc="best")

    fig.suptitle(f"KirchhoffNet closed ring -- {name} (best test acc={best_te:.2f})")
    fig.tight_layout()
    out = os.path.join(RESULTS, f"{name}_ring_boundary.png")
    fig.savefig(out, dpi=140); plt.close(fig)
    print(f"Saved -> results/{name}_ring_boundary.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    ap.add_argument("--grid", type=int, default=36)
    main(ap.parse_args().dataset, ap.parse_args().grid)
