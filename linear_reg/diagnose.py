"""
diagnose.py — print sensitivity values for different tstop choices.
Runs 3 samples with the current params and reports dV(net4)/d(param).
This tells us: which tstop gives meaningful sensitivity to ALL 4 IC nodes.
"""
import json, contextlib, io, os
import numpy as np

from netlist_writer import write_tran_netlist
from simulator_api  import run_sample, ALL_PARAMS
from dataset        import load_dataset

BASE_DIR = r"D:\Kirchoffnet\kirchoff_claude\linear_reg"
NETLIST  = os.path.join(BASE_DIR, "tmp_diag.sp")
INIT     = os.path.join(BASE_DIR, "params_init.json")

def load_params():
    with open(INIT) as f:
        return json.load(f)["params"]

X_v, y_v = load_dataset(n_samples=5)
params = load_params()

for tstop in ["10n", "20n", "50n", "100n", "200n"]:
    print(f"\n=== tstop={tstop} ===")
    sens_all = {n: [] for n in ALL_PARAMS}
    preds = []
    for i in range(5):
        ic = {"net4": float(X_v[i,0]), "net6": float(X_v[i,1]),
              "net2": float(X_v[i,2]), "net3": float(X_v[i,3])}
        write_tran_netlist(params, ic, NETLIST, tstop=tstop)
        try:
            v, sens = run_sample(NETLIST)
            preds.append(v)
            for n in ALL_PARAMS:
                sens_all[n].append(abs(sens[n]))
        except RuntimeError as e:
            print(f"  Sample {i}: FAILED — {e}")
            continue
    if preds:
        print(f"  Predictions: {[f'{p:.3f}' for p in preds]}")
        print(f"  ICs(net4):   {[f'{X_v[i,0]:.3f}' for i in range(len(preds))]}")
        print(f"  Targets:     {[f'{float(y_v[i]):.3f}' for i in range(len(preds))]}")
        print(f"  Mean |sens|:")
        for n in ALL_PARAMS:
            if sens_all[n]:
                print(f"    {n:6s}: {np.mean(sens_all[n]):.3e}")
