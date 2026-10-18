"""
xbar1t1r_netlist.py -- a 1T1R resistive crossbar layer, written from the architecture.

THE ARRAY
---------
One logical weight is a PAIR of 1T1R cells feeding a column pair:

    row i  --[ select NMOS ]--[ G+ ]--> column +
    row i  --[ select NMOS ]--[ G- ]--> column -

    column+ - column-  =  -Rf * sum_i (G+_ij - G-_ij) * (v_i - vref)

A conductance is a physically positive quantity, so a signed weight needs two of them.
That differential pair is universal in this literature: it gives the full signed range,
cancels common-mode drift to first order because both cells age together, and puts a
robust zero anywhere in the window at G+ = G-.

WHY THE SELECT TRANSISTOR
-------------------------
A bare resistor array (1R) has sneak paths: current from a driven row reaches a column
through unselected cells, so the column sums contributions it was never supposed to see
and the MVM is wrong by an amount that depends on the whole array state. The standard
fix is one series select device per cell -- 1T1R -- so an unselected row contributes
nothing. This simulator has no switch primitive (only R/L/C/D/M/V/I/G/E/F/H), which is
not a limitation here: a 1T1R selector *is* a transistor.

The select device is not free, and that is realistic. In triode it adds a series
resistance of roughly 1/(KP*(W/L)*(Vgs-Vt)) in series with the cell -- about 150 ohm at
the sizing below against a 10k cell at full conductance. That error is state-dependent
and is one of the real accuracy limits of 1T1R arrays, so it is left in rather than
sized away.

THE READOUT
-----------
Each column is held at `vref` by a transimpedance amplifier -- a real 5-transistor OTA
plus a feedback resistor. Holding the column fixed is what makes the currents sum
linearly; let it float and every cell sees a different voltage and the array stops
computing a dot product. An ideal VCVS version exists for closed-form checking only and
is never used for a reported number, because an ideal amplifier draws no current and
would hand the array a free readout.

WHERE THE LAYER ENDS
--------------------
At the column outputs. There is no analog neuron in this design. A crossbar accelerator
digitizes at the column (ADC), does the activation in the digital domain, and converts
back to drive the next tile (DAC) -- so the layer boundary is a conversion, not a
transistor. Keeping the activation digital is both what the architecture does and what
makes it exact.
"""

import numpy as np

# ------------------------------------------------------------------ technology --
VDD = 3.3
NCH = ".MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7"
PCH = ".MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7"

SEL_L, SEL_W = "1u", "20u"        # select device: wide, so its series R is small
OTA_L, OTA_W = "1u", "8u"         # OTA NMOS input pair
OTA_PL, OTA_PW = "1u", "16u"      # OTA PMOS mirror
OUT_PW = "160u"                   # 2nd stage PMOS common source (10x the mirror)
OUT_NW = "40u"                    # 2nd stage NMOS current sink
IDEAL_GAIN = 1e5

VREF_DEFAULT = 1.0                # column bias; NMOS input pair needs ~1 V to work
VWL_ON = VDD                      # word line asserted
VWL_OFF = 0.0
V_READ = 0.3                      # read swing on a row, about vref


# ----------------------------------------------------------------------- names --
def row_node(i):
    return f"r{i}"


def wl_node(i):
    return f"wl{i}"


def colp(j):
    return f"cp{j}"


def coln(j):
    return f"cn{j}"


def outp(j):
    return f"op{j}"


def outn(j):
    return f"on{j}"


def read_pairs(n_out):
    """Where the ADC sits: one differential pair per output column."""
    return [(outp(j), outn(j)) for j in range(1, n_out + 1)]


def read_nodes(n_out):
    return [nd for pr in read_pairs(n_out) for nd in pr]


def n_devices(n_in, n_out, ideal_tia=False):
    """Transistors + resistors in one layer.

    Per weight: 2 select transistors + 2 cell resistors.
    Per column pair: 2 TIAs (5 devices each, or 1 ideal) + 2 feedback resistors.
    """
    tia = 1 if ideal_tia else 7
    return n_in * n_out * 4 + n_out * (2 * tia + 2)


def encode_rows(x, vref=VREF_DEFAULT, v_read=V_READ):
    """Feature vector in [-1, 1] -> row voltages.

    A read voltage is deliberately small. Large row voltages would disturb the cells
    they are reading, which is the read/write distinction the device relies on.
    """
    return vref + v_read * np.clip(np.asarray(x, dtype=float), -1.0, 1.0)


