"""
verify_metrics.py -- Gate C. The energy primitive, checked against circuits
whose answer is known in closed form before it is ever pointed at a network.

Three checks, each one a go/no-go:

  C1  resistor across the supply       E = VDD^2/R * T, exactly
  C2  two resistors                    energies add, and the split is right
  C3  RC charging from a step          E_supply = C*VDD^2 (half stored, half
                                       burnt in R) once settled -- this is the
                                       one that proves the integrator is
                                       actually integrating a transient and not
                                       just multiplying a DC point by a window

C3 also fixes the settling-time function against tau = RC, which is the number
the latency column depends on.
"""

import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import metrics                      # noqa: E402
import tech                         # noqa: E402
from simulator_api import run_metered, scratch   # noqa: E402

VDD = tech.VDD


def _write(path, lines):
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _check(label, got, want, rtol=1e-3):
    ok = abs(got - want) <= rtol * max(abs(want), 1e-30)
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {label:<34} got {got: .6e}   want {want: .6e}")
    return ok


def c1_resistor():
    """One resistor across the supply. E = VDD^2/R * T."""
    print("\nC1  resistor across supply")
    r, tstop = 10e3, 100e-9
    nl = _write(scratch("gateC1"), [
        "* Gate C1 -- one resistor across the supply",
        f"V0 vdd 0 DC {VDD}",
        f"R1 vdd 0 {r}",
        f".TRAN {tstop / 100:.6e} {tstop:.6e}",
        ".END",
    ])
    res = run_metered(nl, ["vdd"])
    inv = metrics.device_inventory(nl)
    e = metrics.energy_j(res, inv)

    want_p = VDD ** 2 / r
    want_e = want_p * tstop
    ok = _check("energy", e["total"], want_e)
    ok &= _check("average power", e["p_avg"], want_p)
    ok &= _check("static == total", e["static"], want_e)
    os.remove(nl)
    return ok


def c2_two_resistors():
    """Two resistors. Energies add; the per-source total is the sum."""
    print("\nC2  two resistors in parallel")
    r1, r2, tstop = 10e3, 47e3, 100e-9
    nl = _write(scratch("gateC2"), [
        "* Gate C2 -- two resistors across the supply",
        f"V0 vdd 0 DC {VDD}",
        f"R1 vdd 0 {r1}",
        f"R2 vdd 0 {r2}",
        f".TRAN {tstop / 100:.6e} {tstop:.6e}",
        ".END",
    ])
    res = run_metered(nl, ["vdd"])
    inv = metrics.device_inventory(nl)
    e = metrics.energy_j(res, inv)

    want_e = (VDD ** 2 / r1 + VDD ** 2 / r2) * tstop
    ok = _check("energy", e["total"], want_e)
    ok &= _check("inventory: 2 resistors", len(inv["res"]), 2, rtol=0)
    os.remove(nl)
    return ok


def c3_rc_step():
    """RC charged through a step.

    Once settled the supply has delivered C*VDD^2: half is stored on the cap,
    half was dissipated in R. That identity is independent of R, so it is a
    real test of the integrator rather than a restatement of Ohm's law.

    The same run checks settling_time against the analytic tau = RC: reaching
    a 2% band takes ln(50) * tau = 3.912 * tau.
    """
    print("\nC3  RC step response")
    r, c = 10e3, 10e-15
    tau = r * c
    tstop = 40.0 * tau
    nl = _write(scratch("gateC3"), [
        "* Gate C3 -- RC charged from a supply step",
        f"V0 vdd 0 PULSE(0 {VDD} 0 1e-15 1e-15 {tstop:.6e} {2 * tstop:.6e})",
        f"R1 vdd out {r}",
        f"C1 out 0 {c:.6e}",
        f".TRAN {tau / 50:.6e} {tstop:.6e}",
        ".END",
    ])
    res = run_metered(nl, ["vdd", "out"])
    inv = metrics.device_inventory(nl)
    e = metrics.energy_j(res, inv)

    want_e = c * VDD ** 2
    ok = _check("supply energy = C*VDD^2", e["total"], want_e, rtol=0.05)
    ok &= _check("dynamic dominates", float(e["dynamic"] > 0.9 * e["total"]),
                 1.0, rtol=0)

    t_s, per = metrics.settling_time(res, ["out"], tol=0.02)
    want_t = np.log(50.0) * tau
    ok &= _check("settling time = ln(50)*RC", t_s, want_t, rtol=0.15)
    print(f"        tau = {tau:.3e} s, measured t_settle = {t_s:.3e} s")
    os.remove(nl)
    return ok


def main():
    print("=" * 66)
    print("Gate C -- energy and timing primitives")
    print("=" * 66)
    results = [c1_resistor(), c2_two_resistors(), c3_rc_step()]
    print("\n" + "=" * 66)
    if all(results):
        print("Gate C PASSED -- energy_j and settling_time are trustworthy.")
        return 0
    print("Gate C FAILED -- do not report any energy or latency number until "
          "this passes.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
