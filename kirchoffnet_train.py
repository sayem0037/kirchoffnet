"""
KirchhoffNet Regression Training — TRAN + sensitivity (single call)
=====================================================================
One .TRAN simulation per datapoint (sensitivity=True) gives BOTH the
transient voltage prediction AND the sensitivity dV/dTheta at the
same operating point, so the gradient directly minimises the TRAN loss.

Why short stop time (0.5 ns instead of 100 ns):
  The ring latches to a binary rail (0.14 V or 3.3 V) in < 0.4 ns due
  to the 4.77 mA tail current overwhelming the ~260 µA PMOS load (ratio
  ~18:1).  At t = 100 ns the output is binary and dV/dTheta ≈ 0 (no
  incremental sensitivity at a saturated rail).  Sampling at t = 0.5 ns
  captures the circuit while it is still in the analog transition region:
  V(node) is between the IC and the final rail, and sensitivity is non-zero.

Input encoding:
  4 random IC voltages (one per ring node) injected via .IC statement.
  Each datapoint has a distinct IC pattern → distinct transient trajectory
  → distinct V(output_node) at t = 0.5 ns.

Loss / gradient (same as master):
  L        = (1/N) * sum_i (v_pred_i - target_i)^2
  dL/dth_j = (2/N) * sum_i (v_pred_i - target_i) * dV_tran/dth_j
"""

import sys, os, json, csv, random

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
LOG_FILE     = os.path.join(BASE_DIR, "training_log.csv")
DATASET_FILE = os.path.join(BASE_DIR, "dataset.json")

VDD          = 3.3
RING_NODES   = ["net2", "net3", "net4", "net6"]
THETA_PARAMS = ["V5", "V4", "V3", "V2"]

TEACHER_THETAS = [0.5, 0.5, 0.5, 0.5]
TRAIN_THETAS   = [1.5, 1.5, 1.5, 1.5]

OUTPUT_NODE = "net2"
STOP_TIME   = "0.5n"       # sample before ring latches to binary
N_DATA  = 10
LR      = 0.05
EPOCHS  = 500
SEED    = 42

BETA1, BETA2, EPS = 0.9, 0.999, 1e-8


# ---------------------------------------------------------------------------
# Simulator helper: single .TRAN call → prediction + sensitivity
# ---------------------------------------------------------------------------
def get_tran(thetas, ic_dict, tag):
    """Run .TRAN with sensitivity=True.
    Returns (v_pred at final timestep, {param: dV/dParam at final timestep}).
    """
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
# Dataset
# ---------------------------------------------------------------------------
def generate_dataset():
    """Generate targets using teacher thetas with random IC inputs."""
    random.seed(SEED)
    print(f"Generating dataset  teacher_thetas={TEACHER_THETAS}  stop_time={STOP_TIME}")
    os.makedirs(NETLIST_DIR, exist_ok=True)
    dataset = []
    for i in range(N_DATA):
        ic = {n: round(random.uniform(0.2, VDD - 0.2), 4) for n in RING_NODES}
        v_target, _ = get_tran(TEACHER_THETAS, ic, tag=f"teacher_{i:02d}")
        dataset.append({"ic": ic, "target": v_target})
        print(f"  sample {i:2d}: ic={list(ic.values())}  target={v_target:.4f}V")
    with open(DATASET_FILE, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Dataset saved -> {DATASET_FILE}\n")
    return dataset


def load_or_generate_dataset():
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE) as f:
            data = json.load(f)
        # Regenerate if it was created with the vn-based format (no "ic" key)
        if "ic" not in data[0]:
            print("vn-based dataset found — regenerating with IC inputs.")
            os.remove(DATASET_FILE)
            return generate_dataset()
        print(f"Loaded dataset ({len(data)} samples)")
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
    print(f"\nKirchhoffNet training  (TRAN sensitivity=True, stop={STOP_TIME})")
    print(f"  Output node   : {OUTPUT_NODE}")
    print(f"  N datapoints  : {N}  |  Epochs: {EPOCHS}  |  LR: {LR}")
    print(f"  Init thetas   : {thetas}")
    print(f"  Teacher thetas: {TEACHER_THETAS}")
    print(f"  Targets       : {[round(d['target'],4) for d in dataset]}")
    print("-" * 70)

    log_rows = [["epoch", "mse"] + [f"theta{i+1}" for i in range(4)]
                + [f"sens_{p}" for p in THETA_PARAMS]]

    # Adam state
    m = [0.0] * 4
    v = [0.0] * 4

    for epoch in range(1, EPOCHS + 1):
        total_sq_err = 0.0
        grad_acc     = [0.0] * 4
        last_sens    = {}

        for i, sample in enumerate(dataset):
            # Single TRAN call: transient voltage + sensitivity at same time point
            v_pred, sens = get_tran(thetas, sample["ic"],
                                    tag=f"e{epoch:04d}_s{i:02d}")
            error         = v_pred - sample["target"]
            total_sq_err += error ** 2
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += error * sens[p]
            last_sens = sens

        mse = total_sq_err / N

        # dL/dθ_j = (2/N) * Σ_i error_i * dV_tran/dθ_j
        raw_grad = [(2.0 / N) * g for g in grad_acc]

        # Adam update
        for j in range(4):
            m[j] = BETA1 * m[j] + (1 - BETA1) * raw_grad[j]
            v[j] = BETA2 * v[j] + (1 - BETA2) * raw_grad[j] ** 2
            m_hat = m[j] / (1 - BETA1 ** epoch)
            v_hat = v[j] / (1 - BETA2 ** epoch)
            thetas[j] -= LR * m_hat / (v_hat ** 0.5 + EPS)
            thetas[j]  = max(0.1, min(1.69, thetas[j]))

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

    print(f"\n--- Final evaluation (output_node={OUTPUT_NODE}, stop={STOP_TIME}) ---")
    print(f"{'#':>3}  {'target':>8}  {'v_pred':>8}  {'error':>8}")
    final_sq = 0.0
    for i, sample in enumerate(dataset):
        v_pred, _ = get_tran(thetas, sample["ic"], tag=f"final_{i:02d}")
        err = v_pred - sample["target"]
        final_sq += err ** 2
        print(f"{i:3d}  {sample['target']:8.4f}  {v_pred:8.4f}  {err:+8.4f}")
    print(f"\nFinal MSE : {final_sq/N:.6f}")
    print(f"Final thetas: {[round(t, 4) for t in thetas]}")
    return thetas


if __name__ == "__main__":
    train()
