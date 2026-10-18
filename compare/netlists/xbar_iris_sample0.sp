* DIFFERENTIAL RESISTIVE CROSSBAR (XBAR) -- auto-generated
* layers [(4, 7), (7, 3)] | 406 devices | 118 programmable conductances
* Analog prior art (ISAAC / PUMA lineage), built as KFQ with the
* four NMOS synapses replaced by four conductances and the resistive
* load replaced by a virtual-ground transimpedance amplifier:
*     V(t+) - V(t-) = -Rf * sum_i (G_a - G_b)(v+ - v-)
* readout: 5T OTA
* Data converters are NOT in this netlist; they are charged in the
* area and energy columns through tech.adc_energy / tech.dac_energy.

.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3
VREF0 vref0 0 DC 1.000000
VREF1 vref1 0 DC 0.944227

* ---- data: differential rows about vcm=1.0 V, swing=0.4 V ----
VIP1 xp1 0 DC 0.925714
VIM1 xm1 0 DC 1.074286
VIP2 xp2 0 DC 0.863158
VIM2 xm2 0 DC 1.136842
VIP3 xp3 0 DC 1.010526
VIM3 xm3 0 DC 0.989474
VIP4 xp4 0 DC 1.000000
VIM4 xm4 0 DC 1.000000

* fixed differential reference = the BIAS row. The column
* difference is an odd function of the data without it, so any
* boundary not through the origin is unlearnable.
VBP bp 0 DC 1.200000
VBM bm 0 DC 0.800000

* OTA tail bias
VOTA g_vota 0 DC 0.900000

* ---- neuron tail bias (per layer) ----
VT0 g_VT0 0 DC 0.850000
VT1 g_VT1 0 DC 0.850000

* ===== layer 0: 4 -> 7 (crossbar) =====
* column pair cp0_1/cn0_1: 4 four-quadrant cells + bias row
RA0_0_1P bp cp0_1 4.141926e+04
RB0_0_1P bm cp0_1 1.000000e+06
RB0_0_1N bp cn0_1 1.000000e+06
RA0_0_1N bm cn0_1 4.141926e+04
RA0_1_1P xp1 cp0_1 5.590029e+04
RB0_1_1P xm1 cp0_1 1.000000e+06
RB0_1_1N xp1 cn0_1 1.000000e+06
RA0_1_1N xm1 cn0_1 5.590029e+04
RA0_2_1P xp2 cp0_1 1.000000e+04
RB0_2_1P xm2 cp0_1 1.000000e+06
RB0_2_1N xp2 cn0_1 1.000000e+06
RA0_2_1N xm2 cn0_1 1.000000e+04
RA0_3_1P xp3 cp0_1 1.000000e+06
RB0_3_1P xm3 cp0_1 1.307610e+05
RB0_3_1N xp3 cn0_1 1.307610e+05
RA0_3_1N xm3 cn0_1 1.000000e+06
RA0_4_1P xp4 cp0_1 3.570361e+05
RB0_4_1P xm4 cp0_1 1.000000e+06
RB0_4_1N xp4 cn0_1 1.000000e+06
RA0_4_1N xm4 cn0_1 3.570361e+05
MPP0_11 P0_1_m P0_1_m vdd vdd PCH L=1u W=16u
MPP0_12 tp0_1 P0_1_m vdd vdd PCH L=1u W=16u
MNP0_11 P0_1_m vref0 sp0_1 0 NCH L=1u W=8u
MNP0_12 tp0_1 cp0_1 sp0_1 0 NCH L=1u W=8u
MTP0_1 sp0_1 g_vota 0 0 NCH L=1u W=8u
MPN0_11 N0_1_m N0_1_m vdd vdd PCH L=1u W=16u
MPN0_12 tn0_1 N0_1_m vdd vdd PCH L=1u W=16u
MNN0_11 N0_1_m vref0 sn0_1 0 NCH L=1u W=8u
MNN0_12 tn0_1 cn0_1 sn0_1 0 NCH L=1u W=8u
MTN0_1 sn0_1 g_vota 0 0 NCH L=1u W=8u
RFP0_1 tp0_1 cp0_1 1.254081e+04
RFN0_1 tn0_1 cn0_1 1.254081e+04
CCP0_1 cp0_1 0 0.1f
CCN0_1 cn0_1 0 0.1f
MDP0_1 om0_1 tp0_1 nt0_1 0 NCH L=1u W=8u
MDN0_1 op0_1 tn0_1 nt0_1 0 NCH L=1u W=8u
RDP0_1 vdd om0_1 1.138901e+05
RDN0_1 vdd op0_1 1.138901e+05
MT0_1 nt0_1 g_VT0 0 0 NCH L=1u W=8u
COP0_1 op0_1 0 0.1f
COM0_1 om0_1 0 0.1f

