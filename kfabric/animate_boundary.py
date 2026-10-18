"""
animate_boundary.py -- the decision boundary EVOLVING as the circuit trains.

Every frame is the boundary at the end of one epoch, and every pixel of every
frame is a real SPICE solve of the netlist with that epoch's weights. Nothing
is interpolated from a software model of the circuit.

This needs `train_kfq.py --snapshots`, which stores theta after each epoch;
without it only the final weights survive and the evolution is unrecoverable
without a full retrain.

What the animation shows on `circle`: the boundary starts as an open cut
through the plane and closes into a polygon around the origin. The closing is
the bias row doing its job -- a network with no bias term is odd, so its
boundary is forced through the origin and can never enclose a region.

Usage:
    python animate_boundary.py --dataset circle --tag gif --grid 30 --workers 7
"""
import argparse
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

import train_kfq as T
from datasets_any import load_any

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")

BG = ["#dce8f5", "#f7e3dc"]
PT = ["#1E5FA8", "#A33A2A"]


def _cls(arg):
    th, x = arg
    sc, _ = T.forward(th, x, T._W["layers"], T._W["cfg"], T._W["nl"])
    return int(np.argmax(sc))


def main(a):
    ck = os.path.join(RESULTS, f"kfq_{a.dataset}_{a.tag}.json")
    d = json.load(open(ck))
    snaps = d.get("snapshots") or []
    if not snaps:
        raise SystemExit(f"{ck} has no snapshots -- retrain with --snapshots")
    layers = [tuple(t) for t in d["layers"]]
    cfg = d["cfg"]
    log = d["log"]

    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, n_train=a.n_train,
                                        n_test=a.n_test)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    _, mn, mx = T.to_pm1(Xtr)

    pad = 0.35
    lo, hi = Xtr.min(0) - pad, Xtr.max(0) + pad
    gx = np.linspace(lo[0], hi[0], a.grid)
    gy = np.linspace(lo[1], hi[1], a.grid)
    GX, GY = np.meshgrid(gx, gy)
    P = np.column_stack([GX.ravel(), GY.ravel()])
    Pw, _, _ = T.to_pm1(P, mn, mx)

    idx = list(range(0, len(snaps), a.stride))
    if idx[-1] != len(snaps) - 1:
        idx.append(len(snaps) - 1)
    print(f"{len(idx)} frames x {len(P)} solves "
          f"({a.grid}x{a.grid}), {a.workers} workers", flush=True)

    import multiprocessing as mp
    pool = mp.Pool(a.workers, initializer=T._init_worker,
                   initargs=(layers, cfg, [], f"anim{a.dataset}"))
    frames = []
    try:
        for n, ei in enumerate(idx):
            th = {k: float(v) for k, v in snaps[ei].items()}
            Z = np.array(pool.map(_cls, [(th, Pw[k])
                                         for k in range(len(Pw))]))
            Z = Z.reshape(GX.shape)
            rec = log[ei]
            fig, ax = plt.subplots(figsize=(5.4, 5.2))
            ax.contourf(GX, GY, Z, levels=np.arange(-0.5, C + 0.5, 1.0),
                        colors=BG[:C])
            ax.contour(GX, GY, Z, levels=[0.5], colors=["#333"], linewidths=1.1)
            for c in range(C):
                ax.scatter(Xtr[ytr == c, 0], Xtr[ytr == c, 1], s=13, c=PT[c],
                           edgecolors="white", linewidths=0.35, zorder=3)
                ax.scatter(Xte[yte == c, 0], Xte[yte == c, 1], s=19,
                           marker="^", c=PT[c], edgecolors="white",
                           linewidths=0.35, zorder=3)
            te = rec["test"]
            tes = "—" if te != te else f"{te:.3f}"
            ax.set_title(f"{a.dataset} — epoch {rec['epoch']}\n"
                         f"train {rec['train']:.3f}   test {tes}   "
                         f"loss {rec['loss']:.3f}", fontsize=11)
            ax.set_xlabel("each pixel = one SPICE solve of the trained netlist",
                          fontsize=7.5, color="#555")
            ax.set_xticks([]); ax.set_yticks([])
            fig.tight_layout()
            p = os.path.join(RESULTS, f"_ab_{a.dataset}_{n:02d}.png")
            fig.savefig(p, dpi=115, facecolor="white"); plt.close(fig)
            frames.append(p)
            print(f"  epoch {rec['epoch']:>3}  train {rec['train']:.3f}",
                  flush=True)
    finally:
        pool.close(); pool.join()

    ims = [Image.open(p).convert("P", palette=Image.ADAPTIVE) for p in frames]
    gif = os.path.join(RESULTS, f"{a.dataset}_kfq_boundary.gif")
    # hold the last frame longer so the final boundary is readable
    durs = [a.ms] * (len(ims) - 1) + [a.ms * 4]
    ims[0].save(gif, save_all=True, append_images=ims[1:], duration=durs,
                loop=0)
    for p in frames:
        os.remove(p)
    print("saved ->", gif)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle")
    ap.add_argument("--tag", default="gif")
    ap.add_argument("--grid", type=int, default=30)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--n-train", type=int, default=300)
    ap.add_argument("--n-test", type=int, default=300)
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--ms", type=int, default=650)
    main(ap.parse_args())
