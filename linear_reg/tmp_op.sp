* KirchhoffNet OP netlist (sensitivity) — auto-generated

* MOSFET models (Level-1 Shichman-Hodges)
.MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

* Fixed supplies
V0  vdd  0  DC 3.3
V6  vn   0  DC 1.0

* Trainable tail-NMOS bias sources  [0.7 V, 3.0 V]
VB1 vbias1 0 DC 2.680920
VB2 vbias2 0 DC 2.701142
VB3 vbias3 0 DC 2.700000
VB4 vbias4 0 DC 2.700000

* Trainable PMOS-gate theta sources  [0.0 V, 3.0 V]
V5  theta1 0 DC 2.277403
V4  theta2 0 DC 1.209707
V3  theta3 0 DC 2.700000
V2  theta4 0 DC 2.000000

* Block A  (theta1 = V5, vbias1 = Vb1)
M1  net7  vn     net21  0    NCH L=650n W=6u
M0  net6  net4   net21  0    NCH L=650n W=6u
M5  net21 vbias1 0      0    NCH L=1u   W=12u
M6  net7  theta1 vdd    vdd  PCH L=2u   W=6u
M2  net6  theta1 vdd    vdd  PCH L=2u   W=6u

* Block B  (theta2 = V4, vbias2 = Vb2)
M7  net8  vn     net22  0    NCH L=650n W=6u
M4  net2  net6   net22  0    NCH L=650n W=6u
M3  net22 vbias2 0      0    NCH L=1u   W=12u
M8  net8  theta2 vdd    vdd  PCH L=2u   W=6u
M9  net2  theta2 vdd    vdd  PCH L=2u   W=6u

* Block C  (theta3 = V3, vbias3 = Vb3)
M12 net9  vn     net23  0    NCH L=650n W=6u
M13 net3  net2   net23  0    NCH L=650n W=6u
M14 net23 vbias3 0      0    NCH L=1u   W=12u
M11 net9  theta3 vdd    vdd  PCH L=2u   W=6u
M10 net3  theta3 vdd    vdd  PCH L=2u   W=6u

* Block D  (theta4 = V2, vbias4 = Vb4)
M17 net5  vn     net1   0    NCH L=650n W=6u
M16 net4  net3   net1   0    NCH L=650n W=6u
M15 net1  vbias4 0      0    NCH L=1u   W=12u
M18 net5  theta4 vdd    vdd  PCH L=2u   W=6u
M19 net4  theta4 vdd    vdd  PCH L=2u   W=6u

* 1 pF caps stabilise ring nodes and enable TRAN dynamics
C3 net4 0 1p
C2 net3 0 1p
C1 net2 0 1p
C0 net6 0 1p

* DC operating-point analysis (adjoint sensitivity enabled by simulator flag)
.OP

.END