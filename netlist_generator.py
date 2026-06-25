"""
Generates netlists for the 4-block differential-amplifier ring.

Two separate analyses are used per training step:
  1. write_tran_netlist() -> .TRAN 100p 100n with IC on all 4 ring nodes
     Used to get V(output_node) at t=100ns (the forward-pass prediction).

  2. write_op_netlist() -> .OP (no IC)
     Used to get adjoint sensitivity dV(output_node)/dTheta_i at the DC
     operating point. This requires thetas < 1.7V so all 4 PMOS loads
     operate in the linear region and all 4 sensitivities are non-zero.

Trainable parameters (same in both netlists):
  V5 = theta1 (Block A PMOS gate bias)
  V4 = theta2 (Block B PMOS gate bias)
  V3 = theta3 (Block C PMOS gate bias)
  V2 = theta4 (Block D PMOS gate bias)
"""

import os

_VDD   = 3.3
_VBIAS = 2.7
_VN    = 1.0

_MOSFETS = """\
* === Block A (theta1): vp=net4, out=net6 ===
M1 net7  vn     net21 0   NCH L=650n W=6u
M0 net6  net4   net21 0   NCH L=650n W=6u
M5 net21 vbias  0     0   NCH L=1u   W=12u
M6 net7  theta1 vdd   vdd PCH L=2u   W=6u
M2 net6  theta1 vdd   vdd PCH L=2u   W=6u

* === Block B (theta2): vp=net6, out=net2 ===
M7 net8  vn     net22 0   NCH L=650n W=6u
M4 net2  net6   net22 0   NCH L=650n W=6u
M3 net22 vbias  0     0   NCH L=1u   W=12u
M8 net8  theta2 vdd   vdd PCH L=2u   W=6u
M9 net2  theta2 vdd   vdd PCH L=2u   W=6u

* === Block C (theta3): vp=net2, out=net3 ===
M12 net9  vn     net23 0   NCH L=650n W=6u
M13 net3  net2   net23 0   NCH L=650n W=6u
M14 net23 vbias  0     0   NCH L=1u   W=12u
M11 net9  theta3 vdd   vdd PCH L=2u   W=6u
M10 net3  theta3 vdd   vdd PCH L=2u   W=6u

* === Block D (theta4): vp=net3, out=net4 ===
M17 net5 vn     net1 0   NCH L=650n W=6u
M16 net4 net3   net1 0   NCH L=650n W=6u
M15 net1 vbias  0    0   NCH L=1u   W=12u
M18 net5 theta4 vdd  vdd PCH L=2u   W=6u
M19 net4 theta4 vdd  vdd PCH L=2u   W=6u

* Ring storage caps
C3 net4 0 1p
C2 net3 0 1p
C1 net2 0 1p
C0 net6 0 1p
"""

_HEADER = """\
* Auto-generated KirchhoffNet netlist -- do not edit by hand

.MODEL NCH NMOS (VTO=0.536 KP=170e-6)
.MODEL PCH PMOS (VTO=-0.717 KP=40e-6)

* Fixed supplies
V6 vn    0 DC {vn}
V1 vbias 0 DC {vbias}
V0 vdd   0 DC {vdd}

* Trainable theta voltage sources
V5 theta1 0 DC {t1}
V4 theta2 0 DC {t2}
V3 theta3 0 DC {t3}
V2 theta4 0 DC {t4}

"""


def _header(thetas):
    return _HEADER.format(
        vn=_VN, vbias=_VBIAS, vdd=_VDD,
        t1=thetas[0], t2=thetas[1], t3=thetas[2], t4=thetas[3],
    )


def write_tran_netlist(thetas, ic_dict, path):
    """Write TRAN netlist with IC-based input injection.

    Args:
        thetas  : [theta1, theta2, theta3, theta4] in Volts  (should be < 1.7V)
        ic_dict : {"net2": v, "net3": v, "net4": v, "net6": v}
        path    : output file path
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ic_line = (f".IC V(net2)={ic_dict['net2']} V(net3)={ic_dict['net3']}"
               f" V(net4)={ic_dict['net4']} V(net6)={ic_dict['net6']}")
    content = _header(thetas) + _MOSFETS + ic_line + "\n\n.TRAN 100p 100n\n\n.END\n"
    with open(path, "w") as f:
        f.write(content)


def write_op_netlist(thetas, path):
    """Write DC operating-point netlist (no IC).

    Requires thetas < 1.7V for all 4 sensitivities to be non-zero.

    Args:
        thetas : [theta1, theta2, theta3, theta4] in Volts
        path   : output file path
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    content = _header(thetas) + _MOSFETS + "\n.OP\n\n.END\n"
    with open(path, "w") as f:
        f.write(content)
