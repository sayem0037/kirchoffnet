"""
animate.py -- animate the decision boundary FORMING as the readout trains, on
top of the trained circuit, for a 2-D dataset. Shows how well the trained
KirchhoffNet model captures the dataset's shape.

For each dataset:
  1. load the trained circuit params (results/<name>_stage2_best.json),
  2. push a dense grid of the (x,y) plane through the circuit ONCE (cache the
     4-node 100ns state for every grid point),
  3. train a softmax readout on the data-point states, and every few epochs
     render a frame: the (x,y) plane colored by predicted class + the data
     points -> assemble into an animated GIF.

Usage:  python animate.py --dataset {twomoon|circle|2spirals}
"""
import os, json, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

from netlist_writer import write_chain_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from model import softmax
from common import N_BLOCKS, CIRC_NAMES, READ, encode

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
NETLIST = os.path.join(BASE, "tmp_anim.sp")
GRID_N = 44
FRAMES = 40          # readout-training snapshots
LR = 0.08


def circ_dict(vec):
    return {n: float(vec[k]) for k, n in enumerate(CIRC_NAMES)}


def circ_from_best(name):
    p = os.path.join(RESULTS, f"{name}_stage2_best.json")
    if os.path.exists(p):
        c = json.load(open(p))["circ"]
        return {k: float(v) for k, v in c.items()}
    return {**{f"VTH{i}": 1.7 for i in range(1, 5)}, **{f"VB{i}": 0.8 for i in range(1, 5)}}


def states_for(points, circ):
    """4-node 100ns state for each (x,y) point through the trained circuit.
    Failed solves are filled later with the column mean (avoids holes)."""
    S = np.full((len(points), len(READ)), np.nan)
    for i, x in enumerate(points):
        write_chain_netlist(circ, encode(x), NETLIST, n_blocks=N_BLOCKS)
        try:
            v = eval_chain(NETLIST, READ)
            S[i] = [v[n] for n in READ]
        except Exception:
            pass
    col_mean = np.nanmean(S, axis=0)
    idx = np.where(np.isnan(S))
    S[idx] = np.take(col_mean, idx[1])
    return S


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    Xtr, ytr, Xte, yte = load_dataset(name)
    X = np.vstack([Xtr, Xte]); y = np.concatenate([ytr, yte])
    circ = circ_from_best(name)
    print(f"animate {name}: trained circuit loaded; simulating {GRID_N}x{GRID_N} grid + {len(y)} points...")

    lo = X.min(0) - 0.4; hi = X.max(0) + 0.4
    gx = np.linspace(lo[0], hi[0], GRID_N)
    gy = np.linspace(lo[1], hi[1], GRID_N)
    GX, GY = np.meshgrid(gx, gy)
    grid_pts = np.column_stack([GX.ravel(), GY.ravel()])

    Sgrid = states_for(grid_pts, circ)      # (GRID_N^2, 4)  -- the expensive part, done once
    Sdata = states_for(X, circ)             # (N, 4)
    mu, sd = Sdata.mean(0), Sdata.std(0) + 1e-9
    Ngrid = (Sgrid - mu) / sd
    Ndata = (Sdata - mu) / sd
    nC = int(y.max()) + 1
    onehot = np.eye(nC)

    # train a softmax readout, snapshotting the grid decision each frame
    rng = np.random.default_rng(0)
    W = 0.3 * rng.standard_normal((nC, N_BLOCKS)); b = np.zeros(nC)
    m = {"W": np.zeros_like(W), "b": np.zeros_like(b)}
    v = {"W": np.zeros_like(W), "b": np.zeros_like(b)}
    frames = []
    EPOCHS = FRAMES * 6
    t = 0
    for ep in range(EPOCHS + 1):
        if ep % 6 == 0:   # snapshot
            pred_grid = (Ngrid @ W.T + b).argmax(1).reshape(GRID_N, GRID_N)
            acc = float(((Ndata @ W.T + b).argmax(1) == y).mean())
            frames.append((pred_grid.copy(), acc, ep))
        # Adam step
        logits = Ndata @ W.T + b
        G = (softmax(logits) - onehot[y]) / len(y)
        gW = G.T @ Ndata; gb = G.sum(0); t += 1
        for key, g in (("W", gW), ("b", gb)):
            P = {"W": W, "b": b}[key]
            m[key] = 0.9 * m[key] + 0.1 * g
            v[key] = 0.999 * v[key] + 0.001 * g * g
            P -= LR * (m[key] / (1 - 0.9**t)) / (np.sqrt(v[key] / (1 - 0.999**t)) + 1e-8)

    # render GIF
    cmap = ListedColormap(["#bcd4f0", "#f6c9b0"])       # class regions (light)
    pt_cmap = ListedColormap(["#2a78d6", "#eb6834"])    # data points (bold)
    fig, ax = plt.subplots(figsize=(5.2, 5))

    def draw(i):
        ax.clear()
        pred, acc, ep = frames[i]
        ax.contourf(GX, GY, pred, levels=[-0.5, 0.5, 1.5], colors=["#bcd4f0", "#f6c9b0"], alpha=0.9)
        ax.scatter(X[:, 0], X[:, 1], c=y, cmap=pt_cmap, s=22, edgecolors="white", linewidths=0.5)
        ax.set_title(f"{name} -- decision boundary forming\nepoch {ep}   train+test acc {acc:.2f}")
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1])
        ax.set_xticks([]); ax.set_yticks([])
        return []

    anim = FuncAnimation(fig, draw, frames=len(frames), interval=180, blit=False)
    out = os.path.join(RESULTS, f"{name}_boundary.gif")
    anim.save(out, writer=PillowWriter(fps=6))
    plt.close(fig)
    print(f"Saved -> results/{name}_boundary.gif   (final acc {frames[-1][1]:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