# --------------------------------------------------------------------- the OTA --
def _ota(L, tag, out, inp, inn, vbias, tail):
    """5-transistor OTA: NMOS input pair, PMOS mirror load, NMOS tail.

    Finite gain is the point -- this holds the column only approximately at vref and it
    burns real current, both of which a crossbar has to pay for in silicon.
    """
    m = f"{tag}_m"
    L.append(f"MP{tag}1 {m} {m} vdd vdd PCH L={OTA_PL} W={OTA_PW}")
    L.append(f"MP{tag}2 {out} {m} vdd vdd PCH L={OTA_PL} W={OTA_PW}")
    L.append(f"MN{tag}1 {m} {inp} {tail} 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MN{tag}2 {out} {inn} {tail} 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MT{tag} {tail} {vbias} 0 0 NCH L={OTA_L} W={OTA_W}")


def _opamp2(L, tag, out, inp, inn, vbias, tail):
    """Two-stage op amp: the 5T OTA above, then a PMOS common-source stage.

    WHY TWO STAGES. A TIA must drive its own feedback resistor, and the column it holds
    is a LOW impedance node -- every cell on it is a 10k..1M path to a row driver, so a
    17-row column looks like ~600 ohm. The 5T OTA on its own is a transconductor with
    ~1.4 Mohm output resistance; loaded by Rf + column (~2.6 k) its gain falls to
    gm * 2.6k ~ 0.5, far below the noise gain 1 + Rf * sum(G) ~ 3 it has to beat. It
    was measured in exactly that state: the column wandered 25-135 mV off vref, the
    output barely moved, and the column difference came out with the WRONG SIGN
    (circuit/ideal gain -0.3 .. -4.5) because the output was just following the cells.

    The second stage supplies the drive: gm2 * (ro || load) ~ 4 on top of the first
    stage's ~260 unloaded, i.e. loop gain ~10^3 and a closed-loop error of ~0.3%.

    POLARITY. The common-source stage inverts, so the first stage must be
    non-inverting from the column: the column goes on the mirror-DIODE side gate and
    vref on the output side. Overall the column -> output path is then inverting and
    the Rf loop is negative feedback.
    """
    m, o1 = f"{tag}_m", f"{tag}_o1"
    L.append(f"MP{tag}1 {m} {m} vdd vdd PCH L={OTA_PL} W={OTA_PW}")
    L.append(f"MP{tag}2 {o1} {m} vdd vdd PCH L={OTA_PL} W={OTA_PW}")
    L.append(f"MN{tag}1 {m} {inn} {tail} 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MN{tag}2 {o1} {inp} {tail} 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MT{tag} {tail} {vbias} 0 0 NCH L={OTA_L} W={OTA_W}")
    L.append(f"MP{tag}3 {out} {o1} vdd vdd PCH L={OTA_PL} W={OUT_PW}")
    L.append(f"MN{tag}3 {out} {vbias} 0 0 NCH L={OTA_L} W={OUT_NW}")


