"""
xbar_netlist.py -- the analog prior-art arm: a differential resistive crossbar
with virtual-ground transimpedance readout. The ISAAC / PUMA lineage, built
from primitives this simulator already has.

WHY THIS EXACT TOPOLOGY
-----------------------
The comparison has to be controlled or it says nothing. If the crossbar had a
different input encoding, a different neuron and a different depth from KFQ,
then any difference in the results table would be unattributable. So this
netlist is KFQ with ONE thing changed:

    KFQ   : four NMOS per weight; summing happens because the transistors are
            current sources into a resistive load; the load resistor sets the
            column voltage directly.
    XBAR  : four programmable CONDUCTANCES per weight; summing happens at a
            virtual ground held by a transimpedance amplifier; the feedback
            resistor sets the output voltage.

Everything else -- differential rows about a common mode, the four-quadrant
cross-connection, the bias row, the tail-biased differential-pair neuron whose
two drains feed the next layer, the model cards, VDD, the readout convention --
is identical to kfabric/netlist_kfq.py, imported from it where possible.

THE CELL
--------
Row pair (v+, v-) carries x_i as dv = v+ - v-. Four conductances per weight:

        c+  <-  G_a from v+   and   G_b from v-
        c-  <-  G_b from v+   and   G_a from v-

Both columns are held at vref by their TIA, so the current into c+ is
sum_i [G_a(v+ - vref) + G_b(v- - vref)] and the TIA output is
vref - Rf * I_in. The column difference is therefore

    V(t+) - V(t-) = -Rf * sum_i (G_a,ij - G_b,ij) * (v+_i - v-_i)

exactly -- a pure product of a signed weight with a signed signal, with vref
and the common mode cancelling identically. That closed form is Gate A.

WHY CONDUCTANCES ARE THE TRAINABLE PARAMETER, AND WHY THAT WORKS HERE
---------------------------------------------------------------------
components/resistor.py exposes an exact adjoint dV/dR, the same mechanism that
makes KFQ's voltage sources trainable. So the crossbar can be trained in-situ
by the identical machinery, with one chain rule:

    dV/dG = dV/dR * dR/dG = -R^2 * dV/dR

That matters for the Convergence column: without it the two arms would be
trained by different algorithms and the convergence comparison would be
meaningless.

TWO READOUT MODES, AND WHY BOTH ARE REPORTED
--------------------------------------------
An ideal VCVS op-amp draws no current. Used as the TIA it would hand the
crossbar a free readout and flatter its energy column against KFQ, which pays
for its readout in real transistors. So the default is a 5-transistor OTA built
from the same NCH/PCH cards, and the ideal-VCVS version is kept only as the
closed-form reference for Gate A. The gap between them is itself a result: it
is the price of the readout that the crossbar architecture cannot avoid.

WHAT IS NOT IN THE NETLIST
--------------------------
Data converters. A real multi-layer crossbar digitizes at every layer boundary
and converts back; KFQ does not, and that is the architectural claim under
test. Simulating an ADC is out of scope, so converters are charged in the AREA
and ENERGY columns through metrics.area_um2(periphery=...) and tech.adc_energy
/ tech.dac_energy, counted per column per layer. They are a visible line item,
never folded silently into a total.
"""

import importlib.util
import os

BASE = os.path.dirname(os.path.abspath(__file__))
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")


def _load(name, path):
    """Load a module by explicit path instead of putting its directory on
    sys.path. kfabric/ carries its own simulator_api.py, and adding that
    directory to the search path silently shadows this package's version --
    which is the one with run_metered in it. Import by path, shadow nothing.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_kfq = _load("_netlist_kfq", os.path.join(KFABRIC, "netlist_kfq.py"))

# Reuse, do not re-declare: the two arms must share these or the comparison is
# not controlled.
VDD = _kfq.VDD
NCH, PCH = _kfq.NCH, _kfq.PCH
DP_L, DP_W = _kfq.DP_L, _kfq.DP_W
TAIL_L, TAIL_W = _kfq.TAIL_L, _kfq.TAIL_W
encode = _kfq.encode

# OTA devices, sized off the same family as the KFQ neuron.
OTA_L, OTA_W = "1u", "8u"
OTA_PL, OTA_PW = "1u", "16u"      # PMOS mirror load: wider, lower KP
IDEAL_GAIN = 1e5                  # VCVS gain in ideal-TIA mode

# Conductance window. A 100:1 on/off ratio is the conventional figure for a
# multi-level resistive device; both ends are parameters so the sweep can move
# them.
R_ON_DEFAULT = 10e3               # ohm  -> Gmax = 100 uS
R_OFF_DEFAULT = 1e6               # ohm  -> Gmin = 1 uS


# ---------------------------------------------------------------- names ----
def g_a(l, i, j):
    """First half of a signed weight. The leading 'R' is REQUIRED: in SPICE the
    first letter of a component name declares its type."""
    return f"RA{l}_{i}_{j}"


def g_b(l, i, j):
    return f"RB{l}_{i}_{j}"


def tail_name(l):
    return f"VT{l}"


def row_p(l, i):
    """Layer 0 reads the data sources; deeper layers read the previous
    neuron's two drains, so the stack is differential end to end."""
    if l == 0:
        return "bp" if i == 0 else f"xp{i}"
    return "bp" if i == 0 else f"op{l - 1}_{i}"


