"""
kfq_spec.py -- solve each layer's operating point instead of sharing one.

WHY A SOLVER AND NOT A SWEEP
----------------------------
The MNIST network passed every single-layer gate and still sat at chance. Gate 6
found why: about half of layer 1's devices were CUT OFF, and the four-quadrant
cancellation

    I(c+) - I(c-) = -k (theta_a - theta_b)(v+ - v-)

holds only while all four devices of a cell are in saturation. Cut one off and
the cancellation breaks, so the common-mode term it was there to remove comes
back as a per-column constant. Measured at the output: a fixed offset of
0.085 V against 0.0018 V of data-dependent signal -- a ratio of 48, and the
network predicts one class for every input (train 0.100, loss 2.5567 against
ln 10 = 2.3026).

The cutoff came from sharing ONE thbar and one load_r rule across layers whose
rows sit at different common modes with different swings. Layer 0's rows are
data sources the designer places; layer 1's rows are the previous neuron's
drains, whose common mode and swing the circuit chooses.

THE CONSTRAINTS, PER LAYER
    conduction   theta_l > max(row voltage) + VTO
                 the binding row is CM_l + swing_l/2, not CM_l
    saturation   V(col_l) = VDD - load_r_l * I_col > theta_l - VTO
    current      I_col ~ 2 (n_in+1) * 1/2 k * (overdrive)^2
                 overdrive averages margin + swing/2 across the row swing

These fight: raising theta for conduction headroom raises the overdrive, which
raises I_col QUADRATICALLY, which drops V(col) and breaks saturation. The
resistor that satisfies both is

    load_r_l  <  (VDD - theta_l + VTO) / I_col

taken at a fraction `headroom` of the bound. That is why the naive rule
load_r1 = load_r0 * n_in0/n_in1 was wrong: it assumes equal margins, and the
margins are not equal once the common modes differ.

The row common mode and swing of layer l>0 are properties of the previous
stage, so the whole thing is solved by iteration against the circuit rather
than in closed form.
"""

from netlist_kfq import VDD, VTO_N

KP_N = 120e-6
SYN_WL = 4.0            # synapse W/L, matching SYN_W/SYN_L in netlist_kfq
K_SYN = KP_N * SYN_WL   # 480 uA/V^2


def col_current(n_in, overdrive, bias_row=True):
    """Total DC current into one column half.

    Each of the (n_in + bias) rows contributes TWO devices to each column half
    (one gated by theta_a, one by theta_b), each carrying 1/2 k Vov^2 in
    saturation.
    """
    rows = n_in + (1 if bias_row else 0)
    return 2.0 * rows * 0.5 * K_SYN * overdrive ** 2


def size_layer(n_in, row_cm, row_swing, margin=0.30, headroom=0.65,
               bias_row=True):
    """Choose (theta_bar, load_r) for one layer.

    margin   conduction headroom at the WORST row (the highest one). Must
             exceed 0 with room to spare; the row swing is already accounted
             for separately, so this is pure margin.
    headroom fraction of the saturation-limited resistor to actually use.
    """
    v_hi = row_cm + 0.5 * row_swing          # the binding row for conduction
    thbar = v_hi + VTO_N + margin

    # Overdrive seen by a typical device, averaged over the row swing:
    # theta - v - VTO ranges from `margin` (highest row) to margin + swing.
    overdrive = margin + 0.5 * row_swing
    i_col = col_current(n_in, overdrive, bias_row)

    v_col_min = thbar - VTO_N                # saturation floor
    budget = VDD - v_col_min                 # volts available across the load
    if budget <= 0 or i_col <= 0:
        return None
    load_r = headroom * budget / i_col
    return dict(thbar=thbar, load_r=load_r, i_col=i_col,
                v_col=VDD - load_r * i_col, v_col_min=v_col_min,
                overdrive=overdrive, margin=margin, row_cm=row_cm,
                row_swing=row_swing)


def fmt_r(r):
    """SPICE-safe resistor string. The parser has no atto suffix and reads a
    bare number as ohms, so plain ohms is the safe form."""
    return "%.4g" % max(r, 1.0)


def describe(spec, label=""):
    return ("%-8s thbar %.3f  load_r %8s  I_col %7.1f uA  "
            "V(col) %.3f (floor %.3f)  rows %.3f+-%.3f"
            % (label, spec["thbar"], fmt_r(spec["load_r"]),
               spec["i_col"] * 1e6, spec["v_col"], spec["v_col_min"],
               spec["row_cm"], spec["row_swing"] / 2))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="n_in", type=int, default=64)
    ap.add_argument("--hidden", type=int, default=16)
    ap.add_argument("--vcm", type=float, default=1.064)
    ap.add_argument("--swing", type=float, default=0.40)
    ap.add_argument("--hidden-cm", type=float, default=1.064)
    ap.add_argument("--hidden-swing", type=float, default=0.40)
    ap.add_argument("--margin", type=float, default=0.30)
    ap.add_argument("--headroom", type=float, default=0.65)
    a = ap.parse_args()

    print("per-layer sizing (the shared-thbar rule cut off ~50% of layer 1)\n")
    s0 = size_layer(a.n_in, a.vcm, a.swing, a.margin, a.headroom)
    s1 = size_layer(a.hidden, a.hidden_cm, a.hidden_swing, a.margin,
                    a.headroom)
    print(describe(s0, "layer 0"))
    print(describe(s1, "layer 1"))
    print("\nload_r = %s %s" % (fmt_r(s0["load_r"]), fmt_r(s1["load_r"])))
    print("thbar  = %.3f %.3f" % (s0["thbar"], s1["thbar"]))
    print("\nNote both layers get their OWN thbar. netlist_kfq already takes a")
    print("per-layer load_r; per-layer thbar is set by train_kfq --thbar-per-layer.")
