* KIRCHHOFF FOUR-QUADRANT NETWORK (KFQ) -- auto-generated
* layers [(2, 8), (8, 2)] | 198 devices | 86 trainable sources
* Fully differential. One weight = FOUR cross-connected NMOS:
*     c+ <- (theta_a, v+) (theta_b, v-)
*     c- <- (theta_b, v+) (theta_a, v-)
* so  V(c+) - V(c-) = R k (theta_a - theta_b)(v+ - v-):  a pure
* product of a signed weight with a signed signal. Both the v^2 term
* and the per-column bias cancel IDENTICALLY. The 2-transistor version
* left a bias ~100x the signal, which saturated the neuron and pinned
* the composed map at affine R2 = 1.0000.

.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3

* ---- data: differential rows about vcm=1.0 V, swing=0.4 V ----
VIP1 xp1 0 DC 1.040871
VIM1 xm1 0 DC 0.959129
VIP2 xp2 0 DC 1.200000
VIM2 xm2 0 DC 0.800000

* fixed differential reference = the BIAS row. Without it
* the four-quadrant score has no constant term, the network is
* an ODD function, and any set needing a boundary that does not
* pass through the origin is unlearnable (circle: chance).
VBP bp 0 DC 1.200000
VBM bm 0 DC 0.800000

* ---- trainable weights (gate voltages) ----
VA0_0_1 g_VA0_0_1 0 DC 1.980413
VB0_0_1 g_VB0_0_1 0 DC 1.896623
VA0_1_1 g_VA0_1_1 0 DC 1.949806
VB0_1_1 g_VB0_1_1 0 DC 1.936294
VA0_2_1 g_VA0_2_1 0 DC 1.400000
VB0_2_1 g_VB0_2_1 0 DC 2.600000
VA0_0_2 g_VA0_0_2 0 DC 1.625185
VB0_0_2 g_VB0_0_2 0 DC 1.627613
VA0_1_2 g_VA0_1_2 0 DC 2.378556
VB0_1_2 g_VB0_1_2 0 DC 1.412652
VA0_2_2 g_VA0_2_2 0 DC 1.888347
VB0_2_2 g_VB0_2_2 0 DC 1.400000
VA0_0_3 g_VA0_0_3 0 DC 2.001697
VB0_0_3 g_VB0_0_3 0 DC 1.656473
VA0_1_3 g_VA0_1_3 0 DC 1.740027
VB0_1_3 g_VB0_1_3 0 DC 1.815955
VA0_2_3 g_VA0_2_3 0 DC 2.254226
VB0_2_3 g_VB0_2_3 0 DC 1.404745
VA0_0_4 g_VA0_0_4 0 DC 1.982031
VB0_0_4 g_VB0_0_4 0 DC 1.427714
VA0_1_4 g_VA0_1_4 0 DC 2.351888
VB0_1_4 g_VB0_1_4 0 DC 1.400000
VA0_2_4 g_VA0_2_4 0 DC 1.400000
VB0_2_4 g_VB0_2_4 0 DC 1.805355
VA0_0_5 g_VA0_0_5 0 DC 2.069917
VB0_0_5 g_VB0_0_5 0 DC 1.525705
VA0_1_5 g_VA0_1_5 0 DC 1.400000
VB0_1_5 g_VB0_1_5 0 DC 2.306496
VA0_2_5 g_VA0_2_5 0 DC 1.743584
VB0_2_5 g_VB0_2_5 0 DC 1.629752
VA0_0_6 g_VA0_0_6 0 DC 1.486238
VB0_0_6 g_VB0_0_6 0 DC 2.068776
VA0_1_6 g_VA0_1_6 0 DC 2.321261
VB0_1_6 g_VB0_1_6 0 DC 1.400000
VA0_2_6 g_VA0_2_6 0 DC 1.590801
VB0_2_6 g_VB0_2_6 0 DC 1.745740
VA0_0_7 g_VA0_0_7 0 DC 1.999380
VB0_0_7 g_VB0_0_7 0 DC 1.855662
VA0_1_7 g_VA0_1_7 0 DC 1.993646
VB0_1_7 g_VB0_1_7 0 DC 1.829555
VA0_2_7 g_VA0_2_7 0 DC 1.400000
VB0_2_7 g_VB0_2_7 0 DC 2.593444
VA0_0_8 g_VA0_0_8 0 DC 1.488637
VB0_0_8 g_VB0_0_8 0 DC 2.050007
VA0_1_8 g_VA0_1_8 0 DC 2.300332
VB0_1_8 g_VB0_1_8 0 DC 1.400000
VA0_2_8 g_VA0_2_8 0 DC 1.638214
VB0_2_8 g_VB0_2_8 0 DC 1.862965
VA1_0_1 g_VA1_0_1 0 DC 1.876492
VB1_0_1 g_VB1_0_1 0 DC 1.983508
VA1_1_1 g_VA1_1_1 0 DC 1.682014
VB1_1_1 g_VB1_1_1 0 DC 2.307126
VA1_2_1 g_VA1_2_1 0 DC 2.385487
VB1_2_1 g_VB1_2_1 0 DC 1.764259
VA1_3_1 g_VA1_3_1 0 DC 2.217658
VB1_3_1 g_VB1_3_1 0 DC 1.735015
VA1_4_1 g_VA1_4_1 0 DC 1.809403
VB1_4_1 g_VB1_4_1 0 DC 2.380367
VA1_5_1 g_VA1_5_1 0 DC 2.250720
VB1_5_1 g_VB1_5_1 0 DC 1.770174
VA1_6_1 g_VA1_6_1 0 DC 1.812171
VB1_6_1 g_VB1_6_1 0 DC 2.188330
VA1_7_1 g_VA1_7_1 0 DC 1.763860
VB1_7_1 g_VB1_7_1 0 DC 2.155536
VA1_8_1 g_VA1_8_1 0 DC 1.780034
VB1_8_1 g_VB1_8_1 0 DC 2.206115
VA1_0_2 g_VA1_0_2 0 DC 2.054970
VB1_0_2 g_VB1_0_2 0 DC 1.805031
VA1_1_2 g_VA1_1_2 0 DC 2.289123
VB1_1_2 g_VB1_1_2 0 DC 1.698306
VA1_2_2 g_VA1_2_2 0 DC 1.817699
VB1_2_2 g_VB1_2_2 0 DC 2.393829
VA1_3_2 g_VA1_3_2 0 DC 1.823727
VB1_3_2 g_VB1_3_2 0 DC 2.167519
VA1_4_2 g_VA1_4_2 0 DC 2.375754
VB1_4_2 g_VB1_4_2 0 DC 1.678804
VA1_5_2 g_VA1_5_2 0 DC 1.832778
VB1_5_2 g_VB1_5_2 0 DC 2.200331
VA1_6_2 g_VA1_6_2 0 DC 2.193798
VB1_6_2 g_VB1_6_2 0 DC 1.805161
VA1_7_2 g_VA1_7_2 0 DC 2.147489
VB1_7_2 g_VB1_7_2 0 DC 1.771633
VA1_8_2 g_VA1_8_2 0 DC 2.117788
VB1_8_2 g_VB1_8_2 0 DC 1.828359

