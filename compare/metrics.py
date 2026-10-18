"""
metrics.py -- Accuracy / Convergence / Time / Area / Energy, measured the same
way for every arm.

The point of this module is that no arm gets to define its own yardstick. KFQ,
the crossbar and the digital datapath all hand their netlist and their
simulation result to the same five functions here, so a difference in a column
is a difference in the circuit and not a difference in bookkeeping.

Nothing in the repo did this before: device counts existed
(netlist_kfq.n_devices) and an analytic column current existed
(kfq_spec.col_current), but no energy, no area, no settling time. Those are
what this file adds.

Conventions, fixed once:

  ENERGY   E = integral over the measurement window of sum_k v_k(t) * i_k(t),
           taken over every INDEPENDENT source in the netlist -- the supply and
           every bias and weight source. Trapezoid on the simulator's own
           sweep_axis, so the integration grid is the solver grid and no
           resampling error is introduced. Reported split into the static part
           (the DC draw, which for a LEVEL=1 analog circuit is nearly all of
           it) and the remainder.

  TIME     t_settle = the last instant at which any read node is still further
           than `tol` of its own final swing away from its final value. "Last
           time it was still moving", not "first time it looked close", because
           the second one is fooled by a slow node that crosses early and comes
           back.

  AREA     sum of drawn device areas through tech.py, plus explicit periphery
           line items. First-order, under a stated card, and labelled as such.

  ACCURACY test accuracy with a Wilson 95% interval, which stays honest at the
           small n these circuits are evaluated at.

  CONVERGE epochs to reach `frac` of the run's own best test accuracy, plus the
           raw solve count, because an epoch is not the same amount of work for
           every arm and only the solve count is comparable across them.
"""

import os
import sys

import numpy as np

sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from utils.parser import NetlistParser  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import tech  # noqa: E402

# Sign convention for source power. In this simulator's MNA stamp the branch
# unknown for a voltage source is the current flowing INTO its n1 terminal, so
# the power DELIVERED by the source is -v*i. Gate C (verify_metrics.py) pins
# this down against a resistor of known value; do not change it without
# re-running that gate.
_P_SIGN = -1.0

MOS_TYPES = ("NMOS", "PMOS", "M")
SRC_TYPES = ("V", "I")


# ========================================================== netlist facts ====
def device_inventory(netlist_path):
    """Parse a netlist back into a device inventory.

    Uses the simulator's own NetlistParser rather than a second parser of our
    own, so the inventory can never disagree with what was actually simulated.

    Returns a dict:
        counts    {type: n}
        mos       [(name, model, W, L), ...]
        res       [(name, R), ...]
        cap       [(name, C), ...]
        sources   [(name, n1, n2), ...]      independent V/I sources only
        ctrl      [(name, type), ...]        E/F/G/H
    """
    comps, _ = NetlistParser().parse(netlist_path)

    inv = dict(counts={}, mos=[], res=[], cap=[], sources=[], ctrl=[])
    for name, c in comps.items():
        t = c.get("type", "?")
        inv["counts"][t] = inv["counts"].get(t, 0) + 1

        if t in MOS_TYPES:
            ip = c.get("inst_params", {}) or {}
            mp = c.get("model_params", {}) or {}
            w = ip.get("W", mp.get("W", 1e-6))
            l = ip.get("L", mp.get("L", 1e-6))
            inv["mos"].append((name, c.get("model", "?"), float(w), float(l)))
        elif t == "R":
            inv["res"].append((name, float(c.get("value") or 0.0)))
        elif t == "C":
            inv["cap"].append((name, float(c.get("value") or 0.0)))
        elif t in SRC_TYPES:
            inv["sources"].append((name, c.get("n1"), c.get("n2")))
        elif t in ("E", "F", "G", "H"):
            inv["ctrl"].append((name, t))

    return inv


