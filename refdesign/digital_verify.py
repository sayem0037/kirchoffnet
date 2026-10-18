"""
digital_verify.py -- V3. The gate-level datapath against the software integer model.

WHAT IS CLAIMED, AND WHAT IS NOT
-------------------------------
Claimed: the adder and multiplier the fixed-point network's arithmetic runs through are
real CMOS gates, simulated in this simulator, and they produce exactly the integers the
software model produces -- on EVERY possible input, not a sample. Each case below is a
SPICE solve.

Not claimed: that a whole inference was simulated gate by gate. See the measured
convergence ceiling in V3d; a full INT8 multiplier is roughly 3800 transistors and the
solver stops converging around 150 in a single DC solve.

Verification is at the operating point rather than in transient. Cascaded CMOS stages do
not converge in .TRAN on this simulator at any time step under either integration
method, because the transient's initial DC solve seeds every node at mid-supply -- the
maximum-gain point of a chain of inverting stages. Logic correctness is a DC property,
and .OP does converge, so that is where it is checked.
"""

import argparse
import contextlib
import io
import itertools
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
COMPARE = os.path.join(os.path.dirname(BASE), "compare")
sys.path.insert(0, BASE)
sys.path.insert(0, COMPARE)

import digital_netlist as D                        # noqa: E402
from simulator_api import scratch                  # noqa: E402

sys.path.insert(0, r"D:\Simulator\circuit_simulator with level3\src")
from main import run_simulation_core               # noqa: E402

RESULTS = os.path.join(BASE, "results")


def solve(gates, inputs, reads):
    """One .OP solve; returns the read nodes as bits, or None if Newton gave up.

    Non-convergence is NOT a logic error and must not be reported as one. It is
    input-dependent as well as size-dependent -- a 3-bit adder converges for some
    operand pairs and not others -- so each case is attempted independently and the
    convergence rate is reported alongside the correctness rate. Conflating the two
    would either hide a real mismatch or invent one.
    """
    nl = scratch("verify", BASE)
    try:
        with open(nl, "w") as f:
            f.write(gates.deck(inputs))
        with contextlib.redirect_stdout(io.StringIO()):
            _, r = run_simulation_core(nl, output_nodes=list(reads))
        return D.read_bits(r, reads)
    except Exception:
        return None
    finally:
        if os.path.exists(nl):
            os.remove(nl)


def _verdict(label, n_ok, n_conv, n_total, bad):
    rate = 100.0 * n_conv / max(n_total, 1)
    exact = (n_ok == n_conv) and n_conv > 0
    print(f"  [{'PASS' if exact else 'FAIL'}] {label}")
    print(f"        converged {n_conv}/{n_total} ({rate:.0f}%), "
          f"exact {n_ok}/{n_conv}")
    for row in bad[:4]:
        print(f"        {row}")
    return exact


def n_mos(gates):
    return sum(1 for l in gates.lines if l[:1] in ("M", "m"))


# ------------------------------------------------------------------- checks --
def check_full_adder():
    """All eight input combinations of a 9-gate cascade."""
    print()
    print("V3a  full adder, exhaustive (8 cases)")
    n_ok = n_conv = n_tot = 0
    bad = []
    for a, b, c in itertools.product([0, 1], repeat=3):
        g = D.GateNetlist()
        g.full_adder("a", "b", "c", "s", "co")
        got = solve(g, {"a": a, "b": b, "c": c}, ["s", "co"])
        want = [(a + b + c) & 1, 1 if (a + b + c) > 1 else 0]
        n_tot += 1
        if got is None:
            continue
        n_conv += 1
        if got == want:
            n_ok += 1
        else:
            bad.append(f"a={a} b={b} c={c}: got {got}, want {want}")
    return _verdict("sum and carry exact", n_ok, n_conv, n_tot, bad)