* ---- trainable per-layer gain (diff-pair tail bias) ----
VT0 g_VT0 0 DC 0.850000
VT1 g_VT1 0 DC 0.850000

* ===== layer 0: 2 -> 8 (four-quadrant) =====
* column pair cp0_1/cn0_1: 2 four-quadrant synapses + bias row
MVA0_0_1P cp0_1 g_VA0_0_1 bp 0 NCH L=1u W=4u
MVB0_0_1P cp0_1 g_VB0_0_1 bm 0 NCH L=1u W=4u
MVB0_0_1N cn0_1 g_VB0_0_1 bp 0 NCH L=1u W=4u
MVA0_0_1N cn0_1 g_VA0_0_1 bm 0 NCH L=1u W=4u
MVA0_1_1P cp0_1 g_VA0_1_1 xp1 0 NCH L=1u W=4u
MVB0_1_1P cp0_1 g_VB0_1_1 xm1 0 NCH L=1u W=4u
MVB0_1_1N cn0_1 g_VB0_1_1 xp1 0 NCH L=1u W=4u
MVA0_1_1N cn0_1 g_VA0_1_1 xm1 0 NCH L=1u W=4u
MVA0_2_1P cp0_1 g_VA0_2_1 xp2 0 NCH L=1u W=4u
MVB0_2_1P cp0_1 g_VB0_2_1 xm2 0 NCH L=1u W=4u
MVB0_2_1N cn0_1 g_VB0_2_1 xp2 0 NCH L=1u W=4u
MVA0_2_1N cn0_1 g_VA0_2_1 xm2 0 NCH L=1u W=4u
RLP0_1 vdd cp0_1 6k
RLN0_1 vdd cn0_1 6k
CCP0_1 cp0_1 0 0.1f
CCN0_1 cn0_1 0 0.1f
MDP0_1 ob0_1 cp0_1 t0_1 0 NCH L=1u W=8u
MDN0_1 o0_1 cn0_1 t0_1 0 NCH L=1u W=8u
RDP0_1 vdd ob0_1 200k
RDN0_1 vdd o0_1 200k
MT0_1 t0_1 g_VT0 0 0 NCH L=1u W=8u
COP0_1 o0_1 0 0.1f
COM0_1 ob0_1 0 0.1f