def area_um2(inv, periphery=None):
    """First-order drawn area, in um^2, broken out by contributor.

    periphery : optional dict of {label: area_m2} for things that are not in
                the netlist -- ADCs, DACs, SRAM, digital control. The crossbar
                arm carries converters here; KFQ carries none, which is the
                whole architectural argument and must therefore stay a separate
                line rather than get folded into a total.
    """
    parts = {}
    parts["mos"] = sum(tech.mos_area(w, l) for _, _, w, l in inv["mos"])
    parts["res"] = sum(tech.res_area(r) for _, r in inv["res"])
    parts["cap"] = sum(tech.cap_area(c) for _, c in inv["cap"])
    for label, a in (periphery or {}).items():
        parts[label] = float(a)

    out = {k: v * 1e12 for k, v in parts.items()}      # m^2 -> um^2
    out["total"] = sum(out.values())
    return out


# =============================================================== energy ======
def source_power(result, inv, source_names=None):
    """Instantaneous power delivered by each independent source, in W.

    Returns (t, {name: p_t}). Sources whose branch current the simulator did
    not expose (current sources have no branch equation) are skipped and
    reported by their absence, not silently zeroed.
    """
    t = np.asarray(result.sweep_axis, dtype=float)
    want = set(source_names) if source_names else None

    p = {}
    for name, n1, n2 in inv["sources"]:
        if want is not None and name not in want:
            continue
        try:
            i_t = np.real(np.asarray(result.get_current(name), dtype=float))
        except ValueError:
            continue                      # no branch equation (I-source)
        v1 = _node_v(result, n1, len(t))
        v2 = _node_v(result, n2, len(t))
        p[name] = _P_SIGN * (v1 - v2) * i_t
    return t, p


def _node_v(result, node, n):
    if node == 0 or node == "0":
        return np.zeros(n)
    return np.real(np.asarray(result.get_voltage(node), dtype=float))


def _trapz(y, x):
    fn = getattr(np, "trapezoid", None) or np.trapz
    return float(fn(y, x))


def energy_j(result, inv, source_names=None, t_window=None):
    """Energy drawn over the measurement window, in J.

    t_window : (t0, t1) in seconds. Defaults to the whole transient. For a
               latency-matched comparison pass (0, t_settle) so every arm is
               charged for exactly the time it needs to produce an answer.

    Returns dict: total, static, dynamic, per_source, window, p_avg.
    """
    t, p = source_power(result, inv, source_names)
    if len(t) < 2:
        # .OP or a single-point result: power only, no energy without a window.
        tot = float(sum(float(np.atleast_1d(v)[0]) for v in p.values()))
        return dict(total=float("nan"), static=float("nan"),
                    dynamic=float("nan"), p_avg=tot, window=(0.0, 0.0),
                    per_source={k: float(np.atleast_1d(v)[0])
                                for k, v in p.items()})

    t0, t1 = (t[0], t[-1]) if t_window is None else t_window
    m = (t >= t0) & (t <= t1)
    if m.sum() < 2:
        m = np.ones_like(t, dtype=bool)
    tw, dur = t[m], float(t[m][-1] - t[m][0])

    per = {k: _trapz(v[m], tw) for k, v in p.items()}
    total = float(sum(per.values()))

    # Static = the settled DC draw held for the whole window. Dynamic = what is
    # left, i.e. the switching transient. For a LEVEL=1 analog circuit the
    # second term is essentially zero by construction (no intrinsic caps), and
    # the paper says so rather than pretending the split is informative there.
    p_final = float(sum(float(v[m][-1]) for v in p.values()))
    static = p_final * dur
    return dict(total=total, static=static, dynamic=total - static,
                p_avg=(total / dur if dur > 0 else float("nan")),
                window=(float(tw[0]), float(tw[-1])), per_source=per)


