"""Plot MSE and R² from train_log.csv."""
import csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOG = os.path.join(os.path.dirname(__file__), "train_log.csv")

epochs, mse, r2, v2 = [], [], [], []
with open(LOG) as f:
    reader = csv.DictReader(f)
    for row in reader:
        epochs.append(int(row["epoch"]))
        mse.append(float(row["train_mse"]))
        r2v = row["r2_100ns"]
        r2.append(float(r2v) if r2v != "nan" else float("nan"))
        v2.append(float(row["V2"]))

fig, axes = plt.subplots(3, 1, figsize=(8, 9), sharex=True)
fig.suptitle("KirchhoffNet Binary Classification — Training Curves\n"
             "Sensitivity-based SGD (sign-SGD, V2 only)", fontsize=12)

ax1, ax2, ax3 = axes

ax1.plot(epochs, mse, "b-o", ms=3, lw=1.5)
ax1.set_ylabel("Train MSE\n(vs teacher @ 10 ns)")
ax1.set_yscale("log")
ax1.grid(True, alpha=0.4)
ax1.set_title(f"MSE: {mse[0]:.3f} -> {mse[-1]:.6f}")

r2_valid = [(e, r) for e, r in zip(epochs, r2) if not np.isnan(r)]
if r2_valid:
    ep_r2, vals_r2 = zip(*r2_valid)
    ax2.plot(ep_r2, vals_r2, "g-o", ms=3, lw=1.5)
ax2.axhline(0.90, color="r", ls="--", lw=1, label="R²=0.90 target")
ax2.set_ylabel("R² @ 1µs\n(vs binary labels)")
ax2.set_ylim(-0.1, 1.05)
ax2.grid(True, alpha=0.4)
ax2.legend(fontsize=9)
best_r2 = max(r for r in r2 if not np.isnan(r))
ax2.set_title(f"R²: best = {best_r2:.4f} ({best_r2*100:.1f}%)")

ax3.plot(epochs, v2, "m-o", ms=3, lw=1.5)
ax3.axhline(1.60, color="k", ls="--", lw=1, label="Teacher V2=1.60")
ax3.set_ylabel("V2 (volts)")
ax3.set_xlabel("Epoch")
ax3.grid(True, alpha=0.4)
ax3.legend(fontsize=9)
ax3.set_title(f"V2: {v2[0]:.4f} -> {v2[-1]:.4f}")

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), "training_curves.png")
plt.savefig(out, dpi=120, bbox_inches="tight")
print(f"Saved: {out}")
print(f"\nSummary:")
print(f"  Epochs run     : {len(epochs)}")
print(f"  MSE start->end  : {mse[0]:.5f} -> {mse[-1]:.6f}")
print(f"  R² best        : {best_r2:.4f}  ({best_r2*100:.1f}%)")
print(f"  V2  start->end  : {v2[0]:.5f} -> {v2[-1]:.5f}")
print(f"  Teacher V2     : 1.60000")