* column pair cp0_2/cn0_2: 2 four-quadrant synapses + bias row
MVA0_0_2P cp0_2 g_VA0_0_2 bp 0 NCH L=1u W=4u
MVB0_0_2P cp0_2 g_VB0_0_2 bm 0 NCH L=1u W=4u
MVB0_0_2N cn0_2 g_VB0_0_2 bp 0 NCH L=1u W=4u
MVA0_0_2N cn0_2 g_VA0_0_2 bm 0 NCH L=1u W=4u
MVA0_1_2P cp0_2 g_VA0_1_2 xp1 0 NCH L=1u W=4u
MVB0_1_2P cp0_2 g_VB0_1_2 xm1 0 NCH L=1u W=4u
MVB0_1_2N cn0_2 g_VB0_1_2 xp1 0 NCH L=1u W=4u
MVA0_1_2N cn0_2 g_VA0_1_2 xm1 0 NCH L=1u W=4u
MVA0_2_2P cp0_2 g_VA0_2_2 xp2 0 NCH L=1u W=4u
MVB0_2_2P cp0_2 g_VB0_2_2 xm2 0 NCH L=1u W=4u
MVB0_2_2N cn0_2 g_VB0_2_2 xp2 0 NCH L=1u W=4u
MVA0_2_2N cn0_2 g_VA0_2_2 xm2 0 NCH L=1u W=4u
RLP0_2 vdd cp0_2 6k
RLN0_2 vdd cn0_2 6k
CCP0_2 cp0_2 0 0.1f
CCN0_2 cn0_2 0 0.1f
MDP0_2 ob0_2 cp0_2 t0_2 0 NCH L=1u W=8u
MDN0_2 o0_2 cn0_2 t0_2 0 NCH L=1u W=8u
RDP0_2 vdd ob0_2 200k
RDN0_2 vdd o0_2 200k
MT0_2 t0_2 g_VT0 0 0 NCH L=1u W=8u
COP0_2 o0_2 0 0.1f
COM0_2 ob0_2 0 0.1f

* column pair cp0_3/cn0_3: 2 four-quadrant synapses + bias row
MVA0_0_3P cp0_3 g_VA0_0_3 bp 0 NCH L=1u W=4u
MVB0_0_3P cp0_3 g_VB0_0_3 bm 0 NCH L=1u W=4u
MVB0_0_3N cn0_3 g_VB0_0_3 bp 0 NCH L=1u W=4u
MVA0_0_3N cn0_3 g_VA0_0_3 bm 0 NCH L=1u W=4u
MVA0_1_3P cp0_3 g_VA0_1_3 xp1 0 NCH L=1u W=4u
MVB0_1_3P cp0_3 g_VB0_1_3 xm1 0 NCH L=1u W=4u
MVB0_1_3N cn0_3 g_VB0_1_3 xp1 0 NCH L=1u W=4u
MVA0_1_3N cn0_3 g_VA0_1_3 xm1 0 NCH L=1u W=4u
MVA0_2_3P cp0_3 g_VA0_2_3 xp2 0 NCH L=1u W=4u
MVB0_2_3P cp0_3 g_VB0_2_3 xm2 0 NCH L=1u W=4u
MVB0_2_3N cn0_3 g_VB0_2_3 xp2 0 NCH L=1u W=4u
MVA0_2_3N cn0_3 g_VA0_2_3 xm2 0 NCH L=1u W=4u
RLP0_3 vdd cp0_3 6k
RLN0_3 vdd cn0_3 6k
CCP0_3 cp0_3 0 0.1f
CCN0_3 cn0_3 0 0.1f
MDP0_3 ob0_3 cp0_3 t0_3 0 NCH L=1u W=8u
MDN0_3 o0_3 cn0_3 t0_3 0 NCH L=1u W=8u
RDP0_3 vdd ob0_3 200k
RDN0_3 vdd o0_3 200k
MT0_3 t0_3 g_VT0 0 0 NCH L=1u W=8u
COP0_3 o0_3 0 0.1f
COM0_3 ob0_3 0 0.1f

