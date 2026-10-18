#!/usr/bin/env python3
"""Generate system-level diagrams for the AI Hardware review paper."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Patch
import matplotlib.patches as mpatches
import numpy as np
import os

OUT = "/sessions/gracious-busy-knuth/mnt/outputs/figures"
os.makedirs(OUT, exist_ok=True)

# palette
DIG = "#2f6fb0"      # digital blue
DIG_L = "#d6e6f5"
ANA = "#e08a2b"      # analog amber
ANA_L = "#fbe6cd"
TEAL = "#1b8a8a"
TEAL_L = "#cdeceb"
GREY = "#555555"
GREY_L = "#e9e9e9"
RED = "#c0392b"
INK = "#222222"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "savefig.dpi": 200,
    "figure.dpi": 200,
})

def box(ax, x, y, w, h, text, fc=DIG_L, ec=DIG, tc=INK, fs=10, bold=False, rounded=0.02):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0.01,rounding_size={rounded}",
                       fc=fc, ec=ec, lw=1.6)
    ax.add_patch(p)
    ax.text(x+w/2, y+h/2, text, ha="center", va="center",
            fontsize=fs, color=tc, fontweight="bold" if bold else "normal",
            wrap=True)
    return (x+w/2, y+h/2)

def arrow(ax, p1, p2, color=GREY, lw=1.8, style="-|>", ls="-"):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=14,
                        color=color, lw=lw, linestyle=ls,
                        shrinkA=2, shrinkB=2)
    ax.add_patch(a)

def finish(fig, ax, name, xlim=(0,10), ylim=(0,10), title=None):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold", color=INK, pad=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/{name}.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)

# ---------------------------------------------------------------
# FIG 1 — Taxonomy
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 6.2))
box(ax, 3.7, 8.7, 2.6, 0.9, "AI / ML Hardware", fc="#dfe7ef", ec=INK, bold=True, fs=12)
# two branches
box(ax, 1.2, 6.9, 3.0, 0.9, "DIGITAL\n(compute with bits)", fc=DIG_L, ec=DIG, bold=True)
box(ax, 5.8, 6.9, 3.0, 0.9, "ANALOG / EMERGING\n(compute with physics)", fc=ANA_L, ec=ANA, bold=True)
arrow(ax, (5.0,8.7),(2.7,7.8), color=INK); arrow(ax, (5.0,8.7),(7.3,7.8), color=INK)
# digital leaves
dl = ["GPU\n(programmable)", "TPU / systolic\nASIC", "FPGA\n(reconfigurable)", "Dataflow /\nnear-memory ASIC"]
for i,t in enumerate(dl):
    x = 0.2 + i*2.45
    box(ax, x, 4.6, 2.2, 1.1, t, fc=DIG_L, ec=DIG, fs=9)
    arrow(ax, (2.7,6.9),(x+1.1,5.7), color=DIG, lw=1.3)
# analog leaves
al = ["Resistive\ncrossbar (RRAM/PCM)", "Photonic\n(MZI mesh)", "Neuromorphic\n(spiking)", "Physics-based\n(KirchhoffNet)"]
for i,t in enumerate(al):
    x = 0.2 + i*2.45
    box(ax, x, 2.7, 2.2, 1.1, t, fc=ANA_L, ec=ANA, fs=9)
    arrow(ax, (7.3,6.9),(x+1.1,3.8), color=ANA, lw=1.3)
ax.text(5.0, 1.9, "Cross-cutting axes:  digital⟷analog · compute-centric⟷in-memory · spatial⟷temporal · clocked⟷event-driven",
        ha="center", fontsize=9.5, style="italic", color=GREY)
finish(fig, ax, "fig01_taxonomy", xlim=(0,10.4), ylim=(1.4,10),
       title="Figure 1. A taxonomy of AI hardware")

# ---------------------------------------------------------------
# FIG 2 — MVM primitive
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10.5, 5.2))
ax.text(2.3, 9.3, "The primitive: y = σ(Wx + b)", fontsize=13, fontweight="bold", ha="center")
# matrix
W = np.array([[0.8,0.1,0.5,0.2],[0.3,0.9,0.1,0.6],[0.2,0.4,0.7,0.1],[0.5,0.2,0.3,0.8]])
for i in range(4):
    for j in range(4):
        c = plt.cm.Blues(0.25+0.6*W[i,j])
        ax.add_patch(Rectangle((0.6+j*0.6, 6.0-i*0.6), 0.55, 0.55, fc=c, ec="white"))
ax.text(1.8, 7.1, "W  (weights, reused)", ha="center", fontsize=10, color=DIG, fontweight="bold")
ax.text(1.8, 3.05, "N×N matrix → N² MACs", ha="center", fontsize=9, color=GREY)
# vector
for i in range(4):
    ax.add_patch(Rectangle((3.9, 6.0-i*0.6), 0.55, 0.55, fc=ANA_L, ec=ANA))
ax.text(4.17, 7.1, "x", ha="center", fontsize=11, color=ANA, fontweight="bold")
ax.text(5.0, 4.6, "=", ha="center", fontsize=20)
# output
for i in range(4):
    ax.add_patch(Rectangle((5.5, 6.0-i*0.6), 0.55, 0.55, fc=TEAL_L, ec=TEAL))
ax.text(5.77, 7.1, "y", ha="center", fontsize=11, color=TEAL, fontweight="bold")
# annotations
box(ax, 7.0, 5.6, 3.1, 1.5,
    "Two facts drive all designs:\n① every multiply is INDEPENDENT\n(parallelism wins)\n② W is REUSED across inputs\n(keep weights near compute)",
    fc="#fbfbe8", ec="#b3a600", fs=9.2)
box(ax, 7.0, 3.3, 3.1, 1.6,
    "Digital: build grids of MAC units\nAnalog: store W as a physical\nquantity; let Ohm+Kirchhoff\nlaws do multiply & sum for free",
    fc=GREY_L, ec=GREY, fs=9.2)
finish(fig, ax, "fig02_mvm", xlim=(0,10.4), ylim=(2.6,9.8),
       title="Figure 2. Every neural-network layer reduces to matrix-vector multiplication")

# ---------------------------------------------------------------
# FIG 3 — GPU
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10.5, 6.0))
# HBM stacks
for i,x in enumerate([0.3, 8.9]):
    box(ax, x, 2.2, 0.9, 5.4, "HBM3e\nmemory\n(192 GB)\n~8 TB/s", fc="#efe3f3", ec="#7b4b9e", fs=8.5)
# die outline
ax.add_patch(FancyBboxPatch((1.6,1.8), 6.9, 6.2, boxstyle="round,pad=0.02,rounding_size=0.05",
                            fc="#f4f8fc", ec=DIG, lw=2))
ax.text(5.05, 7.6, "GPU die (dual-die package, >200B transistors)", ha="center",
        fontsize=10, color=DIG, fontweight="bold")
# SMs grid
for r in range(3):
    for c in range(5):
        x = 1.95+c*1.28; y = 3.0+r*1.35
        box(ax, x, y, 1.12, 1.15, "SM\ncores +\nTensor\nCore", fc=DIG_L, ec=DIG, fs=7.5)
# L2 bar
box(ax, 1.95, 2.2, 6.15, 0.55, "Shared L2 cache / interconnect (NVLink 5: 1.8 TB/s)", fc="#cddcea", ec=DIG, fs=8.5)
box(ax, 2.3, 8.15, 5.5, 0.6, "Thousands of parallel cores · 5th-gen Tensor Cores do FP4/FP8/BF16 tile matrix-multiply",
    fc="#fbfbe8", ec="#b3a600", fs=8.5)
finish(fig, ax, "fig03_gpu", xlim=(0,10.4), ylim=(1.6,9.1),
       title="Figure 3. GPU (e.g. NVIDIA Blackwell B200): flexible, massively parallel arithmetic")

# ---------------------------------------------------------------
# FIG 4 — Systolic array
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.5, 7.2))
n = 4
x0, y0, s = 2.6, 2.2, 1.3
for i in range(n):
    for j in range(n):
        x = x0+j*s; y = y0+(n-1-i)*s
        box(ax, x, y, s*0.82, s*0.82, "×\n+", fc=DIG_L, ec=DIG, fs=11, bold=True)
        # right arrow (data)
        if j < n-1:
            arrow(ax, (x+s*0.82, y+s*0.41),(x+s, y+s*0.41), color=ANA, lw=1.5)
        # down arrow (partial sum)
        if i < n-1:
            arrow(ax, (x+s*0.41, y),(x+s*0.41, y-s*0.18), color=TEAL, lw=1.5)
# weight labels
ax.text(x0+n*s*0.42, y0+n*s+0.15, "weights preloaded, one per cell (stationary)",
        ha="center", fontsize=9.5, color=DIG, fontweight="bold")
# input arrows from left
for i in range(n):
    y = y0+(n-1-i)*s+s*0.41
    arrow(ax, (x0-1.0, y),(x0, y), color=ANA, lw=2)
    ax.text(x0-1.15, y, f"x{i+1}", ha="right", va="center", color=ANA, fontsize=10, fontweight="bold")
# outputs bottom
for j in range(n):
    x = x0+j*s+s*0.41
    arrow(ax, (x, y0-0.18),(x, y0-1.0), color=TEAL, lw=2)
    ax.text(x, y0-1.15, f"y{j+1}", ha="center", va="top", color=TEAL, fontsize=10, fontweight="bold")
ax.text(x0+n*s*0.42, y0-1.7, "→ inputs flow rightward   ↓ partial sums accumulate downward   (weights never move → beats the memory wall)",
        ha="center", fontsize=9, color=GREY, style="italic")
finish(fig, ax, "fig04_systolic", xlim=(0.6,9), ylim=(0.2,9),
       title="Figure 4. TPU systolic array: data flows rhythmically through stationary weights")

# ---------------------------------------------------------------
# FIG 5 — FPGA fabric
# ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6.2))
ax.add_patch(FancyBboxPatch((0.4,0.8),9.2,7.4, boxstyle="round,pad=0.02,rounding_size=0.05",
                            fc="#f6faf6", ec=TEAL, lw=2))
labels = {"CLB":("#dfeaf6",DIG),"DSP":("#fbe6cd",ANA),"BRAM":("#e7f3e7",TEAL),"I/O":("#eee",GREY)}
grid = [["I/O","CLB","CLB","DSP","CLB","CLB","DSP","I/O"],
        ["CLB","CLB","BRAM","CLB","DSP","BRAM","CLB","CLB"],
        ["DSP","CLB","CLB","CLB","CLB","CLB","CLB","DSP"],
        ["CLB","BRAM","DSP","CLB","CLB","DSP","BRAM","CLB"],
        ["I/O","CLB","CLB","DSP","CLB","CLB","CLB","I/O"]]
for r,row in enumerate(grid):
    for c,cell in enumerate(row):
        x=0.9+c*1.05; y=6.9-r*1.25
        fc,ec = labels[cell]
        box(ax, x, y, 0.92, 1.05, cell, fc=fc, ec=ec, fs=8)
# routing lines
for c in range(9):
    ax.plot([0.85+c*1.05,0.85+c*1.05],[1.0,7.9], color="#cccccc", lw=0.6, zorder=0)
leg = [Patch(fc=v[0], ec=v[1], label=k) for k,v in labels.items()]
ax.legend(handles=leg, loc="lower center", ncol=4, fontsize=9, bbox_to_anchor=(0.5,-0.13), frameon=False)
ax.text(5.0, 8.5, "Configurable fabric: you WIRE it into the exact accelerator you want (bitstream-programmed)",
        ha="center", fontsize=9.2, color=GREY, style="italic")
finish(fig, ax, "fig05_fpga", xlim=(0,10), ylim=(0.2,9),
       title="Figure 5. FPGA: logic blocks (CLB), multipliers (DSP), memory (BRAM) + programmable routing")

print("BATCH 1 DONE")
