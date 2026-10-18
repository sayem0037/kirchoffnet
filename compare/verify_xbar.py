"""
verify_xbar.py -- Gate A. The crossbar netlist against its closed form.

If the deck is wired correctly then with an ideal transimpedance readout the
column difference is exactly

    V(t+_j) - V(t-_j) = -Rf * sum_i (G_a,ij - G_b,ij) * (v+_i - v-_i)

with no dependence on vref and none on the common mode. Three checks:

  A1  the closed form itself, over random weights and random data
  A2  common-mode rejection: move vcm, the scores must not move
  A3  vref rejection: move vref, the scores must not move

A2 and A3 are the ones worth running. A1 alone can pass on a deck that has the
cross-connection backwards but symmetric; only the rejection tests prove the
four-quadrant cancellation is real rather than coincidental at one operating
point.

A failure here means the NETLIST is wrong, not the physics -- fix it before any
accuracy number is generated, because a miswired crossbar will still train to
something and the something will be meaningless.
"""

import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import xbar_netlist as X                      # noqa: E402
from simulator_api import eval_chain, scratch  # noqa: E402

RF = 2.5e3


def closed_form(w, xs, layers, rf=RF, vcm=1.0, swing=0.4, bias=True,
                r_on=X.R_ON_DEFAULT, r_off=X.R_OFF_DEFAULT):
    """-Rf * sum_i (G_a - G_b) * dv_i, per output column."""
    n_in, n_out = layers[0]
    dv = [swing * float(xs[i - 1]) for i in range(1, n_in + 1)]
    if bias:
        dv = [swing * 1.0] + dv                 # the bias row carries x = +1

    out = []
    for j in range(1, n_out + 1):
        s = 0.0
        for k, i in enumerate(range((0 if bias else 1), n_in + 1)):
            ga, gb = X.w_to_g(w[i if bias else i - 1][j - 1], r_on, r_off)
            s += (ga - gb) * dv[k]
        out.append(-rf * s)
    return np.array(out)


def measure(w, xs, layers, vcm=1.0, vref=1.65, rf=RF, tag="gateA"):
    """Simulated V(t+) - V(t-) per column, ideal TIA."""
    res = X.weights_to_res(w, layers)
    nl = scratch(tag)
    X.write_xbar_netlist(res, xs, layers, nl, rf=f"{rf:.6e}",
                         vcm=vcm, vref=vref, ideal_tia=True)
    v = eval_chain(nl, X.read_nodes(layers))
    os.remove(nl)
    return np.array([v[p] - v[m] for p, m in X.read_pairs(layers)])


def _report(label, got, want, tol):
    scale = max(float(np.max(np.abs(want))), 1e-12)
    err = float(np.max(np.abs(got - want))) / scale
    ok = err <= tol
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<38} "
          f"max rel err {err * 100:7.3f}%  (tol {tol * 100:.1f}%)")
    return ok


def a1_closed_form(seed=0):
    print("\nA1  column difference vs closed form")
    layers = [(6, 4)]
    rng = np.random.default_rng(seed)
    ok = True
    for trial in range(3):
        w = [rng.uniform(-1, 1, (layers[0][0] + 1, layers[0][1]))]
        xs = rng.uniform(-1, 1, layers[0][0])
        got = measure(w, xs, layers)
        want = closed_form(w[0], xs, layers)
        ok &= _report(f"trial {trial}", got, want, 0.01)
        if trial == 0:
            print(f"        simulated {np.array2string(got, precision=4)}")
            print(f"        closed    {np.array2string(want, precision=4)}")
    return ok


def a2_common_mode(seed=1):
    """Move the input common mode. The four-quadrant cell cancels it exactly,
    so the scores must not budge."""
    print("\nA2  common-mode rejection (vcm 0.8 -> 1.2 V)")
    layers = [(6, 4)]
    rng = np.random.default_rng(seed)
    w = [rng.uniform(-1, 1, (layers[0][0] + 1, layers[0][1]))]
    xs = rng.uniform(-1, 1, layers[0][0])

    base = measure(w, xs, layers, vcm=1.0, tag="gateA2a")
    ok = True
    for vcm in (0.8, 1.2):
        got = measure(w, xs, layers, vcm=vcm, tag="gateA2b")
        ok &= _report(f"vcm = {vcm} V", got, base, 0.01)
    return ok


def a3_vref(seed=2):
    """Move the TIA reference. It cancels in the difference, so likewise."""
    print("\nA3  vref rejection (1.2 -> 2.0 V)")
    layers = [(6, 4)]
    rng = np.random.default_rng(seed)
    w = [rng.uniform(-1, 1, (layers[0][0] + 1, layers[0][1]))]
    xs = rng.uniform(-1, 1, layers[0][0])

    base = measure(w, xs, layers, vref=1.65, tag="gateA3a")
    ok = True
    for vref in (1.2, 2.0):
        got = measure(w, xs, layers, vref=vref, tag="gateA3b")
        ok &= _report(f"vref = {vref} V", got, base, 0.01)
    return ok


def main():
    print("=" * 70)
    print("Gate A -- crossbar netlist vs closed form")
    print("=" * 70)
    r = [a1_closed_form(), a2_common_mode(), a3_vref()]
    print("\n" + "=" * 70)
    if all(r):
        print("Gate A PASSED -- the crossbar computes the MVM it claims to.")
        return 0
    print("Gate A FAILED -- the netlist is miswired. Do not train it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
