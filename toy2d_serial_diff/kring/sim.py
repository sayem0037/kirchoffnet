"""One isolated simulation = one private temp dir; returns an explicit status, never raises."""
import contextlib, hashlib, io, math, os, sys, tempfile

_core = None
_SPICE_UNITS = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}


def spice_val(s):
    s = str(s).strip().lower()
    return float(s[:-1]) * _SPICE_UNITS[s[-1]] if s[-1] in _SPICE_UNITS else float(s)


def sim_src_dir(explicit=None):
    p = explicit or os.environ.get("KRING_SIM_SRC")
    if not p:
        raise RuntimeError("simulator source dir not set: pass sim_src=... or set KRING_SIM_SRC")
    return p


def fingerprint(src):
    """sha256 over all simulator .py files (excluding tests): identifies the solver version."""
    h = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(src)):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "test"))
        for f in sorted(files):
            if f.endswith(".py"):
                with open(os.path.join(root, f), "rb") as fh:
                    h.update(f.encode()); h.update(fh.read())
    return h.hexdigest()[:16]


def _get_core(src):
    global _core
    if _core is None:
        if src not in sys.path:
            sys.path.insert(0, src)
        from main import run_simulation_core
        _core = run_simulation_core
    return _core


def simulate(netlist_text, read_nodes, tstop, sens_params=None, sim_src=None, want_t0=False, want_wave=False):
    """Returns dict(status, v, t_final, sens, t0, wave, message).
    status in {ok, no_convergence, nonfinite, incomplete, error}.
    sens: {node: [dV(node,T)/dparam for param in sens_params]}
    wave: (t, V) with V[node][time], only when want_wave"""
    out = dict(status="error", v=None, t_final=None, sens=None, t0=None, wave=None, message="")
    core = _get_core(sim_src_dir(sim_src))
    with tempfile.TemporaryDirectory(prefix="kring_") as td:
        path = os.path.join(td, "ring.sp")
        with open(path, "w") as f:
            f.write(netlist_text)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                _, res = core(path, output_nodes=list(read_nodes),
                              sensitivity=bool(sens_params),
                              keep_lus=bool(sens_params))
        except Exception as e:  # the simulator raises on non-convergence
            msg = f"{type(e).__name__}: {e}"
            out["status"] = "no_convergence" if ("onverge" in msg) else "error"
            out["message"] = msg[:200]
            return out
        t = res.sweep_axis
        out["t_final"] = float(t[-1])
        v = [float(res.get_voltage(n)[-1]) for n in read_nodes]
        if want_t0:
            out["t0"] = {n: float(res.get_voltage(n)[0]) for n in list(read_nodes) + ["dm1", "tl1"]}
        if not all(math.isfinite(x) for x in v):
            out["status"] = "nonfinite"
            return out
        if abs(t[-1] - tstop) > 1e-6 * tstop:
            out["status"] = "incomplete"
            return out
        out["v"] = v
        if want_wave:
            out["wave"] = ([float(x) for x in t], [[float(y) for y in res.get_voltage(n)] for n in read_nodes])
        if sens_params:
            sens = {}
            for n in read_nodes:
                have = set(res.get_sensitivity_parameters(n))
                sens[n] = [float(res.get_sensitivity(n, p)[-1]) if p in have else float("nan")
                           for p in sens_params]
            out["sens"] = sens
        out["status"] = "ok"
    return out