* column pair cp0_4/cn0_4: 2 four-quadrant synapses + bias row
MVA0_0_4P cp0_4 g_VA0_0_4 bp 0 NCH L=1u W=4u
MVB0_0_4P cp0_4 g_VB0_0_4 bm 0 NCH L=1u W=4u
MVB0_0_4N cn0_4 g_VB0_0_4 bp 0 NCH L=1u W=4u
MVA0_0_4N cn0_4 g_VA0_0_4 bm 0 NCH L=1u W=4u
MVA0_1_4P cp0_4 g_VA0_1_4 xp1 0 NCH L=1u W=4u
MVB0_1_4P cp0_4 g_VB0_1_4 xm1 0 NCH L=1u W=4u
MVB0_1_4N cn0_4 g_VB0_1_4 xp1 0 NCH L=1u W=4u
MVA0_1_4N cn0_4 g_VA0_1_4 xm1 0 NCH L=1u W=4u
MVA0_2_4P cp0_4 g_VA0_2_4 xp2 0 NCH L=1u W=4u
MVB0_2_4P cp0_4 g_VB0_2_4 xm2 0 NCH L=1u W=4u
MVB0_2_4N cn0_4 g_VB0_2_4 xp2 0 NCH L=1u W=4u
MVA0_2_4N cn0_4 g_VA0_2_4 xm2 0 NCH L=1u W=4u
RLP0_4 vdd cp0_4 6k
RLN0_4 vdd cn0_4 6k
CCP0_4 cp0_4 0 0.1f
CCN0_4 cn0_4 0 0.1f
MDP0_4 ob0_4 cp0_4 t0_4 0 NCH L=1u W=8u
MDN0_4 o0_4 cn0_4 t0_4 0 NCH L=1u W=8u
RDP0_4 vdd ob0_4 200k
RDN0_4 vdd o0_4 200k
MT0_4 t0_4 g_VT0 0 0 NCH L=1u W=8u
COP0_4 o0_4 0 0.1f
COM0_4 ob0_4 0 0.1f

* column pair cp0_5/cn0_5: 2 four-quadrant synapses + bias row
MVA0_0_5P cp0_5 g_VA0_0_5 bp 0 NCH L=1u W=4u
MVB0_0_5P cp0_5 g_VB0_0_5 bm 0 NCH L=1u W=4u
MVB0_0_5N cn0_5 g_VB0_0_5 bp 0 NCH L=1u W=4u
MVA0_0_5N cn0_5 g_VA0_0_5 bm 0 NCH L=1u W=4u
MVA0_1_5P cp0_5 g_VA0_1_5 xp1 0 NCH L=1u W=4u
MVB0_1_5P cp0_5 g_VB0_1_5 xm1 0 NCH L=1u W=4u
MVB0_1_5N cn0_5 g_VB0_1_5 xp1 0 NCH L=1u W=4u
MVA0_1_5N cn0_5 g_VA0_1_5 xm1 0 NCH L=1u W=4u
MVA0_2_5P cp0_5 g_VA0_2_5 xp2 0 NCH L=1u W=4u
MVB0_2_5P cp0_5 g_VB0_2_5 xm2 0 NCH L=1u W=4u
MVB0_2_5N cn0_5 g_VB0_2_5 xp2 0 NCH L=1u W=4u
MVA0_2_5N cn0_5 g_VA0_2_5 xm2 0 NCH L=1u W=4u
RLP0_5 vdd cp0_5 6k
RLN0_5 vdd cn0_5 6k
CCP0_5 cp0_5 0 0.1f
CCN0_5 cn0_5 0 0.1f
MDP0_5 ob0_5 cp0_5 t0_5 0 NCH L=1u W=8u
MDN0_5 o0_5 cn0_5 t0_5 0 NCH L=1u W=8u
RDP0_5 vdd ob0_5 200k
RDN0_5 vdd o0_5 200k
MT0_5 t0_5 g_VT0 0 0 NCH L=1u W=8u
COP0_5 o0_5 0 0.1f
COM0_5 ob0_5 0 0.1f

