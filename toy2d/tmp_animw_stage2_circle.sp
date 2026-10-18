* KirchhoffNet WIDE parallel diff-amp layer (per-unit trainable refs) -- auto-generated

* MOSFET models (Level-1 Shichman-Hodges)
.MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

* Fixed supply
V0  vdd 0 DC 3.3

* Encoder-driven per-unit inputs
VIN1 in1 0 DC 1.939864
VIN2 in2 0 DC 1.110621
VIN3 in3 0 DC 1.805211
VIN4 in4 0 DC 0.300000
VIN5 in5 0 DC 1.683166
VIN6 in6 0 DC 2.061602
VIN7 in7 0 DC 2.698448
VIN8 in8 0 DC 2.529544
VIN9 in9 0 DC 1.822702
VIN10 in10 0 DC 1.032150
VIN11 in11 0 DC 0.497684
VIN12 in12 0 DC 1.331554
VIN13 in13 0 DC 0.300000
VIN14 in14 0 DC 1.044252
VIN15 in15 0 DC 2.543834
VIN16 in16 0 DC 1.769736
VIN17 in17 0 DC 1.395474
VIN18 in18 0 DC 0.634068
VIN19 in19 0 DC 2.641559
VIN20 in20 0 DC 1.032523
VIN21 in21 0 DC 2.803071
VIN22 in22 0 DC 0.300000
VIN23 in23 0 DC 0.732527
VIN24 in24 0 DC 0.300000

* Trainable PMOS-load thetas
VTH1 th1 0 DC 1.701607
VTH2 th2 0 DC 1.701507
VTH3 th3 0 DC 1.699873
VTH4 th4 0 DC 1.703649
VTH5 th5 0 DC 1.700170
VTH6 th6 0 DC 1.693525
VTH7 th7 0 DC 1.699405
VTH8 th8 0 DC 1.705081
VTH9 th9 0 DC 1.696272
VTH10 th10 0 DC 1.699210
VTH11 th11 0 DC 1.705415
VTH12 th12 0 DC 1.705916
VTH13 th13 0 DC 1.695261
VTH14 th14 0 DC 1.704211
VTH15 th15 0 DC 1.701455
VTH16 th16 0 DC 1.696238
VTH17 th17 0 DC 1.706858
VTH18 th18 0 DC 1.701555
VTH19 th19 0 DC 1.705444
VTH20 th20 0 DC 1.701927
VTH21 th21 0 DC 1.692282
VTH22 th22 0 DC 1.692456
VTH23 th23 0 DC 1.692554
VTH24 th24 0 DC 1.695182

* Trainable tail biases
VB1 vb1 0 DC 0.801538
VB2 vb2 0 DC 0.800662
VB3 vb3 0 DC 0.800804
VB4 vb4 0 DC 0.803293
VB5 vb5 0 DC 0.800594
VB6 vb6 0 DC 0.793254
VB7 vb7 0 DC 0.799114
VB8 vb8 0 DC 0.804414
VB9 vb9 0 DC 0.796091
VB10 vb10 0 DC 0.799237
VB11 vb11 0 DC 0.802773
VB12 vb12 0 DC 0.804505
VB13 vb13 0 DC 0.795395
VB14 vb14 0 DC 0.802277
VB15 vb15 0 DC 0.800624
VB16 vb16 0 DC 0.796570
VB17 vb17 0 DC 0.807969
VB18 vb18 0 DC 0.800265
VB19 vb19 0 DC 0.805335
VB20 vb20 0 DC 0.803425
VB21 vb21 0 DC 0.792609
VB22 vb22 0 DC 0.792438
VB23 vb23 0 DC 0.792280
VB24 vb24 0 DC 0.795516

* Trainable per-unit reference voltages
VN1 vn1 0 DC 0.998495
VN2 vn2 0 DC 1.000947
VN3 vn3 0 DC 0.992898
VN4 vn4 0 DC 0.997157
VN5 vn5 0 DC 0.999208
VN6 vn6 0 DC 1.008358
VN7 vn7 0 DC 1.000335
VN8 vn8 0 DC 0.995302
VN9 vn9 0 DC 1.007772
VN10 vn10 0 DC 1.002211
VN11 vn11 0 DC 1.004962
VN12 vn12 0 DC 1.000517
VN13 vn13 0 DC 1.004951
VN14 vn14 0 DC 1.001521
VN15 vn15 0 DC 0.999451
VN16 vn16 0 DC 1.003788
VN17 vn17 0 DC 0.990994
VN18 vn18 0 DC 1.001873
VN19 vn19 0 DC 0.994654
VN20 vn20 0 DC 0.992928
VN21 vn21 0 DC 1.006819
VN22 vn22 0 DC 1.007553
VN23 vn23 0 DC 1.008531
VN24 vn24 0 DC 1.004011

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

* unit 13: signal=in13 ref=vn13 out=u13
Md13  d13  vn13  t13  0    NCH L=650n W=6u
Ms13  u13  in13  t13  0    NCH L=650n W=6u
Mt13  t13  vb13  0     0    NCH L=1u   W=12u
Mpd13 d13  th13  vdd   vdd  PCH L=2u   W=6u
Mps13 u13  th13  vdd   vdd  PCH L=2u   W=6u
C13   u13  0      0.1f

* unit 14: signal=in14 ref=vn14 out=u14
Md14  d14  vn14  t14  0    NCH L=650n W=6u
Ms14  u14  in14  t14  0    NCH L=650n W=6u
Mt14  t14  vb14  0     0    NCH L=1u   W=12u
Mpd14 d14  th14  vdd   vdd  PCH L=2u   W=6u
Mps14 u14  th14  vdd   vdd  PCH L=2u   W=6u
C14   u14  0      0.1f

