"""
KirchhoffNet — IRIS Classification (Hybrid: TRAN 100ns prediction + .OP sensitivity)
======================================================================================
Prediction : .TRAN at 100ns per sample  →  ring has settled to near-equilibrium output
Sensitivity: .OP  with vn = mean(IC voltages)  →  all 4 thetas get non-zero gradients

Why hybrid?
  At t < 5ns (short TRAN) only theta2 develops meaningful TRAN sensitivity for net2
  because the gradient path through Blocks C and D is blocked when those IC voltages
  sit below the NMOS threshold (~0.54V). The .OP analysis finds the DC saddle-point
  equilibrium analytically, which is always in the linear region, giving non-zero
  dV/dTheta for all 4 blocks regardless of IC values.

  At 100ns the ring has largely settled, so .OP dV/dTheta is a good proxy for how
  each theta shifts the 100ns TRAN output — the gradient approximation is valid.

Feature normalisation [0.8, 2.5]V (vs [0.2, 3.1]V in iris-classification):
  Keeps all 4 IC voltages above the NMOS VTO = 0.536V so no differential pair
  is cut off and the .OP DC solution reflects the TRAN initial conditions more
  faithfully.

vn for .OP call: mean of the 4 normalised IC voltages for that sample.
  This centres the DC operating point on the sample's average feature level
  instead of using a fixed reference.

Loss / gradient:
  L        = (1/N) * sum_i (v_tran_i - target_i)^2
  dL/dth_j = (2/N) * sum_i (v_tran_i - target_i) * dV_op/dth_j

Per datapoint: 2 simulator calls (TRAN 100ns + .OP).
"""

import sys, os, json, csv

SIM_SRC = r"D:\Simulator\circuit_simulator-main\src"
if SIM_SRC not in sys.path:
    sys.path.insert(0, SIM_SRC)

from main import run_simulation_core
from netlist_generator import write_tran_netlist, write_op_netlist

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR     = r"D:\Kirchoffnet\kirchoff_claude"
NETLIST_DIR  = os.path.join(BASE_DIR, "temp_netlists")
DATASET_FILE = os.path.join(BASE_DIR, "iris_hybrid_dataset.json")
LOG_FILE     = os.path.join(BASE_DIR, "iris_hybrid_log.csv")

THETA_PARAMS = ["V5", "V4", "V3", "V2"]
TRAIN_THETAS = [1.5, 1.5, 1.5, 1.5]
OUTPUT_NODE  = "net2"
STOP_TIME    = "100n"

# Feature normalisation range — shifted up so all ICs stay above NMOS VTO=0.536V
V_NORM_LOW  = 0.8
V_NORM_HIGH = 2.5

CLASS_NAMES    = ["setosa", "versicolor", "virginica"]
CLASS_VOLTAGES = [0.5, 1.65, 2.8]

N_DATA  = 30
EPOCHS  = 20
LR      = 0.05
BETA1, BETA2, EPS = 0.9, 0.999, 1e-8


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def load_iris_dataset():
    from sklearn.datasets import load_iris
    iris = load_iris()
    X, y = iris.data, iris.target

    x_min = X.min(axis=0)
    x_max = X.max(axis=0)
    span  = V_NORM_HIGH - V_NORM_LOW
    X_norm = V_NORM_LOW + (X - x_min) / (x_max - x_min) * span

    indices = list(range(0, 10)) + list(range(50, 60)) + list(range(100, 110))

    dataset = []
    for idx in indices:
        feats = X_norm[idx]
        label = int(y[idx])
        ic = {
            "net2": round(float(feats[0]), 4),
            "net3": round(float(feats[1]), 4),
            "net4": round(float(feats[2]), 4),
            "net6": round(float(feats[3]), 4),
        }
        dataset.append({
            "ic":     ic,
            "vn":     round(float(sum(ic.values()) / 4), 4),
            "target": CLASS_VOLTAGES[label],
            "class":  label,
            "label":  CLASS_NAMES[label],
        })

    with open(DATASET_FILE, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Dataset saved  -> {DATASET_FILE}  ({V_NORM_LOW}–{V_NORM_HIGH} V normalisation)")
    for c, name in enumerate(CLASS_NAMES):
        samples = [d for d in dataset if d["class"] == c]
        vn_vals = [d["vn"] for d in samples]
        ic_min  = min(min(d["ic"].values()) for d in samples)
        ic_max  = max(max(d["ic"].values()) for d in samples)
        print(f"  class {c} ({name:>12}): {len(samples)} samples  "
              f"vn=[{min(vn_vals):.3f},{max(vn_vals):.3f}]  "
              f"IC=[{ic_min:.3f},{ic_max:.3f}]  target={CLASS_VOLTAGES[c]}V")
    return dataset


def load_or_generate_dataset():
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE) as f:
            data = json.load(f)
        if "vn" in data[0] and "ic" in data[0]:
            print(f"Loaded hybrid dataset ({len(data)} samples)")
            return data
        os.remove(DATASET_FILE)
    return load_iris_dataset()