* column pair cp0_6/cn0_6: 2 four-quadrant synapses + bias row
MVA0_0_6P cp0_6 g_VA0_0_6 bp 0 NCH L=1u W=4u
MVB0_0_6P cp0_6 g_VB0_0_6 bm 0 NCH L=1u W=4u
MVB0_0_6N cn0_6 g_VB0_0_6 bp 0 NCH L=1u W=4u
MVA0_0_6N cn0_6 g_VA0_0_6 bm 0 NCH L=1u W=4u
MVA0_1_6P cp0_6 g_VA0_1_6 xp1 0 NCH L=1u W=4u
MVB0_1_6P cp0_6 g_VB0_1_6 xm1 0 NCH L=1u W=4u
MVB0_1_6N cn0_6 g_VB0_1_6 xp1 0 NCH L=1u W=4u
MVA0_1_6N cn0_6 g_VA0_1_6 xm1 0 NCH L=1u W=4u
MVA0_2_6P cp0_6 g_VA0_2_6 xp2 0 NCH L=1u W=4u
MVB0_2_6P cp0_6 g_VB0_2_6 xm2 0 NCH L=1u W=4u
MVB0_2_6N cn0_6 g_VB0_2_6 xp2 0 NCH L=1u W=4u
MVA0_2_6N cn0_6 g_VA0_2_6 xm2 0 NCH L=1u W=4u
RLP0_6 vdd cp0_6 6k
RLN0_6 vdd cn0_6 6k
CCP0_6 cp0_6 0 0.1f
CCN0_6 cn0_6 0 0.1f
MDP0_6 ob0_6 cp0_6 t0_6 0 NCH L=1u W=8u
MDN0_6 o0_6 cn0_6 t0_6 0 NCH L=1u W=8u
RDP0_6 vdd ob0_6 200k
RDN0_6 vdd o0_6 200k
MT0_6 t0_6 g_VT0 0 0 NCH L=1u W=8u
COP0_6 o0_6 0 0.1f
COM0_6 ob0_6 0 0.1f

* column pair cp0_7/cn0_7: 2 four-quadrant synapses + bias row
MVA0_0_7P cp0_7 g_VA0_0_7 bp 0 NCH L=1u W=4u
MVB0_0_7P cp0_7 g_VB0_0_7 bm 0 NCH L=1u W=4u
MVB0_0_7N cn0_7 g_VB0_0_7 bp 0 NCH L=1u W=4u
MVA0_0_7N cn0_7 g_VA0_0_7 bm 0 NCH L=1u W=4u
MVA0_1_7P cp0_7 g_VA0_1_7 xp1 0 NCH L=1u W=4u
MVB0_1_7P cp0_7 g_VB0_1_7 xm1 0 NCH L=1u W=4u
MVB0_1_7N cn0_7 g_VB0_1_7 xp1 0 NCH L=1u W=4u
MVA0_1_7N cn0_7 g_VA0_1_7 xm1 0 NCH L=1u W=4u
MVA0_2_7P cp0_7 g_VA0_2_7 xp2 0 NCH L=1u W=4u
MVB0_2_7P cp0_7 g_VB0_2_7 xm2 0 NCH L=1u W=4u
MVB0_2_7N cn0_7 g_VB0_2_7 xp2 0 NCH L=1u W=4u
MVA0_2_7N cn0_7 g_VA0_2_7 xm2 0 NCH L=1u W=4u
RLP0_7 vdd cp0_7 6k
RLN0_7 vdd cn0_7 6k
CCP0_7 cp0_7 0 0.1f
CCN0_7 cn0_7 0 0.1f
MDP0_7 ob0_7 cp0_7 t0_7 0 NCH L=1u W=8u
MDN0_7 o0_7 cn0_7 t0_7 0 NCH L=1u W=8u
RDP0_7 vdd ob0_7 200k
RDN0_7 vdd o0_7 200k
MT0_7 t0_7 g_VT0 0 0 NCH L=1u W=8u
COP0_7 o0_7 0 0.1f
COM0_7 ob0_7 0 0.1f