* unit 15: signal=in15 ref=vn15 out=u15
Md15  d15  vn15  t15  0    NCH L=650n W=6u
Ms15  u15  in15  t15  0    NCH L=650n W=6u
Mt15  t15  vb15  0     0    NCH L=1u   W=12u
Mpd15 d15  th15  vdd   vdd  PCH L=2u   W=6u
Mps15 u15  th15  vdd   vdd  PCH L=2u   W=6u
C15   u15  0      0.1f

* unit 16: signal=in16 ref=vn16 out=u16
Md16  d16  vn16  t16  0    NCH L=650n W=6u
Ms16  u16  in16  t16  0    NCH L=650n W=6u
Mt16  t16  vb16  0     0    NCH L=1u   W=12u
Mpd16 d16  th16  vdd   vdd  PCH L=2u   W=6u
Mps16 u16  th16  vdd   vdd  PCH L=2u   W=6u
C16   u16  0      0.1f

* unit 17: signal=in17 ref=vn17 out=u17
Md17  d17  vn17  t17  0    NCH L=650n W=6u
Ms17  u17  in17  t17  0    NCH L=650n W=6u
Mt17  t17  vb17  0     0    NCH L=1u   W=12u
Mpd17 d17  th17  vdd   vdd  PCH L=2u   W=6u
Mps17 u17  th17  vdd   vdd  PCH L=2u   W=6u
C17   u17  0      0.1f

* unit 18: signal=in18 ref=vn18 out=u18
Md18  d18  vn18  t18  0    NCH L=650n W=6u
Ms18  u18  in18  t18  0    NCH L=650n W=6u
Mt18  t18  vb18  0     0    NCH L=1u   W=12u
Mpd18 d18  th18  vdd   vdd  PCH L=2u   W=6u
Mps18 u18  th18  vdd   vdd  PCH L=2u   W=6u
C18   u18  0      0.1f

* unit 19: signal=in19 ref=vn19 out=u19
Md19  d19  vn19  t19  0    NCH L=650n W=6u
Ms19  u19  in19  t19  0    NCH L=650n W=6u
Mt19  t19  vb19  0     0    NCH L=1u   W=12u
Mpd19 d19  th19  vdd   vdd  PCH L=2u   W=6u
Mps19 u19  th19  vdd   vdd  PCH L=2u   W=6u
C19   u19  0      0.1f

* unit 20: signal=in20 ref=vn20 out=u20
Md20  d20  vn20  t20  0    NCH L=650n W=6u
Ms20  u20  in20  t20  0    NCH L=650n W=6u
Mt20  t20  vb20  0     0    NCH L=1u   W=12u
Mpd20 d20  th20  vdd   vdd  PCH L=2u   W=6u
Mps20 u20  th20  vdd   vdd  PCH L=2u   W=6u
C20   u20  0      0.1f

* unit 21: signal=in21 ref=vn21 out=u21
Md21  d21  vn21  t21  0    NCH L=650n W=6u
Ms21  u21  in21  t21  0    NCH L=650n W=6u
Mt21  t21  vb21  0     0    NCH L=1u   W=12u
Mpd21 d21  th21  vdd   vdd  PCH L=2u   W=6u
Mps21 u21  th21  vdd   vdd  PCH L=2u   W=6u
C21   u21  0      0.1f

* unit 22: signal=in22 ref=vn22 out=u22
Md22  d22  vn22  t22  0    NCH L=650n W=6u
Ms22  u22  in22  t22  0    NCH L=650n W=6u
Mt22  t22  vb22  0     0    NCH L=1u   W=12u
Mpd22 d22  th22  vdd   vdd  PCH L=2u   W=6u
Mps22 u22  th22  vdd   vdd  PCH L=2u   W=6u
C22   u22  0      0.1f

* unit 23: signal=in23 ref=vn23 out=u23
Md23  d23  vn23  t23  0    NCH L=650n W=6u
Ms23  u23  in23  t23  0    NCH L=650n W=6u
Mt23  t23  vb23  0     0    NCH L=1u   W=12u
Mpd23 d23  th23  vdd   vdd  PCH L=2u   W=6u
Mps23 u23  th23  vdd   vdd  PCH L=2u   W=6u
C23   u23  0      0.1f

* unit 24: signal=in24 ref=vn24 out=u24
Md24  d24  vn24  t24  0    NCH L=650n W=6u
Ms24  u24  in24  t24  0    NCH L=650n W=6u
Mt24  t24  vb24  0     0    NCH L=1u   W=12u
Mpd24 d24  th24  vdd   vdd  PCH L=2u   W=6u
Mps24 u24  th24  vdd   vdd  PCH L=2u   W=6u
C24   u24  0      0.1f

* seed transient from a neutral state; read u_j at tstop
.IC V(u1)=1.6500 V(u2)=1.6500 V(u3)=1.6500 V(u4)=1.6500 V(u5)=1.6500 V(u6)=1.6500 V(u7)=1.6500 V(u8)=1.6500 V(u9)=1.6500 V(u10)=1.6500 V(u11)=1.6500 V(u12)=1.6500 V(u13)=1.6500 V(u14)=1.6500 V(u15)=1.6500 V(u16)=1.6500 V(u17)=1.6500 V(u18)=1.6500 V(u19)=1.6500 V(u20)=1.6500 V(u21)=1.6500 V(u22)=1.6500 V(u23)=1.6500 V(u24)=1.6500

.TRAN 10n 100n

.END