# ---------------------------------------------------------------------------
# Simulator calls
# ---------------------------------------------------------------------------
def _extract_sens(result, node):
    avail = result.get_sensitivity_parameters(node) if result.sensitivities else []
    sens  = {}
    for p in THETA_PARAMS:
        if p in avail:
            raw     = result.get_sensitivity(node, p)
            sens[p] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
        else:
            sens[p] = 0.0
    return sens


def get_tran_pred(thetas, ic_dict, tag):
    """TRAN at 100ns — prediction only, no sensitivity."""
    path = os.path.join(NETLIST_DIR, f"tran_{tag}.txt")
    write_tran_netlist(thetas, ic_dict, path, stop_time=STOP_TIME)
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE], sensitivity=False)
    v_raw = result.get_voltage(OUTPUT_NODE)
    return float(v_raw[-1]) if hasattr(v_raw, "__len__") else float(v_raw)


def get_op_sens(thetas, vn, tag):
    """OP — sensitivity only, returns {param: dV/dParam} for all 4 thetas."""
    path = os.path.join(NETLIST_DIR, f"op_{tag}.txt")
    write_op_netlist(thetas, path, vn=vn)
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE], sensitivity=True)
    return _extract_sens(result, OUTPUT_NODE)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def predict_class(v_pred):
    return min(range(3), key=lambda c: abs(v_pred - CLASS_VOLTAGES[c]))