# ================================================================ timing =====
def settling_time(result, read_nodes, tol=0.02, t0=0.0):
    """Time after which every read node stays within `tol` of its final swing.

    Returns (t_settle, per_node). Measured from t0 (default 0), so it is a
    latency and not an absolute timestamp.
    """
    t = np.asarray(result.sweep_axis, dtype=float)
    if len(t) < 3:
        return float("nan"), {}

    per = {}
    for nd in read_nodes:
        v = np.real(np.asarray(result.get_voltage(nd), dtype=float))
        vf = v[-1]
        swing = float(np.max(np.abs(v - vf)))
        if swing <= 0.0:
            per[nd] = 0.0
            continue
        band = tol * swing
        outside = np.nonzero(np.abs(v - vf) > band)[0]
        per[nd] = 0.0 if len(outside) == 0 else float(t[outside[-1]] - t0)

    return (max(per.values()) if per else float("nan")), per


def crossings(t, v, level, rising=None):
    """Times at which v crosses `level`, linearly interpolated.

    Interpolated rather than snapped to the nearest sample: a digital edge is
    resolved by a handful of points even at a fine step, and rounding to the
    grid would put a floor under every delay measurement at one time step.
    """
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float)
    out = []
    for k in range(len(v) - 1):
        a, b = v[k] - level, v[k + 1] - level
        if a == 0.0:
            up = v[min(k + 1, len(v) - 1)] > v[k]
            if rising is None or up == rising:
                out.append(float(t[k]))
            continue
        if a * b < 0.0:
            up = b > a
            if rising is not None and up != rising:
                continue
            out.append(float(t[k] + (t[k + 1] - t[k]) * (-a / (b - a))))
    return out


def prop_delay(result, in_node, out_node, vdd, rising_in=True):
    """50%-to-50% propagation delay for one input edge, in seconds.

    Returns nan if either node never crosses midpoint -- which is the honest
    answer for a gate that did not switch, and is caught by the caller rather
    than silently reported as a zero delay.
    """
    t = np.asarray(result.sweep_axis, dtype=float)
    vi = np.real(np.asarray(result.get_voltage(in_node), dtype=float))
    vo = np.real(np.asarray(result.get_voltage(out_node), dtype=float))
    mid = 0.5 * vdd

    ti = crossings(t, vi, mid, rising=rising_in)
    if not ti:
        return float("nan")
    t_in = ti[0]
    to = [x for x in crossings(t, vo, mid) if x >= t_in]
    return (to[0] - t_in) if to else float("nan")


# ============================================================== accuracy =====
def wilson(acc, n, z=1.96):
    """Wilson score interval. Lifted from kfabric/run_kfq.py so the benchmark
    numbers in this directory and in that one are computed identically."""
    if n == 0:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (acc + z * z / (2 * n)) / d
    h = z * np.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def epochs_to_converge(test_acc, frac=0.95):
    """First epoch reaching `frac` of the run's own best test accuracy.

    Relative to the run's own best, not to an absolute target, so an arm that
    plateaus low is not credited with converging instantly and an arm that
    plateaus high is not penalised for having further to climb.
    """
    a = np.asarray(test_acc, dtype=float)
    if a.size == 0:
        return dict(best=float("nan"), epoch=None, n_epochs=0, frac=frac)
    best = float(np.nanmax(a))
    hit = np.nonzero(a >= frac * best)[0]
    return dict(best=best, epoch=(int(hit[0]) + 1 if len(hit) else None),
                n_epochs=int(a.size), frac=frac)


# ============================================================ reporting ======
def summarise(name, acc_te, n_te, conv, latency_s, energy, area):
    """One arm's row, in the units the paper's table uses."""
    lo, hi = wilson(acc_te, n_te)
    lat = latency_s * 1e9 if latency_s == latency_s else None
    return dict(arm=name, test_acc=acc_te, ci=(lo, hi), n_test=n_te,
                epochs_to_converge=conv.get("epoch"),
                best_acc=conv.get("best"),
                latency_ns=lat,
                energy_pj=energy["total"] * 1e12,
                power_uw=energy["p_avg"] * 1e6,
                area_um2=area["total"], area_breakdown=area)
