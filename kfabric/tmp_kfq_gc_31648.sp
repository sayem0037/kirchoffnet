* KIRCHHOFF FOUR-QUADRANT NETWORK (KFQ) -- auto-generated
* layers [(4, 7), (7, 3)] | 266 devices | 120 trainable sources
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
VIP1 xp1 0 DC 1.049538
VIM1 xm1 0 DC 0.950462
VIP2 xp2 0 DC 0.975484
VIM2 xm2 0 DC 1.024516
VIP3 xp3 0 DC 0.811501
VIM3 xm3 0 DC 1.188499
VIP4 xp4 0 DC 1.015871
VIM4 xm4 0 DC 0.984129

* fixed differential reference = the BIAS row. Without it
* the four-quadrant score has no constant term, the network is
* an ODD function, and any set needing a boundary that does not
* pass through the origin is unlearnable (circle: chance).
VBP bp 0 DC 1.200000
VBM bm 0 DC 0.800000

* ---- trainable weights (gate voltages) ----
VA0_0_1 g_VA0_0_1 0 DC 1.971089
VB0_0_1 g_VB0_0_1 0 DC 1.888911
VA0_1_1 g_VA0_1_1 0 DC 1.860936
VB0_1_1 g_VB0_1_1 0 DC 1.999064
VA0_2_1 g_VA0_2_1 0 DC 1.792292
VB0_2_1 g_VB0_2_1 0 DC 2.067708
VA0_3_1 g_VA0_3_1 0 DC 1.784958
VB0_3_1 g_VB0_3_1 0 DC 2.075042
VA0_4_1 g_VA0_4_1 0 DC 2.023981
VB0_4_1 g_VB0_4_1 0 DC 1.836019
VA0_0_2 g_VA0_0_2 0 DC 2.053827
VB0_0_2 g_VB0_0_2 0 DC 1.806173
VA0_1_2 g_VA0_1_2 0 DC 1.961991
VB0_1_2 g_VB0_1_2 0 DC 1.898009
VA0_2_2 g_VA0_2_2 0 DC 1.998849
VB0_2_2 g_VB0_2_2 0 DC 1.861151
VA0_3_2 g_VA0_3_2 0 DC 1.943087
VB0_3_2 g_VB0_3_2 0 DC 1.916913
VA0_4_2 g_VA0_4_2 0 DC 2.060522
VB0_4_2 g_VB0_4_2 0 DC 1.799478
VA0_0_3 g_VA0_0_3 0 DC 2.024756
VB0_0_3 g_VB0_0_3 0 DC 1.835244
VA0_1_3 g_VA0_1_3 0 DC 1.780822
VB0_1_3 g_VB0_1_3 0 DC 2.079178
VA0_2_3 g_VA0_2_3 0 DC 2.037221
VB0_2_3 g_VB0_2_3 0 DC 1.822779
VA0_3_3 g_VA0_3_3 0 DC 1.790076
VB0_3_3 g_VB0_3_3 0 DC 2.069924
VA0_4_3 g_VA0_4_3 0 DC 1.998897
VB0_4_3 g_VB0_4_3 0 DC 1.861103
VA0_0_4 g_VA0_0_4 0 DC 1.832697
VB0_0_4 g_VB0_0_4 0 DC 2.027303
VA0_1_4 g_VA0_1_4 0 DC 2.038954
VB0_1_4 g_VB0_1_4 0 DC 1.821046
VA0_2_4 g_VA0_2_4 0 DC 1.942438
VB0_2_4 g_VB0_2_4 0 DC 1.917562
VA0_3_4 g_VA0_3_4 0 DC 1.869914
VB0_3_4 g_VB0_3_4 0 DC 1.990086
VA0_4_4 g_VA0_4_4 0 DC 1.906806
VB0_4_4 g_VB0_4_4 0 DC 1.953194
VA0_0_5 g_VA0_0_5 0 DC 1.788496
VB0_0_5 g_VB0_0_5 0 DC 2.071504
VA0_1_5 g_VA0_1_5 0 DC 1.817285
VB0_1_5 g_VB0_1_5 0 DC 2.042715
VA0_2_5 g_VA0_2_5 0 DC 1.981187
VB0_2_5 g_VB0_2_5 0 DC 1.878813
VA0_3_5 g_VA0_3_5 0 DC 1.974157
VB0_3_5 g_VB0_3_5 0 DC 1.885843
VA0_4_5 g_VA0_4_5 0 DC 1.964616
VB0_4_5 g_VB0_4_5 0 DC 1.895384
VA0_0_6 g_VA0_0_6 0 DC 1.895103
VB0_0_6 g_VB0_0_6 0 DC 1.964897
VA0_1_6 g_VA0_1_6 0 DC 2.079163
VB0_1_6 g_VB0_1_6 0 DC 1.780837
VA0_2_6 g_VA0_2_6 0 DC 2.074251
VB0_2_6 g_VB0_2_6 0 DC 1.785749
VA0_3_6 g_VA0_3_6 0 DC 1.985663
VB0_3_6 g_VB0_3_6 0 DC 1.874337
VA0_4_6 g_VA0_4_6 0 DC 1.975138
VB0_4_6 g_VB0_4_6 0 DC 1.884862
VA0_0_7 g_VA0_0_7 0 DC 1.986534
VB0_0_7 g_VB0_0_7 0 DC 1.873466
VA0_1_7 g_VA0_1_7 0 DC 1.896676
VB0_1_7 g_VB0_1_7 0 DC 1.963324
VA0_2_7 g_VA0_2_7 0 DC 1.820529
VB0_2_7 g_VB0_2_7 0 DC 2.039471
VA0_3_7 g_VA0_3_7 0 DC 1.996447
VB0_3_7 g_VB0_3_7 0 DC 1.863553
VA0_4_7 g_VA0_4_7 0 DC 1.937606
VB0_4_7 g_VB0_4_7 0 DC 1.922394
VA1_0_1 g_VA1_0_1 0 DC 1.886967
VB1_0_1 g_VB1_0_1 0 DC 1.973033
VA1_1_1 g_VA1_1_1 0 DC 1.926788
VB1_1_1 g_VB1_1_1 0 DC 1.933212
VA1_2_1 g_VA1_2_1 0 DC 2.018328
VB1_2_1 g_VB1_2_1 0 DC 1.841672
VA1_3_1 g_VA1_3_1 0 DC 2.028432
VB1_3_1 g_VB1_3_1 0 DC 1.831568
VA1_4_1 g_VA1_4_1 0 DC 1.897751
VB1_4_1 g_VB1_4_1 0 DC 1.962249
VA1_5_1 g_VA1_5_1 0 DC 1.946221
VB1_5_1 g_VB1_5_1 0 DC 1.913779
VA1_6_1 g_VA1_6_1 0 DC 1.889604
VB1_6_1 g_VB1_6_1 0 DC 1.970396
VA1_7_1 g_VA1_7_1 0 DC 1.951385
VB1_7_1 g_VB1_7_1 0 DC 1.908615
VA1_0_2 g_VA1_0_2 0 DC 1.893242
VB1_0_2 g_VB1_0_2 0 DC 1.966758
VA1_1_2 g_VA1_1_2 0 DC 1.905421
VB1_1_2 g_VB1_1_2 0 DC 1.954579
VA1_2_2 g_VA1_2_2 0 DC 2.018506
VB1_2_2 g_VB1_2_2 0 DC 1.841494
VA1_3_2 g_VA1_3_2 0 DC 1.868125
VB1_3_2 g_VB1_3_2 0 DC 1.991875
VA1_4_2 g_VA1_4_2 0 DC 1.957936
VB1_4_2 g_VB1_4_2 0 DC 1.902064
VA1_5_2 g_VA1_5_2 0 DC 1.835664
VB1_5_2 g_VB1_5_2 0 DC 2.024336
VA1_6_2 g_VA1_6_2 0 DC 2.005437
VB1_6_2 g_VB1_6_2 0 DC 1.854563
VA1_7_2 g_VA1_7_2 0 DC 1.995108
VB1_7_2 g_VB1_7_2 0 DC 1.864892
VA1_0_3 g_VA1_0_3 0 DC 1.870895
VB1_0_3 g_VB1_0_3 0 DC 1.989105
VA1_1_3 g_VA1_1_3 0 DC 2.015379
VB1_1_3 g_VB1_1_3 0 DC 1.844621
VA1_2_3 g_VA1_2_3 0 DC 1.829893
VB1_2_3 g_VB1_2_3 0 DC 2.030107
VA1_3_3 g_VA1_3_3 0 DC 1.892835
VB1_3_3 g_VB1_3_3 0 DC 1.957165
VA1_4_3 g_VA1_4_3 0 DC 1.850691
VB1_4_3 g_VB1_4_3 0 DC 2.009309
VA1_5_3 g_VA1_5_3 0 DC 1.918738
VB1_5_3 g_VB1_5_3 0 DC 1.941262
VA1_6_3 g_VA1_6_3 0 DC 1.997200
VB1_6_3 g_VB1_6_3 0 DC 1.862800
VA1_7_3 g_VA1_7_3 0 DC 1.868915
VB1_7_3 g_VB1_7_3 0 DC 1.991085

