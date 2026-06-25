"""Plot OP vs TRAN MSE comparison from op_log.csv and tran_log.csv."""

import csv, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BASE = r"D:\Kirchoffnet\kirchoff_claude"

def load(path):
    epochs, mse = [], []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            epochs.append(int(row["epoch"]))
            mse.append(float(row["mse"]))
    return epochs, mse

e_op,   mse_op   = load(f"{BASE}/op_log.csv")
e_tran, mse_tran = load(f"{BASE}/tran_log.csv")

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# linear
axes[0].plot(e_op,   mse_op,   color="#2196F3", lw=2, label=".OP (vn input, DC saddle)")
axes[0].plot(e_tran, mse_tran, color="#FF9800", lw=2, label=".TRAN (IC input, 0.5 ns)")
axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("MSE")
axes[0].set_title("MSE vs Epoch (linear)")
axes[0].legend(); axes[0].grid(True, alpha=0.3)
axes[0].set_xlim(1, max(max(e_op), max(e_tran)))

# log
mse_op_pos   = np.where(np.array(mse_op)   > 0, mse_op,   np.nan)
mse_tran_pos = np.where(np.array(mse_tran) > 0, mse_tran, np.nan)
axes[1].semilogy(e_op,   mse_op_pos,   color="#2196F3", lw=2, label=".OP (vn input, DC saddle)")
axes[1].semilogy(e_tran, mse_tran_pos, color="#FF9800", lw=2, label=".TRAN (IC input, 0.5 ns)")
axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("MSE (log scale)")
axes[1].set_title("MSE vs Epoch (log scale)")
axes[1].legend(); axes[1].grid(True, which="both", alpha=0.3)
axes[1].set_xlim(1, max(max(e_op), max(e_tran)))

# annotations
for ax in axes:
    ax.annotate(f"OP e1: {mse_op[0]:.4f}",
                xy=(e_op[0], mse_op[0]), xytext=(20, 10),
                textcoords="offset points", color="#2196F3", fontsize=8,
                arrowprops=dict(arrowstyle="->", color="#2196F3"))
    ax.annotate(f"TRAN e1: {mse_tran[0]:.4f}",
                xy=(e_tran[0], mse_tran[0]), xytext=(20, -20),
                textcoords="offset points", color="#FF9800", fontsize=8,
                arrowprops=dict(arrowstyle="->", color="#FF9800"))

fig.suptitle("KirchhoffNet — .OP vs .TRAN  (200 epochs, Adam, teacher=[0.5×4], init=[1.5×4])",
             fontweight="bold")
plt.tight_layout()
out = f"{BASE}/mse_comparison.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved -> {out}")
print(f"OP   epoch 1: {mse_op[0]:.6f}  ->  final: {mse_op[-1]:.2e}")
print(f"TRAN epoch 1: {mse_tran[0]:.6f}  ->  final: {mse_tran[-1]:.2e}")
