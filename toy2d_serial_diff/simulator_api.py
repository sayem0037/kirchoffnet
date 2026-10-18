"""
simulator_api.py
----------------
Interface to the circuit simulator for the OPEN feedforward chain.

One TRAN call (sensitivity=True) gives, at the 100ns readout:
  - the output-node voltages  V(node, 100ns)          [forward]
  - the backward transient adjoint sensitivities
        dV(node, 100ns) / dparam                       [gradient signal]
    for every requested parameter -- both the trainable circuit params
    (VTH1..n, VB1..n) AND the encoder-driven input sources (VIN, VREF1..n),
    since all of them are voltage sources in the netlist.
"""

import sys
import io
import contextlib

sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from main import run_simulation_core


def run_chain(netlist_path, read_nodes, param_names):
    """
    Run the chain with adjoint sensitivity.

    read_nodes  : list of output node names to read (e.g. ["h4"] or ["h1","h2","h3","h4"])
    param_names : list of source names to get sensitivities for
                  (circuit params + input sources)

    Returns:
      v_out : {node: float V(node, 100ns)}
      sens  : {node: {param: float dV(node,100ns)/dparam}}   (0.0 if unavailable)
    """
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            netlist_path,
            output_nodes=list(read_nodes),
            sensitivity=True,
            keep_lus=True,
        )

    v_out = {}
    sens = {}
    for node in read_nodes:
        v_out[node] = float(result.get_voltage(node)[-1])
        avail = set(result.get_sensitivity_parameters(node))
        node_sens = {}
        for pname in param_names:
            if pname in avail:
                raw = result.get_sensitivity(node, pname)
                node_sens[pname] = float(raw[-1]) if hasattr(raw, "__len__") else float(raw)
            else:
                node_sens[pname] = 0.0
        sens[node] = node_sens

    return v_out, sens


def eval_chain(netlist_path, read_nodes):
    """Forward-only: return {node: V(node, 100ns)} (no sensitivity)."""
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(netlist_path, output_nodes=list(read_nodes))
    return {node: float(result.get_voltage(node)[-1]) for node in read_nodes}
