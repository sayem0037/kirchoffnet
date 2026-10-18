"""Boundary-formation GIF for a release model: dense grid through the REAL ring (kring pipeline), readout
re-trained from scratch on the train split's ring states (frames), last frames = the shipped readout.
Grid cells whose simulation fails are drawn grey (never guessed).

usage: python -m kring.tools.make_gif <model_dir> <out.gif> [grid_n] [workers]   (KRING_SIM_SRC set)
"""
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
from kring import KRingModel
from kring.tools.experiment import split_arrays


def softmax(z):
    z = z - z.max(-1, keepdims=True); e = np.exp(z); return e / e.sum(-1, keepdims=True)


def main(model_dir, out, grid_n=40, workers=12):
    m = KRingModel.load(os.path.join(model_dir, "model.json"))
    name, seed = m.pkg["provenance"]["dataset"], m.pkg["provenance"]["seed"]
    sp = split_arrays(name, seed)
    (Xtr, ytr), (Xva, yva), (Xte, yte) = sp["train"], sp["val"], sp["test"]
    allX = np.vstack([Xtr, Xva, Xte])
    lo, hi = allX.min(0) - 0.4, allX.max(0) + 0.4
    GX, GY = np.meshgrid(np.linspace(lo[0], hi[0], grid_n), np.linspace(lo[1], hi[1], grid_n))
    grid = np.column_stack([GX.ravel(), GY.ravel()])
    Sg, stg = m.states(grid, workers=workers)
    Str, _ = m.states(Xtr, workers=workers)
    Ste, _ = m.states(Xte, workers=workers)
    gok = ~np.isnan(Sg).any(1)
    print(f"{name}: grid ok {gok.sum()}/{len(grid)}, train ok {(~np.isnan(Str).any(1)).sum()}/{len(Str)}, "
          f"test ok {(~np.isnan(Ste).any(1)).sum()}/{len(Ste)}", flush=True)
    nz = lambda S: (S - m.mu) / m.sd
    Ntr, Nte, Ng = nz(Str), nz(Ste), np.nan_to_num(nz(Sg))

    rng = np.random.default_rng(0)
    Wr = 0.3 * rng.standard_normal((2, m.n)); br = np.zeros(2)
    mm = {"W": np.zeros_like(Wr), "b": np.zeros(2)}; vv = {"W": np.zeros_like(Wr), "b": np.zeros(2)}
    oh = np.eye(2); frames = []; t = 0
    for ep in range(241):
        if ep % 6 == 0:
            pred = (Ng @ Wr.T + br).argmax(1).astype(float); pred[~gok] = np.nan
            frames.append((pred.reshape(grid_n, grid_n), float(((Nte @ Wr.T + br).argmax(1) == yte).mean()),
                           f"readout epoch {ep}"))
        G = (softmax(Ntr @ Wr.T + br) - oh[ytr]) / len(ytr); t += 1
        for k, g in (("W", G.T @ Ntr), ("b", G.sum(0))):
            P = Wr if k == "W" else br
            mm[k] = 0.9 * mm[k] + 0.1 * g; vv[k] = 0.999 * vv[k] + 0.001 * g * g
            P -= 0.08 * (mm[k] / (1 - 0.9 ** t)) / (np.sqrt(vv[k] / (1 - 0.999 ** t)) + 1e-8)
    # final frames: the actual shipped readout
    pred = (Ng @ m.Wout.T + m.bout).argmax(1).astype(float); pred[~gok] = np.nan
    acc = float(((Nte @ m.Wout.T + m.bout).argmax(1) == yte).mean())
    frames += [(pred.reshape(grid_n, grid_n), acc, "shipped release readout")] * 6

    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    cols = ["#2a78d6", "#eb6834"]

    def draw(i):
        ax.clear()
        pred, a, label = frames[i]
        ax.pcolormesh(GX, GY, np.where(np.isnan(pred), 0.5, pred), shading="auto",
                      cmap=matplotlib.colors.ListedColormap(["#bcd4f0", "#d9d9d9", "#f6c9b0"]), vmin=-0.5, vmax=1.5, alpha=0.9)
        ax.scatter(*Xtr.T, c=[cols[k] for k in ytr], s=22, edgecolors="white", linewidths=0.5, label="train")
        ax.scatter(*Xte.T, c=[cols[k] for k in yte], s=34, marker="s", edgecolors="black", linewidths=0.6, label="test")
        ax.set_title(f"{name} -- validated ring model, boundary forming\n{label}   test acc {a:.2f}  (grey = sim failed)", fontsize=9)
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_xticks([]); ax.set_yticks([])
        ax.legend(loc="lower right", fontsize=7, frameon=True)
        return []

    FuncAnimation(fig, draw, frames=len(frames), interval=180).save(out, writer=PillowWriter(fps=6))
    plt.close(fig)
    print("saved", out, "final test acc", acc)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], int(a[3]) if len(a) > 3 else 40, int(a[4]) if len(a) > 4 else 12)
