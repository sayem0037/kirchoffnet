* KirchhoffNet CLOSED-LOOP series diff-amp ring -- auto-generated

* MOSFET models (Level-1 Shichman-Hodges)
.MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

* Fixed supply
V0  vdd 0 DC 3.3

* Trainable PMOS-load thetas
VTH1 th1 0 DC 1.700783
VTH2 th2 0 DC 1.700985
VTH3 th3 0 DC 1.698329
VTH4 th4 0 DC 1.697512
VTH5 th5 0 DC 1.705195
VTH6 th6 0 DC 1.705460
VTH7 th7 0 DC 1.698270
VTH8 th8 0 DC 1.698749
VTH9 th9 0 DC 1.705479
VTH10 th10 0 DC 1.700562

* Trainable tail biases
VB1 vb1 0 DC 0.800441
VB2 vb2 0 DC 0.805093
VB3 vb3 0 DC 0.798073
VB4 vb4 0 DC 0.797819
VB5 vb5 0 DC 0.803440
VB6 vb6 0 DC 0.805477
VB7 vb7 0 DC 0.796241
VB8 vb8 0 DC 0.801750
VB9 vb9 0 DC 0.805501
VB10 vb10 0 DC 0.803664

* Trainable per-stage reference voltages
VN1 vn1 0 DC 0.996385
VN2 vn2 0 DC 1.005253
VN3 vn3 0 DC 0.995581
VN4 vn4 0 DC 1.004072
VN5 vn5 0 DC 0.996227
VN6 vn6 0 DC 1.005284
VN7 vn7 0 DC 0.995243
VN8 vn8 0 DC 1.004757
VN9 vn9 0 DC 0.996293
VN10 vn10 0 DC 1.005126

* stage 1: signal=h10 ref=vn1 out=h1
Md1  dm1  vn1  tl1  0    NCH L=650n W=6u
Ms1  h1   h10   tl1  0    NCH L=650n W=6u
Mt1  tl1  vb1  0     0    NCH L=1u   W=12u
Mpd1 dm1  th1  vdd   vdd  PCH L=2u   W=6u
Mps1 h1   th1  vdd   vdd  PCH L=2u   W=6u
C1   h1   0      1p

* stage 2: signal=h1 ref=vn2 out=h2
Md2  dm2  vn2  tl2  0    NCH L=650n W=6u
Ms2  h2   h1   tl2  0    NCH L=650n W=6u
Mt2  tl2  vb2  0     0    NCH L=1u   W=12u
Mpd2 dm2  th2  vdd   vdd  PCH L=2u   W=6u
Mps2 h2   th2  vdd   vdd  PCH L=2u   W=6u
C2   h2   0      1p

* stage 3: signal=h2 ref=vn3 out=h3
Md3  dm3  vn3  tl3  0    NCH L=650n W=6u
Ms3  h3   h2   tl3  0    NCH L=650n W=6u
Mt3  tl3  vb3  0     0    NCH L=1u   W=12u
Mpd3 dm3  th3  vdd   vdd  PCH L=2u   W=6u
Mps3 h3   th3  vdd   vdd  PCH L=2u   W=6u
C3   h3   0      1p

* stage 4: signal=h3 ref=vn4 out=h4
Md4  dm4  vn4  tl4  0    NCH L=650n W=6u
Ms4  h4   h3   tl4  0    NCH L=650n W=6u
Mt4  tl4  vb4  0     0    NCH L=1u   W=12u
Mpd4 dm4  th4  vdd   vdd  PCH L=2u   W=6u
Mps4 h4   th4  vdd   vdd  PCH L=2u   W=6u
C4   h4   0      1p

* stage 5: signal=h4 ref=vn5 out=h5
Md5  dm5  vn5  tl5  0    NCH L=650n W=6u
Ms5  h5   h4   tl5  0    NCH L=650n W=6u
Mt5  tl5  vb5  0     0    NCH L=1u   W=12u
Mpd5 dm5  th5  vdd   vdd  PCH L=2u   W=6u
Mps5 h5   th5  vdd   vdd  PCH L=2u   W=6u
C5   h5   0      1p

* stage 6: signal=h5 ref=vn6 out=h6
Md6  dm6  vn6  tl6  0    NCH L=650n W=6u
Ms6  h6   h5   tl6  0    NCH L=650n W=6u
Mt6  tl6  vb6  0     0    NCH L=1u   W=12u
Mpd6 dm6  th6  vdd   vdd  PCH L=2u   W=6u
Mps6 h6   th6  vdd   vdd  PCH L=2u   W=6u
C6   h6   0      1p

* stage 7: signal=h6 ref=vn7 out=h7
Md7  dm7  vn7  tl7  0    NCH L=650n W=6u
Ms7  h7   h6   tl7  0    NCH L=650n W=6u
Mt7  tl7  vb7  0     0    NCH L=1u   W=12u
Mpd7 dm7  th7  vdd   vdd  PCH L=2u   W=6u
Mps7 h7   th7  vdd   vdd  PCH L=2u   W=6u
C7   h7   0      1p

* stage 8: signal=h7 ref=vn8 out=h8
Md8  dm8  vn8  tl8  0    NCH L=650n W=6u
Ms8  h8   h7   tl8  0    NCH L=650n W=6u
Mt8  tl8  vb8  0     0    NCH L=1u   W=12u
Mpd8 dm8  th8  vdd   vdd  PCH L=2u   W=6u
Mps8 h8   th8  vdd   vdd  PCH L=2u   W=6u
C8   h8   0      1p

* stage 9: signal=h8 ref=vn9 out=h9
Md9  dm9  vn9  tl9  0    NCH L=650n W=6u
Ms9  h9   h8   tl9  0    NCH L=650n W=6u
Mt9  tl9  vb9  0     0    NCH L=1u   W=12u
Mpd9 dm9  th9  vdd   vdd  PCH L=2u   W=6u
Mps9 h9   th9  vdd   vdd  PCH L=2u   W=6u
C9   h9   0      1p

* stage 10: signal=h9 ref=vn10 out=h10
Md10  dm10  vn10  tl10  0    NCH L=650n W=6u
Ms10  h10   h9   tl10  0    NCH L=650n W=6u
Mt10  tl10  vb10  0     0    NCH L=1u   W=12u
Mpd10 dm10  th10  vdd   vdd  PCH L=2u   W=6u
Mps10 h10   th10  vdd   vdd  PCH L=2u   W=6u
C10   h10   0      1p

* seed the ring with the data point at t=0; read h_j at tstop
.IC V(h1)=1.6086 V(h2)=3.0000 V(h3)=1.2128 V(h4)=3.0000 V(h5)=0.3000 V(h6)=0.9310 V(h7)=0.3000 V(h8)=0.3000 V(h9)=0.4231 V(h10)=3.0000

.TRAN 10n 100n

.END