"""
animate_wide_stage2.py -- decision-boundary animation for the CIRCUIT-TRAINED
wide layer (companion to train_wide_stage2.py).

Same idea as animate_wide.py, but the analog feature map is the LEARNED circuit:
the per-unit VTH/VB/VN found by the 100ns adjoint (loaded from
results/<name>_wide_stage2_best.json), not a frozen random reservoir. A dense
(x,y) grid is pushed through the trained circuit once (cache the N-node 100ns
state per grid point); then the softmax readout is (re)trained and a frame is
rendered every few epochs -> animated GIF of the boundary forming on the
learned analog features.

Usage:  python animate_wide_stage2.py --dataset {twomoon|circle|2spirals}
"""
import os, json, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

from netlist_wide import write_wide_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from model import softmax
from wide_common import N_UNITS, CIRC_NAMES, READ, init_encoder, encode_wide, circ_dict

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
GRID_N, FRAMES, LR = 44, 40, 0.08


def load_trained_circ(name):
    """Return the trained circuit vector (CIRC_NAMES order) + best test acc."""
    p = os.path.join(RESULTS, f"{name}_wide_stage2_best.json")
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"{p} not found -- run `python train_wide_stage2.py --dataset {name}` first.")
    d = json.load(open(p))
    cd = d["circ"]
    circ = np.array([cd[n] for n in CIRC_NAMES], dtype=float)
    return circ, float(d.get("test_acc", float("nan")))


def states_for(points, W, b, circ, netlist):
    S = np.full((len(points), N_UNITS), np.nan)
    for i, x in enumerate(points):
        write_wide_netlist(circ_dict(circ), encode_wide(x, W, b), netlist, n_units=N_UNITS)
        try:
            v = eval_chain(netlist, READ)
            S[i] = [v[n] for n in READ]
        except Exception:
            pass
    cm = np.nanmean(S, axis=0); idx = np.where(np.isnan(S)); S[idx] = np.take(cm, idx[1])
    return S


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    netlist = os.path.join(BASE, f"tmp_animw_stage2_{name}.sp")
    Xtr, ytr, Xte, yte = load_dataset(name)
    X = np.vstack([Xtr, Xte]); y = np.concatenate([ytr, yte])
    W, b = init_encoder(seed=0)
    circ, best_te = load_trained_circ(name)
    print(f"animate_wide_stage2 {name}: N={N_UNITS} units (trained circuit, "
          f"best test={best_te:.2f}); simulating {GRID_N}x{GRID_N} grid + {len(y)} pts...")

    lo = X.min(0) - 0.4; hi = X.max(0) + 0.4
    GX, GY = np.meshgrid(np.linspace(lo[0], hi[0], GRID_N), np.linspace(lo[1], hi[1], GRID_N))
    grid = np.column_stack([GX.ravel(), GY.ravel()])
    Sgrid = states_for(grid, W, b, circ, netlist)
    Sdata = states_for(X, W, b, circ, netlist)
    mu, sd = Sdata.mean(0), Sdata.std(0) + 1e-9
    Ngrid, Ndata = (Sgrid - mu) / sd, (Sdata - mu) / sd
    nC = int(y.max()) + 1; onehot = np.eye(nC)

    rng = np.random.default_rng(0)
    Wr = 0.3 * rng.standard_normal((nC, N_UNITS)); br = np.zeros(nC)
    m = {"W": np.zeros_like(Wr), "b": np.zeros_like(br)}; v = {"W": np.zeros_like(Wr), "b": np.zeros_like(br)}
    frames, t = [], 0
    for ep in range(FRAMES * 6 + 1):
        if ep % 6 == 0:
            pred = (Ngrid @ Wr.T + br).argmax(1).reshape(GRID_N, GRID_N)
            acc = float(((Ndata @ Wr.T + br).argmax(1) == y).mean())
            frames.append((pred.copy(), acc, ep))
        logits = Ndata @ Wr.T + br
        G = (softmax(logits) - onehot[y]) / len(y); t += 1
        for key, g in (("W", G.T @ Ndata), ("b", G.sum(0))):
            P = {"W": Wr, "b": br}[key]
            m[key] = 0.9 * m[key] + 0.1 * g; v[key] = 0.999 * v[key] + 0.001 * g * g
            P -= LR * (m[key] / (1 - 0.9**t)) / (np.sqrt(v[key] / (1 - 0.999**t)) + 1e-8)

    pt_cmap = ListedColormap(["#2a78d6", "#eb6834"])
    fig, ax = plt.subplots(figsize=(5.2, 5))

    def draw(i):
        ax.clear()
        pred, acc, ep = frames[i]
        ax.contourf(GX, GY, pred, levels=[-0.5, 0.5, 1.5], colors=["#bcd4f0", "#f6c9b0"], alpha=0.9)
        ax.scatter(X[:, 0], X[:, 1], c=y, cmap=pt_cmap, s=22, edgecolors="white", linewidths=0.5)
        ax.set_title(f"{name} (wide {N_UNITS}-unit layer, trained circuit)\n"
                     f"epoch {ep}   acc {acc:.2f}")
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_xticks([]); ax.set_yticks([])
        return []

    anim = FuncAnimation(fig, draw, frames=len(frames), interval=180, blit=False)
    out = os.path.join(RESULTS, f"{name}_wide_stage2_boundary.gif")
    anim.save(out, writer=PillowWriter(fps=6)); plt.close(fig)
    print(f"Saved -> results/{name}_wide_stage2_boundary.gif   (final acc {frames[-1][1]:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle", choices=DATASETS)
    main(ap.parse_args().dataset)