def row_m(l, i):
    if l == 0:
        return "bm" if i == 0 else f"xm{i}"
    return "bm" if i == 0 else f"om{l - 1}_{i}"


def colp(l, j):
    return f"cp{l}_{j}"


def coln(l, j):
    return f"cn{l}_{j}"


def tiap(l, j):
    return f"tp{l}_{j}"


def tian(l, j):
    return f"tn{l}_{j}"


def out_node(l, j):
    return f"op{l}_{j}"


def outn_node(l, j):
    return f"om{l}_{j}"


# --------------------------------------------------------------- params ----
def layer_params(l, n_in, n_out, bias=True):
    out = []
    for j in range(1, n_out + 1):
        for i in range((0 if bias else 1), n_in + 1):
            out += [g_a(l, i, j), g_b(l, i, j)]
    return out


def all_params(layers, bias=True):
    """Every trainable conductance, in netlist order."""
    out = []
    for l, (n_in, n_out) in enumerate(layers):
        out += layer_params(l, n_in, n_out, bias)
    return out


def all_tails(layers):
    return [tail_name(l) for l in range(len(layers))]


def instances(param):
    """Netlist device names carrying one logical conductance.

    The four-quadrant cross-connection uses each conductance TWICE -- G_a
    appears from v+ into c+ and from v- into c- -- so one trainable parameter
    is two netlist resistors that must be programmed together. Any gradient
    with respect to the logical conductance is therefore the SUM over these
    instances, and any write must touch both.
    """
    return (f"{param}P", f"{param}N")


def all_instances(layers, bias=True):
    return [nm for p in all_params(layers, bias) for nm in instances(p)]


def n_devices(layers, bias=True, ideal_tia=False):
    """Device count, on the same accounting as netlist_kfq.n_devices.

    Per weight: 4 conductances. Per column pair: 2 TIAs, 2 feedback resistors,
    2 differential-pair devices, 2 drain resistors, 1 tail. A TIA is 1 device
    ideal, 5 as an OTA.
    """
    b = 1 if bias else 0
    tia = 1 if ideal_tia else 5
    return sum(4 * (n_in + b) * n_out + n_out * (2 * tia + 2 + 3 + 2)
               for n_in, n_out in layers)


def read_pairs(layers):
    """Class scores are the LAST layer's TIA output differences. No trained
    read-out: argmax over V(t+_j) - V(t-_j) is the prediction, matching the KFQ
    convention exactly."""
    l = len(layers) - 1
    return [(tiap(l, j), tian(l, j)) for j in range(1, layers[l][1] + 1)]


def read_nodes(layers):
    return [nd for pair in read_pairs(layers) for nd in pair]


# ------------------------------------------------------ weight <-> conductance
def w_to_g(w, r_on=R_ON_DEFAULT, r_off=R_OFF_DEFAULT, levels=None):
    """Map a signed weight in [-1, 1] onto a conductance pair (G_a, G_b).

    The standard differential mapping: one side carries the magnitude, the
    other sits at Gmin, so both stay inside the physical window and their
    difference is proportional to w. `levels` quantizes the programmed
    conductance to N discrete states, which is what a real device gives you and
    what the precision sweep varies.
    """
    g_min, g_max = 1.0 / r_off, 1.0 / r_on
    span = g_max - g_min

    mag = min(1.0, abs(float(w)))
    if levels is not None and levels > 1:
        mag = round(mag * (levels - 1)) / (levels - 1)

    hi = g_min + mag * span
    return (hi, g_min) if w >= 0 else (g_min, hi)