* ---- trainable per-layer gain (diff-pair tail bias) ----
VT0 g_VT0 0 DC 0.850000
VT1 g_VT1 0 DC 0.850000

* ===== layer 0: 4 -> 7 (four-quadrant) =====
* column pair cp0_1/cn0_1: 4 four-quadrant synapses + bias row
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
MVA0_3_1P cp0_1 g_VA0_3_1 xp3 0 NCH L=1u W=4u
MVB0_3_1P cp0_1 g_VB0_3_1 xm3 0 NCH L=1u W=4u
MVB0_3_1N cn0_1 g_VB0_3_1 xp3 0 NCH L=1u W=4u
MVA0_3_1N cn0_1 g_VA0_3_1 xm3 0 NCH L=1u W=4u
MVA0_4_1P cp0_1 g_VA0_4_1 xp4 0 NCH L=1u W=4u
MVB0_4_1P cp0_1 g_VB0_4_1 xm4 0 NCH L=1u W=4u
MVB0_4_1N cn0_1 g_VB0_4_1 xp4 0 NCH L=1u W=4u
MVA0_4_1N cn0_1 g_VA0_4_1 xm4 0 NCH L=1u W=4u
RLP0_1 vdd cp0_1 6k
RLN0_1 vdd cn0_1 6k
CCP0_1 cp0_1 0 10f
CCN0_1 cn0_1 0 10f
MDP0_1 ob0_1 cp0_1 t0_1 0 NCH L=1u W=8u
MDN0_1 o0_1 cn0_1 t0_1 0 NCH L=1u W=8u
RDP0_1 vdd ob0_1 200k
RDN0_1 vdd o0_1 200k
MT0_1 t0_1 g_VT0 0 0 NCH L=1u W=8u
COP0_1 o0_1 0 10f
COM0_1 ob0_1 0 10f

