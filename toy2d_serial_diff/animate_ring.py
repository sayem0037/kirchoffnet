"""
animate_ring.py -- decision-boundary-forming animation for the CLOSED-LOOP ring.

Push a dense grid of the (x,y) plane through the TRAINED ring once (seed via .IC ->
read h1..h10 @100ns, cache the 10-node state per grid point), then train the softmax
readout and render a frame every few epochs: the plane colored by predicted class +
data points -> animated GIF (like toy2d's *_boundary.gif).

Uses the trained circuit from results/<name>_ring_best.json if present (else the
untrained circ_init ring).

Usage:  python animate_ring.py --dataset {twomoon|circle|2spirals}
"""
import os, json, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap

from netlist_ring import write_ring_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
from model import softmax
from ring_common import (N_STAGES, CIRC_NAMES, READ,
                         init_seed_encoder, encode_ic, circ_dict, circ_init)

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
GRID_N, FRAMES, LR = 40, 40, 0.08


def load_circ(name):
    ck = os.path.join(RESULTS, f"{name}_ring_best.json")
    if os.path.exists(ck):
        d = json.load(open(ck))
        print(f"  using TRAINED circuit from {name}_ring_best.json (test acc {d.get('test_acc')})")
        return np.array([d["circ"][n] for n in CIRC_NAMES])
    print("  no checkpoint found -> using untrained circ_init ring")
    return circ_init()


def states_for(points, W, b, circ, netlist):
    S = np.full((len(points), N_STAGES), np.nan)
    nvalid = 0
    for i, x in enumerate(points):
        write_ring_netlist(circ_dict(circ), encode_ic(x, W, b), netlist, n_stages=N_STAGES)
        try:
            v = eval_chain(netlist, READ)
            S[i] = [v[n] for n in READ]; nvalid += 1
        except Exception:
            pass
    cm = np.nanmean(S, axis=0) if nvalid else np.full(N_STAGES, 1.65)
    cm = np.where(np.isfinite(cm), cm, 1.65)
    idx = np.where(np.isnan(S)); S[idx] = np.take(cm, idx[1])
    return S, nvalid


def main(name):
    os.makedirs(RESULTS, exist_ok=True)
    Xtr, ytr, Xte, yte = load_dataset(name)
    X = np.vstack([Xtr, Xte]); y = np.concatenate([ytr, yte])
    W, b = init_seed_encoder(seed=0); circ = load_circ(name)
    netlist = os.path.join(BASE, f"tmp_animr_{name}.sp")   # per-dataset (parallel-safe)
    print(f"animate_ring {name}: N={N_STAGES} stages; simulating {GRID_N}x{GRID_N} grid + {len(y)} pts...")

    # robustness: if the (trained) circuit is degenerate on the data, fall back to
    # the known-convergent untrained circ_init ring (like toy2d's animate_wide).
    Sdata, ndv = states_for(X, W, b, circ, netlist)
    if ndv < 0.7 * len(X):
        print(f"  trained circuit converged on only {ndv}/{len(X)} data pts "
              f"-> falling back to untrained circ_init ring for the animation")
        circ = circ_init()
        Sdata, ndv = states_for(X, W, b, circ, netlist)
    print(f"  data-point convergence: {ndv}/{len(X)}")

    lo = X.min(0) - 0.4; hi = X.max(0) + 0.4
    GX, GY = np.meshgrid(np.linspace(lo[0], hi[0], GRID_N), np.linspace(lo[1], hi[1], GRID_N))
    grid = np.column_stack([GX.ravel(), GY.ravel()])
    Sgrid, ngv = states_for(grid, W, b, circ, netlist)
    print(f"  grid convergence: {ngv}/{len(grid)}")
    mu, sd = Sdata.mean(0), Sdata.std(0) + 1e-9
    Ngrid, Ndata = (Sgrid - mu) / sd, (Sdata - mu) / sd
    nC = int(y.max()) + 1; onehot = np.eye(nC)

    rng = np.random.default_rng(0)
    Wr = 0.3 * rng.standard_normal((nC, N_STAGES)); br = np.zeros(nC)
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
        ax.set_title(f"{name} (closed {N_STAGES}-stage ring) -- boundary forming\nreadout epoch {ep}   acc {acc:.2f}")
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_xticks([]); ax.set_yticks([])
        return []

    anim = FuncAnimation(fig, draw, frames=len(frames), interval=180, blit=False)
    out = os.path.join(RESULTS, f"{name}_ring_boundary.gif")
    anim.save(out, writer=PillowWriter(fps=6)); plt.close(fig)
    print(f"Saved -> results/{name}_ring_boundary.gif   (final acc {frames[-1][1]:.2f})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
