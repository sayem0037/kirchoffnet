# -*- coding: utf-8 -*-
"""
make_figures.py -- the ICCAD figure set, built from results/bench_*.json.

DESIGN RULES APPLIED (and why, so they survive editing)
-------------------------------------------------------
* Three arms -> three categorical hues, taken in fixed slot order from a
  validated palette (blue, orange, aqua). Those three slots are documented to
  clear every colour-vision gate on the all-pairs list, which is the list that
  applies to a scatter. Colour follows the ARM, never its rank, so a figure that
  drops an arm does not repaint the others.
* No dual-axis chart anywhere. Energy and accuracy are different scales, so
  they get a scatter, not two y-axes on one plot.
* Identity is never carried by colour alone: every figure has a legend AND
  direct labels, which is also what makes these readable when the proceedings
  print them in greyscale.
* Values are in ink, not in the series colour; grid and axes are recessive.
* Energy and area span three orders of magnitude between the arms, so those
  axes are logarithmic and say so in the label. A linear axis here would render
  the analog bars as invisible slivers.
"""

import argparse
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
FIGS = os.path.join(BASE, "figs")
os.makedirs(FIGS, exist_ok=True)

# Validated categorical slots, in fixed order. Do not cycle, do not generate.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
YELLOW, MAGENTA, GREEN = "#eda100", "#e87ba4", "#008300"
VIOLET, RED = "#4a3aa7", "#e34948"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8a85"
GRID = "#d8d8d4"

ARM_COLOR = {"KFQ": BLUE, "XBAR": ORANGE, "DMLP": AQUA}
# Every contributor gets its OWN slot. An earlier version reused blue for both
# "mos" and "logic" and orange for both "res" and "accum", which put two
# identical swatches in one legend -- the reader cannot tell which is which,
# and colour is supposed to carry identity.
PART_COLOR = {"mos": BLUE, "res": ORANGE, "cap": AQUA,
              "adc": YELLOW, "dac": MAGENTA, "sram": GREEN,
              "logic": VIOLET, "accum": RED}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "figure.dpi": 160, "savefig.dpi": 300,
    "savefig.bbox": "tight", "legend.frameon": False,
})


def family(arm):
    for k in ARM_COLOR:
        if arm.upper().startswith(k):
            return k
    return "DMLP"


def color_of(arm):
    return ARM_COLOR[family(arm)]