def g_to_r(g):
    return 1.0 / max(g, 1e-15)


def weights_to_res(weights, layers, bias=True, r_on=R_ON_DEFAULT,
                   r_off=R_OFF_DEFAULT, levels=None):
    """{param_name: resistance} for a list of per-layer weight matrices.

    weights[l] has shape (n_in + bias, n_out): row 0 is the bias row when
    `bias` is set.
    """
    res = {}
    for l, (n_in, n_out) in enumerate(layers):
        w = weights[l]
        for j in range(1, n_out + 1):
            for i in range((0 if bias else 1), n_in + 1):
                ga, gb = w_to_g(w[i if bias else i - 1][j - 1],
                                r_on, r_off, levels)
                res[g_a(l, i, j)] = g_to_r(ga)
                res[g_b(l, i, j)] = g_to_r(gb)
    return res


# -------------------------------------------------------------- netlist ----
def _ota(L, name, out, inp, inn, vbias_node, tail):
    """A 5-transistor OTA: NMOS differential pair, PMOS mirror load, NMOS tail.

    Finite gain is the point. Unlike an ideal VCVS this holds the column only
    approximately at vref, and it burns real current -- both of which the
    crossbar architecture has to pay in silicon and must therefore pay here.
    """
    n1 = f"{name}_m"
    L.append(f"MP{name}1 {n1} {n1} vdd vdd PCH L={OTA_PL} W={OTA_PW}")
    L.append(f"MP{name}2 {out} {n1} vdd vdd PCH L={OTA_PL} W={OTA_PW}")
    L.append(f"MN{name}1 {n1} {inp} {tail} 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MN{name}2 {out} {inn} {tail} 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MT{name} {tail} {vbias_node} 0 0 NCH L={TAIL_L} W={TAIL_W}")