* column pair cp0_2/cn0_2: 4 four-quadrant cells + bias row
RA0_0_2P bp cp0_2 1.000000e+06
RB0_0_2P bm cp0_2 5.193875e+04
RB0_0_2N bp cn0_2 5.193875e+04
RA0_0_2N bm cn0_2 1.000000e+06
RA0_1_2P xp1 cp0_2 1.000000e+06
RB0_1_2P xm1 cp0_2 6.894693e+04
RB0_1_2N xp1 cn0_2 6.894693e+04
RA0_1_2N xm1 cn0_2 1.000000e+06
RA0_2_2P xp2 cp0_2 1.000000e+06
RB0_2_2P xm2 cp0_2 8.042446e+04
RB0_2_2N xp2 cn0_2 8.042446e+04
RA0_2_2N xm2 cn0_2 1.000000e+06
RA0_3_2P xp3 cp0_2 2.206058e+04
RB0_3_2P xm3 cp0_2 1.000000e+06
RB0_3_2N xp3 cn0_2 1.000000e+06
RA0_3_2N xm3 cn0_2 2.206058e+04
RA0_4_2P xp4 cp0_2 7.081698e+04
RB0_4_2P xm4 cp0_2 1.000000e+06
RB0_4_2N xp4 cn0_2 1.000000e+06
RA0_4_2N xm4 cn0_2 7.081698e+04
MPP0_21 P0_2_m P0_2_m vdd vdd PCH L=1u W=16u
MPP0_22 tp0_2 P0_2_m vdd vdd PCH L=1u W=16u
MNP0_21 P0_2_m vref0 sp0_2 0 NCH L=1u W=8u
MNP0_22 tp0_2 cp0_2 sp0_2 0 NCH L=1u W=8u
MTP0_2 sp0_2 g_vota 0 0 NCH L=1u W=8u
MPN0_21 N0_2_m N0_2_m vdd vdd PCH L=1u W=16u
MPN0_22 tn0_2 N0_2_m vdd vdd PCH L=1u W=16u
MNN0_21 N0_2_m vref0 sn0_2 0 NCH L=1u W=8u
MNN0_22 tn0_2 cn0_2 sn0_2 0 NCH L=1u W=8u
MTN0_2 sn0_2 g_vota 0 0 NCH L=1u W=8u
RFP0_2 tp0_2 cp0_2 1.254081e+04
RFN0_2 tn0_2 cn0_2 1.254081e+04
CCP0_2 cp0_2 0 0.1f
CCN0_2 cn0_2 0 0.1f
MDP0_2 om0_2 tp0_2 nt0_2 0 NCH L=1u W=8u
MDN0_2 op0_2 tn0_2 nt0_2 0 NCH L=1u W=8u
RDP0_2 vdd om0_2 1.138901e+05
RDN0_2 vdd op0_2 1.138901e+05
MT0_2 nt0_2 g_VT0 0 0 NCH L=1u W=8u
COP0_2 op0_2 0 0.1f
COM0_2 om0_2 0 0.1f