* column pair cp0_8/cn0_8: 2 four-quadrant synapses + bias row
MVA0_0_8P cp0_8 g_VA0_0_8 bp 0 NCH L=1u W=4u
MVB0_0_8P cp0_8 g_VB0_0_8 bm 0 NCH L=1u W=4u
MVB0_0_8N cn0_8 g_VB0_0_8 bp 0 NCH L=1u W=4u
MVA0_0_8N cn0_8 g_VA0_0_8 bm 0 NCH L=1u W=4u
MVA0_1_8P cp0_8 g_VA0_1_8 xp1 0 NCH L=1u W=4u
MVB0_1_8P cp0_8 g_VB0_1_8 xm1 0 NCH L=1u W=4u
MVB0_1_8N cn0_8 g_VB0_1_8 xp1 0 NCH L=1u W=4u
MVA0_1_8N cn0_8 g_VA0_1_8 xm1 0 NCH L=1u W=4u
MVA0_2_8P cp0_8 g_VA0_2_8 xp2 0 NCH L=1u W=4u
MVB0_2_8P cp0_8 g_VB0_2_8 xm2 0 NCH L=1u W=4u
MVB0_2_8N cn0_8 g_VB0_2_8 xp2 0 NCH L=1u W=4u
MVA0_2_8N cn0_8 g_VA0_2_8 xm2 0 NCH L=1u W=4u
RLP0_8 vdd cp0_8 6k
RLN0_8 vdd cn0_8 6k
CCP0_8 cp0_8 0 0.1f
CCN0_8 cn0_8 0 0.1f
MDP0_8 ob0_8 cp0_8 t0_8 0 NCH L=1u W=8u
MDN0_8 o0_8 cn0_8 t0_8 0 NCH L=1u W=8u
RDP0_8 vdd ob0_8 200k
RDN0_8 vdd o0_8 200k
MT0_8 t0_8 g_VT0 0 0 NCH L=1u W=8u
COP0_8 o0_8 0 0.1f
COM0_8 ob0_8 0 0.1f


