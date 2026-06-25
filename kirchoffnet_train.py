"""
KirchhoffNet Regression Training — OP-only approach
=====================================================
One .OP simulation per datapoint gives BOTH the prediction AND the gradient
at the same operating point, so the gradient actually minimises the loss.

Why not .TRAN:
  The ring switches to binary (0.14 V or 3.3 V) in < 1 ns regardless of IC.
  Small theta updates never flip a rail, so TRAN-based MSE stays flat.

Input encoding:
  'vn' (the tail-current reference, normally 1.0 V) is varied across the
  10 datapoints.  Different vn values shift the ring's DC saddle-point to
  a different equilibrium voltage, giving 10 distinct, analog targets.

Constraint:
  All thetas must stay < 1.7 V so every PMOS load stays in its linear
  region and all 4 sensitivities remain non-zero.

Loss / gradient:
  L        = (1/N) * sum_i (v_pred_i - target_i)^2
  dL/dth_j = (2/N) * sum_i (v_pred_i - target_i) * dV_op/dth_j
"""

import sys, os, json, csv

SIM_SRC = r"D:\Simulator\circuit_simulator-main\src"
if SIM_SRC not in sys.path:
    sys.path.insert(0, SIM_SRC)

from main import run_simulation_core
from netlist_generator import write_op_netlist

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR     = r"D:\Kirchoffnet\kirchoff_claude"
NETLIST_DIR  = os.path.join(BASE_DIR, "temp_netlists")
LOG_FILE     = os.path.join(BASE_DIR, "training_log.csv")
DATASET_FILE = os.path.join(BASE_DIR, "dataset.json")

THETA_PARAMS   = ["V5", "V4", "V3", "V2"]
TEACHER_THETAS = [0.5, 0.5, 0.5, 0.5]
TRAIN_THETAS   = [1.5, 1.5, 1.5, 1.5]

OUTPUT_NODE = "net2"
N_DATA  = 10
LR      = 0.05    # base LR; Adam normalises per-param so this is the step size
EPOCHS  = 500

# Adam optimiser hyper-parameters
BETA1, BETA2, EPS = 0.9, 0.999, 1e-8

# 10 distinct vn values shift the DC equilibrium to 10 distinct outputs
VN_VALUES = [round(0.5 + i * 0.1, 1) for i in range(N_DATA)]  # 0.5 … 1.4 V


