* KirchhoffNet OPEN feedforward chain -- auto-generated

* MOSFET models (Level-1 Shichman-Hodges)
.MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

* Fixed supply
V0  vdd 0 DC 3.3

* Encoder-driven input sources (front input + per-stage references)
VIN  nin 0 DC 1.650000
VREF1 vref1 0 DC 1.262350
VREF2 vref2 0 DC 1.241573
VREF3 vref3 0 DC 1.004102
VREF4 vref4 0 DC 1.000000

* Trainable PMOS-load thetas
VTH1 th1 0 DC 1.690623
VTH2 th2 0 DC 1.709362
VTH3 th3 0 DC 1.704753
VTH4 th4 0 DC 1.696671

* Trainable tail biases
VB1 vb1 0 DC 0.790623
VB2 vb2 0 DC 0.809380
VB3 vb3 0 DC 0.802255
VB4 vb4 0 DC 0.796550

* Stage 1: signal=nin  ref=vref1  out=h1
Md1  d1  vref1  t1  0    NCH L=650n W=6u
Ms1  h1  nin  t1  0    NCH L=650n W=6u
Mt1  t1  vb1    0     0    NCH L=1u   W=12u
Mpd1 d1  th1    vdd   vdd  PCH L=2u   W=6u
Mps1 h1  th1    vdd   vdd  PCH L=2u   W=6u
C1   h1  0        0.1f

* Stage 2: signal=h1  ref=vref2  out=h2
Md2  d2  vref2  t2  0    NCH L=650n W=6u
Ms2  h2  h1  t2  0    NCH L=650n W=6u
Mt2  t2  vb2    0     0    NCH L=1u   W=12u
Mpd2 d2  th2    vdd   vdd  PCH L=2u   W=6u
Mps2 h2  th2    vdd   vdd  PCH L=2u   W=6u
C2   h2  0        0.1f

* Stage 3: signal=h2  ref=vref3  out=h3
Md3  d3  vref3  t3  0    NCH L=650n W=6u
Ms3  h3  h2  t3  0    NCH L=650n W=6u
Mt3  t3  vb3    0     0    NCH L=1u   W=12u
Mpd3 d3  th3    vdd   vdd  PCH L=2u   W=6u
Mps3 h3  th3    vdd   vdd  PCH L=2u   W=6u
C3   h3  0        0.1f

* Stage 4: signal=h3  ref=vref4  out=h4
Md4  d4  vref4  t4  0    NCH L=650n W=6u
Ms4  h4  h3  t4  0    NCH L=650n W=6u
Mt4  t4  vb4    0     0    NCH L=1u   W=12u
Mpd4 d4  th4    vdd   vdd  PCH L=2u   W=6u
Mps4 h4  th4    vdd   vdd  PCH L=2u   W=6u
C4   h4  0        0.1f

* Seed a transient from a neutral state; read at tstop (~1 tau)
.IC V(h1)=1.6500 V(h2)=1.6500 V(h3)=1.6500 V(h4)=1.6500

.TRAN 10n 100n

.END