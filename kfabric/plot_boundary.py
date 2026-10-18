"""
plot_boundary.py -- the decision boundary the CIRCUIT draws, on a 2-D toy set.

WHY THIS IS WORTH PLOTTING
--------------------------
`circle` is inner disc against outer ring, both centred on the origin. Two
facts make its boundary the most informative picture in this project:

  1. A linear read-out scores 0.480 on it, against a 0.500 chance rate. Any
     closed boundary here is something a linear model provably cannot draw.
  2. A network with no bias term is an ODD function, f(-x) = -f(x), so its
     boundary must pass through the origin and CANNOT enclose a region. Before
     the bias row was added this net sat at exactly chance (loss 0.6936 against
     ln 2 = 0.6931) for twenty epochs.

So if the plotted boundary is a closed curve around the origin, that is direct
visual evidence for both the nonlinearity and the bias row -- not a metric the
reader has to take on trust.

Every grid point is a real SPICE solve of the trained circuit, and the class is
argmax over the last column pair's voltage difference. Nothing is interpolated
from a software model of the circuit.

Usage:
    python plot_boundary.py --dataset circle --tag circ3 --grid 44 --workers 8
"""
import argparse
import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import train_kfq as T
from datasets_any import load_any

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")

BG = ["#dce8f5", "#f7e3dc"]
PT = ["#1E5FA8", "#A33A2A"]


def main(a):
    ck = os.path.join(RESULTS, f"kfq_{a.dataset}_{a.tag}.json")
    if not os.path.exists(ck):
        raise SystemExit(f"missing {ck} -- train first")
    d = json.load(open(ck))
    layers = [tuple(t) for t in d["layers"]]
    cfg, th = d["cfg"], {k: float(v) for k, v in d["theta"].items()}
    te = [r["test"] for r in d["log"] if r["test"] == r["test"]]
    acc = te[-1] if te else float("nan")

    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, n_train=a.n_train,
                                        n_test=a.n_test)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    _, mn, mx = T.to_pm1(Xtr)

    pad = 0.35
    lo = Xtr.min(0) - pad
    hi = Xtr.max(0) + pad
    gx = np.linspace(lo[0], hi[0], a.grid)
    gy = np.linspace(lo[1], hi[1], a.grid)
    GX, GY = np.meshgrid(gx, gy)
    P = np.column_stack([GX.ravel(), GY.ravel()])
    Pw, _, _ = T.to_pm1(P, mn, mx)

    print(f"{a.dataset}: {len(P)} grid solves of the trained circuit "
          f"({a.grid}x{a.grid}), {a.workers} workers", flush=True)
    if a.workers > 1:
        import multiprocessing as mp
        pool = mp.Pool(a.workers, initializer=T._init_worker,
                       initargs=(layers, cfg, [], f"bnd{a.dataset}"))
        pred = pool.map(_cls, [(th, Pw[k], layers, cfg) for k in range(len(Pw))])
        pool.close(); pool.join()
    else:
        nl = T.scratch(f"bnd_{a.dataset}")
        pred = []
        for k in range(len(Pw)):
            sc, _ = T.forward(th, Pw[k], layers, cfg, nl)
            pred.append(int(np.argmax(sc)))
        if os.path.exists(nl):
            os.remove(nl)
    Z = np.array(pred).reshape(GX.shape)

    fig, ax = plt.subplots(figsize=(5.9, 5.6))
    ax.contourf(GX, GY, Z, levels=np.arange(-0.5, C + 0.5, 1.0),
                colors=BG[:C], alpha=1.0)
    ax.contour(GX, GY, Z, levels=[0.5], colors=["#333"], linewidths=1.1)
    for c in range(C):
        ax.scatter(Xtr[ytr == c, 0], Xtr[ytr == c, 1], s=15, c=PT[c],
                   edgecolors="white", linewidths=0.4, zorder=3,
                   label=f"class {c} (train)")
        ax.scatter(Xte[yte == c, 0], Xte[yte == c, 1], s=22, marker="^",
                   c=PT[c], edgecolors="white", linewidths=0.4, zorder=3)
    ax.set_title(f"{a.dataset} — boundary drawn by the circuit\n"
                 f"KFQ argmax  test {acc:.3f}   |   linear read-out 0.480",
                 fontsize=11)
    ax.set_xlabel("every pixel is one SPICE solve of the trained netlist; "
                  "class = argmax over V(c+)−V(c−)",
                  fontsize=7.5, color="#555")
    ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout()
    out = os.path.join(RESULTS, f"{a.dataset}_kfq_boundary.png")
    fig.savefig(out, dpi=150, facecolor="white")
    print(f"saved -> {out}")


def _cls(arg):
    th, x, layers, cfg = arg
    sc, _ = T.forward(th, x, T._W["layers"], T._W["cfg"], T._W["nl"])
    return int(np.argmax(sc))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle")
    ap.add_argument("--tag", default="circ3")
    ap.add_argument("--grid", type=int, default=44)
    ap.add_argument("--n-train", type=int, default=300)
    ap.add_argument("--n-test", type=int, default=300)
    ap.add_argument("--workers", type=int, default=8)
    main(ap.parse_args())