* column pair cp0_3/cn0_3: 4 four-quadrant cells + bias row
RA0_0_3P bp cp0_3 1.000000e+06
RB0_0_3P bm cp0_3 6.477037e+04
RB0_0_3N bp cn0_3 6.477037e+04
RA0_0_3N bm cn0_3 1.000000e+06
RA0_1_3P xp1 cp0_3 1.000000e+06
RB0_1_3P xm1 cp0_3 2.508652e+05
RB0_1_3N xp1 cn0_3 2.508652e+05
RA0_1_3N xm1 cn0_3 1.000000e+06
RA0_2_3P xp2 cp0_3 1.000000e+06
RB0_2_3P xm2 cp0_3 1.853432e+05
RB0_2_3N xp2 cn0_3 1.853432e+05
RA0_2_3N xm2 cn0_3 1.000000e+06
RA0_3_3P xp3 cp0_3 1.000000e+06
RB0_3_3P xm3 cp0_3 1.107795e+05
RB0_3_3N xp3 cn0_3 1.107795e+05
RA0_3_3N xm3 cn0_3 1.000000e+06
RA0_4_3P xp4 cp0_3 5.711085e+05
RB0_4_3P xm4 cp0_3 1.000000e+06
RB0_4_3N xp4 cn0_3 1.000000e+06
RA0_4_3N xm4 cn0_3 5.711085e+05
MPP0_31 P0_3_m P0_3_m vdd vdd PCH L=1u W=16u
MPP0_32 tp0_3 P0_3_m vdd vdd PCH L=1u W=16u
MNP0_31 P0_3_m vref0 sp0_3 0 NCH L=1u W=8u
MNP0_32 tp0_3 cp0_3 sp0_3 0 NCH L=1u W=8u
MTP0_3 sp0_3 g_vota 0 0 NCH L=1u W=8u
MPN0_31 N0_3_m N0_3_m vdd vdd PCH L=1u W=16u
MPN0_32 tn0_3 N0_3_m vdd vdd PCH L=1u W=16u
MNN0_31 N0_3_m vref0 sn0_3 0 NCH L=1u W=8u
MNN0_32 tn0_3 cn0_3 sn0_3 0 NCH L=1u W=8u
MTN0_3 sn0_3 g_vota 0 0 NCH L=1u W=8u
RFP0_3 tp0_3 cp0_3 1.254081e+04
RFN0_3 tn0_3 cn0_3 1.254081e+04
CCP0_3 cp0_3 0 0.1f
CCN0_3 cn0_3 0 0.1f
MDP0_3 om0_3 tp0_3 nt0_3 0 NCH L=1u W=8u
MDN0_3 op0_3 tn0_3 nt0_3 0 NCH L=1u W=8u
RDP0_3 vdd om0_3 1.138901e+05
RDN0_3 vdd op0_3 1.138901e+05
MT0_3 nt0_3 g_VT0 0 0 NCH L=1u W=8u
COP0_3 op0_3 0 0.1f
COM0_3 om0_3 0 0.1f

* column pair cp0_4/cn0_4: 4 four-quadrant cells + bias row
RA0_0_4P bp cp0_4 1.000000e+06
RB0_0_4P bm cp0_4 2.353246e+04
RB0_0_4N bp cn0_4 2.353246e+04
RA0_0_4N bm cn0_4 1.000000e+06
RA0_1_4P xp1 cp0_4 1.000000e+06
RB0_1_4P xm1 cp0_4 8.809761e+04
RB0_1_4N xp1 cn0_4 8.809761e+04
RA0_1_4N xm1 cn0_4 1.000000e+06
RA0_2_4P xp2 cp0_4 1.000000e+06
RB0_2_4P xm2 cp0_4 4.882264e+04
RB0_2_4N xp2 cn0_4 4.882264e+04
RA0_2_4N xm2 cn0_4 1.000000e+06
RA0_3_4P xp3 cp0_4 2.295967e+04
RB0_3_4P xm3 cp0_4 1.000000e+06
RB0_3_4N xp3 cn0_4 1.000000e+06
RA0_3_4N xm3 cn0_4 2.295967e+04
RA0_4_4P xp4 cp0_4 2.151148e+04
RB0_4_4P xm4 cp0_4 1.000000e+06
RB0_4_4N xp4 cn0_4 1.000000e+06
RA0_4_4N xm4 cn0_4 2.151148e+04
MPP0_41 P0_4_m P0_4_m vdd vdd PCH L=1u W=16u
MPP0_42 tp0_4 P0_4_m vdd vdd PCH L=1u W=16u
MNP0_41 P0_4_m vref0 sp0_4 0 NCH L=1u W=8u
MNP0_42 tp0_4 cp0_4 sp0_4 0 NCH L=1u W=8u
MTP0_4 sp0_4 g_vota 0 0 NCH L=1u W=8u
MPN0_41 N0_4_m N0_4_m vdd vdd PCH L=1u W=16u
MPN0_42 tn0_4 N0_4_m vdd vdd PCH L=1u W=16u
MNN0_41 N0_4_m vref0 sn0_4 0 NCH L=1u W=8u
MNN0_42 tn0_4 cn0_4 sn0_4 0 NCH L=1u W=8u
MTN0_4 sn0_4 g_vota 0 0 NCH L=1u W=8u
RFP0_4 tp0_4 cp0_4 1.254081e+04
RFN0_4 tn0_4 cn0_4 1.254081e+04
CCP0_4 cp0_4 0 0.1f
CCN0_4 cn0_4 0 0.1f
MDP0_4 om0_4 tp0_4 nt0_4 0 NCH L=1u W=8u
MDN0_4 op0_4 tn0_4 nt0_4 0 NCH L=1u W=8u
RDP0_4 vdd om0_4 1.138901e+05
RDN0_4 vdd op0_4 1.138901e+05
MT0_4 nt0_4 g_VT0 0 0 NCH L=1u W=8u
COP0_4 op0_4 0 0.1f
COM0_4 om0_4 0 0.1f