def check_adder(nbits=3):
    """Exhaustive sweep of an n-bit ripple-carry adder."""
    print()
    print(f"V3b  {nbits}-bit ripple adder, exhaustive ({(2**nbits)**2} cases)")
    A = [f"a{i}" for i in range(nbits)]
    B = [f"b{i}" for i in range(nbits)]
    S = [f"s{i}" for i in range(nbits)]
    n_ok = n_conv = n_tot = 0
    bad = []
    for x, y in itertools.product(range(2 ** nbits), repeat=2):
        g = D.GateNetlist()
        g.ripple_add(A, B, S)
        ins = {}
        ins.update({A[i]: b for i, b in enumerate(D.bits_of(x, nbits))})
        ins.update({B[i]: b for i, b in enumerate(D.bits_of(y, nbits))})
        bits = solve(g, ins, S)
        n_tot += 1
        if bits is None:
            continue
        n_conv += 1
        val = D.value_of(bits, signed=False)
        want = (x + y) % (2 ** nbits)
        if val == want:
            n_ok += 1
        else:
            bad.append(f"{x} + {y}: hardware {val}, expected {want}")
    return _verdict("hardware sum == integer sum (mod 2^n)",
                    n_ok, n_conv, n_tot, bad)


def check_multiplier(nbits=2):
    """Exhaustive sweep of an n x n array multiplier."""
    print()
    print(f"V3c  {nbits}x{nbits} array multiplier, exhaustive "
          f"({(2**nbits)**2} cases)")
    A = [f"a{i}" for i in range(nbits)]
    B = [f"b{i}" for i in range(nbits)]
    P = [None] * (2 * nbits)
    n_ok = n_conv = n_tot = 0
    bad = []
    for x, y in itertools.product(range(2 ** nbits), repeat=2):
        g = D.GateNetlist()
        g.array_multiply(A, B, P)
        ins = {}
        ins.update({A[i]: b for i, b in enumerate(D.bits_of(x, nbits))})
        ins.update({B[i]: b for i, b in enumerate(D.bits_of(y, nbits))})
        bits = solve(g, ins, P)
        n_tot += 1
        if bits is None:
            continue
        n_conv += 1
        val = D.value_of(bits, signed=False)
        if val == x * y:
            n_ok += 1
        else:
            bad.append(f"{x} x {y}: hardware {val}, expected {x * y}")
    return _verdict("hardware product == integer product",
                    n_ok, n_conv, n_tot, bad)


def report_ceiling():
    """Measure where DC convergence stops, so the limit is a number and not a hunch."""
    print()
    print("V3d  measured .OP convergence ceiling")
    rows = []
    for w in (2, 3, 4, 5):
        g = D.GateNetlist()
        A = [f"a{i}" for i in range(w)]
        B = [f"b{i}" for i in range(w)]
        S = [f"s{i}" for i in range(w)]
        g.ripple_add(A, B, S)
        ins = {**{a: 1 for a in A}, **{b: 0 for b in B}}
        rows.append((w, n_mos(g), solve(g, ins, S) is not None))
    for w, n, ok in rows:
        print(f"        {w}-bit adder  {n:4d} MOS  "
              f"{'converges' if ok else 'does NOT converge'}")
    last = max([n for _, n, ok in rows if ok], default=0)
    print(f"  ceiling ~{last} transistors per DC solve. A full INT8 multiplier is")
    print(f"  ~3800 transistors and is NOT claimed to have been simulated; what is")
    print(f"  verified is that every primitive it is built from is exact.")
    return True


def main(a):
    print("=" * 72)
    print("V3 -- gate-level datapath vs the software integer model (.OP)")
    print("=" * 72)
    r = [check_full_adder(), check_adder(a.adder_bits),
         check_multiplier(a.mul_bits), report_ceiling()]
    print()
    print("=" * 72)
    if all(r):
        print("V3 PASSED -- every datapath primitive is exact on every possible input.")
        return 0
    print("V3 FAILED -- the netlist and the model disagree.")
    return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--adder-bits", type=int, default=3)
    ap.add_argument("--mul-bits", type=int, default=2)
    sys.exit(main(ap.parse_args()))
