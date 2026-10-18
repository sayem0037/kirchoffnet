"""
simulator_api.py -- the shared wrapper, extended for measurement.

`run_chain` and `eval_chain` are byte-compatible with the copy that sits in
kfabric/, toy2d/, toy2d_serial_diff/, toy2d_spidernet/ and bin_class/, so any
training loop can import from here without changing a line. What this version
adds is `run_metered`: a forward-only transient at a fine time step that keeps
the whole waveform, which is what the energy and settling-time metrics need and
what the training path deliberately does not produce.

Why training and measurement need different runs. Training uses
`.TRAN 50n 100n` -- three time steps -- with `sensitivity=True, keep_lus=True`.
That is a deliberate choice recorded in kfabric: the node settles in ~1e-13 s,
so extra steps buy nothing for the gradient, and every retained step costs one
cached LU factorization. But three points cannot resolve a settling edge and
cannot integrate a power waveform. So measurement re-runs the same netlist
forward-only, with no LU retention, at whatever step resolves the transient.
"""

import contextlib
import io
import os
import re
import sys

sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from main import run_simulation_core  # noqa: E402


# ------------------------------------------------- training-path (shared) ---
def run_chain(netlist_path, read_nodes, param_names):
    """One transient with adjoint sensitivity.

    read_nodes  : output nodes to read
    param_names : source names to get sensitivities for

    Returns (v_out, sens):
      v_out : {node: V(node, t_stop)}
      sens  : {node: {param: dV(node, t_stop)/dparam}}   0.0 if unavailable
    """
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(
            netlist_path, output_nodes=list(read_nodes),
            sensitivity=True, keep_lus=True,
        )

    v_out, sens = {}, {}
    for node in read_nodes:
        v_out[node] = float(result.get_voltage(node)[-1])
        avail = set(result.get_sensitivity_parameters(node))
        node_sens = {}
        for pname in param_names:
            if pname in avail:
                raw = result.get_sensitivity(node, pname)
                node_sens[pname] = (float(raw[-1]) if hasattr(raw, "__len__")
                                    else float(raw))
            else:
                node_sens[pname] = 0.0
        sens[node] = node_sens
    return v_out, sens


def eval_chain(netlist_path, read_nodes):
    """Forward-only: {node: V(node, t_stop)}. No sensitivity."""
    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(netlist_path,
                                        output_nodes=list(read_nodes))
    return {node: float(result.get_voltage(node)[-1]) for node in read_nodes}


# ------------------------------------------------------- measurement path ---
_TRAN_RE = re.compile(r"^\s*\.TRAN\s+\S+\s+\S+\s*$", re.IGNORECASE | re.M)


def retime(netlist_path, tstep, tstop, out_path=None):
    """Rewrite a netlist's .TRAN card to a finer grid, leaving all else alone.

    The netlist writers already in the repo all emit exactly one `.TRAN tstep
    tstop` line, so this is a surgical substitution rather than a re-render --
    which matters, because it guarantees the measured circuit is bit-identical
    to the trained one apart from the time grid.

    tstep, tstop : SPICE strings ("10p", "2n") or floats in seconds.
    """
    def fmt(x):
        return x if isinstance(x, str) else f"{float(x):.6e}"

    with open(netlist_path) as f:
        text = f.read()

    card = f".TRAN {fmt(tstep)} {fmt(tstop)}"
    new, n = _TRAN_RE.subn(card, text)
    if n == 0:
        raise ValueError(f"no .TRAN card found in {netlist_path}; "
                         "retime() only understands transient decks")
    if n > 1:
        raise ValueError(f"{n} .TRAN cards in {netlist_path}; expected one")

    out_path = out_path or netlist_path
    with open(out_path, "w") as f:
        f.write(new)
    return out_path


def run_metered(netlist_path, read_nodes, tstep=None, tstop=None,
                out_path=None):
    """Forward-only transient that keeps the whole waveform.

    If tstep/tstop are given the deck is retimed first (into `out_path` if
    given, so the original is not touched). Returns the raw SimulationResult:
    the caller hands it straight to metrics.energy_j / metrics.settling_time,
    which need the branch currents and the full sweep axis, not just the final
    sample.
    """
    path = netlist_path
    if tstep is not None or tstop is not None:
        if tstep is None or tstop is None:
            raise ValueError("pass both tstep and tstop, or neither")
        path = retime(netlist_path, tstep, tstop, out_path)

    with contextlib.redirect_stdout(io.StringIO()):
        _, result = run_simulation_core(path, output_nodes=list(read_nodes))
    return result


def scratch(tag, base=None):
    """Per-process scratch netlist path.

    Sharing one scratch file between concurrent workers silently corrupted two
    result sets earlier in this project -- nothing errored, the symptom was a
    log with elapsed times running backwards -- so the pid is part of the name
    and every worker gets its own file. See kfabric/train_kfq.py:scratch.
    """
    base = base or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, f"tmp_{tag}_{os.getpid()}.sp")