# ------------------------------------------------------------------- the layer --
def write_layer(gp, gm, xs, path, rf=2e3, vref=VREF_DEFAULT, v_read=V_READ,
                wl_mask=None, ideal_tia=False, vota=0.8, cap="10f"):
    """Emit one crossbar layer as a SPICE deck.

    gp, gm  : (n_in, n_out) conductance arrays in siemens, G+ and G-
    xs      : (n_in,) features in [-1, 1]
    rf      : transimpedance feedback resistance (ohms)
    wl_mask : optional (n_in,) of 0/1 -- which word lines are asserted. Default all on,
              which is the parallel read every crossbar does. Used by the sneak-path
              check to deselect a row.
    ideal_tia : VCVS instead of the OTA. Closed-form verification ONLY.

    Returns the device count.
    """
    gp = np.asarray(gp, dtype=float)
    gm = np.asarray(gm, dtype=float)
    n_in, n_out = gp.shape
    if gm.shape != (n_in, n_out):
        raise ValueError(f"gp {gp.shape} and gm {gm.shape} disagree")
    if len(xs) != n_in:
        raise ValueError(f"{len(xs)} features for {n_in} rows")
    wl = np.ones(n_in) if wl_mask is None else np.asarray(wl_mask)

    v_rows = encode_rows(xs, vref, v_read)
    nd = n_devices(n_in, n_out, ideal_tia)

    L = [
        "* 1T1R RESISTIVE CROSSBAR LAYER -- auto-generated",
        f"* {n_in} rows x {n_out} column pairs | {nd} devices | "
        f"{2 * n_in * n_out} cells",
        "* One weight = two 1T1R cells into a column pair:",
        "*     col+ - col-  =  -Rf * sum_i (G+ - G-) * (v_i - vref)",
        "* Each cell is a select NMOS in series with the programmed resistor, so an",
        "* unselected row contributes no sneak current.",
        f"* readout: {'IDEAL VCVS (verification only)' if ideal_tia else '2-stage op amp'}",
        "", NCH, PCH, "",
        f"V0 vdd 0 DC {VDD}",
        f"VREF vref 0 DC {vref:.6f}",
    ]
    if not ideal_tia:
        L.append(f"VOTA g_vota 0 DC {vota:.6f}")

    L += ["", f"* ---- row drivers (the DACs): vref {vref} V +- {v_read} V ----"]
    for i in range(1, n_in + 1):
        L.append(f"VR{i} {row_node(i)} 0 DC {v_rows[i - 1]:.6f}")

    L += ["", "* ---- word lines: asserted rows take part in the read ----"]
    for i in range(1, n_in + 1):
        v = VWL_ON if wl[i - 1] else VWL_OFF
        L.append(f"VWL{i} {wl_node(i)} 0 DC {v:.6f}")

    L += ["", "* ---- the array: 2 cells per weight, 1T1R each ----"]
    for j in range(1, n_out + 1):
        L.append(f"* column pair {colp(j)}/{coln(j)}")
        for i in range(1, n_in + 1):
            rp = 1.0 / max(gp[i - 1, j - 1], 1e-15)
            rm = 1.0 / max(gm[i - 1, j - 1], 1e-15)
            # G+ cell -> column +
            L.append(f"MSP{i}_{j} {row_node(i)} {wl_node(i)} np{i}_{j} 0 "
                     f"NCH L={SEL_L} W={SEL_W}")
            L.append(f"RCP{i}_{j} np{i}_{j} {colp(j)} {rp:.6e}")
            # G- cell -> column -
            L.append(f"MSN{i}_{j} {row_node(i)} {wl_node(i)} nm{i}_{j} 0 "
                     f"NCH L={SEL_L} W={SEL_W}")
            L.append(f"RCN{i}_{j} nm{i}_{j} {coln(j)} {rm:.6e}")

        # transimpedance readout, one per column of the pair
        if ideal_tia:
            L.append(f"ETP{j} {outp(j)} 0 vref {colp(j)} {IDEAL_GAIN:.1f}")
            L.append(f"ETN{j} {outn(j)} 0 vref {coln(j)} {IDEAL_GAIN:.1f}")
        else:
            _opamp2(L, f"P{j}", outp(j), "vref", colp(j), "g_vota", f"sp{j}")
            _opamp2(L, f"N{j}", outn(j), "vref", coln(j), "g_vota", f"sn{j}")
        L.append(f"RFP{j} {outp(j)} {colp(j)} {rf:.6e}")
        L.append(f"RFN{j} {outn(j)} {coln(j)} {rf:.6e}")
        L.append(f"CP{j} {colp(j)} 0 {cap}")
        L.append(f"CN{j} {coln(j)} 0 {cap}")
        L.append("")

    seeds = []
    for j in range(1, n_out + 1):
        seeds += [f"V({colp(j)})={vref:.4f}", f"V({coln(j)})={vref:.4f}",
                  f"V({outp(j)})={vref:.4f}", f"V({outn(j)})={vref:.4f}"]
    L += ["* solver seed; the data is in the row drivers",
          ".IC " + " ".join(seeds), "", ".OP", "", ".END"]

    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return nd


def closed_form(gp, gm, xs, rf=2e3, v_read=V_READ):
    """What an ideal array would produce: -Rf * sum_i (G+ - G-) * (v_i - vref).

    (v_i - vref) is exactly v_read * x_i by construction, so vref drops out.
    """
    dv = v_read * np.clip(np.asarray(xs, dtype=float), -1.0, 1.0)
    return -rf * ((np.asarray(gp) - np.asarray(gm)).T @ dv)


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n_in, n_out = 4, 3
    gp = rng.uniform(1e-6, 1e-4, (n_in, n_out))
    gm = rng.uniform(1e-6, 1e-4, (n_in, n_out))
    xs = rng.uniform(-1, 1, n_in)
    n = write_layer(gp, gm, xs, "demo_1t1r.sp")
    print(f"wrote demo_1t1r.sp | {n_in}x{n_out} | {n} devices | "
          f"read nodes {read_nodes(n_out)}")
    print(f"closed form: {np.array2string(closed_form(gp, gm, xs), precision=4)}")
