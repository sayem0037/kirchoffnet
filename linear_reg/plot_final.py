"""
plot_final.py — comprehensive summary plot of all training runs.
Reads train_log.csv and also uses hardcoded best-run data from momentum SGD.
"""
import os, csv
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

BASE = os.path.dirname(__file__)
LOG  = os.path.join(BASE, "train_log.csv")
OUT  = os.path.join(BASE, "final_results.png")

# ── Best known result: momentum SGD, 200 epochs ──────────────
# From run b3drravpg (recorded in output file)
BEST_MOMENTUM_R2 = 0.4013
BEST_MOMENTUM_EPOCH = 200

def load_log(path):
    epochs, mse, r2 = [], [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            epochs.append(int(row["epoch"]))
            mse.append(float(row["mse_loss"]))
            r2.append(float(row["r2"]))
    return np.array(epochs), np.array(mse), np.array(r2)

epochs, mse, r2 = load_log(LOG)
best_r2_ever = max(max(r2), BEST_MOMENTUM_R2)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "KirchhoffNet Regression Training — Honest Results\n"
    "4-block differential-amp ring  |  TRAN 100ns  |  30 samples  |  8 trainable params",
    fontsize=12, fontweight="bold"
)

# ── Left: MSE loss ────────────────────────────────────────────
ax1 = axes[0]
ax1.plot(epochs, mse, color="steelblue", linewidth=1.5, label="Adam (this run)")
ax1.axhline(y=mse[0], color="gray", linewidth=0.8, linestyle="--", label=f"Initial MSE={mse[0]:.3f}")
ax1.set_xlabel("Epoch")
ax1.set_ylabel("MSE Loss (V²)")
ax1.set_title("Mean Squared Error")
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.set_ylim(bottom=0)

# ── Right: R² score ───────────────────────────────────────────
ax2 = axes[1]
ax2.plot(epochs, r2, color="darkorange", linewidth=1.5, label="Adam (this run)")

# Mark best momentum SGD result
ax2.axhline(y=BEST_MOMENTUM_R2, color="green", linewidth=1.5, linestyle="--",
            label=f"Best ever: Momentum SGD R²={BEST_MOMENTUM_R2:.3f} ({BEST_MOMENTUM_R2*100:.1f}%)")
ax2.axhline(y=0.90, color="red", linewidth=1.2, linestyle=":", label="Target R²=0.90")
ax2.axhline(y=0.0,  color="black", linewidth=0.8, linestyle="-", alpha=0.3, label="R²=0 (predicts mean)")

# Shade the achievable region
ax2.fill_between(epochs, 0, np.clip(r2, 0, 1), alpha=0.15, color="darkorange")

ax2.set_xlabel("Epoch")
ax2.set_ylabel("R² Score")
ax2.set_title("R² Coefficient of Determination")
ax2.set_ylim(-0.5, 1.05)
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

# Annotation: why 0.90 is not reachable
ax2.annotate(
    "Circuit ceiling ≈ 0.40\n"
    "(only Block D active at 100ns;\n"
    "sensitivity ~1e-8 V/V, nanosecale corrections\n"
    "vs volt-scale IC dominance)",
    xy=(epochs[-1]*0.6, 0.42),
    fontsize=8, color="darkgreen",
    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8)
)

final_r2 = r2[-1]
ax2.annotate(
    f"Final R²={final_r2:.3f}\n({final_r2*100:.1f}%)",
    xy=(epochs[-1], final_r2),
    xytext=(-60, -30), textcoords="offset points",
    fontsize=9, color="darkorange",
    arrowprops=dict(arrowstyle="->", color="darkorange"),
)

plt.tight_layout()
plt.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT}")
print(f"\nSummary:")
print(f"  Initial MSE:      {mse[0]:.4f}")
print(f"  Final MSE:        {mse[-1]:.4f}  ({(1-mse[-1]/mse[0])*100:.1f}% improvement)")
print(f"  Final R²:         {r2[-1]:.4f}  ({r2[-1]*100:.1f}%)")
print(f"  Best R² (Adam):   {max(r2):.4f}  ({max(r2)*100:.1f}%)")
print(f"  Best R² (ever):   {BEST_MOMENTUM_R2:.4f}  ({BEST_MOMENTUM_R2*100:.1f}%)")
print(f"  R²=0.90 target:   NOT REACHABLE with this circuit+tstop configuration")
plt.show()
