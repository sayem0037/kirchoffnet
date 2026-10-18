* KirchhoffNet WIDE parallel diff-amp layer (per-unit trainable refs) -- auto-generated

* MOSFET models (Level-1 Shichman-Hodges)
.MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

* Fixed supply
V0  vdd 0 DC 3.3

* Encoder-driven per-unit inputs
VIN1 in1 0 DC 1.650000
VIN2 in2 0 DC 1.650000
VIN3 in3 0 DC 1.650000
VIN4 in4 0 DC 1.650000
VIN5 in5 0 DC 1.650000
VIN6 in6 0 DC 1.650000
VIN7 in7 0 DC 1.650000
VIN8 in8 0 DC 1.650000
VIN9 in9 0 DC 1.650000
VIN10 in10 0 DC 1.650000
VIN11 in11 0 DC 1.650000
VIN12 in12 0 DC 1.650000

* Trainable PMOS-load thetas
VTH1 th1 0 DC 1.700000
VTH2 th2 0 DC 1.700000
VTH3 th3 0 DC 1.700000
VTH4 th4 0 DC 1.700000
VTH5 th5 0 DC 1.700000
VTH6 th6 0 DC 1.700000
VTH7 th7 0 DC 1.700000
VTH8 th8 0 DC 1.700000
VTH9 th9 0 DC 1.700000
VTH10 th10 0 DC 1.700000
VTH11 th11 0 DC 1.700000
VTH12 th12 0 DC 1.700000

* Trainable tail biases
VB1 vb1 0 DC 0.800000
VB2 vb2 0 DC 0.800000
VB3 vb3 0 DC 0.800000
VB4 vb4 0 DC 0.800000
VB5 vb5 0 DC 0.800000
VB6 vb6 0 DC 0.800000
VB7 vb7 0 DC 0.800000
VB8 vb8 0 DC 0.800000
VB9 vb9 0 DC 0.800000
VB10 vb10 0 DC 0.800000
VB11 vb11 0 DC 0.800000
VB12 vb12 0 DC 0.800000

* Trainable per-unit reference voltages
VN1 vn1 0 DC 1.000000
VN2 vn2 0 DC 1.000000
VN3 vn3 0 DC 1.000000
VN4 vn4 0 DC 1.000000
VN5 vn5 0 DC 1.000000
VN6 vn6 0 DC 1.000000
VN7 vn7 0 DC 1.000000
VN8 vn8 0 DC 1.000000
VN9 vn9 0 DC 1.000000
VN10 vn10 0 DC 1.000000
VN11 vn11 0 DC 1.000000
VN12 vn12 0 DC 1.000000

* unit 1: signal=in1 ref=vn1 out=u1
Md1  d1  vn1  t1  0    NCH L=650n W=6u
Ms1  u1  in1  t1  0    NCH L=650n W=6u
Mt1  t1  vb1  0     0    NCH L=1u   W=12u
Mpd1 d1  th1  vdd   vdd  PCH L=2u   W=6u
Mps1 u1  th1  vdd   vdd  PCH L=2u   W=6u
C1   u1  0      0.1f

* unit 2: signal=in2 ref=vn2 out=u2
Md2  d2  vn2  t2  0    NCH L=650n W=6u
Ms2  u2  in2  t2  0    NCH L=650n W=6u
Mt2  t2  vb2  0     0    NCH L=1u   W=12u
Mpd2 d2  th2  vdd   vdd  PCH L=2u   W=6u
Mps2 u2  th2  vdd   vdd  PCH L=2u   W=6u
C2   u2  0      0.1f

* unit 3: signal=in3 ref=vn3 out=u3
Md3  d3  vn3  t3  0    NCH L=650n W=6u
Ms3  u3  in3  t3  0    NCH L=650n W=6u
Mt3  t3  vb3  0     0    NCH L=1u   W=12u
Mpd3 d3  th3  vdd   vdd  PCH L=2u   W=6u
Mps3 u3  th3  vdd   vdd  PCH L=2u   W=6u
C3   u3  0      0.1f

* unit 4: signal=in4 ref=vn4 out=u4
Md4  d4  vn4  t4  0    NCH L=650n W=6u
Ms4  u4  in4  t4  0    NCH L=650n W=6u
Mt4  t4  vb4  0     0    NCH L=1u   W=12u
Mpd4 d4  th4  vdd   vdd  PCH L=2u   W=6u
Mps4 u4  th4  vdd   vdd  PCH L=2u   W=6u
C4   u4  0      0.1f