# ---------------------------------------------------------------------------
# Simulator helper: single .OP call → prediction + sensitivity
# ---------------------------------------------------------------------------
def get_op(thetas, vn, tag):
    """Run .OP with sensitivity.  Returns (v_pred, {param: dV/dParam})."""
    path = os.path.join(NETLIST_DIR, f"op_{tag}.txt")
    write_op_netlist(thetas, path, vn=vn)
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE], sensitivity=True)
    if result is None:
        raise RuntimeError(f"OP failed: thetas={thetas}, vn={vn}")

    v_raw  = result.get_voltage(OUTPUT_NODE)
    v_pred = float(v_raw[-1]) if hasattr(v_raw, "__len__") else float(v_raw)

    avail = result.get_sensitivity_parameters(OUTPUT_NODE) if result.sensitivities else []
    sens  = {}
    for p in THETA_PARAMS:
        if p in avail:
            raw    = result.get_sensitivity(OUTPUT_NODE, p)
            sens[p] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
        else:
            sens[p] = 0.0
    return v_pred, sens


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def generate_dataset():
    """Generate targets using teacher thetas, one per vn value."""
    print(f"Generating dataset  teacher_thetas={TEACHER_THETAS}")
    print(f"  vn values: {VN_VALUES}")
    os.makedirs(NETLIST_DIR, exist_ok=True)
    dataset = []
    for i, vn in enumerate(VN_VALUES):
        v_target, _ = get_op(TEACHER_THETAS, vn, tag=f"teacher_{i:02d}")
        dataset.append({"vn": vn, "target": v_target})
        print(f"  sample {i:2d}: vn={vn:.1f}V  target={v_target:.4f}V")
    with open(DATASET_FILE, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Dataset saved -> {DATASET_FILE}\n")
    return dataset


def load_or_generate_dataset():
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE) as f:
            data = json.load(f)
        # Regenerate if it was created with the old IC-based format
        if "vn" not in data[0]:
            print("Old IC-based dataset found — regenerating with vn inputs.")
            os.remove(DATASET_FILE)
            return generate_dataset()
        print(f"Loaded dataset ({len(data)} samples)  vn={[d['vn'] for d in data]}")
        return data
    return generate_dataset()


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train():
    os.makedirs(NETLIST_DIR, exist_ok=True)
    dataset = load_or_generate_dataset()
    N = len(dataset)

    thetas = list(TRAIN_THETAS)
    print(f"\nKirchhoffNet training  (OP-only: prediction + gradient from same call)")
    print(f"  Output node  : {OUTPUT_NODE}")
    print(f"  N datapoints : {N}  |  Epochs: {EPOCHS}  |  LR: {LR}")
    print(f"  Init thetas  : {thetas}")
    print(f"  Teacher thetas: {TEACHER_THETAS}")
    print(f"  Targets      : {[d['target'] for d in dataset]}")
    print("-" * 70)

    log_rows = [["epoch", "mse"] + [f"theta{i+1}" for i in range(4)]
                + [f"sens_{p}" for p in THETA_PARAMS]]

    # Adam state
    m = [0.0] * 4   # first moment
    v = [0.0] * 4   # second moment

    for epoch in range(1, EPOCHS + 1):
        total_sq_err = 0.0
        grad_acc     = [0.0] * 4
        last_sens    = {}

        for i, sample in enumerate(dataset):
            v_pred, sens = get_op(thetas, sample["vn"],
                                  tag=f"e{epoch:04d}_s{i:02d}")
            error         = v_pred - sample["target"]
            total_sq_err += error ** 2
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += error * sens[p]
            last_sens = sens

        mse = total_sq_err / N

        # Full gradient: dL/dθ_j = (2/N) * Σ_i error_i * sens_j
        raw_grad = [(2.0 / N) * g for g in grad_acc]

        # Adam update — normalises each param by its own gradient history
        for j in range(4):
            m[j] = BETA1 * m[j] + (1 - BETA1) * raw_grad[j]
            v[j] = BETA2 * v[j] + (1 - BETA2) * raw_grad[j] ** 2
            m_hat = m[j] / (1 - BETA1 ** epoch)
            v_hat = v[j] / (1 - BETA2 ** epoch)
            thetas[j] -= LR * m_hat / (v_hat ** 0.5 + EPS)
            thetas[j]  = max(0.1, min(1.69, thetas[j]))   # keep in valid range

        log_rows.append([epoch, mse] + list(thetas)
                        + [last_sens.get(p, 0.0) for p in THETA_PARAMS])

        if epoch == 1 or epoch % 10 == 0:
            print(
                f"Epoch {epoch:4d}  MSE={mse:.6f}  "
                f"T=[{thetas[0]:.4f},{thetas[1]:.4f},"
                f"{thetas[2]:.4f},{thetas[3]:.4f}]  "
                f"sens=[{last_sens.get('V5',0):+.3e},"
                f"{last_sens.get('V4',0):+.3e},"
                f"{last_sens.get('V3',0):+.3e},"
                f"{last_sens.get('V2',0):+.3e}]"
            )

    with open(LOG_FILE, "w", newline="") as f:
        csv.writer(f).writerows(log_rows)
    print(f"\nTraining complete. Log -> {LOG_FILE}")

    print(f"\n--- Final evaluation (output_node={OUTPUT_NODE}) ---")
    print(f"{'#':>3}  {'vn':>5}  {'target':>8}  {'v_pred':>8}  {'error':>8}")
    final_sq = 0.0
    for i, sample in enumerate(dataset):
        v_pred, _ = get_op(thetas, sample["vn"], tag=f"final_{i:02d}")
        err = v_pred - sample["target"]
        final_sq += err ** 2
        print(f"{i:3d}  {sample['vn']:5.1f}  {sample['target']:8.4f}"
              f"  {v_pred:8.4f}  {err:+8.4f}")
    print(f"\nFinal MSE : {final_sq/N:.6f}")
    print(f"Final thetas: {[round(t,4) for t in thetas]}")
    return thetas


if __name__ == "__main__":
    train()
