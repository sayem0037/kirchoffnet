* fixed-point datapath -- gate level
.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3

VI0 a 0 DC 0.0000
VI1 b 0 DC 0.0000
VI2 cin 0 DC 0.0000

MNA1 s_h_x1 a nx1 0 NCH L=0.35u W=2u
MNB1 nx1 b 0 0 NCH L=0.35u W=2u
MPA1 s_h_x1 a vdd vdd PCH L=0.35u W=5u
MPB1 s_h_x1 b vdd vdd PCH L=0.35u W=5u
MNA2 s_h_x2 a nx2 0 NCH L=0.35u W=2u
MNB2 nx2 s_h_x1 0 0 NCH L=0.35u W=2u
MPA2 s_h_x2 a vdd vdd PCH L=0.35u W=5u
MPB2 s_h_x2 s_h_x1 vdd vdd PCH L=0.35u W=5u
MNA3 s_h_x3 b nx3 0 NCH L=0.35u W=2u
MNB3 nx3 s_h_x1 0 0 NCH L=0.35u W=2u
MPA3 s_h_x3 b vdd vdd PCH L=0.35u W=5u
MPB3 s_h_x3 s_h_x1 vdd vdd PCH L=0.35u W=5u
MNA4 s_h s_h_x2 nx4 0 NCH L=0.35u W=2u
MNB4 nx4 s_h_x3 0 0 NCH L=0.35u W=2u
MPA4 s_h s_h_x2 vdd vdd PCH L=0.35u W=5u
MPB4 s_h s_h_x3 vdd vdd PCH L=0.35u W=5u
MNA5 s_x1 s_h nx5 0 NCH L=0.35u W=2u
MNB5 nx5 cin 0 0 NCH L=0.35u W=2u
MPA5 s_x1 s_h vdd vdd PCH L=0.35u W=5u
MPB5 s_x1 cin vdd vdd PCH L=0.35u W=5u
MNA6 s_x2 s_h nx6 0 NCH L=0.35u W=2u
MNB6 nx6 s_x1 0 0 NCH L=0.35u W=2u
MPA6 s_x2 s_h vdd vdd PCH L=0.35u W=5u
MPB6 s_x2 s_x1 vdd vdd PCH L=0.35u W=5u
MNA7 s_x3 cin nx7 0 NCH L=0.35u W=2u
MNB7 nx7 s_x1 0 0 NCH L=0.35u W=2u
MPA7 s_x3 cin vdd vdd PCH L=0.35u W=5u
MPB7 s_x3 s_x1 vdd vdd PCH L=0.35u W=5u
MNA8 s s_x2 nx8 0 NCH L=0.35u W=2u
MNB8 nx8 s_x3 0 0 NCH L=0.35u W=2u
MPA8 s s_x2 vdd vdd PCH L=0.35u W=5u
MPB8 s s_x3 vdd vdd PCH L=0.35u W=5u
MNA9 cout_n1 a nx9 0 NCH L=0.35u W=2u
MNB9 nx9 b 0 0 NCH L=0.35u W=2u
MPA9 cout_n1 a vdd vdd PCH L=0.35u W=5u
MPB9 cout_n1 b vdd vdd PCH L=0.35u W=5u
MNA10 cout_n2 s_h nx10 0 NCH L=0.35u W=2u
MNB10 nx10 cin 0 0 NCH L=0.35u W=2u
MPA10 cout_n2 s_h vdd vdd PCH L=0.35u W=5u
MPB10 cout_n2 cin vdd vdd PCH L=0.35u W=5u
MNA11 cout cout_n1 nx11 0 NCH L=0.35u W=2u
MNB11 nx11 cout_n2 0 0 NCH L=0.35u W=2u
MPA11 cout cout_n1 vdd vdd PCH L=0.35u W=5u
MPB11 cout cout_n2 vdd vdd PCH L=0.35u W=5u

.OP
.END