* unit 5: signal=in5 ref=vn5 out=u5
Md5  d5  vn5  t5  0    NCH L=650n W=6u
Ms5  u5  in5  t5  0    NCH L=650n W=6u
Mt5  t5  vb5  0     0    NCH L=1u   W=12u
Mpd5 d5  th5  vdd   vdd  PCH L=2u   W=6u
Mps5 u5  th5  vdd   vdd  PCH L=2u   W=6u
C5   u5  0      0.1f

* unit 6: signal=in6 ref=vn6 out=u6
Md6  d6  vn6  t6  0    NCH L=650n W=6u
Ms6  u6  in6  t6  0    NCH L=650n W=6u
Mt6  t6  vb6  0     0    NCH L=1u   W=12u
Mpd6 d6  th6  vdd   vdd  PCH L=2u   W=6u
Mps6 u6  th6  vdd   vdd  PCH L=2u   W=6u
C6   u6  0      0.1f

* unit 7: signal=in7 ref=vn7 out=u7
Md7  d7  vn7  t7  0    NCH L=650n W=6u
Ms7  u7  in7  t7  0    NCH L=650n W=6u
Mt7  t7  vb7  0     0    NCH L=1u   W=12u
Mpd7 d7  th7  vdd   vdd  PCH L=2u   W=6u
Mps7 u7  th7  vdd   vdd  PCH L=2u   W=6u
C7   u7  0      0.1f

* unit 8: signal=in8 ref=vn8 out=u8
Md8  d8  vn8  t8  0    NCH L=650n W=6u
Ms8  u8  in8  t8  0    NCH L=650n W=6u
Mt8  t8  vb8  0     0    NCH L=1u   W=12u
Mpd8 d8  th8  vdd   vdd  PCH L=2u   W=6u
Mps8 u8  th8  vdd   vdd  PCH L=2u   W=6u
C8   u8  0      0.1f

* unit 9: signal=in9 ref=vn9 out=u9
Md9  d9  vn9  t9  0    NCH L=650n W=6u
Ms9  u9  in9  t9  0    NCH L=650n W=6u
Mt9  t9  vb9  0     0    NCH L=1u   W=12u
Mpd9 d9  th9  vdd   vdd  PCH L=2u   W=6u
Mps9 u9  th9  vdd   vdd  PCH L=2u   W=6u
C9   u9  0      0.1f

* unit 10: signal=in10 ref=vn10 out=u10
Md10  d10  vn10  t10  0    NCH L=650n W=6u
Ms10  u10  in10  t10  0    NCH L=650n W=6u
Mt10  t10  vb10  0     0    NCH L=1u   W=12u
Mpd10 d10  th10  vdd   vdd  PCH L=2u   W=6u
Mps10 u10  th10  vdd   vdd  PCH L=2u   W=6u
C10   u10  0      0.1f

* unit 11: signal=in11 ref=vn11 out=u11
Md11  d11  vn11  t11  0    NCH L=650n W=6u
Ms11  u11  in11  t11  0    NCH L=650n W=6u
Mt11  t11  vb11  0     0    NCH L=1u   W=12u
Mpd11 d11  th11  vdd   vdd  PCH L=2u   W=6u
Mps11 u11  th11  vdd   vdd  PCH L=2u   W=6u
C11   u11  0      0.1f

* unit 12: signal=in12 ref=vn12 out=u12
Md12  d12  vn12  t12  0    NCH L=650n W=6u
Ms12  u12  in12  t12  0    NCH L=650n W=6u
Mt12  t12  vb12  0     0    NCH L=1u   W=12u
Mpd12 d12  th12  vdd   vdd  PCH L=2u   W=6u
Mps12 u12  th12  vdd   vdd  PCH L=2u   W=6u
C12   u12  0      0.1f

* seed transient from a neutral state; read u_j at tstop
.IC V(u1)=1.6500 V(u2)=1.6500 V(u3)=1.6500 V(u4)=1.6500 V(u5)=1.6500 V(u6)=1.6500 V(u7)=1.6500 V(u8)=1.6500 V(u9)=1.6500 V(u10)=1.6500 V(u11)=1.6500 V(u12)=1.6500

.TRAN 10n 100n

.END