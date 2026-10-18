"""
netlist_kfq.py -- KIRCHHOFF FOUR-QUADRANT NETWORK. Fully differential: signed
weights AND signed signals, so the common mode cancels exactly.

THE DEFECT THIS FIXES (measured, Gate 2 / gate_diff.py)
-------------------------------------------------------
The 2-transistor differential column (netlist_kdn.py) fixed the sign problem --
48% of weights came out negative, effective rank held at 4.34 through depth 6
instead of collapsing to 1.03. But every self-consistent window it found was
12-34 mV wide and the composed map stayed affine at R2 = 1.0000. The reason is
in the algebra of that cell. With single-ended rows,

    score_j = k(thbar - VTO) * sum_i dtheta_ij   -   k * sum_i dtheta_ij v_i
              [------ per-column BIAS ------]        [------ SIGNAL ------]

The rows sit as a narrow band on a large common mode (the fixed point put them
at ~1.0 V), and the weight multiplies the ABSOLUTE row voltage. So the bias term
carries (thbar - VTO) ~ 1.17 while the data-dependent term carries only the
deviation ~ 0.01: a per-column offset roughly 100x the signal. That offset
hard-saturates the column's differential pair before any data arrives, and a
saturated pair has ~zero incremental gain -- which is exactly the measured
collapse. It also explains why |score| = 0.476 V looked healthy: that statistic
was measuring BIAS SPREAD between columns, not signal.

Differential columns with single-ended rows is only half a fix.

THE FOUR-QUADRANT CELL
----------------------
Drive each input as a DIFFERENCE about a fixed common mode and cross-connect
four devices to the column pair -- the standard differential in-memory-computing
cell:

    row pair (v+, v-)            x_i is carried by  dv = v+ - v-

        c+  <-  M(gate=theta_a, src=v+)   and   M(gate=theta_b, src=v-)
        c-  <-  M(gate=theta_b, src=v+)   and   M(gate=theta_a, src=v-)

With A = theta_a - VTO and B = theta_b - VTO the column difference is

    I(c+) - I(c-) = 1/2 k [ (A-v+)^2 - (B-v+)^2 + (B-v-)^2 - (A-v-)^2 ]
                  = 1/2 k [ (A-B)(A+B-2v+) - (A-B)(A+B-2v-) ]
                  = -k (theta_a - theta_b) (v+ - v-)

    ==>  score_j = R k * sum_i dtheta_ij * dv_i          dtheta = theta_a - theta_b

A pure product of a trainable SIGNED weight with a SIGNED signal. Both the
v^2 term and the entire common-mode/bias term cancel identically -- not
approximately, and not by tuning. There is no offset left to saturate the
neuron with, so the differential pair that follows sees only data.

Cost: 4 devices per weight (against 2) plus 3 per column pair. That is the
price of four-quadrant operation and it is what the literature pays too; a
Gilbert multiplier costs more.

THE NEURON, AND WHY THE STACK NOW CLOSES
----------------------------------------
The differential pair already produces BOTH drains. Single-ended rows threw one
of them away, which is what forced the data back onto a common mode in the first
place. Here both drains become the next layer's row pair, so the network is
differential end to end and every layer sees a zero-mean signal.

Every weight (theta_a, theta_b) and every layer gain (the pair's tail bias) is a
plain voltage source, so all of them are visible to the simulator's transient
adjoint -- verified against central finite differences at cosine 1.000000. The
class scores are the last layer's column differences; argmax over them is the
prediction, with no trained read-out anywhere.
"""

VDD = 3.3

NCH = ".MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7"
PCH = ".MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7"
VTO_N, VTO_P = 0.531, 0.71

SYN_L, SYN_W = "1u", "4u"        # synapse NMOS (four per logical weight)
DP_L, DP_W = "1u", "8u"          # differential-pair input devices
TAIL_L, TAIL_W = "1u", "8u"      # tail current source


# ---------------------------------------------------------------- names ----
def theta_a(l, i, j):
    """First half of a signed weight. The leading 'V' is REQUIRED: in SPICE the
    first letter of a component name declares its type, so a source named
    A0_1_1 is not parsed as a voltage source at all -- its gate node floats and
    the DC solve dies with 'Factor is exactly singular'."""
    return f"VA{l}_{i}_{j}"


def theta_b(l, i, j):
    return f"VB{l}_{i}_{j}"


def tail_name(l):
    """One trainable gain knob per layer: the signal-propagation constant."""
    return f"VT{l}"


def in_p(i):
    return f"VIP{i}"


def in_m(i):
    return f"VIM{i}"


def row_p(l, i):
    # i = 0 is the fixed bias reference, shared by every layer.
    if i == 0:
        return "bp"
    return f"xp{i}" if l == 0 else f"o{l-1}_{i}"


def row_m(l, i):
    if i == 0:
        return "bm"
    return f"xm{i}" if l == 0 else f"ob{l-1}_{i}"


