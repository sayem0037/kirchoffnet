"""
make_plots.py -- the two requested figure families, per arm per dataset.

  1. accuracy vs epoch       train and test, a Wilson band on test, chance marked
  2. weight convergence      how the trained parameters actually moved

DESIGN NOTES (so they survive editing)
--------------------------------------
* Accuracy is a trend over time with two series, so it is a line chart with a legend AND
  direct labels -- identity never rests on colour alone, which also keeps it readable in
  greyscale print.
* Weight trajectories are 100+ series. That is not a categorical palette problem to be
  solved with more hues; past a handful of series the honest form is EMPHASIS: a sample
  of individual traces drawn thin and translucent for texture, with an opaque
  mean +- spread band carrying the actual message. Generating 200 colours would be
  unreadable and colour-vision-hostile.
* The analog panel draws the device rails, because "a weight stopped moving" and "a
  weight hit the edge of what the device can store" look identical otherwise, and only
  one of them is convergence.
* One axis per plot. No dual-axis anywhere.
* Colours are the validated slots used elsewhere in this project, in fixed order.
"""

import argparse
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt       # noqa: E402
import numpy as np                    # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
COMPARE = os.path.join(os.path.dirname(BASE), "compare")
sys.path.insert(0, BASE)
sys.path.insert(0, COMPARE)

from trainlog import load_log, load_meta          # noqa: E402
import metrics                                    # noqa: E402

RESULTS = os.path.join(BASE, "results")
FIGS = os.path.join(BASE, "figs")
os.makedirs(FIGS, exist_ok=True)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VIOLET, RED = "#4a3aa7", "#e34948"
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8a85", "#d8d8d4"

ARM_COLOR = {"xbar": BLUE, "digital": ORANGE}
ARM_LABEL = {"xbar": "1T1R crossbar (in-situ)",
             "digital": "fixed-point MLP (QAT)"}
RULE_LABEL = {"writeverify": "write-verify", "manhattan": "Manhattan"}


def arm_label(arm, stem):
    """Arm name, plus the crossbar's update rule as recorded in the run's meta."""
    if arm == "xbar":
        rule = load_meta(stem).get("update_rule")
        return f"1T1R crossbar (in-situ, {RULE_LABEL.get(rule, 'Manhattan')})"
    return ARM_LABEL[arm]

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.dpi": 160, "savefig.dpi": 300,
    "savefig.bbox": "tight", "legend.frameon": False,
})