* column pair cp0_5/cn0_5: 4 four-quadrant cells + bias row
RA0_0_5P bp cp0_5 4.680892e+04
RB0_0_5P bm cp0_5 1.000000e+06
RB0_0_5N bp cn0_5 1.000000e+06
RA0_0_5N bm cn0_5 4.680892e+04
RA0_1_5P xp1 cp0_5 5.869246e+04
RB0_1_5P xm1 cp0_5 1.000000e+06
RB0_1_5N xp1 cn0_5 1.000000e+06
RA0_1_5N xm1 cn0_5 5.869246e+04
RA0_2_5P xp2 cp0_5 1.000000e+06
RB0_2_5P xm2 cp0_5 5.659603e+04
RB0_2_5N xp2 cn0_5 5.659603e+04
RA0_2_5N xm2 cn0_5 1.000000e+06
RA0_3_5P xp3 cp0_5 5.313132e+04
RB0_3_5P xm3 cp0_5 1.000000e+06
RB0_3_5N xp3 cn0_5 1.000000e+06
RA0_3_5N xm3 cn0_5 5.313132e+04
RA0_4_5P xp4 cp0_5 4.888970e+04
RB0_4_5P xm4 cp0_5 1.000000e+06
RB0_4_5N xp4 cn0_5 1.000000e+06
RA0_4_5N xm4 cn0_5 4.888970e+04
MPP0_51 P0_5_m P0_5_m vdd vdd PCH L=1u W=16u
MPP0_52 tp0_5 P0_5_m vdd vdd PCH L=1u W=16u
MNP0_51 P0_5_m vref0 sp0_5 0 NCH L=1u W=8u
MNP0_52 tp0_5 cp0_5 sp0_5 0 NCH L=1u W=8u
MTP0_5 sp0_5 g_vota 0 0 NCH L=1u W=8u
MPN0_51 N0_5_m N0_5_m vdd vdd PCH L=1u W=16u
MPN0_52 tn0_5 N0_5_m vdd vdd PCH L=1u W=16u
MNN0_51 N0_5_m vref0 sn0_5 0 NCH L=1u W=8u
MNN0_52 tn0_5 cn0_5 sn0_5 0 NCH L=1u W=8u
MTN0_5 sn0_5 g_vota 0 0 NCH L=1u W=8u
RFP0_5 tp0_5 cp0_5 1.254081e+04
RFN0_5 tn0_5 cn0_5 1.254081e+04
CCP0_5 cp0_5 0 0.1f
CCN0_5 cn0_5 0 0.1f
MDP0_5 om0_5 tp0_5 nt0_5 0 NCH L=1u W=8u
MDN0_5 op0_5 tn0_5 nt0_5 0 NCH L=1u W=8u
RDP0_5 vdd om0_5 1.138901e+05
RDN0_5 vdd op0_5 1.138901e+05
MT0_5 nt0_5 g_VT0 0 0 NCH L=1u W=8u
COP0_5 op0_5 0 0.1f
COM0_5 om0_5 0 0.1f

