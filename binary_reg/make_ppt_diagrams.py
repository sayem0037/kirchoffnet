"""Generate supporting diagrams for the project PPT (ring topology, block schematic,
metastable-trap illustration, dataset scatter)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import os

OUT = r"D:\Kirchoffnet\kirchoff_claude\binary_reg\ppt_assets"
os.makedirs(OUT, exist_ok=True)

BLUE   = "#2a78d6"
AQUA   = "#1baf7a"
RED    = "#e34948"
GRID   = "#e1e0d9"
INK    = "#0b0b0b"
INK2   = "#52514e"

# ---------- 1. Ring topology diagram ----------
fig, ax = plt.subplots(figsize=(9, 5), facecolor="white")
ax.set_xlim(0, 10); ax.set_ylim(0, 6); ax.axis("off")

nodes = {
    "net4": (1.2, 4.5), "net6": (4.2, 5.6), "net2": (7.2, 4.5), "net3": (5.7, 1.2),
}
blocks = [("A", "net4", "net6", "V5 / VB1"), ("B", "net6", "net2", "V4 / VB2"),
          ("C", "net2", "net3", "V3 / VB3"), ("D", "net3", "net4", "V2 / VB4")]

for name, (x, y) in nodes.items():
    ax.add_patch(mpatches.Circle((x, y), 0.35, facecolor="#fcfcfb", edgecolor=INK, linewidth=1.5, zorder=3))
    ax.text(x, y, name, ha="center", va="center", fontsize=11, fontweight="bold", zorder=4)

for label, src, dst, params in blocks:
    x0, y0 = nodes[src]; x1, y1 = nodes[dst]
    mx, my = (x0 + x1) / 2, (x0 + x1) / 2 * 0 + (y0 + y1) / 2
    # curve control point pushed outward from centroid
    cx, cy = 4.5, 3.5
    ctrl = (mx + (mx - cx) * 0.5, my + (my - cy) * 0.5)
    arrow = FancyArrowPatch((x0, y0), (x1, y1), connectionstyle=f"arc3,rad=0.25",
                             arrowstyle="-|>", mutation_scale=20, color=BLUE, linewidth=2, zorder=2)
    ax.add_patch(arrow)
    lx, ly = (x0 + x1) / 2 + (mx - cx) * 0.35, (y0 + y1) / 2 + (my - cy) * 0.35
    ax.text(lx, ly, f"Block {label}\n({params})", ha="center", va="center", fontsize=9,
            color=INK2, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=GRID))

ax.text(5, 0.2, "4 inverting stages in a closed loop -> positive feedback -> bistable ring",
        ha="center", fontsize=10, color=INK2, style="italic")
ax.set_title("Ring Topology: 4-Block Differential-Amplifier Loop", fontsize=13, fontweight="bold", color=INK)
fig.tight_layout()
fig.savefig(f"{OUT}/ring_topology.png", dpi=150, facecolor="white")
plt.close(fig)

# ---------- 2. Single block schematic ----------
fig, ax = plt.subplots(figsize=(6, 6), facecolor="white")
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")

def box(x, y, w, h, label, fc="#fcfcfb"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", facecolor=fc, edgecolor=INK, linewidth=1.3))
    ax.text(x + w/2, y + h/2, label, ha="center", va="center", fontsize=9)

ax.text(5, 9.5, "VDD = 3.3V", ha="center", fontsize=10, fontweight="bold")
ax.plot([5, 5], [9.3, 8.8], color=INK, linewidth=1.5)
box(2, 7, 2.2, 1.2, "PCH (dummy)\ngate=theta", "#cde2fb")
box(5.5, 7, 2.2, 1.2, "PCH (signal)\ngate=theta", BLUE)
ax.plot([3.1, 3.1], [8.8, 7], color=INK, linewidth=1.2)
ax.plot([6.6, 6.6], [8.8, 7], color=INK, linewidth=1.2)

box(2, 4.5, 2.2, 1.2, "NCH (dummy)\ngate=VN=1.0V", "#cde2fb")
box(5.5, 4.5, 2.2, 1.2, "NCH (signal)\ngate=net_in", BLUE)
ax.text(1.0, 5.1, "net_x", fontsize=8, color=INK2)
ax.text(8.0, 5.1, "net_out\n(prediction)", fontsize=8, color=AQUA, fontweight="bold")
ax.plot([3.1, 3.1], [7, 5.7], color=INK, linewidth=1.2)
ax.plot([6.6, 6.6], [7, 5.7], color=INK, linewidth=1.2)

box(3.4, 2, 3.2, 1.2, "NCH (tail)\ngate=vbias", "#e0dcf5")
ax.plot([3.1, 5], [4.5, 3.2], color=INK, linewidth=1.2)
ax.plot([6.6, 5], [4.5, 3.2], color=INK, linewidth=1.2)
ax.plot([5, 5], [2, 1.3], color=INK, linewidth=1.5)
ax.text(5, 0.9, "GND", ha="center", fontsize=10, fontweight="bold")

ax.set_title("One Block: Differential-Pair Inverter Stage", fontsize=12, fontweight="bold", pad=10)
fig.tight_layout()
fig.savefig(f"{OUT}/block_schematic.png", dpi=150, facecolor="white")
plt.close(fig)

# ---------- 3. Metastable trap illustration ----------
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), facecolor="white")

x = np.linspace(0, 3.3, 400)
def potential(x, wells):
    v = np.zeros_like(x)
    for c, w, d in wells:
        v += -d * np.exp(-((x - c) ** 2) / (2 * w ** 2))
    return v

ax = axes[0]
v_broken = potential(x, [(1.0, 0.5, 1.0)])
ax.plot(x, v_broken, color=RED, linewidth=2.5)
ax.scatter([1.0], [potential(np.array([1.0]), [(1.0, 0.5, 1.0)])[0]], color=RED, zorder=5, s=60)
ax.set_title("Before: symmetric IC = 1.0V\n(single flat trap, R²=0.428)", fontsize=10)
ax.set_xlabel("Ring state"); ax.set_ylabel("Effective potential")
ax.set_yticks([]); ax.grid(alpha=0.3)

ax = axes[1]
v_fixed = potential(x, [(0.4, 0.5, 1.4), (2.9, 0.5, 1.4)])
ax.plot(x, v_fixed, color=AQUA, linewidth=2.5)
ax.scatter([0.4, 2.9], potential(np.array([0.4, 2.9]), [(0.4, 0.5, 1.4), (2.9, 0.5, 1.4)]),
           color=AQUA, zorder=5, s=60)
ax.set_title("After: class-consistent ICs\n(two deep attractors, R²=0.998)", fontsize=10)
ax.set_xlabel("Ring state"); ax.set_yticks([]); ax.grid(alpha=0.3)

fig.suptitle("The Metastable Trap: Symmetric Init vs. Class-Consistent Init", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(f"{OUT}/metastable_trap.png", dpi=150, facecolor="white")
plt.close(fig)

# ---------- 4. Dataset visualization ----------
fig, ax = plt.subplots(figsize=(8, 3.6), facecolor="white")
ic_high = [0.3, 0.5, 0.7, 0.9, 1.1]
ic_low  = [1.3, 1.6, 1.9, 2.2, 2.5]
ax.scatter(ic_high, [3.3]*5, color=BLUE, s=90, label="HIGH class (target=3.3V)", zorder=3)
ax.scatter(ic_low, [0.3]*5, color=RED, s=90, label="LOW class (target=0.3V)", zorder=3)
ax.axvline(1.2, color=INK2, linestyle="--", linewidth=1.3, label="Boundary = 1.2V")
ax.scatter([1.1], [3.3], facecolor="none", edgecolor=INK, s=220, linewidth=2, zorder=4)
ax.annotate("hardest sample\n(IC=1.1V)", (1.1, 3.3), xytext=(1.1, 2.2),
            ha="center", fontsize=8, color=INK,
            arrowprops=dict(arrowstyle="->", color=INK))
ax.set_xlabel("IC(net3) — the classification feature (V)")
ax.set_ylabel("Target voltage (V)")
ax.set_title("The 10-Sample Dataset", fontsize=12, fontweight="bold")
ax.legend(frameon=False, loc="center right", fontsize=9)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(f"{OUT}/dataset_scatter.png", dpi=150, facecolor="white")
plt.close(fig)

print("Saved 4 diagrams to", OUT)