def write_xbar_netlist(res, xs, layers, path, cap="0.1f",
                       tstep="50n", tstop="100n", ic=1.0,
                       rf="2.5k", rd="200k", vtail=0.85, vref=1.0,
                       vcm=1.0, swing=0.4, bias=True, ideal_tia=False,
                       vota=0.9):
    """
    res    : {RA.../RB...: ohms}  the programmed conductances
    xs     : n_in0 values in [-1, 1]  (the data point)
    layers : [(n_in, n_out), ...]
    rf     : TIA feedback resistance -- one value, or ONE PER LAYER. Like KFQ's
             load_r this must scale with fan-in: the column current is a sum of
             n_in terms, so the value that gives a healthy output swing at
             fan-in 8 saturates at fan-in 64. Use xbar_spec.size_layer().
    ideal_tia : VCVS op-amp instead of the 5T OTA. For Gate A and for the
             readout-cost ablation only -- never for a reported energy number.

    Returns the device count.
    """
    def _per_layer(v, what):
        if isinstance(v, (list, tuple)):
            if len(v) != len(layers):
                raise ValueError(f"{what} has {len(v)} entries for "
                                 f"{len(layers)} layers")
            return list(v)
        return [v] * len(layers)

    rfs = _per_layer(rf, "rf")
    # rd is per layer too. It sets the neuron drain common mode as
    # VDD - rd*Id, which IS the next layer's row common mode and therefore the
    # next layer's amplifier input common mode. At rd = 200k the drains sat at
    # 0.27 V -- below an NMOS input pair's turn-on -- so the following TIAs
    # were dead and the column degenerated into a passive resistive load.
    rds = _per_layer(rd, "rd")
    # vref is PER LAYER and must track that layer's row common mode.
    #
    # It is tempting to park every TIA at mid-supply. That is wrong and it cost
    # a debugging round: the four-quadrant cell cancels the common mode in the
    # column DIFFERENCE, but each individual TIA still sinks the common-mode
    # current sum_i G_i * (v_row_i - vref). With rows at 1.0 V and vref at
    # 1.65 V that is ~0.65 V across every conductance in the column, which at
    # fan-in 5 and Rf = 26k drives the amplifier output past 8 V. Both TIAs
    # rail, and a railed amplifier has no incremental gain, so the difference
    # -- the thing that was supposed to be immune -- collapses to zero. The
    # sizing loop read that as "swing too small", raised Rf further, and ran
    # itself into the floor.
    #
    # Setting vref to the row common mode zeroes that current by construction,
    # which is also how a real crossbar is biased. Layer 0 knows its rows sit
    # at vcm; deeper layers read the previous neuron's drains, whose common
    # mode xbar_spec.solve_vref() measures.
    vrefs = _per_layer(vref, "vref")

    n_in0 = layers[0][0]
    nd = n_devices(layers, bias, ideal_tia)
    L = [
        "* DIFFERENTIAL RESISTIVE CROSSBAR (XBAR) -- auto-generated",
        f"* layers {layers} | {nd} devices | "
        f"{len(all_params(layers, bias))} programmable conductances",
        "* Analog prior art (ISAAC / PUMA lineage), built as KFQ with the",
        "* four NMOS synapses replaced by four conductances and the resistive",
        "* load replaced by a virtual-ground transimpedance amplifier:",
        "*     V(t+) - V(t-) = -Rf * sum_i (G_a - G_b)(v+ - v-)",
        f"* readout: {'IDEAL VCVS (Gate A only)' if ideal_tia else '5T OTA'}",
        "* Data converters are NOT in this netlist; they are charged in the",
        "* area and energy columns through tech.adc_energy / tech.dac_energy.",
        "", NCH, PCH, "", f"V0 vdd 0 DC {VDD}",
    ] + [f"VREF{l} vref{l} 0 DC {vrefs[l]:.6f}" for l in range(len(layers))] + [
        "",
        f"* ---- data: differential rows about vcm={vcm} V, swing={swing} V ----",
    ]
    for i in range(1, n_in0 + 1):
        vp, vm = encode(float(xs[i - 1]), vcm, swing)
        L.append(f"VIP{i} xp{i} 0 DC {vp:.6f}")
        L.append(f"VIM{i} xm{i} 0 DC {vm:.6f}")

    if bias:
        bp, bm = encode(1.0, vcm, swing)
        L += ["", "* fixed differential reference = the BIAS row. The column",
              "* difference is an odd function of the data without it, so any",
              "* boundary not through the origin is unlearnable.",
              f"VBP bp 0 DC {bp:.6f}", f"VBM bm 0 DC {bm:.6f}"]

    if not ideal_tia:
        L += ["", "* OTA tail bias", f"VOTA g_vota 0 DC {vota:.6f}"]

    L += ["", "* ---- neuron tail bias (per layer) ----"]
    for l in range(len(layers)):
        L.append(f"{tail_name(l)} g_{tail_name(l)} 0 DC {float(vtail):.6f}")

    for l, (n_in, n_out) in enumerate(layers):
        L += ["", f"* ===== layer {l}: {n_in} -> {n_out} (crossbar) ====="]
        for j in range(1, n_out + 1):
            cp, cn = colp(l, j), coln(l, j)
            L.append(f"* column pair {cp}/{cn}: {n_in} four-quadrant cells"
                     + (" + bias row" if bias else ""))
            for i in range((0 if bias else 1), n_in + 1):
                ra, rb = g_a(l, i, j), g_b(l, i, j)
                rp, rm = row_p(l, i), row_m(l, i)
                L.append(f"{ra}P {rp} {cp} {res[ra]:.6e}")
                L.append(f"{rb}P {rm} {cp} {res[rb]:.6e}")
                L.append(f"{rb}N {rp} {cn} {res[rb]:.6e}")
                L.append(f"{ra}N {rm} {cn} {res[ra]:.6e}")

            tp, tn = tiap(l, j), tian(l, j)
            if ideal_tia:
                L.append(f"ETP{l}_{j} {tp} 0 vref{l} {cp} {IDEAL_GAIN:.1f}")
                L.append(f"ETN{l}_{j} {tn} 0 vref{l} {cn} {IDEAL_GAIN:.1f}")
            else:
                _ota(L, f"P{l}_{j}", tp, f"vref{l}", cp, "g_vota", f"sp{l}_{j}")
                _ota(L, f"N{l}_{j}", tn, f"vref{l}", cn, "g_vota", f"sn{l}_{j}")
            L.append(f"RFP{l}_{j} {tp} {cp} {rfs[l]}")
            L.append(f"RFN{l}_{j} {tn} {cn} {rfs[l]}")
            L.append(f"CCP{l}_{j} {cp} 0 {cap}")
            L.append(f"CCN{l}_{j} {cn} 0 {cap}")

            # neuron: the same tail-biased differential pair KFQ uses, so the
            # nonlinearity is not a confound between the two arms.
            op, om = out_node(l, j), outn_node(l, j)
            tl = f"nt{l}_{j}"
            L.append(f"MDP{l}_{j} {om} {tp} {tl} 0 NCH L={DP_L} W={DP_W}")
            L.append(f"MDN{l}_{j} {op} {tn} {tl} 0 NCH L={DP_L} W={DP_W}")
            L.append(f"RDP{l}_{j} vdd {om} {rds[l]}")
            L.append(f"RDN{l}_{j} vdd {op} {rds[l]}")
            L.append(f"MT{l}_{j} {tl} g_{tail_name(l)} 0 0 NCH "
                     f"L={TAIL_L} W={TAIL_W}")
            L.append(f"COP{l}_{j} {op} 0 {cap}")
            L.append(f"COM{l}_{j} {om} 0 {cap}")
            L.append("")

    seeds = []
    for l, (_, n_out) in enumerate(layers):
        for j in range(1, n_out + 1):
            seeds += [f"V({colp(l, j)})={vrefs[l]:.4f}",
                      f"V({coln(l, j)})={vrefs[l]:.4f}",
                      f"V({tiap(l, j)})={vrefs[l]:.4f}",
                      f"V({tian(l, j)})={vrefs[l]:.4f}",
                      f"V({out_node(l, j)})={ic:.4f}",
                      f"V({outn_node(l, j)})={ic:.4f}"]
    L += ["* neutral solver seed; the data is in the input sources",
          ".IC " + " ".join(seeds), "", f".TRAN {tstep} {tstop}", "", ".END"]

    with open(path, "w") as f:
        f.write("\n".join(L))
    return nd


