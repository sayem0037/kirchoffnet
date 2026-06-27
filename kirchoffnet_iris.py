"""
KirchhoffNet — 3-Class IRIS Classification
===========================================
Trains the 4-block differential-amplifier ring circuit to classify IRIS flowers.

Input encoding:
  The 4 IRIS features map directly to the 4 ring-node IC voltages:
    sepal length -> net2 IC
    sepal width  -> net3 IC
    petal length -> net4 IC
    petal width  -> net6 IC
  Each feature is independently min-max normalised to [0.2 V, 3.1 V]
  using statistics from the full 150-sample IRIS dataset.

Output encoding (class -> target voltage):
    setosa     (class 0) -> 0.5  V
    versicolor (class 1) -> 1.65 V
    virginica  (class 2) -> 2.8  V
  V(net2) at t=0.5 ns is compared to all three target voltages; the
  nearest one determines the predicted class.

Simulator:
  One .TRAN 10p 0.5n call per datapoint with sensitivity=True returns
  BOTH the output voltage and dV(net2)/dTheta_j at the same time point,
  so the gradient directly minimises the TRAN loss.

Loss / gradient:
  L        = (1/N) * sum_i (v_pred_i - target_i)^2
  dL/dth_j = (2/N) * sum_i (v_pred_i - target_i) * dV_tran/dth_j

Known limitation:
  At t=0.5 ns, only Block B (theta2/V4) has substantial sensitivity for
  net2. Blocks C and D (theta3/V3, theta4/V2) are 2-3 ring hops away;
  their signals have not propagated to net2 yet. Training effectively
  updates theta1 and theta2. This is a ring-propagation constraint
  (switching time ~0.4 ns per stage), not a software bug.

Dataset: 30 samples — 10 per class (indices 0-9, 50-59, 100-109 of IRIS).
"""

import sys, os, json, csv

SIM_SRC = r"D:\Simulator\circuit_simulator-main\src"
if SIM_SRC not in sys.path:
    sys.path.insert(0, SIM_SRC)

from main import run_simulation_core
from netlist_generator import write_tran_netlist

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR     = r"D:\Kirchoffnet\kirchoff_claude"
NETLIST_DIR  = os.path.join(BASE_DIR, "temp_netlists")
DATASET_FILE = os.path.join(BASE_DIR, "iris_dataset.json")
LOG_FILE     = os.path.join(BASE_DIR, "iris_training_log.csv")

THETA_PARAMS = ["V5", "V4", "V3", "V2"]
TRAIN_THETAS = [1.5, 1.5, 1.5, 1.5]
OUTPUT_NODE  = "net2"
STOP_TIME    = "0.5n"

# Class -> target voltage mapping
CLASS_NAMES    = ["setosa", "versicolor", "virginica"]
CLASS_VOLTAGES = [0.5, 1.65, 2.8]

# Ring nodes in feature order
RING_NODES = ["net2", "net3", "net4", "net6"]

N_DATA  = 30      # 10 per class
EPOCHS  = 100
LR      = 0.05
BETA1, BETA2, EPS = 0.9, 0.999, 1e-8


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def load_iris_dataset():
    """Load IRIS, normalise features to [0.2, 3.1] V, subsample 10 per class."""
    from sklearn.datasets import load_iris
    iris     = load_iris()
    X, y     = iris.data, iris.target   # X: (150, 4), y: (150,)

    # Normalise using full-dataset statistics so scale is fixed
    x_min = X.min(axis=0)
    x_max = X.max(axis=0)
    X_norm = 0.2 + (X - x_min) / (x_max - x_min) * 2.9   # -> [0.2, 3.1] V

    # 10 samples per class: indices 0-9, 50-59, 100-109
    indices = list(range(0, 10)) + list(range(50, 60)) + list(range(100, 110))

    dataset = []
    for idx in indices:
        feats = X_norm[idx]
        label = int(y[idx])
        dataset.append({
            "ic": {
                "net2": round(float(feats[0]), 4),   # sepal length
                "net3": round(float(feats[1]), 4),   # sepal width
                "net4": round(float(feats[2]), 4),   # petal length
                "net6": round(float(feats[3]), 4),   # petal width
            },
            "target": CLASS_VOLTAGES[label],
            "class":  label,
            "label":  CLASS_NAMES[label],
        })

    with open(DATASET_FILE, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"IRIS dataset saved -> {DATASET_FILE}")
    class_counts = {c: sum(1 for d in dataset if d["class"] == c) for c in range(3)}
    for c, name in enumerate(CLASS_NAMES):
        print(f"  class {c} ({name}): {class_counts[c]} samples  "
              f"target={CLASS_VOLTAGES[c]} V")
    return dataset