* ===== layer 1: 8 -> 2 (four-quadrant) =====
* column pair cp1_1/cn1_1: 8 four-quadrant synapses + bias row
MVA1_0_1P cp1_1 g_VA1_0_1 bp 0 NCH L=1u W=4u
MVB1_0_1P cp1_1 g_VB1_0_1 bm 0 NCH L=1u W=4u
MVB1_0_1N cn1_1 g_VB1_0_1 bp 0 NCH L=1u W=4u
MVA1_0_1N cn1_1 g_VA1_0_1 bm 0 NCH L=1u W=4u
MVA1_1_1P cp1_1 g_VA1_1_1 o0_1 0 NCH L=1u W=4u
MVB1_1_1P cp1_1 g_VB1_1_1 ob0_1 0 NCH L=1u W=4u
MVB1_1_1N cn1_1 g_VB1_1_1 o0_1 0 NCH L=1u W=4u
MVA1_1_1N cn1_1 g_VA1_1_1 ob0_1 0 NCH L=1u W=4u
MVA1_2_1P cp1_1 g_VA1_2_1 o0_2 0 NCH L=1u W=4u
MVB1_2_1P cp1_1 g_VB1_2_1 ob0_2 0 NCH L=1u W=4u
MVB1_2_1N cn1_1 g_VB1_2_1 o0_2 0 NCH L=1u W=4u
MVA1_2_1N cn1_1 g_VA1_2_1 ob0_2 0 NCH L=1u W=4u
MVA1_3_1P cp1_1 g_VA1_3_1 o0_3 0 NCH L=1u W=4u
MVB1_3_1P cp1_1 g_VB1_3_1 ob0_3 0 NCH L=1u W=4u
MVB1_3_1N cn1_1 g_VB1_3_1 o0_3 0 NCH L=1u W=4u
MVA1_3_1N cn1_1 g_VA1_3_1 ob0_3 0 NCH L=1u W=4u
MVA1_4_1P cp1_1 g_VA1_4_1 o0_4 0 NCH L=1u W=4u
MVB1_4_1P cp1_1 g_VB1_4_1 ob0_4 0 NCH L=1u W=4u
MVB1_4_1N cn1_1 g_VB1_4_1 o0_4 0 NCH L=1u W=4u
MVA1_4_1N cn1_1 g_VA1_4_1 ob0_4 0 NCH L=1u W=4u
MVA1_5_1P cp1_1 g_VA1_5_1 o0_5 0 NCH L=1u W=4u
MVB1_5_1P cp1_1 g_VB1_5_1 ob0_5 0 NCH L=1u W=4u
MVB1_5_1N cn1_1 g_VB1_5_1 o0_5 0 NCH L=1u W=4u
MVA1_5_1N cn1_1 g_VA1_5_1 ob0_5 0 NCH L=1u W=4u
MVA1_6_1P cp1_1 g_VA1_6_1 o0_6 0 NCH L=1u W=4u
MVB1_6_1P cp1_1 g_VB1_6_1 ob0_6 0 NCH L=1u W=4u
MVB1_6_1N cn1_1 g_VB1_6_1 o0_6 0 NCH L=1u W=4u
MVA1_6_1N cn1_1 g_VA1_6_1 ob0_6 0 NCH L=1u W=4u
MVA1_7_1P cp1_1 g_VA1_7_1 o0_7 0 NCH L=1u W=4u
MVB1_7_1P cp1_1 g_VB1_7_1 ob0_7 0 NCH L=1u W=4u
MVB1_7_1N cn1_1 g_VB1_7_1 o0_7 0 NCH L=1u W=4u
MVA1_7_1N cn1_1 g_VA1_7_1 ob0_7 0 NCH L=1u W=4u
MVA1_8_1P cp1_1 g_VA1_8_1 o0_8 0 NCH L=1u W=4u
MVB1_8_1P cp1_1 g_VB1_8_1 ob0_8 0 NCH L=1u W=4u
MVB1_8_1N cn1_1 g_VB1_8_1 o0_8 0 NCH L=1u W=4u
MVA1_8_1N cn1_1 g_VA1_8_1 ob0_8 0 NCH L=1u W=4u
RLP1_1 vdd cp1_1 6k
RLN1_1 vdd cn1_1 6k
CCP1_1 cp1_1 0 0.1f
CCN1_1 cn1_1 0 0.1f
MDP1_1 ob1_1 cp1_1 t1_1 0 NCH L=1u W=8u
MDN1_1 o1_1 cn1_1 t1_1 0 NCH L=1u W=8u
RDP1_1 vdd ob1_1 200k
RDN1_1 vdd o1_1 200k
MT1_1 t1_1 g_VT1 0 0 NCH L=1u W=8u
COP1_1 o1_1 0 0.1f
COM1_1 ob1_1 0 0.1f