* column pair cp0_2/cn0_2: 4 four-quadrant synapses + bias row
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
MVA0_3_2P cp0_2 g_VA0_3_2 xp3 0 NCH L=1u W=4u
MVB0_3_2P cp0_2 g_VB0_3_2 xm3 0 NCH L=1u W=4u
MVB0_3_2N cn0_2 g_VB0_3_2 xp3 0 NCH L=1u W=4u
MVA0_3_2N cn0_2 g_VA0_3_2 xm3 0 NCH L=1u W=4u
MVA0_4_2P cp0_2 g_VA0_4_2 xp4 0 NCH L=1u W=4u
MVB0_4_2P cp0_2 g_VB0_4_2 xm4 0 NCH L=1u W=4u
MVB0_4_2N cn0_2 g_VB0_4_2 xp4 0 NCH L=1u W=4u
MVA0_4_2N cn0_2 g_VA0_4_2 xm4 0 NCH L=1u W=4u
RLP0_2 vdd cp0_2 6k
RLN0_2 vdd cn0_2 6k
CCP0_2 cp0_2 0 10f
CCN0_2 cn0_2 0 10f
MDP0_2 ob0_2 cp0_2 t0_2 0 NCH L=1u W=8u
MDN0_2 o0_2 cn0_2 t0_2 0 NCH L=1u W=8u
RDP0_2 vdd ob0_2 200k
RDN0_2 vdd o0_2 200k
MT0_2 t0_2 g_VT0 0 0 NCH L=1u W=8u
COP0_2 o0_2 0 10f
COM0_2 ob0_2 0 10f