* column pair cp0_6/cn0_6: 4 four-quadrant cells + bias row
RA0_0_6P bp cp0_6 5.142956e+04
RB0_0_6P bm cp0_6 1.000000e+06
RB0_0_6N bp cn0_6 1.000000e+06
RA0_0_6N bm cn0_6 5.142956e+04
RA0_1_6P xp1 cp0_6 5.606857e+04
RB0_1_6P xm1 cp0_6 1.000000e+06
RB0_1_6N xp1 cn0_6 1.000000e+06
RA0_1_6N xm1 cn0_6 5.606857e+04
RA0_2_6P xp2 cp0_6 1.000000e+06
RB0_2_6P xm2 cp0_6 5.391496e+04
RB0_2_6N xp2 cn0_6 5.391496e+04
RA0_2_6N xm2 cn0_6 1.000000e+06
RA0_3_6P xp3 cp0_6 3.858153e+04
RB0_3_6P xm3 cp0_6 1.000000e+06
RB0_3_6N xp3 cn0_6 1.000000e+06
RA0_3_6N xm3 cn0_6 3.858153e+04
RA0_4_6P xp4 cp0_6 6.440815e+04
RB0_4_6P xm4 cp0_6 1.000000e+06
RB0_4_6N xp4 cn0_6 1.000000e+06
RA0_4_6N xm4 cn0_6 6.440815e+04
MPP0_61 P0_6_m P0_6_m vdd vdd PCH L=1u W=16u
MPP0_62 tp0_6 P0_6_m vdd vdd PCH L=1u W=16u
MNP0_61 P0_6_m vref0 sp0_6 0 NCH L=1u W=8u
MNP0_62 tp0_6 cp0_6 sp0_6 0 NCH L=1u W=8u
MTP0_6 sp0_6 g_vota 0 0 NCH L=1u W=8u
MPN0_61 N0_6_m N0_6_m vdd vdd PCH L=1u W=16u
MPN0_62 tn0_6 N0_6_m vdd vdd PCH L=1u W=16u
MNN0_61 N0_6_m vref0 sn0_6 0 NCH L=1u W=8u
MNN0_62 tn0_6 cn0_6 sn0_6 0 NCH L=1u W=8u
MTN0_6 sn0_6 g_vota 0 0 NCH L=1u W=8u
RFP0_6 tp0_6 cp0_6 1.254081e+04
RFN0_6 tn0_6 cn0_6 1.254081e+04
CCP0_6 cp0_6 0 0.1f
CCN0_6 cn0_6 0 0.1f
MDP0_6 om0_6 tp0_6 nt0_6 0 NCH L=1u W=8u
MDN0_6 op0_6 tn0_6 nt0_6 0 NCH L=1u W=8u
RDP0_6 vdd om0_6 1.138901e+05
RDN0_6 vdd op0_6 1.138901e+05
MT0_6 nt0_6 g_VT0 0 0 NCH L=1u W=8u
COP0_6 op0_6 0 0.1f
COM0_6 om0_6 0 0.1f

* column pair cp0_7/cn0_7: 4 four-quadrant cells + bias row
RA0_0_7P bp cp0_7 1.000000e+06
RB0_0_7P bm cp0_7 7.407221e+04
RB0_0_7N bp cn0_7 7.407221e+04
RA0_0_7N bm cn0_7 1.000000e+06
RA0_1_7P xp1 cp0_7 3.629067e+05
RB0_1_7P xm1 cp0_7 1.000000e+06
RB0_1_7N xp1 cn0_7 1.000000e+06
RA0_1_7N xm1 cn0_7 3.629067e+05
RA0_2_7P xp2 cp0_7 1.000000e+06
RB0_2_7P xm2 cp0_7 2.933507e+04
RB0_2_7N xp2 cn0_7 2.933507e+04
RA0_2_7N xm2 cn0_7 1.000000e+06
RA0_3_7P xp3 cp0_7 2.512099e+04
RB0_3_7P xm3 cp0_7 1.000000e+06
RB0_3_7N xp3 cn0_7 1.000000e+06
RA0_3_7N xm3 cn0_7 2.512099e+04
RA0_4_7P xp4 cp0_7 5.705511e+04
RB0_4_7P xm4 cp0_7 1.000000e+06
RB0_4_7N xp4 cn0_7 1.000000e+06
RA0_4_7N xm4 cn0_7 5.705511e+04
MPP0_71 P0_7_m P0_7_m vdd vdd PCH L=1u W=16u
MPP0_72 tp0_7 P0_7_m vdd vdd PCH L=1u W=16u
MNP0_71 P0_7_m vref0 sp0_7 0 NCH L=1u W=8u
MNP0_72 tp0_7 cp0_7 sp0_7 0 NCH L=1u W=8u
MTP0_7 sp0_7 g_vota 0 0 NCH L=1u W=8u
MPN0_71 N0_7_m N0_7_m vdd vdd PCH L=1u W=16u
MPN0_72 tn0_7 N0_7_m vdd vdd PCH L=1u W=16u
MNN0_71 N0_7_m vref0 sn0_7 0 NCH L=1u W=8u
MNN0_72 tn0_7 cn0_7 sn0_7 0 NCH L=1u W=8u
MTN0_7 sn0_7 g_vota 0 0 NCH L=1u W=8u
RFP0_7 tp0_7 cp0_7 1.254081e+04
RFN0_7 tn0_7 cn0_7 1.254081e+04
CCP0_7 cp0_7 0 0.1f
CCN0_7 cn0_7 0 0.1f
MDP0_7 om0_7 tp0_7 nt0_7 0 NCH L=1u W=8u
MDN0_7 op0_7 tn0_7 nt0_7 0 NCH L=1u W=8u
RDP0_7 vdd om0_7 1.138901e+05
RDN0_7 vdd op0_7 1.138901e+05
MT0_7 nt0_7 g_VT0 0 0 NCH L=1u W=8u
COP0_7 op0_7 0 0.1f
COM0_7 om0_7 0 0.1f