def _tidy(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", visible=False)


def load_bench(dataset, tag):
    p = os.path.join(RESULTS, f"bench_{dataset}_{tag}.json")
    if not os.path.exists(p):
        cands = sorted(glob.glob(os.path.join(RESULTS, f"bench_{dataset}_*.json")),
                       key=os.path.getmtime, reverse=True)
        if not cands:
            raise FileNotFoundError(
                f"no bench_{dataset}_*.json -- run run_bench.py first")
        p = cands[0]
    return json.load(open(p)), p


# ---------------------------------------------------------------- fig 1 -----
def fig_accuracy(d, out):
    """Test accuracy with Wilson 95% intervals, chance marked."""
    rows = [r for r in d["rows"] if r.get("test") is not None
            and r["arm"] != "chance"]
    if not rows:
        return None
    chance = next((r["test"] for r in d["rows"] if r["arm"] == "chance"), None)

    names = [r["arm"] for r in rows]
    vals = [r["test"] for r in rows]
    lo = [v - (r.get("ci") or [v, v])[0] for v, r in zip(vals, rows)]
    hi = [(r.get("ci") or [v, v])[1] - v for v, r in zip(vals, rows)]

    fig, ax = plt.subplots(figsize=(7.0, 0.42 * len(rows) + 1.5))
    y = np.arange(len(rows))
    ax.barh(y, vals, height=0.62, color=[color_of(n) for n in names],
            zorder=2)
    ax.errorbar(vals, y, xerr=[lo, hi], fmt="none", ecolor=INK2,
                elinewidth=1.2, capsize=3, zorder=3)
    for yi, v in zip(y, vals):
        ax.text(v + 0.018, yi, f"{v:.3f}", va="center", ha="left",
                fontsize=8.5, color=INK)

    if chance is not None:
        ax.axvline(chance, color=MUTED, lw=1.2, ls="--", zorder=1)
        # Above the first bar, not below the last: the y-axis is inverted, so
        # the "below" position falls outside the axes and gets clipped.
        ax.text(chance, -0.75, f" chance {chance:.2f}",
                color=MUTED, fontsize=8, va="center")

    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_ylim(len(rows) - 0.5, -1.1)      # headroom for the chance label
    ax.set_xlim(0, 1.16)
    ax.set_xlabel("test accuracy (Wilson 95% interval)")
    ax.set_title(f"Accuracy on {d['dataset']}  "
                 f"({d['n_test']} test samples)", loc="left")
    ax.grid(axis="y", visible=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.savefig(out); plt.close(fig)
    return out


# ---------------------------------------------------------------- fig 2 -----
def fig_energy_accuracy(d, out):
    """Energy vs accuracy -- the Pareto view.

    Better is UP AND LEFT: high accuracy for little energy. (An earlier draft
    of this figure said "down and right" in its own title, which is exactly
    backwards and would have had a reader read the worst arm as the best one.)

    Points are de-duplicated. The parallel and serial digital variants have
    IDENTICAL energy and accuracy -- they trade latency against area and
    nothing else -- so they land on the same coordinates and their labels
    overprint into unreadable mush. They share one point and one label here;
    what separates them belongs to figures 3 and 4.
    """
    rows = [r for r in d["rows"]
            if r.get("hw", {}).get("energy_j") and r.get("test") is not None]
    if len(rows) < 2:
        return None

    merged = {}
    for r in rows:
        key = (round(r["hw"]["energy_j"], 18), round(r["test"], 6))
        merged.setdefault(key, []).append(r)

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    seen = set()
    for (e_j, acc), grp in merged.items():
        fam = family(grp[0]["arm"])
        ax.scatter(e_j * 1e12, acc, s=95, color=color_of(grp[0]["arm"]),
                   edgecolor="white", linewidth=1.2, zorder=3,
                   label=fam if fam not in seen else None)
        seen.add(fam)

        names = [g["arm"] for g in grp]
        if len(names) > 1:
            # "DMLP INT8 parallel" + "DMLP INT8 serial" -> "DMLP INT8"
            head = names[0].rsplit(" ", 1)[0]
            label = head if all(n.startswith(head) for n in names)                 else " / ".join(names)
        else:
            label = names[0]
        ax.annotate(label, (e_j * 1e12, acc), textcoords="offset points",
                    xytext=(9, 6), fontsize=8, color=INK2)

    ax.set_xscale("log")
    ax.set_xlabel("energy per inference (pJ, log scale)")
    ax.set_ylabel("test accuracy")
    ax.set_title(f"Energy vs accuracy on {d['dataset']}   "
                 f"(better = up and left)", loc="left")
    ax.margins(x=0.22, y=0.16)
    ax.legend(loc="lower left", fontsize=8)
    _tidy(ax)
    ax.grid(axis="x", visible=True)
    fig.savefig(out); plt.close(fig)
    return out


# ---------------------------------------------------------------- fig 3 -----
def fig_area(d, out):
    """Area, split by what it is spent on.

    TWO PANELS, deliberately. The analog and digital arms differ by more than
    two orders of magnitude (0.008 mm^2 against 1.845 mm^2), so on one linear
    axis the KFQ bar is a single invisible pixel -- which communicates nothing,
    even though "it is tiny" is exactly the finding. A log axis is not the fix
    either: segment lengths in a STACKED bar have to stay proportional to be
    read as parts of a whole, and a log axis destroys that. So each family gets
    its own scale, and the panel titles carry the totals.
    """
    rows = [r for r in d["rows"] if r.get("hw", {}).get("area_um2")]
    if not rows:
        return None

    parts = []
    for r in rows:
        bd = r["hw"].get("area_breakdown") or {}
        parts += [k for k in bd if k != "total"]
    order = [p for p in ("mos", "res", "cap", "logic", "accum", "sram",
                         "adc", "dac") if p in set(parts)]

    groups = [("Analog", [r for r in rows if family(r["arm"]) != "DMLP"]),
              ("Digital", [r for r in rows if family(r["arm"]) == "DMLP"])]
    groups = [g for g in groups if g[1]]

    heights = [0.5 * len(g[1]) + 1.6 for g in groups]
    fig, axes = plt.subplots(len(groups), 1, figsize=(7.2, sum(heights)),
                             gridspec_kw=dict(height_ratios=heights))
    axes = np.atleast_1d(axes)

    for ai, (ax, (label, grp)) in enumerate(zip(axes, groups)):
        y = np.arange(len(grp))
        left = np.zeros(len(grp))
        for part in order:
            vals = np.array([float((r["hw"].get("area_breakdown") or {})
                                   .get(part, 0.0)) for r in grp])
            if not vals.any():
                continue
            ax.barh(y, vals, left=left, height=0.6, label=part,
                    color=PART_COLOR.get(part, MUTED), zorder=2,
                    edgecolor="white", linewidth=0.8)
            left += vals

        for yi, r in enumerate(grp):
            ax.text(r["hw"]["area_um2"] * 1.02, yi,
                    f"{r['hw']['area_um2'] / 1e6:.3f} mm²", va="center",
                    ha="left", fontsize=8.5, color=INK)

        ax.set_yticks(y)
        ax.set_yticklabels([r["arm"] for r in grp])
        ax.invert_yaxis()
        tot = np.array([r["hw"]["area_um2"] for r in grp], dtype=float)
        ax.set_xlim(0, max(tot.max(), left.max()) * 1.30)
        ax.set_title(label, loc="left", fontsize=9, color=INK2)
        ax.grid(axis="y", visible=False)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        # Legend BELOW the axes, never inside: at "lower right" it landed on
        # top of the XBAR bar and covered its value label, which is the one
        # number the panel exists to show.
        used = ax.get_legend_handles_labels()[1]
        # The bottom panel also carries the shared x-axis label, so its legend
        # needs to clear that too.
        drop = -0.30 if ai == len(groups) - 1 else -0.13
        ax.legend(ncol=min(len(used), 5), fontsize=8, loc="upper center",
                  bbox_to_anchor=(0.5, drop), borderaxespad=0.0)

    axes[-1].set_xlabel("area (µm², first-order estimate at 350 nm)")
    fig.suptitle(f"Area breakdown on {d['dataset']} "
                 f"(note the two panels have different scales)",
                 x=0.09, ha="left", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out); plt.close(fig)
    return out


# ---------------------------------------------------------------- fig 4 -----
def fig_latency_sweep(dataset, out):
    """Settling time vs node load.

    This is the figure that keeps the latency claim honest. Every netlist in
    the repo uses 0.1 fF, which settles in ~1e-13 s -- fine for training, not a
    silicon latency. Publishing the sweep makes the load assumption explicit
    instead of hiding it inside one number.
    """
    series = []
    for arm in ("kfq", "xbar"):
        hits = sorted(glob.glob(os.path.join(RESULTS, f"hw_{arm}_{dataset}_*.json")),
                      key=os.path.getmtime, reverse=True)
        if not hits:
            continue
        d = json.load(open(hits[0]))
        rows = sorted(d["rows"], key=lambda r: r["cap_f"])
        if len(rows) < 2:
            continue
        series.append((arm.upper(), [r["cap_f"] for r in rows],
                       [r["latency_s"] for r in rows]))
    if not series:
        return None

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for name, cs, ts in series:
        ax.plot(np.array(cs) * 1e15, np.array(ts) * 1e9, marker="o",
                ms=6, lw=2, color=ARM_COLOR[family(name)], label=name,
                zorder=3)
        ax.annotate(name, (cs[-1] * 1e15, ts[-1] * 1e9),
                    textcoords="offset points", xytext=(6, -2),
                    fontsize=8, color=INK2)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("node load capacitance (fF, log scale)")
    ax.set_ylabel("settling time (ns, log scale)")
    ax.set_title(f"Latency vs load on {dataset}  "
                 f"(0.1 fF is the training convenience, not a silicon load)",
                 loc="left", fontsize=9)
    ax.legend(fontsize=8)
    _tidy(ax)
    ax.grid(axis="x", visible=True)
    fig.savefig(out); plt.close(fig)
    return out


# ---------------------------------------------------------------- fig 5 -----
def fig_converters(d, out):
    """What fraction of each arm's energy goes to data conversion.

    KFQ's bar is zero by construction -- it never leaves the analog domain
    between layers -- and that is the architectural claim the paper is making,
    so it gets its own figure rather than a footnote.
    """
    # ANALOG ARMS ONLY. The digital arms also report zero converters, but for
    # an entirely different reason -- they never leave the digital domain at
    # all -- so labelling their energy "analog core" would be false, and their
    # bars dwarf the axis while answering a question this figure is not asking.
    rows = [r for r in d["rows"] if r.get("hw", {}).get("energy_j")
            and r["hw"].get("converters") is not None
            and family(r["arm"]) != "DMLP"]
    if not rows:
        return None

    names = [r["arm"] for r in rows]
    core = np.array([r["hw"]["energy_j"] - r["hw"].get("converters_j", 0.0)
                     for r in rows]) * 1e12
    conv = np.array([r["hw"].get("converters_j", 0.0) for r in rows]) * 1e12

    fig, ax = plt.subplots(figsize=(7.0, 0.62 * len(rows) + 2.0))
    y = np.arange(len(rows))
    ax.barh(y, core, height=0.55, color=BLUE, label="compute core",
            zorder=2, edgecolor="white", linewidth=0.8)
    ax.barh(y, conv, left=core, height=0.62, color=ORANGE,
            label="data conversion", zorder=2, edgecolor="white",
            linewidth=0.8)
    for yi, (c, v, r) in enumerate(zip(core, conv, rows)):
        cv = r["hw"]["converters"]
        tag = f"{c + v:.1f} pJ"
        if cv.get("adc") or cv.get("dac"):
            share = 100.0 * v / max(c + v, 1e-30)
            tag += (f"   ADC {cv['adc']}, DAC {cv['dac']}"
                    f"  ->  {share:.0f}% of energy is conversion")
        else:
            tag += "   no converters"
        ax.text((c + v) * 1.02, yi, tag, va="center", ha="left",
                fontsize=8.2, color=INK)

    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlim(0, (core + conv).max() * 1.75)
    ax.set_xlabel("energy per inference (pJ)")
    ax.set_title("Where the analog energy goes: core vs data conversion",
                 loc="left")
    ax.legend(fontsize=8, ncol=2, loc="upper center",
              bbox_to_anchor=(0.5, -0.30), borderaxespad=0.0)
    ax.grid(axis="y", visible=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.savefig(out); plt.close(fig)
    return out


# ================================================================== main =====
def main(a):
    d, src = load_bench(a.dataset, a.tag)
    print(f"figures from {os.path.basename(src)}")

    made = []
    for fn, name in ((fig_accuracy, "fig1_accuracy"),
                     (fig_energy_accuracy, "fig2_energy_accuracy"),
                     (fig_area, "fig3_area"),
                     (fig_converters, "fig5_converters")):
        p = os.path.join(FIGS, f"{name}_{a.dataset}.png")
        r = fn(d, p)
        made.append((name, r))

    p = os.path.join(FIGS, f"fig4_latency_{a.dataset}.png")
    made.append(("fig4_latency", fig_latency_sweep(a.dataset, p)))

    for name, r in made:
        print(f"  {'wrote ' if r else 'SKIP  '}{name:<22} "
              f"{os.path.basename(r) if r else '(no data)'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--tag", default="run")
    sys.exit(main(ap.parse_args()))