* column pair cp0_3/cn0_3: 4 four-quadrant synapses + bias row
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
MVA0_3_3P cp0_3 g_VA0_3_3 xp3 0 NCH L=1u W=4u
MVB0_3_3P cp0_3 g_VB0_3_3 xm3 0 NCH L=1u W=4u
MVB0_3_3N cn0_3 g_VB0_3_3 xp3 0 NCH L=1u W=4u
MVA0_3_3N cn0_3 g_VA0_3_3 xm3 0 NCH L=1u W=4u
MVA0_4_3P cp0_3 g_VA0_4_3 xp4 0 NCH L=1u W=4u
MVB0_4_3P cp0_3 g_VB0_4_3 xm4 0 NCH L=1u W=4u
MVB0_4_3N cn0_3 g_VB0_4_3 xp4 0 NCH L=1u W=4u
MVA0_4_3N cn0_3 g_VA0_4_3 xm4 0 NCH L=1u W=4u
RLP0_3 vdd cp0_3 6k
RLN0_3 vdd cn0_3 6k
CCP0_3 cp0_3 0 10f
CCN0_3 cn0_3 0 10f
MDP0_3 ob0_3 cp0_3 t0_3 0 NCH L=1u W=8u
MDN0_3 o0_3 cn0_3 t0_3 0 NCH L=1u W=8u
RDP0_3 vdd ob0_3 200k
RDN0_3 vdd o0_3 200k
MT0_3 t0_3 g_VT0 0 0 NCH L=1u W=8u
COP0_3 o0_3 0 10f
COM0_3 ob0_3 0 10f

* column pair cp0_4/cn0_4: 4 four-quadrant synapses + bias row
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
MVA0_3_4P cp0_4 g_VA0_3_4 xp3 0 NCH L=1u W=4u
MVB0_3_4P cp0_4 g_VB0_3_4 xm3 0 NCH L=1u W=4u
MVB0_3_4N cn0_4 g_VB0_3_4 xp3 0 NCH L=1u W=4u
MVA0_3_4N cn0_4 g_VA0_3_4 xm3 0 NCH L=1u W=4u
MVA0_4_4P cp0_4 g_VA0_4_4 xp4 0 NCH L=1u W=4u
MVB0_4_4P cp0_4 g_VB0_4_4 xm4 0 NCH L=1u W=4u
MVB0_4_4N cn0_4 g_VB0_4_4 xp4 0 NCH L=1u W=4u
MVA0_4_4N cn0_4 g_VA0_4_4 xm4 0 NCH L=1u W=4u
RLP0_4 vdd cp0_4 6k
RLN0_4 vdd cn0_4 6k
CCP0_4 cp0_4 0 10f
CCN0_4 cn0_4 0 10f
MDP0_4 ob0_4 cp0_4 t0_4 0 NCH L=1u W=8u
MDN0_4 o0_4 cn0_4 t0_4 0 NCH L=1u W=8u
RDP0_4 vdd ob0_4 200k
RDN0_4 vdd o0_4 200k
MT0_4 t0_4 g_VT0 0 0 NCH L=1u W=8u
COP0_4 o0_4 0 10f
COM0_4 ob0_4 0 10f