def compute_accuracy(thetas, dataset, epoch):
    correct = 0
    for i, s in enumerate(dataset):
        v = get_tran_pred(thetas, s["ic"], tag=f"acc_e{epoch:03d}_s{i:02d}")
        if predict_class(v) == s["class"]:
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

    print(f"\nKirchhoffNet IRIS Hybrid  (TRAN {STOP_TIME} pred + .OP sensitivity)")
    print(f"  Output node      : {OUTPUT_NODE}")
    print(f"  Normalisation    : [{V_NORM_LOW}, {V_NORM_HIGH}] V  (ICs above NMOS VTO=0.54V)")
    print(f"  Samples          : {N} (10/class) | Epochs: {EPOCHS} | LR: {LR}")
    print(f"  Init thetas      : {thetas}")
    print(f"  Class voltages   : {dict(zip(CLASS_NAMES, CLASS_VOLTAGES))}")
    print("-" * 72)

    log_rows = [["epoch", "mse", "accuracy"]
                + [f"theta{i+1}" for i in range(4)]
                + [f"sens_{p}" for p in THETA_PARAMS]]

    for epoch in range(1, EPOCHS + 1):
        total_sq_err = 0.0
        grad_acc     = [0.0] * 4
        last_sens    = {}

        for i, s in enumerate(dataset):
            # Forward: TRAN 100ns for prediction
            v_pred = get_tran_pred(thetas, s["ic"], tag=f"e{epoch:03d}_s{i:02d}")
            # Gradient: .OP with sample's mean IC as vn
            sens   = get_op_sens(thetas, s["vn"], tag=f"e{epoch:03d}_s{i:02d}")

            error         = v_pred - s["target"]
            total_sq_err += error ** 2
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += error * sens[p]
            last_sens = sens

        mse      = total_sq_err / N
        raw_grad = [(2.0 / N) * g for g in grad_acc]

        for j in range(4):
            m[j] = BETA1 * m[j] + (1 - BETA1) * raw_grad[j]
            v[j] = BETA2 * v[j] + (1 - BETA2) * raw_grad[j] ** 2
            m_hat = m[j] / (1 - BETA1 ** epoch)
            v_hat = v[j] / (1 - BETA2 ** epoch)
            thetas[j] -= LR * m_hat / (v_hat ** 0.5 + EPS)
            thetas[j]  = max(0.1, min(1.69, thetas[j]))

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

    print(f"\n--- Final evaluation ---")
    print(f"{'#':>3}  {'label':>12}  {'target':>7}  {'v_pred':>7}  {'pred_class':>12}  {'ok':>4}")
    correct = 0
    for i, s in enumerate(dataset):
        v_pred = get_tran_pred(thetas, s["ic"], tag=f"final_{i:02d}")
        pc  = predict_class(v_pred)
        ok  = pc == s["class"]
        correct += int(ok)
        print(f"{i:3d}  {s['label']:>12}  {s['target']:7.2f}  "
              f"{v_pred:7.4f}  {CLASS_NAMES[pc]:>12}  {'Y' if ok else 'N':>4}")

    print(f"\nFinal accuracy : {correct/N:.0%}  ({correct}/{N})")
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

    rows     = log_rows[1:]
    epochs   = [int(r[0])   for r in rows]
    mse      = [float(r[1]) for r in rows]
    accuracy = [float(r[2]) if r[2] != "" else None for r in rows]

    acc_epochs = [e for e, a in zip(epochs, accuracy) if a is not None]
    acc_vals   = [a for a in accuracy if a is not None]

    # Theta trajectories (columns 3-6)
    theta_traces = [[float(r[3 + j]) for r in rows] for j in range(4)]
    theta_labels = ["theta1 (V5/BlockA)", "theta2 (V4/BlockB)",
                    "theta3 (V3/BlockC)", "theta4 (V2/BlockD)"]
    theta_colors = ["#E91E63", "#2196F3", "#4CAF50", "#FF9800"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # MSE
    mse_pos = np.where(np.array(mse) > 0, mse, np.nan)
    axes[0].semilogy(epochs, mse_pos, color="#E91E63", lw=2)
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("MSE (log scale)")
    axes[0].set_title("Training Loss (MSE)")
    axes[0].grid(True, which="both", alpha=0.3); axes[0].set_xlim(1, max(epochs))

    # Accuracy
    axes[1].plot(acc_epochs, [a * 100 for a in acc_vals],
                 color="#2196F3", lw=2, marker="o", markersize=4)
    axes[1].axhline(33.3, color="gray", lw=1, linestyle="--", label="Random (33%)")
    axes[1].axhline(66.7, color="orange", lw=1, linestyle="--", label="2-class ceiling (67%)")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Accuracy (%)")
    axes[1].set_title("Classification Accuracy")
    axes[1].set_ylim(0, 105); axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(1, max(epochs)); axes[1].legend(fontsize=8)

    # Theta trajectories
    for j in range(4):
        axes[2].plot(epochs, theta_traces[j], color=theta_colors[j],
                     lw=1.5, label=theta_labels[j])
    axes[2].axhline(0.1,  color="black", lw=0.8, linestyle=":", alpha=0.5, label="clamp bounds")
    axes[2].axhline(1.69, color="black", lw=0.8, linestyle=":", alpha=0.5)
    axes[2].set_xlabel("Epoch"); axes[2].set_ylabel("Theta (V)")
    axes[2].set_title("Theta Trajectories")
    axes[2].set_ylim(-0.05, 1.8); axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(1, max(epochs)); axes[2].legend(fontsize=7)

    fig.suptitle(
        f"KirchhoffNet IRIS Hybrid  (TRAN {STOP_TIME} pred + .OP sensitivity, "
        f"IC=[{V_NORM_LOW},{V_NORM_HIGH}]V, Adam)",
        fontweight="bold"
    )
    plt.tight_layout()
    out = os.path.join(BASE_DIR, "iris_hybrid_results.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Plot saved -> {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    thetas, log_rows = train()
    plot_results(log_rows)
    print("\nDone.")