* ===== layer 1: 7 -> 3 (crossbar) =====
* column pair cp1_1/cn1_1: 7 four-quadrant cells + bias row
RA1_0_1P bp cp1_1 5.727452e+05
RB1_0_1P bm cp1_1 1.000000e+06
RB1_0_1N bp cn1_1 1.000000e+06
RA1_0_1N bm cn1_1 5.727452e+05
RA1_1_1P op0_1 cp1_1 8.275520e+04
RB1_1_1P om0_1 cp1_1 1.000000e+06
RB1_1_1N op0_1 cn1_1 1.000000e+06
RA1_1_1N om0_1 cn1_1 8.275520e+04
RA1_2_1P op0_2 cp1_1 1.000000e+06
RB1_2_1P om0_2 cp1_1 2.410706e+04
RB1_2_1N op0_2 cn1_1 2.410706e+04
RA1_2_1N om0_2 cn1_1 1.000000e+06
RA1_3_1P op0_3 cp1_1 1.000000e+06
RB1_3_1P om0_3 cp1_1 1.363619e+05
RB1_3_1N op0_3 cn1_1 1.363619e+05
RA1_3_1N om0_3 cn1_1 1.000000e+06
RA1_4_1P op0_4 cp1_1 1.000000e+06
RB1_4_1P om0_4 cp1_1 2.545738e+04
RB1_4_1N op0_4 cn1_1 2.545738e+04
RA1_4_1N om0_4 cn1_1 1.000000e+06
RA1_5_1P op0_5 cp1_1 1.000000e+06
RB1_5_1P om0_5 cp1_1 2.237473e+04
RB1_5_1N op0_5 cn1_1 2.237473e+04
RA1_5_1N om0_5 cn1_1 1.000000e+06
RA1_6_1P op0_6 cp1_1 1.000000e+06
RB1_6_1P om0_6 cp1_1 2.537385e+04
RB1_6_1N op0_6 cn1_1 2.537385e+04
RA1_6_1N om0_6 cn1_1 1.000000e+06
RA1_7_1P op0_7 cp1_1 1.000000e+06
RB1_7_1P om0_7 cp1_1 2.639473e+04
RB1_7_1N op0_7 cn1_1 2.639473e+04
RA1_7_1N om0_7 cn1_1 1.000000e+06
MPP1_11 P1_1_m P1_1_m vdd vdd PCH L=1u W=16u
MPP1_12 tp1_1 P1_1_m vdd vdd PCH L=1u W=16u
MNP1_11 P1_1_m vref1 sp1_1 0 NCH L=1u W=8u
MNP1_12 tp1_1 cp1_1 sp1_1 0 NCH L=1u W=8u
MTP1_1 sp1_1 g_vota 0 0 NCH L=1u W=8u
MPN1_11 N1_1_m N1_1_m vdd vdd PCH L=1u W=16u
MPN1_12 tn1_1 N1_1_m vdd vdd PCH L=1u W=16u
MNN1_11 N1_1_m vref1 sn1_1 0 NCH L=1u W=8u
MNN1_12 tn1_1 cn1_1 sn1_1 0 NCH L=1u W=8u
MTN1_1 sn1_1 g_vota 0 0 NCH L=1u W=8u
RFP1_1 tp1_1 cp1_1 1.735673e+04
RFN1_1 tn1_1 cn1_1 1.735673e+04
CCP1_1 cp1_1 0 0.1f
CCN1_1 cn1_1 0 0.1f
MDP1_1 om1_1 tp1_1 nt1_1 0 NCH L=1u W=8u
MDN1_1 op1_1 tn1_1 nt1_1 0 NCH L=1u W=8u
RDP1_1 vdd om1_1 2.000000e+05
RDN1_1 vdd op1_1 2.000000e+05
MT1_1 nt1_1 g_VT1 0 0 NCH L=1u W=8u
COP1_1 op1_1 0 0.1f
COM1_1 om1_1 0 0.1f

