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


def run_sample(netlist_path):
    """
    Run one training sample: TRAN forward pass + global adjoint backward pass.

    Returns both the circuit output AND the exact gradients in a single call.
    The adjoint backward pass computes dV(net4, t=100ns)/d(param) for all 8
    trainable parameters — at the correct TRAN circuit state (not DC equilibrium).

    netlist_path: path to a TRAN netlist written by write_tran_netlist()
    returns:
      v_pred : float — V(net4) at t=100ns (the circuit's prediction)
      sens   : dict  — {param_name: dV(net4,t=100ns)/dparam} for all 8 params
    """
    # Suppress the simulator's verbose per-step print output
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            netlist_path,
            output_nodes=[OUTPUT_NODE],
            global_adjoint=True,   # backward adjoint pass for exact transient gradients
            keep_lus=True,         # cache LU factorizations (required for adjoint)
        )

    # Forward output: V(net4) at the final time step (t=100ns)
    v_pred = float(result.get_voltage(OUTPUT_NODE)[-1])

    # Adjoint sensitivity: dV(net4, t_final)/dparam for each trainable source
    # "Integrated_Transient" is the backward-integrated adjoint = dV(t_final)/dparam
    raw_sens = result.global_sensitivities["Integrated_Transient"][OUTPUT_NODE]
    sens = {name: float(raw_sens.get(name, 0.0)) for name in ALL_PARAMS}

    return v_pred, sens