def _tidy(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def runs_for(arm, dataset, tag):
    stem = os.path.join(RESULTS, f"{arm}_{dataset}_{tag}")
    if os.path.exists(f"{stem}_log.csv"):
        return stem
    hits = sorted(glob.glob(os.path.join(RESULTS, f"{arm}_{dataset}_*_log.csv")),
                  key=os.path.getmtime, reverse=True)
    return hits[0][:-8] if hits else None


# ---------------------------------------------------------------- accuracy --
def fig_accuracy(stem, arm, dataset, out):
    ep, loss, tr, te, _, _ = load_log(stem)
    if ep.size == 0:
        return None
    meta = load_meta(stem)
    n_te = meta.get("n_test", 0)
    C = meta.get("C", 2)
    col = ARM_COLOR[arm]

    fig, ax = plt.subplots(figsize=(6.6, 4.0))

    if n_te:
        lo = np.array([metrics.wilson(v, n_te)[0] for v in te])
        hi = np.array([metrics.wilson(v, n_te)[1] for v in te])
        ax.fill_between(ep, lo, hi, color=col, alpha=0.14, lw=0,
                        label="test 95% interval", zorder=1)

    ax.plot(ep, tr, lw=2, color=MUTED, ls="--", label="train", zorder=3)
    ax.plot(ep, te, lw=2, color=col, label="test", zorder=4)

    ax.axhline(1.0 / C, color=MUTED, lw=1.1, ls=":", zorder=2)
    ax.text(ep[-1], 1.0 / C, f" chance {1.0/C:.2f}", color=MUTED, fontsize=8,
            va="bottom", ha="right")

    b = int(np.argmax(te))
    ax.scatter([ep[b]], [te[b]], s=55, color=col, edgecolor="white",
               linewidth=1.2, zorder=5)
    ax.annotate(f"best {te[b]:.3f} @ ep {ep[b]}", (ep[b], te[b]),
                textcoords="offset points", xytext=(8, 8), fontsize=8.5,
                color=INK)
    ax.annotate("train", (ep[-1], tr[-1]), textcoords="offset points",
                xytext=(6, 0), fontsize=8, color=INK2)
    ax.annotate("test", (ep[-1], te[-1]), textcoords="offset points",
                xytext=(6, 0), fontsize=8, color=col)

    ax.set_xlabel("epoch")
    ax.set_ylabel("accuracy")
    ax.set_ylim(0, 1.06)
    ax.set_xlim(ep.min() - 0.5, ep.max() * 1.12)
    ax.set_title(f"{arm_label(arm, stem)} on {dataset}", loc="left")
    ax.legend(loc="lower right", fontsize=8)
    _tidy(ax)
    fig.savefig(out); plt.close(fig)
    return out


# -------------------------------------------------------------- weight trace --
def fig_weights(stem, arm, dataset, out, n_show=40, seed=0):
    ep, loss, tr, te, W, names = load_log(stem)
    if ep.size == 0 or W.shape[1] == 0:
        return None
    meta = load_meta(stem)
    col = ARM_COLOR[arm]
    analog = (arm == "xbar")

    if analog:
        dev = meta.get("device", {})
        g_on, g_off = dev.get("g_on", 1e-4), dev.get("g_off", 1e-6)
        Y = (W - g_off) / (g_on - g_off)          # position in the device window
        ylab = "conductance, as a fraction of the device window"
        rails = (0.0, 1.0)
    else:
        Y = W
        ylab = "weight value (fixed point, dequantized)"
        rails = None

    rng = np.random.default_rng(seed)
    pick = rng.choice(Y.shape[1], size=min(n_show, Y.shape[1]), replace=False)

    fig, ax = plt.subplots(figsize=(6.6, 4.2))

    # Individual traces: thin and translucent. They give texture and show the jitter;
    # they are deliberately not individually identifiable, because 40 distinguishable
    # colours do not exist.
    for k in pick:
        ax.plot(ep, Y[:, k], lw=0.7, color=col, alpha=0.22, zorder=2)

    mu = Y.mean(axis=1)
    sd = Y.std(axis=1)
    ax.fill_between(ep, mu - sd, mu + sd, color=col, alpha=0.20, lw=0,
                    label="all weights, mean $\\pm$ sd", zorder=3)
    ax.plot(ep, mu, lw=2.2, color=col, label="mean", zorder=4)

    if rails:
        for r, lab in ((rails[0], "$G_{off}$"), (rails[1], "$G_{on}$")):
            ax.axhline(r, color=RED, lw=1.1, ls="--", zorder=1)
            ax.text(ep[-1], r, f" {lab}", color=RED, fontsize=8,
                    va="bottom" if r == rails[0] else "top", ha="right")
        ax.set_ylim(-0.08, 1.08)
        pinned = float(np.mean((Y[-1] > 0.97) | (Y[-1] < 0.03)))
        ax.annotate(f"{pinned*100:.0f}% of cells at a rail at the end",
                    (0.02, 0.03), xycoords="axes fraction", fontsize=8.5,
                    color=INK)

    mv = float(np.mean(np.abs(Y[-1] - Y[0])))
    ax.annotate(f"mean |change| over training: {mv:.3f}",
                (0.02, 0.95), xycoords="axes fraction", fontsize=8.5, color=INK)

    ax.set_xlabel("epoch")
    ax.set_ylabel(ylab)
    ax.set_xlim(ep.min() - 0.5, ep.max() * 1.10)
    ax.set_title(f"Weight convergence - {arm_label(arm, stem)} on {dataset}\n"
                 f"{len(pick)} of {Y.shape[1]} logged "
                 f"{'cells' if analog else 'weights'} shown individually",
                 loc="left", fontsize=9.5)
    ax.legend(loc="upper right", fontsize=8)
    _tidy(ax)
    fig.savefig(out); plt.close(fig)
    return out


# ------------------------------------------------------------------- main ----
def main(a):
    made = []
    for ds in a.datasets:
        for arm in a.arms:
            stem = runs_for(arm, ds, a.tag)
            if stem is None:
                print(f"  (no run for {arm} / {ds})")
                continue
            p1 = os.path.join(FIGS, f"acc_{arm}_{ds}.png")
            p2 = os.path.join(FIGS, f"weights_{arm}_{ds}.png")
            made.append((f"{arm}/{ds} accuracy", fig_accuracy(stem, arm, ds, p1)))
            made.append((f"{arm}/{ds} weights", fig_weights(stem, arm, ds, p2)))

    for label, path in made:
        print(f"  {'wrote ' if path else 'SKIP  '}{label:<28} "
              f"{os.path.basename(path) if path else ''}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+",
                    default=["twomoon", "circle", "2spirals"])
    ap.add_argument("--arms", nargs="+", default=["xbar", "digital"])
    ap.add_argument("--tag", default="run")
    sys.exit(main(ap.parse_args()))
