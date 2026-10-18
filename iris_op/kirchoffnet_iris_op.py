"""
KirchhoffNet -- IRIS 3-Class Classification via TRAN (3ns, petal-only IC)
==========================================================================
Analysis   : .TRAN at 3ns -- ring partially committed, analog output
Input      : petal length (most discriminative IRIS feature) -> net4 IC
             Other nodes (net2, net3, net6) fixed at 1.5V (neutral reference)
Sensitivity: TRAN adjoint at 3ns -- theta2 (V4/Block B) dominates

Why petal-only IC injection?
  All 4 features as IC creates cross-feature interference:
    petal_length (net4) pushes net2 UP for versicolor/virginica
    petal_width  (net6) pushes net2 DOWN for virginica (high petal_width)
  These competing effects make versicolor and virginica indistinguishable
  (their distributions overlap completely).

  With ONLY petal_length -> net4 IC and others fixed at 1.5V:
    setosa   IC ~ 0.9V < vn=1.0V  -> Block A: M1>M0 -> net6 UP -> net2 DOWN -> LOW
    versicolor IC ~ 1.5V > vn      -> Block A: M0>M1 -> net6 DOWN -> net2 UP -> HIGH
    virginica  IC ~ 2.2V >> vn     -> same direction as versicolor but stronger -> HIGHER
  Result: clean 3-level separation (teacher accuracy = 87%).

Why teacher-generated TRAN targets?
  Targets are the teacher circuit's (thetas=[0.5,0.5,0.5,0.5]) TRAN output at
  each sample's petal IC. These are self-consistent -- the circuit CAN produce
  them at theta values near the teacher. Training from [1.5,1.5,1.5,1.5] moves
  thetas toward the teacher's configuration.

  Fixed class voltages (0.5/1.65/2.8V): outside the circuit's 3ns TRAN range
  for some theta configurations -> gradient points wrong direction -> stuck.

Classification boundaries:
  Computed from the teacher's per-class mean TRAN outputs at 3ns:
    setosa/versicolor  ~ 1.38V
    versicolor/virginica ~ 2.33V
  Recomputed from trained circuit outputs at final evaluation for best accuracy.

Theoretical ceiling:
  Versicolor (max petal 4.9cm, IC=1.87V) overlaps with virginica (min 4.5cm,
  IC=1.81V) -> 4 boundary samples cannot be correctly classified by petal alone.
  Ceiling: 26/30 = 87%.

Loss / gradient (TRAN at t=3ns):
  L        = (1/N) * sum_i (v_pred_i - target_i)^2
  dL/dth_j = (2/N) * sum_i (v_pred_i - target_i) * dV_tran/dth_j

Per datapoint: 1 simulator call (.TRAN 10p 3n with sensitivity=True).
Speed: ~0.3s per call (301 time steps), ~300s per epoch.
Epochs: 200.
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
DATASET_FILE = os.path.join(BASE_DIR, "iris_op_dataset.json")
LOG_FILE     = os.path.join(BASE_DIR, "iris_op_log.csv")

THETA_PARAMS   = ["V5", "V4", "V3", "V2"]
TEACHER_THETAS = [0.5, 0.5, 0.5, 0.5]   # generates targets
TRAIN_THETAS   = [1.5, 1.5, 1.5, 1.5]   # training init
OUTPUT_NODE    = "net2"
STOP_TIME      = "3n"                     # 301 time steps, ring partially committed

# petal_length IC normalization -- only net4 varies
PL_IC_LOW   = 0.8    # for petal_length_min (1.0 cm)
PL_IC_HIGH  = 2.5    # for petal_length_max (6.9 cm)
NEUTRAL_IC  = 1.5    # net2, net3, net6 fixed (above NMOS threshold, neutral)

CLASS_NAMES = ["setosa", "versicolor", "virginica"]

N_DATA  = 30
EPOCHS  = 200
LR      = 0.05
BETA1, BETA2, EPS = 0.9, 0.999, 1e-8


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------
def _run_tran(thetas, ic_dict, tag):
    """Single TRAN call at STOP_TIME -- returns (v_pred, {param: sensitivity})."""
    path = os.path.join(NETLIST_DIR, "tran_%s.txt" % tag)
    write_tran_netlist(thetas, ic_dict, path, stop_time=STOP_TIME)
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE], sensitivity=True)
    if result is None:
        raise RuntimeError("TRAN failed: thetas=%s, tag=%s" % (thetas, tag))
    v_raw  = result.get_voltage(OUTPUT_NODE)
    v_pred = float(v_raw[-1]) if hasattr(v_raw, "__len__") else float(v_raw)
    avail  = result.get_sensitivity_parameters(OUTPUT_NODE) if result.sensitivities else []
    sens   = {}
    for p in THETA_PARAMS:
        if p in avail:
            raw     = result.get_sensitivity(OUTPUT_NODE, p)
            sens[p] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
        else:
            sens[p] = 0.0
    return v_pred, sens


# ---------------------------------------------------------------------------
# Dataset -- teacher TRAN targets (same strategy as master branch regression)
# ---------------------------------------------------------------------------
def _petal_to_ic(pl, pl_min, pl_max):
    return PL_IC_LOW + (pl - pl_min) / (pl_max - pl_min) * (PL_IC_HIGH - PL_IC_LOW)


def _make_ic(petal_ic):
    """IC dict: only net4 varies, others are neutral reference."""
    return {
        "net2": NEUTRAL_IC,
        "net3": NEUTRAL_IC,
        "net4": round(float(petal_ic), 4),
        "net6": NEUTRAL_IC,
    }


def load_iris_dataset():
    from sklearn.datasets import load_iris
    iris = load_iris()
    X, y = iris.data, iris.target

    pl     = X[:, 2]
    pl_min = float(pl.min())
    pl_max = float(pl.max())

    os.makedirs(NETLIST_DIR, exist_ok=True)
    indices = list(range(0, 10)) + list(range(50, 60)) + list(range(100, 110))
    print("Generating TRAN teacher targets (%s) at %s, petal-only IC ..." % (TEACHER_THETAS, STOP_TIME))
    dataset = []
    for k, idx in enumerate(indices):
        label   = int(y[idx])
        petal   = float(X[idx, 2])
        petal_ic = round(float(_petal_to_ic(petal, pl_min, pl_max)), 4)
        ic      = _make_ic(petal_ic)
        target, _ = _run_tran(TEACHER_THETAS, ic, "teacher_%02d" % k)
        dataset.append({
            "ic":              ic,
            "target":          round(target, 4),
            "class":           label,
            "label":           CLASS_NAMES[label],
            "petal_length_cm": round(petal, 1),
            "petal_ic":        petal_ic,
        })

    # Classification boundaries: midpoints of teacher per-class mean outputs
    class_mean = []
    for c in range(3):
        ts = [d["target"] for d in dataset if d["class"] == c]
        class_mean.append(sum(ts) / len(ts))
    boundaries = [(class_mean[c] + class_mean[c+1]) / 2 for c in range(2)]

    meta = {
        "teacher_thetas": TEACHER_THETAS,
        "boundaries": boundaries,
        "class_mean_targets": class_mean,
        "pl_min": pl_min, "pl_max": pl_max,
        "stop_time": STOP_TIME,
    }

    with open(DATASET_FILE, "w") as f:
        json.dump({"dataset": dataset, "meta": meta}, f, indent=2)

    print("Dataset saved -> %s" % DATASET_FILE)
    print("  Teacher: %s  stop=%s  petal IC [%.1f, %.1f] V  neutral_IC=%.1f V" % (
        TEACHER_THETAS, STOP_TIME, PL_IC_LOW, PL_IC_HIGH, NEUTRAL_IC))
    for c, name in enumerate(CLASS_NAMES):
        s  = [d for d in dataset if d["class"] == c]
        ts = [d["target"] for d in s]
        ps = [d["petal_ic"] for d in s]
        print("  class %d (%12s): petal_IC=[%.3f,%.3f]V  target=[%.3f,%.3f]V  mean=%.3f" % (
            c, name, min(ps), max(ps), min(ts), max(ts), class_mean[c]))
    print("  Boundaries: setosa/versicolor=%.3fV  versicolor/virginica=%.3fV" % tuple(boundaries))

    # Quick accuracy check with teacher boundaries
    correct = sum(1 for d in dataset if _predict_class(d["target"], boundaries) == d["class"])
    print("  Teacher accuracy (ceiling): %d/30 = %.0f%%" % (correct, correct/30*100))
    return dataset, boundaries


def load_or_generate_dataset():
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE) as f:
            saved = json.load(f)
        if (isinstance(saved, dict) and "meta" in saved
                and saved["meta"].get("teacher_thetas") == TEACHER_THETAS
                and saved["meta"].get("stop_time") == STOP_TIME):
            data       = saved["dataset"]
            boundaries = saved["meta"]["boundaries"]
            print("Loaded dataset (%d samples)  teacher=%s  boundaries=[%.3f, %.3f] V" % (
                len(data), TEACHER_THETAS, boundaries[0], boundaries[1]))
            return data, boundaries
        os.remove(DATASET_FILE)
    return load_iris_dataset()


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def _predict_class(v_pred, boundaries):
    if v_pred < boundaries[0]:
        return 0   # setosa
    elif v_pred < boundaries[1]:
        return 1   # versicolor
    else:
        return 2   # virginica


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train():
    os.makedirs(NETLIST_DIR, exist_ok=True)
    dataset, boundaries = load_or_generate_dataset()
    N = len(dataset)

    thetas = list(TRAIN_THETAS)
    m, v   = [0.0] * 4, [0.0] * 4

    print("\nKirchhoffNet IRIS TRAN Classification (petal-only IC, teacher targets)")
    print("  Input        : petal_length -> net4 IC in [%.1f, %.1f] V (others=%.1f V)" % (
        PL_IC_LOW, PL_IC_HIGH, NEUTRAL_IC))
    print("  TRAN stop    : %s  (301 steps)" % STOP_TIME)
    print("  Teacher      : %s -> targets in [%.3f, %.3f] V" % (
        TEACHER_THETAS,
        min(d["target"] for d in dataset), max(d["target"] for d in dataset)))
    print("  Boundaries   : [%.3f, %.3f] V" % tuple(boundaries))
    print("  Samples      : %d (10/class)  |  Epochs: %d  |  LR: %.3f" % (N, EPOCHS, LR))
    print("  Init thetas  : %s" % thetas)
    print("-" * 72)

    log_rows = [["epoch", "mse", "accuracy"]
                + ["theta%d" % (i+1) for i in range(4)]
                + ["sens_%s" % p for p in THETA_PARAMS]]

    for epoch in range(1, EPOCHS + 1):
        total_sq_err = 0.0
        grad_acc     = [0.0] * 4
        correct      = 0
        last_sens    = {}

        for i, s in enumerate(dataset):
            v_pred, sens = _run_tran(thetas, s["ic"], "e%03d_s%02d" % (epoch, i))
            error         = v_pred - s["target"]
            total_sq_err += error ** 2
            correct      += int(_predict_class(v_pred, boundaries) == s["class"])
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += error * sens[p]
            last_sens = sens

        mse      = total_sq_err / N
        accuracy = correct / N
        raw_grad = [(2.0 / N) * g for g in grad_acc]

        for j in range(4):
            m[j] = BETA1 * m[j] + (1 - BETA1) * raw_grad[j]
            v[j] = BETA2 * v[j] + (1 - BETA2) * raw_grad[j] ** 2
            m_hat = m[j] / (1 - BETA1 ** epoch)
            v_hat = v[j] / (1 - BETA2 ** epoch)
            thetas[j] -= LR * m_hat / (v_hat ** 0.5 + EPS)
            thetas[j]  = max(0.1, min(1.69, thetas[j]))

        if epoch == 1 or epoch % 10 == 0:
            print("Epoch %3d  MSE=%.5f  Acc=%.0f%%  T=[%.3f,%.3f,%.3f,%.3f]  "
                  "sens=[%+.2e,%+.2e,%+.2e,%+.2e]" % (
                  epoch, mse, accuracy*100,
                  thetas[0], thetas[1], thetas[2], thetas[3],
                  last_sens.get("V5", 0), last_sens.get("V4", 0),
                  last_sens.get("V3", 0), last_sens.get("V2", 0)))

        log_rows.append(
            [epoch, mse, accuracy]
            + list(thetas)
            + [last_sens.get(p, 0.0) for p in THETA_PARAMS]
        )

    with open(LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerows(log_rows)
    print("\nTraining complete. Log -> %s" % LOG_FILE)

    # Final evaluation: recompute boundaries from trained circuit's class outputs
    print("\n--- Final per-sample evaluation (recomputed boundaries) ---")
    final_preds = []
    for i, s in enumerate(dataset):
        v_pred, _ = _run_tran(thetas, s["ic"], "final_%02d" % i)
        final_preds.append(v_pred)

    # Optimal boundaries from trained outputs
    final_means = []
    for c in range(3):
        vals = [final_preds[i] for i, s in enumerate(dataset) if s["class"] == c]
        final_means.append(sum(vals) / len(vals))
    final_boundaries = [(final_means[c] + final_means[c+1]) / 2 for c in range(2)]
    print("  Trained class means: %s" % [round(m, 3) for m in final_means])
    print("  Optimal boundaries : %s" % [round(b, 3) for b in final_boundaries])

    print("\n  %3s  %12s  %5s  %6s  %7s  %7s  %12s  %4s" % (
        "#", "label", "petal", "IC", "target", "v_pred", "pred", "ok"))
    correct = 0
    for i, s in enumerate(dataset):
        v_pred = final_preds[i]
        pc = _predict_class(v_pred, final_boundaries)
        ok = pc == s["class"]
        correct += int(ok)
        print("  %3d  %12s  %5.1f  %6.3f  %7.3f  %7.4f  %12s  %4s" % (
            i, s["label"], s["petal_length_cm"], s["petal_ic"],
            s["target"], v_pred, CLASS_NAMES[pc], "Y" if ok else "N"))

    print("\n  Final accuracy (optimal boundaries): %d/30 = %.0f%%" % (correct, correct/30*100))
    print("  Final thetas  : %s" % [round(t, 4) for t in thetas])
    return thetas, log_rows, boundaries, final_boundaries


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_results(log_rows, boundaries, final_boundaries):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    rows     = log_rows[1:]
    epochs   = [int(r[0])   for r in rows]
    mse      = [float(r[1]) for r in rows]
    accuracy = [float(r[2]) * 100 for r in rows]

    theta_traces = [[float(r[3 + j]) for r in rows] for j in range(4)]
    theta_labels = ["theta1 (V5/Block A)", "theta2 (V4/Block B)",
                    "theta3 (V3/Block C)", "theta4 (V2/Block D)"]
    theta_colors = ["#E91E63", "#2196F3", "#4CAF50", "#FF9800"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # MSE
    mse_pos = np.where(np.array(mse) > 0, mse, np.nan)
    axes[0].semilogy(epochs, mse_pos, color="#E91E63", lw=2)
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("MSE (log scale)")
    axes[0].set_title("Training Loss (MSE)")
    axes[0].grid(True, which="both", alpha=0.3); axes[0].set_xlim(1, max(epochs))

    # Accuracy
    axes[1].plot(epochs, accuracy, color="#2196F3", lw=2)
    axes[1].axhline(33.3, color="gray",   lw=1, linestyle="--", label="Random (33%)")
    axes[1].axhline(80.0, color="green",  lw=1, linestyle="--", label="80% target")
    axes[1].axhline(87.0, color="purple", lw=1, linestyle="--", label="Petal ceiling (87%)")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Accuracy (%)")
    axes[1].set_title("Classification Accuracy")
    axes[1].set_ylim(0, 105); axes[1].grid(True, alpha=0.3)
    axes[1].set_xlim(1, max(epochs)); axes[1].legend(fontsize=8)

    # Theta trajectories
    for j in range(4):
        axes[2].plot(epochs, theta_traces[j], color=theta_colors[j],
                     lw=1.5, label=theta_labels[j])
    axes[2].axhline(0.1,  color="black", lw=0.8, linestyle=":", alpha=0.5)
    axes[2].axhline(1.69, color="black", lw=0.8, linestyle=":", alpha=0.5, label="clamp [0.1, 1.69]")
    axes[2].axhline(0.5,  color="gray",  lw=0.8, linestyle="-.", alpha=0.5, label="teacher (0.5V)")
    axes[2].set_xlabel("Epoch"); axes[2].set_ylabel("Theta (V)")
    axes[2].set_title("Theta Trajectories")
    axes[2].set_ylim(-0.05, 1.8); axes[2].grid(True, alpha=0.3)
    axes[2].set_xlim(1, max(epochs)); axes[2].legend(fontsize=7)

    fig.suptitle(
        "KirchhoffNet IRIS TRAN@3ns Classification  "
        "(petal_length->net4 IC, teacher targets, Adam, 30 samples)",
        fontweight="bold"
    )
    plt.tight_layout()
    out = os.path.join(BASE_DIR, "iris_op_results.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print("Plot saved -> %s" % out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    thetas, log_rows, boundaries, final_boundaries = train()
    plot_results(log_rows, boundaries, final_boundaries)
    print("\nDone.")