* column pair cp0_5/cn0_5: 4 four-quadrant synapses + bias row
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
MVA0_3_5P cp0_5 g_VA0_3_5 xp3 0 NCH L=1u W=4u
MVB0_3_5P cp0_5 g_VB0_3_5 xm3 0 NCH L=1u W=4u
MVB0_3_5N cn0_5 g_VB0_3_5 xp3 0 NCH L=1u W=4u
MVA0_3_5N cn0_5 g_VA0_3_5 xm3 0 NCH L=1u W=4u
MVA0_4_5P cp0_5 g_VA0_4_5 xp4 0 NCH L=1u W=4u
MVB0_4_5P cp0_5 g_VB0_4_5 xm4 0 NCH L=1u W=4u
MVB0_4_5N cn0_5 g_VB0_4_5 xp4 0 NCH L=1u W=4u
MVA0_4_5N cn0_5 g_VA0_4_5 xm4 0 NCH L=1u W=4u
RLP0_5 vdd cp0_5 6k
RLN0_5 vdd cn0_5 6k
CCP0_5 cp0_5 0 10f
CCN0_5 cn0_5 0 10f
MDP0_5 ob0_5 cp0_5 t0_5 0 NCH L=1u W=8u
MDN0_5 o0_5 cn0_5 t0_5 0 NCH L=1u W=8u
RDP0_5 vdd ob0_5 200k
RDN0_5 vdd o0_5 200k
MT0_5 t0_5 g_VT0 0 0 NCH L=1u W=8u
COP0_5 o0_5 0 10f
COM0_5 ob0_5 0 10f

* column pair cp0_6/cn0_6: 4 four-quadrant synapses + bias row
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
MVA0_3_6P cp0_6 g_VA0_3_6 xp3 0 NCH L=1u W=4u
MVB0_3_6P cp0_6 g_VB0_3_6 xm3 0 NCH L=1u W=4u
MVB0_3_6N cn0_6 g_VB0_3_6 xp3 0 NCH L=1u W=4u
MVA0_3_6N cn0_6 g_VA0_3_6 xm3 0 NCH L=1u W=4u
MVA0_4_6P cp0_6 g_VA0_4_6 xp4 0 NCH L=1u W=4u
MVB0_4_6P cp0_6 g_VB0_4_6 xm4 0 NCH L=1u W=4u
MVB0_4_6N cn0_6 g_VB0_4_6 xp4 0 NCH L=1u W=4u
MVA0_4_6N cn0_6 g_VA0_4_6 xm4 0 NCH L=1u W=4u
RLP0_6 vdd cp0_6 6k
RLN0_6 vdd cn0_6 6k
CCP0_6 cp0_6 0 10f
CCN0_6 cn0_6 0 10f
MDP0_6 ob0_6 cp0_6 t0_6 0 NCH L=1u W=8u
MDN0_6 o0_6 cn0_6 t0_6 0 NCH L=1u W=8u
RDP0_6 vdd ob0_6 200k
RDN0_6 vdd o0_6 200k
MT0_6 t0_6 g_VT0 0 0 NCH L=1u W=8u
COP0_6 o0_6 0 10f
COM0_6 ob0_6 0 10f

* column pair cp0_7/cn0_7: 4 four-quadrant synapses + bias row
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
MVA0_3_7P cp0_7 g_VA0_3_7 xp3 0 NCH L=1u W=4u
MVB0_3_7P cp0_7 g_VB0_3_7 xm3 0 NCH L=1u W=4u
MVB0_3_7N cn0_7 g_VB0_3_7 xp3 0 NCH L=1u W=4u
MVA0_3_7N cn0_7 g_VA0_3_7 xm3 0 NCH L=1u W=4u
MVA0_4_7P cp0_7 g_VA0_4_7 xp4 0 NCH L=1u W=4u
MVB0_4_7P cp0_7 g_VB0_4_7 xm4 0 NCH L=1u W=4u
MVB0_4_7N cn0_7 g_VB0_4_7 xp4 0 NCH L=1u W=4u
MVA0_4_7N cn0_7 g_VA0_4_7 xm4 0 NCH L=1u W=4u
RLP0_7 vdd cp0_7 6k
RLN0_7 vdd cn0_7 6k
CCP0_7 cp0_7 0 10f
CCN0_7 cn0_7 0 10f
MDP0_7 ob0_7 cp0_7 t0_7 0 NCH L=1u W=8u
MDN0_7 o0_7 cn0_7 t0_7 0 NCH L=1u W=8u
RDP0_7 vdd ob0_7 200k
RDN0_7 vdd o0_7 200k
MT0_7 t0_7 g_VT0 0 0 NCH L=1u W=8u
COP0_7 o0_7 0 10f
COM0_7 ob0_7 0 10f


