* KirchhoffNet SPIDERNET crossbar -- auto-generated
* 4 rails x 4 state nodes = 16 theta-gated NMOS edges

* MOSFET model (Level-1 Shichman-Hodges; no body effect, no intrinsic C)
.MODEL NCH NMOS LEVEL=1 VTO=0.55 KP=170e-6

* Encoder-driven input rails (the data point)
VR1 v1 0 DC 0.692735
VR2 v2 0 DC 0.200000
VR3 v3 0 DC 1.371552
VR4 v4 0 DC 0.200000

* Trainable per-edge gate voltages (thetas)
VTH1 theta1 0 DC 2.475438
VTH2 theta2 0 DC 2.320737
VTH3 theta3 0 DC 2.784254
VTH4 theta4 0 DC 2.462940
VTH5 theta5 0 DC 2.078598
VTH6 theta6 0 DC 2.616957
VTH7 theta7 0 DC 3.182400
VTH8 theta8 0 DC 2.968249
VTH9 theta9 0 DC 1.977759
VTH10 theta10 0 DC 1.900000
VTH11 theta11 0 DC 2.026035
VTH12 theta12 0 DC 2.424796
VTH13 theta13 0 DC 1.900000
VTH14 theta14 0 DC 2.268725
VTH15 theta15 0 DC 1.900000
VTH16 theta16 0 DC 1.960640

* state node net1: fed by every rail through its own theta
M1_1 v1 theta1 net1 0 NCH L=350n W=2u
M2_1 v2 theta2 net1 0 NCH L=350n W=2u
M3_1 v3 theta3 net1 0 NCH L=350n W=2u
M4_1 v4 theta4 net1 0 NCH L=350n W=2u
C1 net1 0 0.1f

* state node net2: fed by every rail through its own theta
M1_2 v1 theta5 net2 0 NCH L=350n W=2u
M2_2 v2 theta6 net2 0 NCH L=350n W=2u
M3_2 v3 theta7 net2 0 NCH L=350n W=2u
M4_2 v4 theta8 net2 0 NCH L=350n W=2u
C2 net2 0 0.1f

* state node net3: fed by every rail through its own theta
M1_3 v1 theta9 net3 0 NCH L=350n W=2u
M2_3 v2 theta10 net3 0 NCH L=350n W=2u
M3_3 v3 theta11 net3 0 NCH L=350n W=2u
M4_3 v4 theta12 net3 0 NCH L=350n W=2u
C3 net3 0 0.1f

* state node net4: fed by every rail through its own theta
M1_4 v1 theta13 net4 0 NCH L=350n W=2u
M2_4 v2 theta14 net4 0 NCH L=350n W=2u
M3_4 v3 theta15 net4 0 NCH L=350n W=2u
M4_4 v4 theta16 net4 0 NCH L=350n W=2u
C4 net4 0 0.1f

* neutral solver seed (state is settled by tstop; data is in the rails)
.IC V(net1)=1.0000 V(net2)=1.0000 V(net3)=1.0000 V(net4)=1.0000

.TRAN 10n 100n

.END