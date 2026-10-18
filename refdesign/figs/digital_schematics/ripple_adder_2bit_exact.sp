* fixed-point datapath -- gate level
.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3

VI0 a0 0 DC 0.0000
VI1 a1 0 DC 0.0000
VI2 b0 0 DC 0.0000
VI3 b1 0 DC 0.0000

MNA1 s0_h_x1 a0 nx1 0 NCH L=0.35u W=2u
MNB1 nx1 b0 0 0 NCH L=0.35u W=2u
MPA1 s0_h_x1 a0 vdd vdd PCH L=0.35u W=5u
MPB1 s0_h_x1 b0 vdd vdd PCH L=0.35u W=5u
MNA2 s0_h_x2 a0 nx2 0 NCH L=0.35u W=2u
MNB2 nx2 s0_h_x1 0 0 NCH L=0.35u W=2u
MPA2 s0_h_x2 a0 vdd vdd PCH L=0.35u W=5u
MPB2 s0_h_x2 s0_h_x1 vdd vdd PCH L=0.35u W=5u
MNA3 s0_h_x3 b0 nx3 0 NCH L=0.35u W=2u
MNB3 nx3 s0_h_x1 0 0 NCH L=0.35u W=2u
MPA3 s0_h_x3 b0 vdd vdd PCH L=0.35u W=5u
MPB3 s0_h_x3 s0_h_x1 vdd vdd PCH L=0.35u W=5u
MNA4 s0_h s0_h_x2 nx4 0 NCH L=0.35u W=2u
MNB4 nx4 s0_h_x3 0 0 NCH L=0.35u W=2u
MPA4 s0_h s0_h_x2 vdd vdd PCH L=0.35u W=5u
MPB4 s0_h s0_h_x3 vdd vdd PCH L=0.35u W=5u
MNA5 s0_x1 s0_h nx5 0 NCH L=0.35u W=2u
MNB5 nx5 0 0 0 NCH L=0.35u W=2u
MPA5 s0_x1 s0_h vdd vdd PCH L=0.35u W=5u
MPB5 s0_x1 0 vdd vdd PCH L=0.35u W=5u
MNA6 s0_x2 s0_h nx6 0 NCH L=0.35u W=2u
MNB6 nx6 s0_x1 0 0 NCH L=0.35u W=2u
MPA6 s0_x2 s0_h vdd vdd PCH L=0.35u W=5u
MPB6 s0_x2 s0_x1 vdd vdd PCH L=0.35u W=5u
MNA7 s0_x3 0 nx7 0 NCH L=0.35u W=2u
MNB7 nx7 s0_x1 0 0 NCH L=0.35u W=2u
MPA7 s0_x3 0 vdd vdd PCH L=0.35u W=5u
MPB7 s0_x3 s0_x1 vdd vdd PCH L=0.35u W=5u
MNA8 s0 s0_x2 nx8 0 NCH L=0.35u W=2u
MNB8 nx8 s0_x3 0 0 NCH L=0.35u W=2u
MPA8 s0 s0_x2 vdd vdd PCH L=0.35u W=5u
MPB8 s0 s0_x3 vdd vdd PCH L=0.35u W=5u
MNA9 ra_c0_n1 a0 nx9 0 NCH L=0.35u W=2u
MNB9 nx9 b0 0 0 NCH L=0.35u W=2u
MPA9 ra_c0_n1 a0 vdd vdd PCH L=0.35u W=5u
MPB9 ra_c0_n1 b0 vdd vdd PCH L=0.35u W=5u
MNA10 ra_c0_n2 s0_h nx10 0 NCH L=0.35u W=2u
MNB10 nx10 0 0 0 NCH L=0.35u W=2u
MPA10 ra_c0_n2 s0_h vdd vdd PCH L=0.35u W=5u
MPB10 ra_c0_n2 0 vdd vdd PCH L=0.35u W=5u
MNA11 ra_c0 ra_c0_n1 nx11 0 NCH L=0.35u W=2u
MNB11 nx11 ra_c0_n2 0 0 NCH L=0.35u W=2u
MPA11 ra_c0 ra_c0_n1 vdd vdd PCH L=0.35u W=5u
MPB11 ra_c0 ra_c0_n2 vdd vdd PCH L=0.35u W=5u
MNA12 s1_h_x1 a1 nx12 0 NCH L=0.35u W=2u
MNB12 nx12 b1 0 0 NCH L=0.35u W=2u
MPA12 s1_h_x1 a1 vdd vdd PCH L=0.35u W=5u
MPB12 s1_h_x1 b1 vdd vdd PCH L=0.35u W=5u
MNA13 s1_h_x2 a1 nx13 0 NCH L=0.35u W=2u
MNB13 nx13 s1_h_x1 0 0 NCH L=0.35u W=2u
MPA13 s1_h_x2 a1 vdd vdd PCH L=0.35u W=5u
MPB13 s1_h_x2 s1_h_x1 vdd vdd PCH L=0.35u W=5u
MNA14 s1_h_x3 b1 nx14 0 NCH L=0.35u W=2u
MNB14 nx14 s1_h_x1 0 0 NCH L=0.35u W=2u
MPA14 s1_h_x3 b1 vdd vdd PCH L=0.35u W=5u
MPB14 s1_h_x3 s1_h_x1 vdd vdd PCH L=0.35u W=5u
MNA15 s1_h s1_h_x2 nx15 0 NCH L=0.35u W=2u
MNB15 nx15 s1_h_x3 0 0 NCH L=0.35u W=2u
MPA15 s1_h s1_h_x2 vdd vdd PCH L=0.35u W=5u
MPB15 s1_h s1_h_x3 vdd vdd PCH L=0.35u W=5u
MNA16 s1_x1 s1_h nx16 0 NCH L=0.35u W=2u
MNB16 nx16 ra_c0 0 0 NCH L=0.35u W=2u
MPA16 s1_x1 s1_h vdd vdd PCH L=0.35u W=5u
MPB16 s1_x1 ra_c0 vdd vdd PCH L=0.35u W=5u
MNA17 s1_x2 s1_h nx17 0 NCH L=0.35u W=2u
MNB17 nx17 s1_x1 0 0 NCH L=0.35u W=2u
MPA17 s1_x2 s1_h vdd vdd PCH L=0.35u W=5u
MPB17 s1_x2 s1_x1 vdd vdd PCH L=0.35u W=5u
MNA18 s1_x3 ra_c0 nx18 0 NCH L=0.35u W=2u
MNB18 nx18 s1_x1 0 0 NCH L=0.35u W=2u
MPA18 s1_x3 ra_c0 vdd vdd PCH L=0.35u W=5u
MPB18 s1_x3 s1_x1 vdd vdd PCH L=0.35u W=5u
MNA19 s1 s1_x2 nx19 0 NCH L=0.35u W=2u
MNB19 nx19 s1_x3 0 0 NCH L=0.35u W=2u
MPA19 s1 s1_x2 vdd vdd PCH L=0.35u W=5u
MPB19 s1 s1_x3 vdd vdd PCH L=0.35u W=5u
MNA20 ra_c1_n1 a1 nx20 0 NCH L=0.35u W=2u
MNB20 nx20 b1 0 0 NCH L=0.35u W=2u
MPA20 ra_c1_n1 a1 vdd vdd PCH L=0.35u W=5u
MPB20 ra_c1_n1 b1 vdd vdd PCH L=0.35u W=5u
MNA21 ra_c1_n2 s1_h nx21 0 NCH L=0.35u W=2u
MNB21 nx21 ra_c0 0 0 NCH L=0.35u W=2u
MPA21 ra_c1_n2 s1_h vdd vdd PCH L=0.35u W=5u
MPB21 ra_c1_n2 ra_c0 vdd vdd PCH L=0.35u W=5u
MNA22 ra_c1 ra_c1_n1 nx22 0 NCH L=0.35u W=2u
MNB22 nx22 ra_c1_n2 0 0 NCH L=0.35u W=2u
MPA22 ra_c1 ra_c1_n1 vdd vdd PCH L=0.35u W=5u
MPB22 ra_c1 ra_c1_n2 vdd vdd PCH L=0.35u W=5u

.OP
.END
