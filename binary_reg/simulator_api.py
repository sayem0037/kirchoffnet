"""
simulator_api.py
----------------
Single-call interface to the Python circuit simulator.

The original approach used TWO simulator calls per sample:
  1. TRAN  → V(net4) at t=100ns  (forward output)
  2. .OP   → dV(net4)/dparam    (DC adjoint sensitivity — WRONG state)

Problem: the .OP sensitivity is computed at the DC equilibrium (circuit railed),
which is a DIFFERENT circuit state than the TRAN output. The gradient was
therefore pointing in the wrong direction.

Fix: ONE TRAN call with global_adjoint=True.
  - TRAN forward pass  → V(net4) at t=100ns
  - Backward adjoint   → dV(net4, t=100ns)/dparam  (exact, correct state)

This is simpler and more accurate.
"""

import sys
import io
import contextlib

# Add the simulator's source directory to Python's import path
sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from main import run_simulation_core

# ── Circuit output node ──────────────────────────────────────
OUTPUT_NODE = "net4"   # V(net4) at t=100ns is the circuit's prediction

# ── Trainable parameter names (must match voltage source names in netlist) ──
# NOTE: the SPICE parser uppercases all names → VB1 not Vb1
THETA_SOURCES = ["V5", "V4", "V3", "V2"]             # PMOS gate biases
VBIAS_SOURCES = ["VB1", "VB2", "VB3", "VB4"]         # tail NMOS gate biases
ALL_PARAMS    = THETA_SOURCES + VBIAS_SOURCES         # all 8 trainable params


def eval_sample(netlist_path):
    """Forward-only TRAN — no sensitivity. Fast; used only for 100ns evaluation."""
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            netlist_path,
            output_nodes=[OUTPUT_NODE],
        )
    return float(result.get_voltage(OUTPUT_NODE)[-1])


def run_sample(netlist_path):
    """
    Run one training sample: TRAN forward pass + instantaneous adjoint sensitivity.

    Uses sensitivity=True (NOT global_adjoint) to get dV(net4, t_final)/dparam
    at the final time step via the local Jacobian transpose solve. This is the
    same approach as iris_op which achieved 93.3% accuracy.

    The global_adjoint (Integrated_Transient) approach was found to give
    near-machine-precision values (~1e-15) for this circuit due to the
    time-integrated adjoint canceling across the transient.

    netlist_path: path to a TRAN netlist written by write_tran_netlist()
    returns:
      v_pred : float — V(net4) at t_final (the circuit's prediction)
      sens   : dict  — {param_name: dV(net4,t_final)/dparam} for all 8 params
    """
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            netlist_path,
            output_nodes=[OUTPUT_NODE],
            sensitivity=True,    # instantaneous adjoint at each timestep
            keep_lus=True,
        )

    # Forward output: V(net4) at the final time step
    v_pred = float(result.get_voltage(OUTPUT_NODE)[-1])

    # Instantaneous sensitivity at final timestep: dV(net4, t_final)/dparam
    # result.get_sensitivity(node, param) returns the full time series; [-1] = final step
    sens = {}
    avail = result.get_sensitivity_parameters(OUTPUT_NODE)
    for name in ALL_PARAMS:
        if name in avail:
            raw = result.get_sensitivity(OUTPUT_NODE, name)
            sens[name] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
        else:
            sens[name] = 0.0

    return v_pred, sens