* ===== layer 1: 7 -> 3 (four-quadrant) =====
* column pair cp1_1/cn1_1: 7 four-quadrant synapses + bias row
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
RLP1_1 vdd cp1_1 6k
RLN1_1 vdd cn1_1 6k
CCP1_1 cp1_1 0 10f
CCN1_1 cn1_1 0 10f
MDP1_1 ob1_1 cp1_1 t1_1 0 NCH L=1u W=8u
MDN1_1 o1_1 cn1_1 t1_1 0 NCH L=1u W=8u
RDP1_1 vdd ob1_1 200k
RDN1_1 vdd o1_1 200k
MT1_1 t1_1 g_VT1 0 0 NCH L=1u W=8u
COP1_1 o1_1 0 10f
COM1_1 ob1_1 0 10f

* column pair cp1_2/cn1_2: 7 four-quadrant synapses + bias row
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
RLP1_2 vdd cp1_2 6k
RLN1_2 vdd cn1_2 6k
CCP1_2 cp1_2 0 10f
CCN1_2 cn1_2 0 10f
MDP1_2 ob1_2 cp1_2 t1_2 0 NCH L=1u W=8u
MDN1_2 o1_2 cn1_2 t1_2 0 NCH L=1u W=8u
RDP1_2 vdd ob1_2 200k
RDN1_2 vdd o1_2 200k
MT1_2 t1_2 g_VT1 0 0 NCH L=1u W=8u
COP1_2 o1_2 0 10f
COM1_2 ob1_2 0 10f

