"""
Runs both training approaches for 200 epochs and saves separate CSV logs.
  op_log.csv   — .OP prediction + sensitivity (vn as input)
  tran_log.csv — .TRAN prediction + sensitivity (IC as input, stop=0.5ns)
"""

import sys, os, json, csv, random

SIM_SRC = r"D:\Simulator\circuit_simulator-main\src"
if SIM_SRC not in sys.path:
    sys.path.insert(0, SIM_SRC)

from main import run_simulation_core
from netlist_generator import write_op_netlist, write_tran_netlist

BASE_DIR    = r"D:\Kirchoffnet\kirchoff_claude"
NETLIST_DIR = os.path.join(BASE_DIR, "temp_netlists")
os.makedirs(NETLIST_DIR, exist_ok=True)

THETA_PARAMS   = ["V5", "V4", "V3", "V2"]
TEACHER_THETAS = [0.5, 0.5, 0.5, 0.5]
TRAIN_THETAS   = [1.5, 1.5, 1.5, 1.5]
OUTPUT_NODE    = "net2"
N_DATA         = 10
EPOCHS         = 200
LR             = 0.05
BETA1, BETA2, EPS = 0.9, 0.999, 1e-8
SEED           = 42
VDD            = 3.3
RING_NODES     = ["net2", "net3", "net4", "net6"]
VN_VALUES      = [round(0.5 + i * 0.1, 1) for i in range(N_DATA)]


# ── helpers ────────────────────────────────────────────────────────────────

def _parse_result(result, node, params):
    v_raw  = result.get_voltage(node)
    v_pred = float(v_raw[-1]) if hasattr(v_raw, "__len__") else float(v_raw)
    avail  = result.get_sensitivity_parameters(node) if result.sensitivities else []
    sens   = {}
    for p in params:
        if p in avail:
            raw    = result.get_sensitivity(node, p)
            sens[p] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
        else:
            sens[p] = 0.0
    return v_pred, sens


def get_op(thetas, vn, tag):
    path = os.path.join(NETLIST_DIR, f"op_{tag}.txt")
    write_op_netlist(thetas, path, vn=vn)
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE], sensitivity=True)
    return _parse_result(result, OUTPUT_NODE, THETA_PARAMS)


def get_tran(thetas, ic_dict, tag):
    path = os.path.join(NETLIST_DIR, f"tran_{tag}.txt")
    write_tran_netlist(thetas, ic_dict, path, stop_time="0.5n")
    _, result = run_simulation_core(path, output_nodes=[OUTPUT_NODE], sensitivity=True)
    return _parse_result(result, OUTPUT_NODE, THETA_PARAMS)


def adam_update(thetas, m, v, raw_grad, epoch):
    for j in range(4):
        m[j] = BETA1 * m[j] + (1 - BETA1) * raw_grad[j]
        v[j] = BETA2 * v[j] + (1 - BETA2) * raw_grad[j] ** 2
        m_hat = m[j] / (1 - BETA1 ** epoch)
        v_hat = v[j] / (1 - BETA2 ** epoch)
        thetas[j] -= LR * m_hat / (v_hat ** 0.5 + EPS)
        thetas[j]  = max(0.1, min(1.69, thetas[j]))


# ── OP training ────────────────────────────────────────────────────────────

def run_op():
    print("\n" + "=" * 60)
    print("APPROACH 1: .OP  (vn as input, DC saddle-point)")
    print("=" * 60)

    # dataset
    print("Generating OP dataset...")
    dataset = []
    for i, vn in enumerate(VN_VALUES):
        v_target, _ = get_op(TEACHER_THETAS, vn, tag=f"op_teacher_{i:02d}")
        dataset.append({"vn": vn, "target": v_target})
        print(f"  vn={vn:.1f}V  target={v_target:.4f}V")

    thetas = list(TRAIN_THETAS)
    m, v   = [0.0]*4, [0.0]*4
    log    = [["epoch", "mse"] + [f"theta{i+1}" for i in range(4)]]

    for epoch in range(1, EPOCHS + 1):
        sq_err, grad_acc = 0.0, [0.0]*4
        for i, s in enumerate(dataset):
            v_pred, sens = get_op(thetas, s["vn"], tag=f"op_e{epoch:03d}_s{i:02d}")
            err = v_pred - s["target"]
            sq_err += err ** 2
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += err * sens[p]
        mse      = sq_err / N_DATA
        raw_grad = [(2.0 / N_DATA) * g for g in grad_acc]
        adam_update(thetas, m, v, raw_grad, epoch)
        log.append([epoch, mse] + list(thetas))
        if epoch == 1 or epoch % 20 == 0:
            print(f"  Epoch {epoch:3d}  MSE={mse:.6f}  T={[round(t,4) for t in thetas]}")

    path = os.path.join(BASE_DIR, "op_log.csv")
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(log)
    print(f"  Saved -> {path}")
    return log


# ── TRAN training ──────────────────────────────────────────────────────────

def run_tran():
    print("\n" + "=" * 60)
    print("APPROACH 2: .TRAN  (IC as input, stop=0.5ns)")
    print("=" * 60)

    # dataset
    random.seed(SEED)
    print("Generating TRAN dataset...")
    dataset = []
    for i in range(N_DATA):
        ic = {n: round(random.uniform(0.2, VDD - 0.2), 4) for n in RING_NODES}
        v_target, _ = get_tran(TEACHER_THETAS, ic, tag=f"tran_teacher_{i:02d}")
        dataset.append({"ic": ic, "target": v_target})
        print(f"  sample {i:2d}: target={v_target:.4f}V")

    thetas = list(TRAIN_THETAS)
    m, v   = [0.0]*4, [0.0]*4
    log    = [["epoch", "mse"] + [f"theta{i+1}" for i in range(4)]]

    for epoch in range(1, EPOCHS + 1):
        sq_err, grad_acc = 0.0, [0.0]*4
        for i, s in enumerate(dataset):
            v_pred, sens = get_tran(thetas, s["ic"], tag=f"tran_e{epoch:03d}_s{i:02d}")
            err = v_pred - s["target"]
            sq_err += err ** 2
            for j, p in enumerate(THETA_PARAMS):
                grad_acc[j] += err * sens[p]
        mse      = sq_err / N_DATA
        raw_grad = [(2.0 / N_DATA) * g for g in grad_acc]
        adam_update(thetas, m, v, raw_grad, epoch)
        log.append([epoch, mse] + list(thetas))
        if epoch == 1 or epoch % 20 == 0:
            print(f"  Epoch {epoch:3d}  MSE={mse:.6f}  T={[round(t,4) for t in thetas]}")

    path = os.path.join(BASE_DIR, "tran_log.csv")
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(log)
    print(f"  Saved -> {path}")
    return log


if __name__ == "__main__":
    run_op()
    run_tran()
    print("\nBoth done. Run plot_comparison.py to compare.")