* column pair cp1_2/cn1_2: 8 four-quadrant synapses + bias row
MVA1_0_2P cp1_2 g_VA1_0_2 bp 0 NCH L=1u W=4u
MVB1_0_2P cp1_2 g_VB1_0_2 bm 0 NCH L=1u W=4u
MVB1_0_2N cn1_2 g_VB1_0_2 bp 0 NCH L=1u W=4u
MVA1_0_2N cn1_2 g_VA1_0_2 bm 0 NCH L=1u W=4u
MVA1_1_2P cp1_2 g_VA1_1_2 o0_1 0 NCH L=1u W=4u
MVB1_1_2P cp1_2 g_VB1_1_2 ob0_1 0 NCH L=1u W=4u
MVB1_1_2N cn1_2 g_VB1_1_2 o0_1 0 NCH L=1u W=4u
MVA1_1_2N cn1_2 g_VA1_1_2 ob0_1 0 NCH L=1u W=4u
MVA1_2_2P cp1_2 g_VA1_2_2 o0_2 0 NCH L=1u W=4u
MVB1_2_2P cp1_2 g_VB1_2_2 ob0_2 0 NCH L=1u W=4u
MVB1_2_2N cn1_2 g_VB1_2_2 o0_2 0 NCH L=1u W=4u
MVA1_2_2N cn1_2 g_VA1_2_2 ob0_2 0 NCH L=1u W=4u
MVA1_3_2P cp1_2 g_VA1_3_2 o0_3 0 NCH L=1u W=4u
MVB1_3_2P cp1_2 g_VB1_3_2 ob0_3 0 NCH L=1u W=4u
MVB1_3_2N cn1_2 g_VB1_3_2 o0_3 0 NCH L=1u W=4u
MVA1_3_2N cn1_2 g_VA1_3_2 ob0_3 0 NCH L=1u W=4u
MVA1_4_2P cp1_2 g_VA1_4_2 o0_4 0 NCH L=1u W=4u
MVB1_4_2P cp1_2 g_VB1_4_2 ob0_4 0 NCH L=1u W=4u
MVB1_4_2N cn1_2 g_VB1_4_2 o0_4 0 NCH L=1u W=4u
MVA1_4_2N cn1_2 g_VA1_4_2 ob0_4 0 NCH L=1u W=4u
MVA1_5_2P cp1_2 g_VA1_5_2 o0_5 0 NCH L=1u W=4u
MVB1_5_2P cp1_2 g_VB1_5_2 ob0_5 0 NCH L=1u W=4u
MVB1_5_2N cn1_2 g_VB1_5_2 o0_5 0 NCH L=1u W=4u
MVA1_5_2N cn1_2 g_VA1_5_2 ob0_5 0 NCH L=1u W=4u
MVA1_6_2P cp1_2 g_VA1_6_2 o0_6 0 NCH L=1u W=4u
MVB1_6_2P cp1_2 g_VB1_6_2 ob0_6 0 NCH L=1u W=4u
MVB1_6_2N cn1_2 g_VB1_6_2 o0_6 0 NCH L=1u W=4u
MVA1_6_2N cn1_2 g_VA1_6_2 ob0_6 0 NCH L=1u W=4u
MVA1_7_2P cp1_2 g_VA1_7_2 o0_7 0 NCH L=1u W=4u
MVB1_7_2P cp1_2 g_VB1_7_2 ob0_7 0 NCH L=1u W=4u
MVB1_7_2N cn1_2 g_VB1_7_2 o0_7 0 NCH L=1u W=4u
MVA1_7_2N cn1_2 g_VA1_7_2 ob0_7 0 NCH L=1u W=4u
MVA1_8_2P cp1_2 g_VA1_8_2 o0_8 0 NCH L=1u W=4u
MVB1_8_2P cp1_2 g_VB1_8_2 ob0_8 0 NCH L=1u W=4u
MVB1_8_2N cn1_2 g_VB1_8_2 o0_8 0 NCH L=1u W=4u
MVA1_8_2N cn1_2 g_VA1_8_2 ob0_8 0 NCH L=1u W=4u
RLP1_2 vdd cp1_2 6k
RLN1_2 vdd cn1_2 6k
CCP1_2 cp1_2 0 0.1f
CCN1_2 cn1_2 0 0.1f
MDP1_2 ob1_2 cp1_2 t1_2 0 NCH L=1u W=8u
MDN1_2 o1_2 cn1_2 t1_2 0 NCH L=1u W=8u
RDP1_2 vdd ob1_2 200k
RDN1_2 vdd o1_2 200k
MT1_2 t1_2 g_VT1 0 0 NCH L=1u W=8u
COP1_2 o1_2 0 0.1f
COM1_2 ob1_2 0 0.1f

* neutral solver seed; the data is in the input sources
.IC V(cp0_1)=1.0000 V(cn0_1)=1.0000 V(o0_1)=1.0000 V(ob0_1)=1.0000 V(cp0_2)=1.0000 V(cn0_2)=1.0000 V(o0_2)=1.0000 V(ob0_2)=1.0000 V(cp0_3)=1.0000 V(cn0_3)=1.0000 V(o0_3)=1.0000 V(ob0_3)=1.0000 V(cp0_4)=1.0000 V(cn0_4)=1.0000 V(o0_4)=1.0000 V(ob0_4)=1.0000 V(cp0_5)=1.0000 V(cn0_5)=1.0000 V(o0_5)=1.0000 V(ob0_5)=1.0000 V(cp0_6)=1.0000 V(cn0_6)=1.0000 V(o0_6)=1.0000 V(ob0_6)=1.0000 V(cp0_7)=1.0000 V(cn0_7)=1.0000 V(o0_7)=1.0000 V(ob0_7)=1.0000 V(cp0_8)=1.0000 V(cn0_8)=1.0000 V(o0_8)=1.0000 V(ob0_8)=1.0000 V(cp1_1)=1.0000 V(cn1_1)=1.0000 V(o1_1)=1.0000 V(ob1_1)=1.0000 V(cp1_2)=1.0000 V(cn1_2)=1.0000 V(o1_2)=1.0000 V(ob1_2)=1.0000

.TRAN 50n 100n

.END