* column pair cp1_2/cn1_2: 7 four-quadrant cells + bias row
RA1_0_2P bp cp1_2 1.165410e+05
RB1_0_2P bm cp1_2 1.000000e+06
RB1_0_2N bp cn1_2 1.000000e+06
RA1_0_2N bm cn1_2 1.165410e+05
RA1_1_2P op0_1 cp1_2 1.000000e+06
RB1_1_2P om0_1 cp1_2 1.342149e+04
RB1_1_2N op0_1 cn1_2 1.342149e+04
RA1_1_2N om0_1 cn1_2 1.000000e+06
RA1_2_2P op0_2 cp1_2 1.000000e+06
RB1_2_2P om0_2 cp1_2 1.400212e+04
RB1_2_2N op0_2 cn1_2 1.400212e+04
RA1_2_2N om0_2 cn1_2 1.000000e+06
RA1_3_2P op0_3 cp1_2 1.000000e+06
RB1_3_2P om0_3 cp1_2 1.286941e+05
RB1_3_2N op0_3 cn1_2 1.286941e+05
RA1_3_2N om0_3 cn1_2 1.000000e+06
RA1_4_2P op0_4 cp1_2 1.000000e+06
RB1_4_2P om0_4 cp1_2 1.000000e+04
RB1_4_2N op0_4 cn1_2 1.000000e+04
RA1_4_2N om0_4 cn1_2 1.000000e+06
RA1_5_2P op0_5 cp1_2 1.585006e+04
RB1_5_2P om0_5 cp1_2 1.000000e+06
RB1_5_2N op0_5 cn1_2 1.000000e+06
RA1_5_2N om0_5 cn1_2 1.585006e+04
RA1_6_2P op0_6 cp1_2 1.941875e+04
RB1_6_2P om0_6 cp1_2 1.000000e+06
RB1_6_2N op0_6 cn1_2 1.000000e+06
RA1_6_2N om0_6 cn1_2 1.941875e+04
RA1_7_2P op0_7 cp1_2 1.000000e+06
RB1_7_2P om0_7 cp1_2 1.656683e+04
RB1_7_2N op0_7 cn1_2 1.656683e+04
RA1_7_2N om0_7 cn1_2 1.000000e+06
MPP1_21 P1_2_m P1_2_m vdd vdd PCH L=1u W=16u
MPP1_22 tp1_2 P1_2_m vdd vdd PCH L=1u W=16u
MNP1_21 P1_2_m vref1 sp1_2 0 NCH L=1u W=8u
MNP1_22 tp1_2 cp1_2 sp1_2 0 NCH L=1u W=8u
MTP1_2 sp1_2 g_vota 0 0 NCH L=1u W=8u
MPN1_21 N1_2_m N1_2_m vdd vdd PCH L=1u W=16u
MPN1_22 tn1_2 N1_2_m vdd vdd PCH L=1u W=16u
MNN1_21 N1_2_m vref1 sn1_2 0 NCH L=1u W=8u
MNN1_22 tn1_2 cn1_2 sn1_2 0 NCH L=1u W=8u
MTN1_2 sn1_2 g_vota 0 0 NCH L=1u W=8u
RFP1_2 tp1_2 cp1_2 1.735673e+04
RFN1_2 tn1_2 cn1_2 1.735673e+04
CCP1_2 cp1_2 0 0.1f
CCN1_2 cn1_2 0 0.1f
MDP1_2 om1_2 tp1_2 nt1_2 0 NCH L=1u W=8u
MDN1_2 op1_2 tn1_2 nt1_2 0 NCH L=1u W=8u
RDP1_2 vdd om1_2 2.000000e+05
RDN1_2 vdd op1_2 2.000000e+05
MT1_2 nt1_2 g_VT1 0 0 NCH L=1u W=8u
COP1_2 op1_2 0 0.1f
COM1_2 om1_2 0 0.1f