* column pair cp1_3/cn1_3: 7 four-quadrant synapses + bias row
MVA1_0_3P cp1_3 g_VA1_0_3 bp 0 NCH L=1u W=4u
MVB1_0_3P cp1_3 g_VB1_0_3 bm 0 NCH L=1u W=4u
MVB1_0_3N cn1_3 g_VB1_0_3 bp 0 NCH L=1u W=4u
MVA1_0_3N cn1_3 g_VA1_0_3 bm 0 NCH L=1u W=4u
MVA1_1_3P cp1_3 g_VA1_1_3 o0_1 0 NCH L=1u W=4u
MVB1_1_3P cp1_3 g_VB1_1_3 ob0_1 0 NCH L=1u W=4u
MVB1_1_3N cn1_3 g_VB1_1_3 o0_1 0 NCH L=1u W=4u
MVA1_1_3N cn1_3 g_VA1_1_3 ob0_1 0 NCH L=1u W=4u
MVA1_2_3P cp1_3 g_VA1_2_3 o0_2 0 NCH L=1u W=4u
MVB1_2_3P cp1_3 g_VB1_2_3 ob0_2 0 NCH L=1u W=4u
MVB1_2_3N cn1_3 g_VB1_2_3 o0_2 0 NCH L=1u W=4u
MVA1_2_3N cn1_3 g_VA1_2_3 ob0_2 0 NCH L=1u W=4u
MVA1_3_3P cp1_3 g_VA1_3_3 o0_3 0 NCH L=1u W=4u
MVB1_3_3P cp1_3 g_VB1_3_3 ob0_3 0 NCH L=1u W=4u
MVB1_3_3N cn1_3 g_VB1_3_3 o0_3 0 NCH L=1u W=4u
MVA1_3_3N cn1_3 g_VA1_3_3 ob0_3 0 NCH L=1u W=4u
MVA1_4_3P cp1_3 g_VA1_4_3 o0_4 0 NCH L=1u W=4u
MVB1_4_3P cp1_3 g_VB1_4_3 ob0_4 0 NCH L=1u W=4u
MVB1_4_3N cn1_3 g_VB1_4_3 o0_4 0 NCH L=1u W=4u
MVA1_4_3N cn1_3 g_VA1_4_3 ob0_4 0 NCH L=1u W=4u
MVA1_5_3P cp1_3 g_VA1_5_3 o0_5 0 NCH L=1u W=4u
MVB1_5_3P cp1_3 g_VB1_5_3 ob0_5 0 NCH L=1u W=4u
MVB1_5_3N cn1_3 g_VB1_5_3 o0_5 0 NCH L=1u W=4u
MVA1_5_3N cn1_3 g_VA1_5_3 ob0_5 0 NCH L=1u W=4u
MVA1_6_3P cp1_3 g_VA1_6_3 o0_6 0 NCH L=1u W=4u
MVB1_6_3P cp1_3 g_VB1_6_3 ob0_6 0 NCH L=1u W=4u
MVB1_6_3N cn1_3 g_VB1_6_3 o0_6 0 NCH L=1u W=4u
MVA1_6_3N cn1_3 g_VA1_6_3 ob0_6 0 NCH L=1u W=4u
MVA1_7_3P cp1_3 g_VA1_7_3 o0_7 0 NCH L=1u W=4u
MVB1_7_3P cp1_3 g_VB1_7_3 ob0_7 0 NCH L=1u W=4u
MVB1_7_3N cn1_3 g_VB1_7_3 o0_7 0 NCH L=1u W=4u
MVA1_7_3N cn1_3 g_VA1_7_3 ob0_7 0 NCH L=1u W=4u
RLP1_3 vdd cp1_3 6k
RLN1_3 vdd cn1_3 6k
CCP1_3 cp1_3 0 10f
CCN1_3 cn1_3 0 10f
MDP1_3 ob1_3 cp1_3 t1_3 0 NCH L=1u W=8u
MDN1_3 o1_3 cn1_3 t1_3 0 NCH L=1u W=8u
RDP1_3 vdd ob1_3 200k
RDN1_3 vdd o1_3 200k
MT1_3 t1_3 g_VT1 0 0 NCH L=1u W=8u
COP1_3 o1_3 0 10f
COM1_3 ob1_3 0 10f

* neutral solver seed; the data is in the input sources
.IC V(cp0_1)=1.0000 V(cn0_1)=1.0000 V(o0_1)=1.0000 V(ob0_1)=1.0000 V(cp0_2)=1.0000 V(cn0_2)=1.0000 V(o0_2)=1.0000 V(ob0_2)=1.0000 V(cp0_3)=1.0000 V(cn0_3)=1.0000 V(o0_3)=1.0000 V(ob0_3)=1.0000 V(cp0_4)=1.0000 V(cn0_4)=1.0000 V(o0_4)=1.0000 V(ob0_4)=1.0000 V(cp0_5)=1.0000 V(cn0_5)=1.0000 V(o0_5)=1.0000 V(ob0_5)=1.0000 V(cp0_6)=1.0000 V(cn0_6)=1.0000 V(o0_6)=1.0000 V(ob0_6)=1.0000 V(cp0_7)=1.0000 V(cn0_7)=1.0000 V(o0_7)=1.0000 V(ob0_7)=1.0000 V(cp1_1)=1.0000 V(cn1_1)=1.0000 V(o1_1)=1.0000 V(ob1_1)=1.0000 V(cp1_2)=1.0000 V(cn1_2)=1.0000 V(o1_2)=1.0000 V(ob1_2)=1.0000 V(cp1_3)=1.0000 V(cn1_3)=1.0000 V(o1_3)=1.0000 V(ob1_3)=1.0000

.TRAN 50n 100n

.END