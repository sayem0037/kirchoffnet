"""
verify_xbar1t1r.py -- V1 and V2. Does the array compute what it claims, and does the
select transistor earn its place?

V1  closed form        column difference == -Rf * sum_i (G+ - G-) * (v_i - vref)
V2  sneak-path block   a row with its word line LOW must contribute ~nothing
V3  linearity          doubling a row voltage doubles its contribution
V4  real TIA           V1 again with the TRANSISTOR op amp that training uses

V1-V3 use the ideal VCVS readout. V4 exists because that left the transistor TIA -- the
one every training run goes through -- unverified, and it was broken: a single-stage
5T OTA cannot drive Rf into a low-impedance column, and its column difference came out
with the wrong sign. Nothing caught it until training thrashed.

V2 is the one that matters most. The whole argument for 1T1R over a bare resistor array
is that unselected cells stop conducting; if deasserting a word line does not change the
column current, then the select devices are decoration and this is a 1R array with extra
transistors in it.
"""

import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
COMPARE = os.path.join(os.path.dirname(BASE), "compare")
sys.path.insert(0, BASE)
sys.path.insert(0, COMPARE)

import xbar1t1r_netlist as XB                       # noqa: E402
from simulator_api import eval_chain, scratch       # noqa: E402

RF = 2e3


def measure(gp, gm, xs, rf=RF, wl_mask=None, ideal_tia=True, tag="v"):
    """Simulated column differences, one per output."""
    n_out = gp.shape[1]
    nl = scratch(tag, BASE)
    XB.write_layer(gp, gm, xs, nl, rf=rf, wl_mask=wl_mask, ideal_tia=ideal_tia)
    v = eval_chain(nl, XB.read_nodes(n_out))
    os.path.exists(nl) and os.remove(nl)
    return np.array([v[p] - v[m] for p, m in XB.read_pairs(n_out)])


def _report(label, got, want, tol):
    scale = max(float(np.max(np.abs(want))), 1e-12)
    err = float(np.max(np.abs(got - want))) / scale
    ok = err <= tol
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<40} "
          f"max rel err {err * 100:7.3f}%  (tol {tol * 100:.1f}%)")
    return ok


def v1_closed_form(seed=0):
    print("\nV1  column difference vs closed form (ideal TIA)")
    rng = np.random.default_rng(seed)
    ok = True
    for trial in range(3):
        gp = rng.uniform(1e-6, 1e-4, (5, 3))
        gm = rng.uniform(1e-6, 1e-4, (5, 3))
        xs = rng.uniform(-1, 1, 5)
        got = measure(gp, gm, xs, tag="v1")
        want = XB.closed_form(gp, gm, xs, RF)
        ok &= _report(f"trial {trial}", got, want, 0.05)
        if trial == 0:
            print(f"        simulated {np.array2string(got, precision=4)}")
            print(f"        closed    {np.array2string(want, precision=4)}")
    print("        (a few % is expected: the select transistor's series resistance")
    print("         is real and the closed form does not model it)")
    return ok


def v2_sneak_path(seed=1):
    """Deassert one row's word line. Its contribution must vanish.

    Compared against the closed form computed WITHOUT that row, which is what a perfect
    selector would give.
    """
    print("\nV2  sneak-path blocking (the reason for the select transistor)")
    rng = np.random.default_rng(seed)
    n_in, n_out = 5, 3
    gp = rng.uniform(5e-5, 1e-4, (n_in, n_out))     # high conductance: worst case
    gm = rng.uniform(5e-5, 1e-4, (n_in, n_out))
    xs = rng.uniform(-1, 1, n_in)

    # Row 1 is made to DOMINATE: fully asymmetric cells at full drive, so its
    # contribution is the largest term in every column. The first version of this test
    # used random weights for row 1 too, and its G+ and G- nearly cancelled -- the row
    # was contributing ~0 before it was deselected, so removing it changed nothing and
    # the test "failed" while the netlist was fine. A blocking test has to make the
    # blocked thing matter.
    gp[0, :] = 1e-4
    gm[0, :] = 1e-6
    xs[0] = 1.0

    all_on = measure(gp, gm, xs, tag="v2a")

    mask = np.ones(n_in); mask[0] = 0                # deselect row 1
    got = measure(gp, gm, xs, wl_mask=mask, tag="v2b")

    gp2, gm2, xs2 = gp.copy(), gm.copy(), xs.copy()
    gp2[0, :] = 0.0; gm2[0, :] = 0.0                 # perfect selector: row contributes 0
    want = XB.closed_form(gp2, gm2, xs2, RF)

    print(f"        all rows on        {np.array2string(all_on, precision=4)}")
    print(f"        row 1 deselected   {np.array2string(got, precision=4)}")
    print(f"        ideal (row absent) {np.array2string(want, precision=4)}")

    moved = float(np.max(np.abs(all_on - got)))
    print(f"        deselecting moved the output by {moved:.4f} V "
          f"-- it must be non-zero or the word line does nothing")
    ok = moved > 1e-3
    print(f"  [{'PASS' if ok else 'FAIL'}] word line has an effect")
    ok &= _report("matches ideal row removal", got, want, 0.10)
    return ok


def v3_linearity(seed=2):
    """Halving every row voltage must halve every column difference."""
    print("\nV3  linearity in the row drive")
    rng = np.random.default_rng(seed)
    gp = rng.uniform(1e-6, 1e-4, (5, 3))
    gm = rng.uniform(1e-6, 1e-4, (5, 3))
    xs = rng.uniform(-1, 1, 5)
    full = measure(gp, gm, xs, tag="v3a")
    half = measure(gp, gm, 0.5 * xs, tag="v3b")
    return _report("half drive gives half output", half, 0.5 * full, 0.05)


def v4_real_tia(seed=3):
    print("\nV4  column difference vs closed form (TRANSISTOR op-amp TIA)")
    rng = np.random.default_rng(seed)
    ok = True
    for trial, n_in in enumerate((5, 17, 17)):
        gp = rng.uniform(1e-6, 1e-4, (n_in, 3))
        gm = rng.uniform(1e-6, 1e-4, (n_in, 3))
        xs = rng.uniform(-1, 1, n_in)
        got = measure(gp, gm, xs, ideal_tia=False, tag="v4")
        want = XB.closed_form(gp, gm, xs, RF)
        ok &= _report(f"trial {trial} ({n_in} rows)", got, want, 0.05)
    return ok


def main():
    print("=" * 74)
    print("1T1R crossbar -- architecture verification")
    print("=" * 74)
    r = [v1_closed_form(), v2_sneak_path(), v3_linearity(), v4_real_tia()]
    print("\n" + "=" * 74)
    if all(r):
        print("PASSED -- the array computes an MVM and the select devices block "
              "unselected rows.")
        return 0
    print("FAILED -- do not train this. Fix the netlist first.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
