* KirchhoffNet TRAN netlist (forward pass) -- auto-generated

* MOSFET models (Level-1 Shichman-Hodges)
.MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

* Fixed supplies
V0  vdd  0  DC 3.3
V6  vn   0  DC 1.0

* Trainable tail-NMOS bias sources
VB1 vbias1 0 DC 0.800000
VB2 vbias2 0 DC 0.800000
VB3 vbias3 0 DC 0.800000
VB4 vbias4 0 DC 0.800000

* Trainable PMOS-gate theta sources
V5  theta1 0 DC 1.658729
V4  theta2 0 DC 1.700000
V3  theta3 0 DC 1.700000
V2  theta4 0 DC 1.700000

* Block A  (theta1 = V5, vbias1 = VB1)   net4 -> net6
M1  net7  vn     net21  0    NCH L=650n W=6u
M0  net6  net4   net21  0    NCH L=650n W=6u
M5  net21 vbias1 0      0    NCH L=1u   W=12u
M6  net7  theta1 vdd    vdd  PCH L=2u   W=6u
M2  net6  theta1 vdd    vdd  PCH L=2u   W=6u

* Block B  (theta2 = V4, vbias2 = VB2)   net6 -> net2
M7  net8  vn     net22  0    NCH L=650n W=6u
M4  net2  net6   net22  0    NCH L=650n W=6u
M3  net22 vbias2 0      0    NCH L=1u   W=12u
M8  net8  theta2 vdd    vdd  PCH L=2u   W=6u
M9  net2  theta2 vdd    vdd  PCH L=2u   W=6u

* Block C  (theta3 = V3, vbias3 = VB3)   net2 -> net3
M12 net9  vn     net23  0    NCH L=650n W=6u
M13 net3  net2   net23  0    NCH L=650n W=6u
M14 net23 vbias3 0      0    NCH L=1u   W=12u
M11 net9  theta3 vdd    vdd  PCH L=2u   W=6u
M10 net3  theta3 vdd    vdd  PCH L=2u   W=6u

* Block D  (theta4 = V2, vbias4 = VB4)   net3 -> net4
M17 net5  vn     net1   0    NCH L=650n W=6u
M16 net4  net3   net1   0    NCH L=650n W=6u
M15 net1  vbias4 0      0    NCH L=1u   W=12u
M18 net5  theta4 vdd    vdd  PCH L=2u   W=6u
M19 net4  theta4 vdd    vdd  PCH L=2u   W=6u

* 0.1 pF caps: tau = R*C ~ 100ns at vbias=0.8V
C3 net4 0 0.1f
C2 net3 0 0.1f
C1 net2 0 0.1f
C0 net6 0 0.1f

* Input features encoded as ring-node starting voltages
.IC V(net4)=1.665663 V(net6)=0.500000 V(net2)=1.456235 V(net3)=0.780873

.TRAN 10n 1u

.END