def colp(l, j):
    return f"cp{l}_{j}"


def coln(l, j):
    return f"cn{l}_{j}"


def out_node(l, j):
    return f"o{l}_{j}"


def outn_node(l, j):
    return f"ob{l}_{j}"


def layer_thetas(l, n_in, n_out, bias=True):
    """Weights of layer l. Index i = 0 is the BIAS row.

    Why a bias row is mandatory here, not optional: the four-quadrant cell
    computes score = sum_i w_ij * dv_i with NO constant term -- the same
    cancellation that removes the ruinous common-mode offset also removes the
    bias. A tanh network with zero bias is an ODD function, f(-x) = -f(x), so
    its decision boundary must pass through the origin and cannot enclose a
    region. Measured: the `circle` set (inner disc vs outer ring, both centred
    on the origin) sat at exactly chance, loss 0.6936 against ln 2 = 0.6931,
    and did not move in 20 epochs.

    The fix is the textbook one -- an extra input row held at a fixed
    differential reference, with its own trainable weight, so each column gets
    a trainable constant. In hardware that is one more row of four devices.
    """
    out = []
    for j in range(1, n_out + 1):
        for i in range((0 if bias else 1), n_in + 1):
            out += [theta_a(l, i, j), theta_b(l, i, j)]
    return out


def all_thetas(layers, tails=True, bias=True):
    out = []
    for l, (n_in, n_out) in enumerate(layers):
        out += layer_thetas(l, n_in, n_out, bias)
        if tails:
            out.append(tail_name(l))
    return out


def n_devices(layers, bias=True):
    # 4 synapse NMOS per weight (+1 bias row); per column: 2 pair + 1 tail
    b = 1 if bias else 0
    return sum(4 * (n_in + b) * n_out + 3 * n_out for n_in, n_out in layers)


def read_pairs(layers):
    """Class scores are the LAST layer's column differences. No software
    read-out: argmax over V(c+_j) - V(c-_j) is the prediction."""
    l = len(layers) - 1
    return [(colp(l, j), coln(l, j)) for j in range(1, layers[l][1] + 1)]


def read_nodes(layers):
    return [nd for pair in read_pairs(layers) for nd in pair]


def encode(x, vcm, swing):
    """x in [-1, 1] -> (v+, v-) about vcm. The data lives ONLY in the
    difference; the common mode is identical for every input and cancels in the
    column difference, which is the whole point of the four-quadrant cell."""
    return vcm + 0.5 * swing * x, vcm - 0.5 * swing * x