def load_or_generate_dataset():
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE) as f:
            data = json.load(f)
        if "class" in data[0] and "ic" in data[0]:
            print(f"Loaded IRIS dataset ({len(data)} samples)")
            return data
        print("Stale dataset format — regenerating.")
        os.remove(DATASET_FILE)
    return load_iris_dataset()


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------
def get_tran(thetas, ic_dict, tag):
    """Run .TRAN with sensitivity=True. Returns (v_pred, {param: sens})."""
    path = os.path.join(NETLIST_DIR, f"tran_{tag}.txt")
    write_tran_netlist(thetas, ic_dict, path, stop_time=STOP_TIME)
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE],
                                    sensitivity=True)
    if result is None:
        raise RuntimeError(f"TRAN failed: thetas={thetas}, ic={ic_dict}")

    v_raw  = result.get_voltage(OUTPUT_NODE)
    v_pred = float(v_raw[-1]) if hasattr(v_raw, "__len__") else float(v_raw)

    avail = result.get_sensitivity_parameters(OUTPUT_NODE) if result.sensitivities else []
    sens  = {}
    for p in THETA_PARAMS:
        if p in avail:
            raw     = result.get_sensitivity(OUTPUT_NODE, p)
            sens[p] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
        else:
            sens[p] = 0.0
    return v_pred, sens


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------
def predict_class(v_pred):
    """Nearest-voltage classifier."""
    return min(range(3), key=lambda c: abs(v_pred - CLASS_VOLTAGES[c]))


