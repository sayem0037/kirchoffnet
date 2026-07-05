"""
netlist_writer.py
-----------------
Generates SPICE netlists compatible with the Python circuit simulator.

Two public functions:
  write_tran_netlist(params, ic_voltages, path)
      -> TRAN netlist: forward pass, reads V(net4) at 100 ns
  write_op_netlist(params, path)
      -> OP netlist: adjoint sensitivity, computes dV(net4)/d(param)

'params' is a dict with all 8 trainable source values:
  V5, V4, V3, V2   -> PMOS gate biases (thetas)
  Vb1, Vb2, Vb3, Vb4 -> tail NMOS gate biases (vbiases)
"""

# ── Fixed circuit constants (never change) ───────────────────
VDD = 3.3   # supply voltage in volts
VN  = 1.0   # reference voltage for differential-pair NMOS inputs


def _build_circuit_lines(params):
    """
    Returns a list of netlist lines for the shared circuit topology.
    Called by both write_tran_netlist and write_op_netlist.

    params: dict {V5, V4, V3, V2, Vb1, Vb2, Vb3, Vb4}
    """
    p = params   # short alias for readability
    return [
        # ── MOSFET device models ─────────────────────────────────
        "* MOSFET models (Level-1 Shichman-Hodges)",
        ".MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
        ".MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
        "",
        # ── Fixed supply voltages ────────────────────────────────
        "* Fixed supplies",
        f"V0  vdd  0  DC {VDD}",        # power supply rail
        f"V6  vn   0  DC {VN}",         # common reference for all NMOS diff pairs
        "",
        # ── Trainable vbias sources (tail NMOS bias, one per block) ─
        "* Trainable tail-NMOS bias sources  [0.7 V, 3.0 V]",
        f"VB1 vbias1 0 DC {p['VB1']:.6f}",   # Block A tail bias (uppercase: parser upcases names)
        f"VB2 vbias2 0 DC {p['VB2']:.6f}",   # Block B tail bias
        f"VB3 vbias3 0 DC {p['VB3']:.6f}",   # Block C tail bias
        f"VB4 vbias4 0 DC {p['VB4']:.6f}",   # Block D tail bias
        "",
        # ── Trainable theta sources (PMOS load gate bias, one per block) ─
        "* Trainable PMOS-gate theta sources  [0.0 V, 3.0 V]",
        f"V5  theta1 0 DC {p['V5']:.6f}",    # Block A theta
        f"V4  theta2 0 DC {p['V4']:.6f}",    # Block B theta
        f"V3  theta3 0 DC {p['V3']:.6f}",    # Block C theta
        f"V2  theta4 0 DC {p['V2']:.6f}",    # Block D theta
        "",
        # ── Block A: input = net4, output = net6 ─────────────────
        "* Block A  (theta1 = V5, vbias1 = Vb1)",
        "M1  net7  vn     net21  0    NCH L=650n W=6u",    # dummy branch NMOS
        "M0  net6  net4   net21  0    NCH L=650n W=6u",    # signal branch NMOS
        "M5  net21 vbias1 0      0    NCH L=1u   W=12u",   # tail current source (W=12u = 2x6u)
        "M6  net7  theta1 vdd    vdd  PCH L=2u   W=6u",    # dummy branch PMOS load
        "M2  net6  theta1 vdd    vdd  PCH L=2u   W=6u",    # signal branch PMOS load
        "",
        # ── Block B: input = net6, output = net2 ─────────────────
        "* Block B  (theta2 = V4, vbias2 = Vb2)",
        "M7  net8  vn     net22  0    NCH L=650n W=6u",
        "M4  net2  net6   net22  0    NCH L=650n W=6u",
        "M3  net22 vbias2 0      0    NCH L=1u   W=12u",
        "M8  net8  theta2 vdd    vdd  PCH L=2u   W=6u",
        "M9  net2  theta2 vdd    vdd  PCH L=2u   W=6u",
        "",
        # ── Block C: input = net2, output = net3 ─────────────────
        "* Block C  (theta3 = V3, vbias3 = Vb3)",
        "M12 net9  vn     net23  0    NCH L=650n W=6u",
        "M13 net3  net2   net23  0    NCH L=650n W=6u",
        "M14 net23 vbias3 0      0    NCH L=1u   W=12u",
        "M11 net9  theta3 vdd    vdd  PCH L=2u   W=6u",
        "M10 net3  theta3 vdd    vdd  PCH L=2u   W=6u",
        "",
        # ── Block D: input = net3, output = net4 ─────────────────
        "* Block D  (theta4 = V2, vbias4 = Vb4)",
        "M17 net5  vn     net1   0    NCH L=650n W=6u",
        "M16 net4  net3   net1   0    NCH L=650n W=6u",
        "M15 net1  vbias4 0      0    NCH L=1u   W=12u",
        "M18 net5  theta4 vdd    vdd  PCH L=2u   W=6u",
        "M19 net4  theta4 vdd    vdd  PCH L=2u   W=6u",
        "",
        # ── Storage capacitors (one per ring node) ───────────────
        "* 0.1 pF caps: tau = R*C ~ 100ns at vbias=0.8V; use tstop=10ns (0.1 tau) for all 8 params active",
        "C3 net4 0 0.1f",    # output node cap
        "C2 net3 0 0.1f",    # Block C output cap
        "C1 net2 0 0.1f",    # Block B output cap
        "C0 net6 0 0.1f",    # Block A output cap
    ]


def write_tran_netlist(params, ic_voltages, path, tstep="1n", tstop="100n"):
    """
    Write a transient-analysis netlist for the forward pass.

    params:      dict {V5, V4, V3, V2, Vb1-Vb4} -- current trainable values
    ic_voltages: dict {net4, net6, net2, net3}   -- input features as voltage ICs
    path:        file path to write (will be overwritten)
    tstep:       transient time step  (default 1 ns)
    tstop:       transient stop time  (default 100 ns)
    """
    ic = ic_voltages   # short alias

    # Build the .IC line: four ring nodes start at the scaled input-feature voltages
    ic_line = (
        f".IC "
        f"V(net4)={ic['net4']:.6f} "    # feature 1 (MedInc)   -> Block A input
        f"V(net6)={ic['net6']:.6f} "    # feature 2 (HouseAge) -> Block B input
        f"V(net2)={ic['net2']:.6f} "    # feature 3 (AveRooms) -> Block C input
        f"V(net3)={ic['net3']:.6f}"     # feature 4 (AveOccup) -> Block D input
    )

    lines = (
        ["* KirchhoffNet TRAN netlist (forward pass) — auto-generated", ""]
        + _build_circuit_lines(params)
        + [
            "",
            "* Input features encoded as ring-node starting voltages",
            ic_line,
            "",
            "* Run transient to 100 ns; V(net4) at final step is the prediction",
            f".TRAN {tstep} {tstop}",
            "",
            ".END",
        ]
    )

    with open(path, "w") as f:
        f.write("\n".join(lines))


def write_op_netlist(params, path):
    """
    Write a DC operating-point netlist for adjoint sensitivity computation.
    No .IC — the circuit solves for its own DC equilibrium.

    params: dict {V5, V4, V3, V2, Vb1-Vb4} -- current trainable values
    path:   file path to write (will be overwritten)
    """
    lines = (
        ["* KirchhoffNet OP netlist (sensitivity) — auto-generated", ""]
        + _build_circuit_lines(params)
        + [
            "",
            "* DC operating-point analysis (adjoint sensitivity enabled by simulator flag)",
            ".OP",
            "",
            ".END",
        ]
    )

    with open(path, "w") as f:
        f.write("\n".join(lines))
