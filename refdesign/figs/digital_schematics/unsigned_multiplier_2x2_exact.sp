* fixed-point datapath -- gate level
.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3

VI0 a0 0 DC 0.0000
VI1 a1 0 DC 0.0000
VI2 b0 0 DC 0.0000
VI3 b1 0 DC 0.0000

MNA1 mul_pp0_0_nd a0 nx1 0 NCH L=0.35u W=2u
MNB1 nx1 b0 0 0 NCH L=0.35u W=2u
MPA1 mul_pp0_0_nd a0 vdd vdd PCH L=0.35u W=5u
MPB1 mul_pp0_0_nd b0 vdd vdd PCH L=0.35u W=5u
MN2 mul_pp0_0 mul_pp0_0_nd 0 0 NCH L=0.35u W=2u
MP2 mul_pp0_0 mul_pp0_0_nd vdd vdd PCH L=0.35u W=5u
MNA3 mul_pp0_1_nd a1 nx3 0 NCH L=0.35u W=2u
MNB3 nx3 b0 0 0 NCH L=0.35u W=2u
MPA3 mul_pp0_1_nd a1 vdd vdd PCH L=0.35u W=5u
MPB3 mul_pp0_1_nd b0 vdd vdd PCH L=0.35u W=5u
MN4 mul_pp0_1 mul_pp0_1_nd 0 0 NCH L=0.35u W=2u
MP4 mul_pp0_1 mul_pp0_1_nd vdd vdd PCH L=0.35u W=5u
MNA5 mul_pp1_0_nd a0 nx5 0 NCH L=0.35u W=2u
MNB5 nx5 b1 0 0 NCH L=0.35u W=2u
MPA5 mul_pp1_0_nd a0 vdd vdd PCH L=0.35u W=5u
MPB5 mul_pp1_0_nd b1 vdd vdd PCH L=0.35u W=5u
MN6 mul_pp1_0 mul_pp1_0_nd 0 0 NCH L=0.35u W=2u
MP6 mul_pp1_0 mul_pp1_0_nd vdd vdd PCH L=0.35u W=5u
MNA7 mul_pp1_1_nd a1 nx7 0 NCH L=0.35u W=2u
MNB7 nx7 b1 0 0 NCH L=0.35u W=2u
MPA7 mul_pp1_1_nd a1 vdd vdd PCH L=0.35u W=5u
MPB7 mul_pp1_1_nd b1 vdd vdd PCH L=0.35u W=5u
MN8 mul_pp1_1 mul_pp1_1_nd 0 0 NCH L=0.35u W=2u
MP8 mul_pp1_1 mul_pp1_1_nd vdd vdd PCH L=0.35u W=5u
MNA9 mul_s1_0_h_x1 mul_pp0_1 nx9 0 NCH L=0.35u W=2u
MNB9 nx9 mul_pp1_0 0 0 NCH L=0.35u W=2u
MPA9 mul_s1_0_h_x1 mul_pp0_1 vdd vdd PCH L=0.35u W=5u
MPB9 mul_s1_0_h_x1 mul_pp1_0 vdd vdd PCH L=0.35u W=5u
MNA10 mul_s1_0_h_x2 mul_pp0_1 nx10 0 NCH L=0.35u W=2u
MNB10 nx10 mul_s1_0_h_x1 0 0 NCH L=0.35u W=2u
MPA10 mul_s1_0_h_x2 mul_pp0_1 vdd vdd PCH L=0.35u W=5u
MPB10 mul_s1_0_h_x2 mul_s1_0_h_x1 vdd vdd PCH L=0.35u W=5u
MNA11 mul_s1_0_h_x3 mul_pp1_0 nx11 0 NCH L=0.35u W=2u
MNB11 nx11 mul_s1_0_h_x1 0 0 NCH L=0.35u W=2u
MPA11 mul_s1_0_h_x3 mul_pp1_0 vdd vdd PCH L=0.35u W=5u
MPB11 mul_s1_0_h_x3 mul_s1_0_h_x1 vdd vdd PCH L=0.35u W=5u
MNA12 mul_s1_0_h mul_s1_0_h_x2 nx12 0 NCH L=0.35u W=2u
MNB12 nx12 mul_s1_0_h_x3 0 0 NCH L=0.35u W=2u
MPA12 mul_s1_0_h mul_s1_0_h_x2 vdd vdd PCH L=0.35u W=5u
MPB12 mul_s1_0_h mul_s1_0_h_x3 vdd vdd PCH L=0.35u W=5u
MNA13 mul_s1_0_x1 mul_s1_0_h nx13 0 NCH L=0.35u W=2u
MNB13 nx13 0 0 0 NCH L=0.35u W=2u
MPA13 mul_s1_0_x1 mul_s1_0_h vdd vdd PCH L=0.35u W=5u
MPB13 mul_s1_0_x1 0 vdd vdd PCH L=0.35u W=5u
MNA14 mul_s1_0_x2 mul_s1_0_h nx14 0 NCH L=0.35u W=2u
MNB14 nx14 mul_s1_0_x1 0 0 NCH L=0.35u W=2u
MPA14 mul_s1_0_x2 mul_s1_0_h vdd vdd PCH L=0.35u W=5u
MPB14 mul_s1_0_x2 mul_s1_0_x1 vdd vdd PCH L=0.35u W=5u
MNA15 mul_s1_0_x3 0 nx15 0 NCH L=0.35u W=2u
MNB15 nx15 mul_s1_0_x1 0 0 NCH L=0.35u W=2u
MPA15 mul_s1_0_x3 0 vdd vdd PCH L=0.35u W=5u
MPB15 mul_s1_0_x3 mul_s1_0_x1 vdd vdd PCH L=0.35u W=5u
MNA16 mul_s1_0 mul_s1_0_x2 nx16 0 NCH L=0.35u W=2u
MNB16 nx16 mul_s1_0_x3 0 0 NCH L=0.35u W=2u
MPA16 mul_s1_0 mul_s1_0_x2 vdd vdd PCH L=0.35u W=5u
MPB16 mul_s1_0 mul_s1_0_x3 vdd vdd PCH L=0.35u W=5u
MNA17 mul_c1_0_n1 mul_pp0_1 nx17 0 NCH L=0.35u W=2u
MNB17 nx17 mul_pp1_0 0 0 NCH L=0.35u W=2u
MPA17 mul_c1_0_n1 mul_pp0_1 vdd vdd PCH L=0.35u W=5u
MPB17 mul_c1_0_n1 mul_pp1_0 vdd vdd PCH L=0.35u W=5u
MNA18 mul_c1_0_n2 mul_s1_0_h nx18 0 NCH L=0.35u W=2u
MNB18 nx18 0 0 0 NCH L=0.35u W=2u
MPA18 mul_c1_0_n2 mul_s1_0_h vdd vdd PCH L=0.35u W=5u
MPB18 mul_c1_0_n2 0 vdd vdd PCH L=0.35u W=5u
MNA19 mul_c1_0 mul_c1_0_n1 nx19 0 NCH L=0.35u W=2u
MNB19 nx19 mul_c1_0_n2 0 0 NCH L=0.35u W=2u
MPA19 mul_c1_0 mul_c1_0_n1 vdd vdd PCH L=0.35u W=5u
MPB19 mul_c1_0 mul_c1_0_n2 vdd vdd PCH L=0.35u W=5u
MNA20 mul_s1_1_h_x1 0 nx20 0 NCH L=0.35u W=2u
MNB20 nx20 mul_pp1_1 0 0 NCH L=0.35u W=2u
MPA20 mul_s1_1_h_x1 0 vdd vdd PCH L=0.35u W=5u
MPB20 mul_s1_1_h_x1 mul_pp1_1 vdd vdd PCH L=0.35u W=5u
MNA21 mul_s1_1_h_x2 0 nx21 0 NCH L=0.35u W=2u
MNB21 nx21 mul_s1_1_h_x1 0 0 NCH L=0.35u W=2u
MPA21 mul_s1_1_h_x2 0 vdd vdd PCH L=0.35u W=5u
MPB21 mul_s1_1_h_x2 mul_s1_1_h_x1 vdd vdd PCH L=0.35u W=5u
MNA22 mul_s1_1_h_x3 mul_pp1_1 nx22 0 NCH L=0.35u W=2u
MNB22 nx22 mul_s1_1_h_x1 0 0 NCH L=0.35u W=2u
MPA22 mul_s1_1_h_x3 mul_pp1_1 vdd vdd PCH L=0.35u W=5u
MPB22 mul_s1_1_h_x3 mul_s1_1_h_x1 vdd vdd PCH L=0.35u W=5u
MNA23 mul_s1_1_h mul_s1_1_h_x2 nx23 0 NCH L=0.35u W=2u
MNB23 nx23 mul_s1_1_h_x3 0 0 NCH L=0.35u W=2u
MPA23 mul_s1_1_h mul_s1_1_h_x2 vdd vdd PCH L=0.35u W=5u
MPB23 mul_s1_1_h mul_s1_1_h_x3 vdd vdd PCH L=0.35u W=5u
MNA24 mul_s1_1_x1 mul_s1_1_h nx24 0 NCH L=0.35u W=2u
MNB24 nx24 mul_c1_0 0 0 NCH L=0.35u W=2u
MPA24 mul_s1_1_x1 mul_s1_1_h vdd vdd PCH L=0.35u W=5u
MPB24 mul_s1_1_x1 mul_c1_0 vdd vdd PCH L=0.35u W=5u
MNA25 mul_s1_1_x2 mul_s1_1_h nx25 0 NCH L=0.35u W=2u
MNB25 nx25 mul_s1_1_x1 0 0 NCH L=0.35u W=2u
MPA25 mul_s1_1_x2 mul_s1_1_h vdd vdd PCH L=0.35u W=5u
MPB25 mul_s1_1_x2 mul_s1_1_x1 vdd vdd PCH L=0.35u W=5u
MNA26 mul_s1_1_x3 mul_c1_0 nx26 0 NCH L=0.35u W=2u
MNB26 nx26 mul_s1_1_x1 0 0 NCH L=0.35u W=2u
MPA26 mul_s1_1_x3 mul_c1_0 vdd vdd PCH L=0.35u W=5u
MPB26 mul_s1_1_x3 mul_s1_1_x1 vdd vdd PCH L=0.35u W=5u
MNA27 mul_s1_1 mul_s1_1_x2 nx27 0 NCH L=0.35u W=2u
MNB27 nx27 mul_s1_1_x3 0 0 NCH L=0.35u W=2u
MPA27 mul_s1_1 mul_s1_1_x2 vdd vdd PCH L=0.35u W=5u
MPB27 mul_s1_1 mul_s1_1_x3 vdd vdd PCH L=0.35u W=5u
MNA28 mul_c1_1_n1 0 nx28 0 NCH L=0.35u W=2u
MNB28 nx28 mul_pp1_1 0 0 NCH L=0.35u W=2u
MPA28 mul_c1_1_n1 0 vdd vdd PCH L=0.35u W=5u
MPB28 mul_c1_1_n1 mul_pp1_1 vdd vdd PCH L=0.35u W=5u
MNA29 mul_c1_1_n2 mul_s1_1_h nx29 0 NCH L=0.35u W=2u
MNB29 nx29 mul_c1_0 0 0 NCH L=0.35u W=2u
MPA29 mul_c1_1_n2 mul_s1_1_h vdd vdd PCH L=0.35u W=5u
MPB29 mul_c1_1_n2 mul_c1_0 vdd vdd PCH L=0.35u W=5u
MNA30 mul_c1_1 mul_c1_1_n1 nx30 0 NCH L=0.35u W=2u
MNB30 nx30 mul_c1_1_n2 0 0 NCH L=0.35u W=2u
MPA30 mul_c1_1 mul_c1_1_n1 vdd vdd PCH L=0.35u W=5u
MPB30 mul_c1_1 mul_c1_1_n2 vdd vdd PCH L=0.35u W=5u

.OP
.END
