"""Quick diagnostic: forward-only 100ns eval for several V2 values (no adjoint)."""
import os, sys, json, io, contextlib
import numpy as np

sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from main import run_simulation_core

sys.path.insert(0, r"D:\Kirchoffnet\kirchoff_claude\binary_reg")
from netlist_writer import write_tran_netlist
from dataset        import load_dataset

BASE_DIR     = r"D:\Kirchoffnet\kirchoff_claude\binary_reg"
NETLIST_PATH = os.path.join(BASE_DIR, "tmp_diag.sp")
INIT_JSON    = os.path.join(BASE_DIR, "params_init.json")
OUTPUT_NODE  = "net4"

X_v, y_v = load_dataset()
with open(INIT_JSON) as f:
    base_params = json.load(f)["params"]


def fwd_only(netlist_path):
    """Forward TRAN only — no sensitivity, no LU caching. Fast."""
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            netlist_path,
            output_nodes=[OUTPUT_NODE],
        )
    return float(result.get_voltage(OUTPUT_NODE)[-1])


def eval_v2(v2_val):
    params = dict(base_params)
    params["V2"] = v2_val
    preds = []
    for i in range(len(X_v)):
        ic = {"net4": float(X_v[i, 0]), "net6": float(X_v[i, 1]),
              "net2": float(X_v[i, 2]), "net3": float(X_v[i, 3])}
        write_tran_netlist(params, ic, NETLIST_PATH, tstop="100n")
        try:
            preds.append(fwd_only(NETLIST_PATH))
        except Exception:
            preds.append(float("nan"))

    preds = np.array(preds)
    valid = ~np.isnan(preds)
    ss_res = float(np.sum((preds[valid] - y_v[valid])**2))
    ss_tot = float(np.sum((y_v[valid] - y_v[valid].mean())**2))
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 1e-30 else 0.0

    print(f"\nV2={v2_val:.4f}  R²={r2:.4f}  SS_res={ss_res:.4f}")
    print(f"  {'i':>2}  IC(net3)   y      v100    err²")
    for i in range(len(X_v)):
        p  = preds[i]
        e2 = (p - y_v[i])**2 if not np.isnan(p) else float("nan")
        flag = " <-WRONG" if abs(p - y_v[i]) > 0.5 else ""
        print(f"  {i:>2}  {X_v[i,3]:>6.1f}    {y_v[i]:>4.1f}   {p:>7.4f}  {e2:>7.4f}{flag}")
    return r2


def eval_v2_tstop(v2_val, tstop):
    params = dict(base_params)
    params["V2"] = v2_val
    preds = []
    for i in range(len(X_v)):
        ic = {"net4": float(X_v[i, 0]), "net6": float(X_v[i, 1]),
              "net2": float(X_v[i, 2]), "net3": float(X_v[i, 3])}
        tstep_map = {"500n": "5n", "1u": "10n", "5u": "50n", "100n": "1n"}
        tstep = tstep_map.get(tstop, "1n")
        write_tran_netlist(params, ic, NETLIST_PATH, tstep=tstep, tstop=tstop)
        try:
            preds.append(fwd_only(NETLIST_PATH))
        except Exception:
            preds.append(float("nan"))
    preds = np.array(preds)
    valid = ~np.isnan(preds)
    ss_res = float(np.sum((preds[valid] - y_v[valid])**2))
    ss_tot = float(np.sum((y_v[valid] - y_v[valid].mean())**2))
    r2 = 1.0 - ss_res/ss_tot if ss_tot > 1e-30 else 0.0
    print(f"\nV2={v2_val:.4f}  tstop={tstop}  R²={r2:.4f}")
    for i in range(len(X_v)):
        p  = preds[i]
        e2 = (p - y_v[i])**2 if not np.isnan(p) else float("nan")
        flag = " <-WRONG" if not np.isnan(p) and abs(p - y_v[i]) > 0.5 else ""
        print(f"  {i:>2}  IC={X_v[i,3]:>4.1f}  y={y_v[i]:>4.1f}  v={p:>7.4f}  e2={e2:>7.4f}{flag}")
    return r2

# Check new class-consistent ICs at V2=1.70 and nearby values
for v2 in [1.70, 1.68, 1.66]:
    eval_v2_tstop(v2, "100n")
