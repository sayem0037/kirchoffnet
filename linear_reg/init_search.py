"""
init_search.py
--------------
Grid search to find the best symmetric starting parameters (theta, vbias)
where the circuit gives useful analog output and non-zero sensitivities.

Problem with original settings (vbias=2.7V):
  - Tail current ~3.4 mA → ring latches in < 1 ns
  - By t=100 ns the output is always railed to 0V or 3.3V (digital, not analog)
  - Sensitivities at the railed state are near-zero for most parameters

Fix: use low vbias (near threshold, ~0.7-0.9V) so the ring settles SLOWLY.
  - At vbias=0.7V: I_tail ~21 uA → time constant ~160 ns
  - At t=100 ns the ring is still mid-way between IC and equilibrium → analog range
  - Input features (encoded as .IC) actually influence the t=100ns output

Scoring:
  - v_range: how much V(net4) changes between low IC (0.5V) and high IC (2.5V)
             Large v_range = input features have strong effect on output
  - n_nonzero: how many of the 8 parameters have non-zero adjoint sensitivity
               More = more parameters can be trained
"""

import sys
import io
import contextlib
import json
import numpy as np

# Add simulator to Python path
sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from main import run_simulation_core
from netlist_writer import write_tran_netlist

# ── Constants ────────────────────────────────────────────────
OUTPUT_NODE   = "net4"
THETA_SOURCES = ["V5", "V4", "V3", "V2"]
VBIAS_SOURCES = ["VB1", "VB2", "VB3", "VB4"]
ALL_PARAMS    = THETA_SOURCES + VBIAS_SOURCES
NETLIST_PATH  = r"D:\Kirchoffnet\kirchoff_claude\linear_reg\tmp_search.sp"
OUTPUT_JSON   = r"D:\Kirchoffnet\kirchoff_claude\linear_reg\params_init.json"

# Two IC conditions to measure the analog range of the output
IC_LOW  = {n: 0.5 for n in ["net4", "net6", "net2", "net3"]}   # all inputs low
IC_HIGH = {n: 2.5 for n in ["net4", "net6", "net2", "net3"]}   # all inputs high
IC_MID  = {n: 1.5 for n in ["net4", "net6", "net2", "net3"]}   # neutral starting point


def run_tran(params, ic):
    """
    Run TRAN with global adjoint backward pass.
    Returns V(net4) at t=100ns and the adjoint sensitivity dict.
    """
    write_tran_netlist(params, ic, NETLIST_PATH, tstop="100n")

    # Suppress the simulator's per-step prints
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            NETLIST_PATH,
            output_nodes=[OUTPUT_NODE],
            global_adjoint=True,   # backward adjoint pass: gives dV(t_final)/dparam
            keep_lus=True,         # required for adjoint
        )

    v_out = float(result.get_voltage(OUTPUT_NODE)[-1])

    # "Integrated_Transient" = backward adjoint result = dV(net4, t=100ns)/dparam
    raw = result.global_sensitivities["Integrated_Transient"][OUTPUT_NODE]
    sens = {name: float(raw.get(name, 0.0)) for name in ALL_PARAMS}

    return v_out, sens


def evaluate(theta_val, vbias_val):
    """
    Evaluate a symmetric (theta, vbias) point — all blocks get the same values.
    Returns a dict with scoring metrics.
    """
    # Build symmetric params dict
    params = {k: theta_val for k in THETA_SOURCES}
    params.update({k: vbias_val for k in VBIAS_SOURCES})

    # Run at low and high IC to measure output range
    v_low,  _        = run_tran(params, IC_LOW)
    v_high, _        = run_tran(params, IC_HIGH)
    v_mid,  sens_mid = run_tran(params, IC_MID)   # get sensitivity at neutral IC

    # Output range: how much the input features shift the output
    v_range = abs(v_high - v_low)

    # Count non-zero sensitivities (threshold 1e-8 to ignore floating-point zeros)
    n_nonzero = sum(1 for v in sens_mid.values() if abs(v) > 1e-8)

    # Combined score: range × non-zero count (both matter)
    score = v_range * n_nonzero

    return {
        "score"    : score,
        "v_range"  : v_range,
        "v_low"    : v_low,
        "v_high"   : v_high,
        "v_mid"    : v_mid,
        "n_nonzero": n_nonzero,
        "sens_mid" : sens_mid,
    }


# ── Grid search ───────────────────────────────────────────────
# theta: PMOS gate bias — lower = stronger PMOS load current
# vbias: tail NMOS bias — LOWER = slower circuit = more analog at t=100ns
theta_vals = [1.5, 1.7, 1.9, 2.1, 2.3]       # V
vbias_vals = [0.70, 0.75, 0.80, 0.85, 0.90]   # V  (keep near threshold for slow dynamics)

print("Searching for best (theta, vbias) starting point...")
print(f"{'theta':>6} {'vbias':>6} | {'v_low':>6} {'v_high':>6} {'v_range':>7} {'nonzero':>7} | {'score':>7}")
print("-" * 68)

best_score  = -1.0
best_theta  = None
best_vbias  = None
best_result = None

for theta in theta_vals:
    for vbias in vbias_vals:
        try:
            r = evaluate(theta, vbias)
            print(
                f"{theta:6.2f} {vbias:6.2f} | "
                f"{r['v_low']:6.3f} {r['v_high']:6.3f} {r['v_range']:7.3f} {r['n_nonzero']:7d} | "
                f"{r['score']:7.3f}"
            )
            if r["score"] > best_score:
                best_score  = r["score"]
                best_theta  = theta
                best_vbias  = vbias
                best_result = r
        except Exception as e:
            print(f"{theta:6.2f} {vbias:6.2f} | ERROR: {e}")

# ── Report best point ─────────────────────────────────────────
print(f"\n{'='*68}")
print(f"Best starting point: theta={best_theta:.2f}V, vbias={best_vbias:.2f}V")
print(f"  Output range (low->high IC): {best_result['v_range']:.3f}V")
print(f"  V(net4) at low  IC (0.5V): {best_result['v_low']:.3f}V")
print(f"  V(net4) at mid  IC (1.5V): {best_result['v_mid']:.3f}V")
print(f"  V(net4) at high IC (2.5V): {best_result['v_high']:.3f}V")
print(f"  Non-zero sensitivities: {best_result['n_nonzero']}/8")
print(f"  Sensitivities at mid IC:")
for name, val in best_result["sens_mid"].items():
    star = " *" if abs(val) > 1e-8 else ""
    print(f"    d(net4)/d({name:4s}) = {val:+.6f}{star}")

# ── Save best params to JSON ──────────────────────────────────
init_params = {k: best_theta for k in THETA_SOURCES}
init_params.update({k: best_vbias for k in VBIAS_SOURCES})

with open(OUTPUT_JSON, "w") as f:
    json.dump({"params": init_params, "theta": best_theta, "vbias": best_vbias}, f, indent=2)

print(f"\nSaved to {OUTPUT_JSON}")
print("Run train.py to start training with these parameters.")