def compute_accuracy(thetas, dataset, epoch):
    """Run forward pass on all samples, return accuracy (0-1)."""
    correct = 0
    for i, sample in enumerate(dataset):
        v_pred, _ = get_tran(thetas, sample["ic"], tag=f"acc_e{epoch:03d}_s{i:02d}")
        if predict_class(v_pred) == sample["class"]:
            correct += 1
    return correct / len(dataset)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train():
    os.makedirs(NETLIST_DIR, exist_ok=True)
    dataset = load_or_generate_dataset()
    N = len(dataset)

    thetas = list(TRAIN_THETAS)
    m, v   = [0.0] * 4, [0.0] * 4

    print(f"\nKirchhoffNet IRIS Classification  (TRAN sensitivity=True, stop={STOP_TIME})")
    print(f"  Output node   : {OUTPUT_NODE}")
    print(f"  Samples       : {N} (10 per class)  |  Epochs: {EPOCHS}  |  LR: {LR}")
    print(f"  Init thetas   : {thetas}")
    print(f"  Class voltages: setosa={CLASS_VOLTAGES[0]}V  "
          f"versicolor={CLASS_VOLTAGES[1]}V  virginica={CLASS_VOLTAGES[2]}V")
    print("-" * 72)

    log_rows = [["epoch", "mse", "accuracy"]
                + [f"theta{i+1}" for i in range(4)]
                + [f"sens_{p}" for p in THETA_PARAMS]]

    for epoch in range(1, EPOCHS + 1):
        total_sq_err = 0.0
        grad_acc     = [0.0] * 4
        last_sens    = {}

        for i, sample in enumerate(dataset):
            v_pred, sens = get_tran(thetas, sample["ic"],
                                    tag=f"e{epoch:03d}_s{i:02d}")
            error         = v_pred - sample["target"]
            total_sq_err += error ** 2
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += error * sens[p]
            last_sens = sens

        mse      = total_sq_err / N
        raw_grad = [(2.0 / N) * g for g in grad_acc]

        # Adam update
        for j in range(4):
            m[j] = BETA1 * m[j] + (1 - BETA1) * raw_grad[j]
            v[j] = BETA2 * v[j] + (1 - BETA2) * raw_grad[j] ** 2
            m_hat = m[j] / (1 - BETA1 ** epoch)
            v_hat = v[j] / (1 - BETA2 ** epoch)
            thetas[j] -= LR * m_hat / (v_hat ** 0.5 + EPS)
            thetas[j]  = max(0.1, min(1.69, thetas[j]))

        # Accuracy (uses extra simulator calls; skip on non-reporting epochs to save time)
        if epoch == 1 or epoch % 10 == 0:
            accuracy = compute_accuracy(thetas, dataset, epoch)
            print(
                f"Epoch {epoch:3d}  MSE={mse:.5f}  Acc={accuracy:.0%}  "
                f"T=[{thetas[0]:.3f},{thetas[1]:.3f},{thetas[2]:.3f},{thetas[3]:.3f}]  "
                f"sens=[{last_sens.get('V5',0):+.2e},{last_sens.get('V4',0):+.2e},"
                f"{last_sens.get('V3',0):+.2e},{last_sens.get('V2',0):+.2e}]"
            )
        else:
            accuracy = None

        log_rows.append(
            [epoch, mse, accuracy if accuracy is not None else ""]
            + list(thetas)
            + [last_sens.get(p, 0.0) for p in THETA_PARAMS]
        )

    with open(LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerows(log_rows)
    print(f"\nTraining complete. Log -> {LOG_FILE}")

    # Final accuracy with detailed breakdown
    print(f"\n--- Final evaluation ---")
    print(f"{'#':>3}  {'label':>12}  {'target':>7}  {'v_pred':>7}  {'pred_class':>12}  {'ok':>4}")
    correct = 0
    for i, sample in enumerate(dataset):
        v_pred, _ = get_tran(thetas, sample["ic"], tag=f"final_{i:02d}")
        pc  = predict_class(v_pred)
        ok  = pc == sample["class"]
        correct += int(ok)
        print(f"{i:3d}  {sample['label']:>12}  {sample['target']:7.2f}  "
              f"{v_pred:7.4f}  {CLASS_NAMES[pc]:>12}  {'Y' if ok else 'N':>4}")

    final_acc = correct / N
    print(f"\nFinal accuracy : {final_acc:.0%}  ({correct}/{N})")
    print(f"Final thetas   : {[round(t, 4) for t in thetas]}")
    return thetas, log_rows


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_results(log_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    header = log_rows[0]
    rows   = log_rows[1:]

    epochs   = [int(r[0])   for r in rows]
    mse      = [float(r[1]) for r in rows]
    accuracy = [float(r[2]) if r[2] != "" else None for r in rows]

    acc_epochs = [e for e, a in zip(epochs, accuracy) if a is not None]
    acc_vals   = [a for a in accuracy if a is not None]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # MSE (log scale)
    mse_pos = np.where(np.array(mse) > 0, mse, np.nan)
    axes[0].semilogy(epochs, mse_pos, color="#E91E63", lw=2)
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("MSE (log scale)")
    axes[0].set_title("Training Loss (MSE)")
    axes[0].grid(True, which="both", alpha=0.3)
    axes[0].set_xlim(1, max(epochs))

    # Accuracy
    axes[1].plot(acc_epochs, [a * 100 for a in acc_vals],
                 color="#2196F3", lw=2, marker="o", markersize=4)
    axes[1].axhline(33.3, color="gray", lw=1, linestyle="--", label="Random baseline (33%)")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Accuracy (%)")
    axes[1].set_title("Classification Accuracy")
    axes[1].set_ylim(0, 105); axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(1, max(epochs)); axes[1].legend()

    fig.suptitle(
        "KirchhoffNet IRIS Classification  "
        "(TRAN 0.5 ns, IC inputs, 30 samples, Adam)",
        fontweight="bold"
    )
    plt.tight_layout()
    out = os.path.join(BASE_DIR, "iris_results.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Plot saved -> {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    thetas, log_rows = train()
    plot_results(log_rows)
    print("\nDone.")