* column pair cp1_3/cn1_3: 7 four-quadrant cells + bias row
RA1_0_3P bp cp1_3 1.000000e+06
RB1_0_3P bm cp1_3 5.262403e+04
RB1_0_3N bp cn1_3 5.262403e+04
RA1_0_3N bm cn1_3 1.000000e+06
RA1_1_3P op0_1 cp1_3 7.882829e+04
RB1_1_3P om0_1 cp1_3 1.000000e+06
RB1_1_3N op0_1 cn1_3 1.000000e+06
RA1_1_3N om0_1 cn1_3 7.882829e+04
RA1_2_3P op0_2 cp1_3 2.577461e+04
RB1_2_3P om0_2 cp1_3 1.000000e+06
RB1_2_3N op0_2 cn1_3 1.000000e+06
RA1_2_3N om0_2 cn1_3 2.577461e+04
RA1_3_3P op0_3 cp1_3 1.000000e+06
RB1_3_3P om0_3 cp1_3 1.991559e+05
RB1_3_3N op0_3 cn1_3 1.991559e+05
RA1_3_3N om0_3 cn1_3 1.000000e+06
RA1_4_3P op0_4 cp1_3 1.928725e+04
RB1_4_3P om0_4 cp1_3 1.000000e+06
RB1_4_3N op0_4 cn1_3 1.000000e+06
RA1_4_3N om0_4 cn1_3 1.928725e+04
RA1_5_3P op0_5 cp1_3 3.178959e+04
RB1_5_3P om0_5 cp1_3 1.000000e+06
RB1_5_3N op0_5 cn1_3 1.000000e+06
RA1_5_3N om0_5 cn1_3 3.178959e+04
RA1_6_3P op0_6 cp1_3 4.838535e+04
RB1_6_3P om0_6 cp1_3 1.000000e+06
RB1_6_3N op0_6 cn1_3 1.000000e+06
RA1_6_3N om0_6 cn1_3 4.838535e+04
RA1_7_3P op0_7 cp1_3 1.824077e+04
RB1_7_3P om0_7 cp1_3 1.000000e+06
RB1_7_3N op0_7 cn1_3 1.000000e+06
RA1_7_3N om0_7 cn1_3 1.824077e+04
MPP1_31 P1_3_m P1_3_m vdd vdd PCH L=1u W=16u
MPP1_32 tp1_3 P1_3_m vdd vdd PCH L=1u W=16u
MNP1_31 P1_3_m vref1 sp1_3 0 NCH L=1u W=8u
MNP1_32 tp1_3 cp1_3 sp1_3 0 NCH L=1u W=8u
MTP1_3 sp1_3 g_vota 0 0 NCH L=1u W=8u
MPN1_31 N1_3_m N1_3_m vdd vdd PCH L=1u W=16u
MPN1_32 tn1_3 N1_3_m vdd vdd PCH L=1u W=16u
MNN1_31 N1_3_m vref1 sn1_3 0 NCH L=1u W=8u
MNN1_32 tn1_3 cn1_3 sn1_3 0 NCH L=1u W=8u
MTN1_3 sn1_3 g_vota 0 0 NCH L=1u W=8u
RFP1_3 tp1_3 cp1_3 1.735673e+04
RFN1_3 tn1_3 cn1_3 1.735673e+04
CCP1_3 cp1_3 0 0.1f
CCN1_3 cn1_3 0 0.1f
MDP1_3 om1_3 tp1_3 nt1_3 0 NCH L=1u W=8u
MDN1_3 op1_3 tn1_3 nt1_3 0 NCH L=1u W=8u
RDP1_3 vdd om1_3 2.000000e+05
RDN1_3 vdd op1_3 2.000000e+05
MT1_3 nt1_3 g_VT1 0 0 NCH L=1u W=8u
COP1_3 op1_3 0 0.1f
COM1_3 om1_3 0 0.1f

* neutral solver seed; the data is in the input sources
.IC V(cp0_1)=1.0000 V(cn0_1)=1.0000 V(tp0_1)=1.0000 V(tn0_1)=1.0000 V(op0_1)=1.0000 V(om0_1)=1.0000 V(cp0_2)=1.0000 V(cn0_2)=1.0000 V(tp0_2)=1.0000 V(tn0_2)=1.0000 V(op0_2)=1.0000 V(om0_2)=1.0000 V(cp0_3)=1.0000 V(cn0_3)=1.0000 V(tp0_3)=1.0000 V(tn0_3)=1.0000 V(op0_3)=1.0000 V(om0_3)=1.0000 V(cp0_4)=1.0000 V(cn0_4)=1.0000 V(tp0_4)=1.0000 V(tn0_4)=1.0000 V(op0_4)=1.0000 V(om0_4)=1.0000 V(cp0_5)=1.0000 V(cn0_5)=1.0000 V(tp0_5)=1.0000 V(tn0_5)=1.0000 V(op0_5)=1.0000 V(om0_5)=1.0000 V(cp0_6)=1.0000 V(cn0_6)=1.0000 V(tp0_6)=1.0000 V(tn0_6)=1.0000 V(op0_6)=1.0000 V(om0_6)=1.0000 V(cp0_7)=1.0000 V(cn0_7)=1.0000 V(tp0_7)=1.0000 V(tn0_7)=1.0000 V(op0_7)=1.0000 V(om0_7)=1.0000 V(cp1_1)=0.9442 V(cn1_1)=0.9442 V(tp1_1)=0.9442 V(tn1_1)=0.9442 V(op1_1)=1.0000 V(om1_1)=1.0000 V(cp1_2)=0.9442 V(cn1_2)=0.9442 V(tp1_2)=0.9442 V(tn1_2)=0.9442 V(op1_2)=1.0000 V(om1_2)=1.0000 V(cp1_3)=0.9442 V(cn1_3)=0.9442 V(tp1_3)=0.9442 V(tn1_3)=0.9442 V(op1_3)=1.0000 V(om1_3)=1.0000

.TRAN 50n 100n

.END