ADC_SHARE = 128      # columns per ADC instance (ISAAC: one 8-bit ADC at
                     # 1.2 GHz time-multiplexed across 128 bitlines)
DAC_SHARE = 1        # rows are driven concurrently, so one driver per row


def converter_counts(layers, adc_share=ADC_SHARE, dac_share=DAC_SHARE):
    """Data converters, counted TWICE because area and energy need different
    numbers and conflating them is a real error.

    CONVERSIONS per inference -- what ENERGY is charged for. Every column's
    analog result must be digitized, so this is one conversion per column per
    layer regardless of how the hardware is organised.

    INSTANCES -- what AREA is charged for. ADCs are NOT one-per-column in any
    real design. An 8-bit ADC is roughly 12x the area of a 128x128 crossbar
    array, so the standard architecture time-multiplexes ONE ADC across 128
    bitlines within the array's read window (ISAAC, ISCA 2016; PUMA follows the
    same scheme, and later work such as FORMS only raises it to one ADC per 32
    columns for iso-area studies).

    Charging one ADC instance per column, as the first version of this function
    did, overstated the crossbar's area by 160,000 um^2 on iris -- 45% of its
    reported total, and enough to change the headline comparison. It made the
    baseline look far worse than the architecture it is supposed to represent.
    """
    n_dac_conv = sum(n_in for n_in, _ in layers)
    n_adc_conv = sum(n_out for _, n_out in layers)
    # ceil-divide per layer: a layer with 7 columns still needs one ADC.
    n_adc_inst = sum(-(-n_out // adc_share) for _, n_out in layers)
    n_dac_inst = sum(-(-n_in // dac_share) for n_in, _ in layers)
    return dict(dac=n_dac_conv, adc=n_adc_conv,
                adc_instances=n_adc_inst, dac_instances=n_dac_inst,
                adc_share=adc_share)


if __name__ == "__main__":
    import numpy as np

    layers = [(4, 7), (7, 3)]
    rng = np.random.default_rng(0)
    w = [rng.normal(0, 0.5, (n_in + 1, n_out)) for n_in, n_out in layers]
    res = weights_to_res(w, layers)
    n = write_xbar_netlist(res, [0.5, -0.2, 0.9, -1.0], layers,
                           "tmp_xbar_demo.sp")
    print(f"wrote tmp_xbar_demo.sp | layers={layers} | devices={n} "
          f"| conductances={len(all_params(layers))} "
          f"| read={read_pairs(layers)} | conv={converter_counts(layers)}")