# -------------------------------------------------------------- netlist ----
def write_kfq_netlist(theta, xs, layers, path, cap="0.1f",
                      tstep="50n", tstop="100n", ic=1.0,
                      load_r="20k", rd="200k", vtail=0.75,
                      vcm=1.0, swing=0.4, bias=True):
    """
    theta : {VA.../VB...: volts, VT{l}: volts}   weights and per-layer gains.
            A missing tail entry falls back to `vtail`.
    xs    : array-like of n_in0 values in [-1, 1]  (the data point)
    layers: [(n_in, n_out), ...]                   e.g. [(4, 7), (7, 3)]
    load_r: one value, or ONE PER LAYER. The column's DC drop is
            load_r * k * n_in * margin^2, so it scales with FAN-IN: the value
            that keeps a 64-input layer saturated leaves a 16-input layer
            barely driven. Measured at fan-in 8 the right value is ~2.5k and at
            fan-in 64 it is ~200, i.e. inversely proportional as the formula
            says. A single number for a 64 -> 16 -> 10 network therefore cannot
            be right for both layers.
    """
    if isinstance(load_r, (list, tuple)):
        if len(load_r) != len(layers):
            raise ValueError(f"load_r has {len(load_r)} entries for "
                             f"{len(layers)} layers")
        load_rs = list(load_r)
    else:
        load_rs = [load_r] * len(layers)
    n_in0 = layers[0][0]
    L = [
        "* KIRCHHOFF FOUR-QUADRANT NETWORK (KFQ) -- auto-generated",
        f"* layers {layers} | {n_devices(layers, bias)} devices | "
        f"{len(all_thetas(layers))} trainable sources",
        "* Fully differential. One weight = FOUR cross-connected NMOS:",
        "*     c+ <- (theta_a, v+) (theta_b, v-)",
        "*     c- <- (theta_b, v+) (theta_a, v-)",
        "* so  V(c+) - V(c-) = R k (theta_a - theta_b)(v+ - v-):  a pure",
        "* product of a signed weight with a signed signal. Both the v^2 term",
        "* and the per-column bias cancel IDENTICALLY. The 2-transistor version",
        "* left a bias ~100x the signal, which saturated the neuron and pinned",
        "* the composed map at affine R2 = 1.0000.",
        "", NCH, PCH, "", f"V0 vdd 0 DC {VDD}", "",
        f"* ---- data: differential rows about vcm={vcm} V, swing={swing} V ----",
    ]
    for i in range(1, n_in0 + 1):
        vp, vm = encode(float(xs[i - 1]), vcm, swing)
        L.append(f"{in_p(i)} xp{i} 0 DC {vp:.6f}")
        L.append(f"{in_m(i)} xm{i} 0 DC {vm:.6f}")

    if bias:
        bp, bm = encode(1.0, vcm, swing)
        L += ["", "* fixed differential reference = the BIAS row. Without it",
              "* the four-quadrant score has no constant term, the network is",
              "* an ODD function, and any set needing a boundary that does not",
              "* pass through the origin is unlearnable (circle: chance).",
              f"VBP bp 0 DC {bp:.6f}", f"VBM bm 0 DC {bm:.6f}"]

    L += ["", "* ---- trainable weights (gate voltages) ----"]
    for l, (n_in, n_out) in enumerate(layers):
        for nm in layer_thetas(l, n_in, n_out, bias):
            L.append(f"{nm} g_{nm} 0 DC {theta[nm]:.6f}")

    L += ["", "* ---- trainable per-layer gain (diff-pair tail bias) ----"]
    for l in range(len(layers)):
        tn = tail_name(l)
        L.append(f"{tn} g_{tn} 0 DC {float(theta.get(tn, vtail)):.6f}")

    for l, (n_in, n_out) in enumerate(layers):
        L += ["", f"* ===== layer {l}: {n_in} -> {n_out} (four-quadrant) ====="]
        for j in range(1, n_out + 1):
            cp, cn = colp(l, j), coln(l, j)
            L.append(f"* column pair {cp}/{cn}: {n_in} four-quadrant synapses"
                     + (" + bias row" if bias else ""))
            for i in range((0 if bias else 1), n_in + 1):
                ga, gb = theta_a(l, i, j), theta_b(l, i, j)
                rp, rm = row_p(l, i), row_m(l, i)
                L.append(f"M{ga}P {cp} g_{ga} {rp} 0 NCH L={SYN_L} W={SYN_W}")
                L.append(f"M{gb}P {cp} g_{gb} {rm} 0 NCH L={SYN_L} W={SYN_W}")
                L.append(f"M{gb}N {cn} g_{gb} {rp} 0 NCH L={SYN_L} W={SYN_W}")
                L.append(f"M{ga}N {cn} g_{ga} {rm} 0 NCH L={SYN_L} W={SYN_W}")
            L.append(f"RLP{l}_{j} vdd {cp} {load_rs[l]}")
            L.append(f"RLN{l}_{j} vdd {cn} {load_rs[l]}")
            L.append(f"CCP{l}_{j} {cp} 0 {cap}")
            L.append(f"CCN{l}_{j} {cn} 0 {cap}")

            # neuron: tail-biased differential pair. BOTH drains are kept and
            # become the next layer's row pair -- throwing one away is what
            # forced the data back onto a common mode in the 2T build.
            op, om = out_node(l, j), outn_node(l, j)
            tl = f"t{l}_{j}"
            L.append(f"MDP{l}_{j} {om} {cp} {tl} 0 NCH L={DP_L} W={DP_W}")
            L.append(f"MDN{l}_{j} {op} {cn} {tl} 0 NCH L={DP_L} W={DP_W}")
            L.append(f"RDP{l}_{j} vdd {om} {rd}")
            L.append(f"RDN{l}_{j} vdd {op} {rd}")
            L.append(f"MT{l}_{j} {tl} g_{tail_name(l)} 0 0 NCH "
                     f"L={TAIL_L} W={TAIL_W}")
            L.append(f"COP{l}_{j} {op} 0 {cap}")
            L.append(f"COM{l}_{j} {om} 0 {cap}")
            L.append("")

    seeds = []
    for l, (_, n_out) in enumerate(layers):
        for j in range(1, n_out + 1):
            seeds += [f"V({colp(l, j)})={ic:.4f}", f"V({coln(l, j)})={ic:.4f}",
                      f"V({out_node(l, j)})={ic:.4f}",
                      f"V({outn_node(l, j)})={ic:.4f}"]
    L += ["* neutral solver seed; the data is in the input sources",
          ".IC " + " ".join(seeds), "", f".TRAN {tstep} {tstop}", "", ".END"]

    with open(path, "w") as f:
        f.write("\n".join(L))
    return n_devices(layers, bias)


if __name__ == "__main__":
    layers = [(4, 7), (7, 3)]
    th = {nm: 1.7 for nm in all_thetas(layers)}
    n = write_kfq_netlist(th, [0.5, -0.2, 0.9, -1.0], layers, "tmp_kfq_demo.sp")
    print(f"wrote tmp_kfq_demo.sp | layers={layers} | devices={n} "
          f"| params={len(all_thetas(layers))} | read={read_pairs(layers)}")
