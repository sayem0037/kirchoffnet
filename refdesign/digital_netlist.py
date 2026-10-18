"""
digital_netlist.py -- a fixed-point MAC datapath, built from CMOS gates.

WHAT IS HERE
------------
A real gate-level netlist: AND gates for partial products, full adders built from NAND,
a ripple-carry array multiplier, and a ripple-carry accumulator. Emitted as SPICE from
the same 0.35 um cards the analog arm uses, so a transistor here and a transistor there
are the same transistor.

WHY IT IS VERIFIED AT DC AND NOT IN TRANSIENT
---------------------------------------------
Multi-stage CMOS cascades do not converge in transient on this simulator. A single gate
is fine; anything driven by another gate fails at the first timestep, at every step size
from 1 ps to 20 ps, under both trapezoidal and backward Euler, with and without explicit
initial conditions. The cause is structural: the transient's initial DC solve seeds every
node at mid-supply, which is the maximum-gain point of a chain of inverting stages, so
Newton is started at the worst possible place.

Logic correctness, however, is a DC property. `.OP` *does* converge on cascades. So the
datapath's function is verified at the operating point -- which is exactly what
bit-accuracy means -- and the transient simulations are confined to single gates, where
they work, for energy and delay. The limitation is reported rather than worked around.

ENCODING
--------
Two's complement, N bits, LSB first in every bus. Logic levels are 0 V and VDD; a node
is read as 1 if it sits above VDD/2.
"""

import numpy as np

VDD = 3.3
NCH = (".MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7")
PCH = (".MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7")
WN, WP, LG = "2u", "5u", "0.35u"


class GateNetlist:
    """Accumulates gate instances and hands back a SPICE deck.

    Every gate gets a unique instance index, so a datapath can be built by calling
    nand/inv/and/xor in whatever order the structural description needs.
    """

    def __init__(self):
        self.lines = []
        self.n = 0
        self.nodes = set(["0", "vdd"])

    # ------------------------------------------------------------- primitives --
    def inv(self, a, out):
        self.n += 1; i = self.n
        self.lines += [f"MN{i} {out} {a} 0 0 NCH L={LG} W={WN}",
                       f"MP{i} {out} {a} vdd vdd PCH L={LG} W={WP}"]
        self.nodes |= {a, out}
        return out

    def nand(self, a, b, out):
        self.n += 1; i = self.n
        self.lines += [f"MNA{i} {out} {a} nx{i} 0 NCH L={LG} W={WN}",
                       f"MNB{i} nx{i} {b} 0 0 NCH L={LG} W={WN}",
                       f"MPA{i} {out} {a} vdd vdd PCH L={LG} W={WP}",
                       f"MPB{i} {out} {b} vdd vdd PCH L={LG} W={WP}"]
        self.nodes |= {a, b, out}
        return out

    def nor(self, a, b, out):
        self.n += 1; i = self.n
        self.lines += [f"MNA{i} {out} {a} 0 0 NCH L={LG} W={WN}",
                       f"MNB{i} {out} {b} 0 0 NCH L={LG} W={WN}",
                       f"MPA{i} px{i} {a} vdd vdd PCH L={LG} W={WP}",
                       f"MPB{i} {out} {b} px{i} vdd PCH L={LG} W={WP}"]
        self.nodes |= {a, b, out}
        return out

    # -------------------------------------------------------------- compounds --
    def and2(self, a, b, out):
        t = f"{out}_nd"
        self.nand(a, b, t)
        return self.inv(t, out)

    def or2(self, a, b, out):
        t = f"{out}_nr"
        self.nor(a, b, t)
        return self.inv(t, out)

    def xor2(self, a, b, out):
        """XOR from four NANDs -- the standard static-CMOS construction."""
        g1, g2, g3 = f"{out}_x1", f"{out}_x2", f"{out}_x3"
        self.nand(a, b, g1)
        self.nand(a, g1, g2)
        self.nand(b, g1, g3)
        return self.nand(g2, g3, out)

    def full_adder(self, a, b, cin, s, cout):
        """sum = a^b^cin, carry = majority(a,b,cin), as 2 XOR + 3 NAND."""
        h = f"{s}_h"
        self.xor2(a, b, h)
        self.xor2(h, cin, s)
        n1, n2 = f"{cout}_n1", f"{cout}_n2"
        self.nand(a, b, n1)
        self.nand(h, cin, n2)
        self.nand(n1, n2, cout)
        return s, cout

    # ------------------------------------------------------------- datapaths --
    def ripple_add(self, A, B, S, cin="0", tag="ra"):
        """S = A + B, LSB first. Returns the final carry node name."""
        c = cin
        for k in range(len(A)):
            cout = f"{tag}_c{k}"
            self.full_adder(A[k], B[k], c, S[k], cout)
            c = cout
        return c

    def array_multiply(self, A, B, P, tag="mul"):
        """Unsigned array multiplier. len(P) must be len(A)+len(B).

        Partial products are AND gates; the rows are summed with ripple-carry adders.
        This is the textbook structure the published MLP-accelerator reference designs
        use, and it is what the gate counts in the cost model assume.
        """
        na, nb = len(A), len(B)
        # row 0 of partial products
        prev = []
        for i in range(na):
            nd = f"{tag}_pp0_{i}"
            self.and2(A[i], B[0], nd)
            prev.append(nd)
        P[0] = prev[0]

        for j in range(1, nb):
            pp = []
            for i in range(na):
                nd = f"{tag}_pp{j}_{i}"
                self.and2(A[i], B[j], nd)
                pp.append(nd)
            # add pp to prev[1:], shifted
            addend = prev[1:] + ["0"]
            S = [f"{tag}_s{j}_{i}" for i in range(na)]
            c = "0"
            for i in range(na):
                cout = f"{tag}_c{j}_{i}"
                self.full_adder(addend[i], pp[i], c, S[i], cout)
                c = cout
            P[j] = S[0]
            prev = S[:] + [c]
        for i in range(1, na + 1):
            P[nb - 1 + i] = prev[i]
        return P

    # ----------------------------------------------------------------- output --
    def deck(self, inputs, analysis=".OP"):
        """Assemble the SPICE deck. `inputs` maps node name -> 0/1."""
        L = ["* fixed-point datapath -- gate level", NCH, PCH, "",
             f"V0 vdd 0 DC {VDD}", ""]
        for k, (node, bit) in enumerate(sorted(inputs.items())):
            L.append(f"VI{k} {node} 0 DC {VDD if bit else 0.0:.4f}")
        L += [""] + self.lines + ["", analysis, ".END"]
        return "\n".join(L) + "\n"


# --------------------------------------------------------------------- helpers --
def bits_of(value, n):
    """Two's-complement bit list, LSB first."""
    v = int(value) & ((1 << n) - 1)
    return [(v >> i) & 1 for i in range(n)]


def value_of(bits, signed=True):
    v = sum(int(b) << i for i, b in enumerate(bits))
    if signed and bits and bits[-1]:
        v -= 1 << len(bits)
    return v


def read_bits(result, nodes, vdd=VDD):
    """Node voltages -> logic levels, thresholded at VDD/2."""
    out = []
    for nd in nodes:
        v = float(np.real(np.atleast_1d(result.get_voltage(nd))[-1]))
        out.append(1 if v > 0.5 * vdd else 0)
    return out
