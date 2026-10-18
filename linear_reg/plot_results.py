"""
plot_results.py — plot MSE loss and R^2 over training epochs
Reads train_log.csv written by train.py.
"""

import os
import csv
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

LOG_CSV  = os.path.join(os.path.dirname(__file__), "train_log.csv")
OUT_PNG  = os.path.join(os.path.dirname(__file__), "training_results.png")

# If epoch numbers restart (new run appended to log), renumber them sequentially


def load_log(path):
    epochs, mse, r2, best_r2 = [], [], [], []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            epochs.append(int(row["epoch"]))
            mse.append(float(row["mse_loss"]))
            r2.append(float(row["r2"]))
            best_r2.append(float(row["best_r2"]))
    return epochs, mse, r2, best_r2


def plot(epochs, mse, r2, best_r2):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    fig.suptitle("KirchhoffNet — Regression Training", fontsize=14, fontweight="bold")

    # ── MSE loss ──────────────────────────────────────────────
    ax1.plot(epochs, mse, color="steelblue", linewidth=1.5, label="MSE loss")
    ax1.set_ylabel("MSE Loss (V²)")
    ax1.set_title("Mean Squared Error per Epoch")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.4f"))

    # ── R² ────────────────────────────────────────────────────
    ax2.plot(epochs, r2,      color="darkorange",  linewidth=1.5, label="R² (this epoch)")
    ax2.plot(epochs, best_r2, color="green",       linewidth=1.5, linestyle="--", label="Best R²")
    ax2.axhline(y=0.90, color="red", linewidth=1.0, linestyle=":", label="90% target")
    ax2.set_ylabel("R² Score")
    ax2.set_xlabel("Epoch")
    ax2.set_title("R² Coefficient of Determination")
    ax2.set_ylim(min(-0.1, min(r2) - 0.05), 1.05)
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Annotate final R²
    final_r2 = r2[-1]
    best_val = max(best_r2)
    ax2.annotate(
        f"Best R²={best_val:.4f}",
        xy=(epochs[best_r2.index(best_val)], best_val),
        xytext=(10, -20), textcoords="offset points",
        fontsize=9, color="green",
        arrowprops=dict(arrowstyle="->", color="green"),
    )

    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    print(f"Plot saved: {OUT_PNG}")
    plt.show()


if __name__ == "__main__":
    if not os.path.exists(LOG_CSV):
        print(f"No log found at {LOG_CSV} — run train.py first.")
    else:
        epochs, mse, r2, best_r2 = load_log(LOG_CSV)
        print(f"Loaded {len(epochs)} epochs from {LOG_CSV}")
        print(f"Final MSE: {mse[-1]:.5f}   Best R^2: {max(best_r2):.4f} ({max(best_r2)*100:.1f}%)")
        plot(epochs, mse, r2, best_r2)
