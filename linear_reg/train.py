"""
train.py  —  Grid search over (V2, VB4) for KirchhoffNet binary classification.

At tstop=100ns the ring has fully latched. Only Block D params (V2, VB4) have
non-zero adjoint sensitivity. Gradient descent oscillates at the bistable
bifurcation; grid search avoids this by directly evaluating R2 at each point.

No optimizer — just evaluate, compare, keep best.
"""

import os, json, csv
import numpy as np
from itertools import product

from netlist_writer import write_tran_netlist
from simulator_api  import run_sample, THETA_SOURCES, VBIAS_SOURCES, ALL_PARAMS
from dataset        import load_dataset

BASE_DIR     = r"D:\Kirchoffnet\kirchoff_claude\linear_reg"
NETLIST_PATH = os.path.join(BASE_DIR, "tmp_tran.sp")
INIT_JSON    = os.path.join(BASE_DIR, "params_init.json")
BEST_JSON    = os.path.join(BASE_DIR, "best_params.json")
LOG_CSV      = os.path.join(BASE_DIR, "train_log.csv")

N_SAMPLES = 10
TSTOP     = "100n"

# Grid over Block D params only — others stay fixed at init values.
# V2 range: saturation at ~1.659V, threshold-at-VN at ~1.677V; search wider.
# VB4 range: tail bias, currently 0.8V; search ±0.1V.
V2_VALUES  = np.round(np.arange(1.60, 1.751, 0.005), 4)   # 31 values
VB4_VALUES = np.round(np.arange(0.70, 0.901, 0.005), 4)   # 41 values


def load_base_params():
    with open(INIT_JSON) as f:
        return json.load(f)["params"]


def r2_score(preds, targets):
    ss_res = float(np.sum((preds - targets) ** 2))
    ss_tot = float(np.sum((targets - targets.mean()) ** 2))
    if ss_tot < 1e-30:
        return 0.0
    return 1.0 - ss_res / ss_tot


def evaluate(params, X_v, y_v):
    preds = []
    for i in range(len(y_v)):
        ic = {
            "net4": float(X_v[i, 0]),
            "net6": float(X_v[i, 1]),
            "net2": float(X_v[i, 2]),
            "net3": float(X_v[i, 3]),
        }
        write_tran_netlist(params, ic, NETLIST_PATH, tstop=TSTOP)
        try:
            v_pred, _ = run_sample(NETLIST_PATH)
            preds.append(float(v_pred))
        except RuntimeError:
            preds.append(float("nan"))
    preds = np.array(preds)
    valid = ~np.isnan(preds)
    if not valid.any():
        return float("nan"), float("nan"), 0
    r2  = r2_score(preds[valid], y_v[valid])
    mse = float(np.mean((preds[valid] - y_v[valid]) ** 2))
    return r2, mse, int(valid.sum())


def train():
    X_v, y_v = load_dataset(n_samples=N_SAMPLES)
    base_params = load_base_params()

    print(f"Grid search: {len(V2_VALUES)} V2 x {len(VB4_VALUES)} VB4 = "
          f"{len(V2_VALUES)*len(VB4_VALUES)} points, {N_SAMPLES} samples each")
    print(f"V2  : [{V2_VALUES[0]:.3f}, {V2_VALUES[-1]:.3f}] V")
    print(f"VB4 : [{VB4_VALUES[0]:.3f}, {VB4_VALUES[-1]:.3f}] V\n")

    best_r2     = -float("inf")
    best_params = None
    total       = len(V2_VALUES) * len(VB4_VALUES)
    done        = 0

    with open(LOG_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["v2", "vb4", "r2", "mse", "solved"])

        for v2, vb4 in product(V2_VALUES, VB4_VALUES):
            params = dict(base_params)
            params["V2"]  = float(v2)
            params["VB4"] = float(vb4)

            r2, mse, solved = evaluate(params, X_v, y_v)
            done += 1

            r2_str  = f"{r2:.4f}"  if not (isinstance(r2,  float) and np.isnan(r2))  else "nan"
            mse_str = f"{mse:.4f}" if not (isinstance(mse, float) and np.isnan(mse)) else "nan"
            writer.writerow([f"{v2:.4f}", f"{vb4:.4f}", r2_str, mse_str, solved])
            f.flush()

            improved = not np.isnan(r2) and r2 > best_r2
            if improved:
                best_r2     = r2
                best_params = dict(params)
                with open(BEST_JSON, "w") as bf:
                    json.dump({"r2": best_r2, "mse": mse, "params": best_params}, bf, indent=2)

            if done % 50 == 0 or improved:
                flag = "  <-- BEST" if improved else ""
                print(f"[{done:4d}/{total}] V2={v2:.4f} VB4={vb4:.4f}  "
                      f"R2={r2_str}  best={best_r2:.4f}{flag}")

    print(f"\nDone. Best R2={best_r2:.4f}")
    if best_params:
        print(f"  V2={best_params['V2']:.4f}  VB4={best_params['VB4']:.4f}")
        print("Best params saved to best_params.json")
    return best_r2


if __name__ == "__main__":
    train()
