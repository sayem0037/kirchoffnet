* DIFFERENTIAL RESISTIVE CROSSBAR (XBAR) -- auto-generated
* layers [(2, 2)] | 58 devices | 12 programmable conductances
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

* ---- data: differential rows about vcm=1.0 V, swing=0.4 V ----
VIP1 xp1 0 DC 1.120000
VIM1 xm1 0 DC 0.880000
VIP2 xp2 0 DC 0.920000
VIM2 xm2 0 DC 1.080000

* fixed differential reference = the BIAS row. The column
* difference is an odd function of the data without it, so any
* boundary not through the origin is unlearnable.
VBP bp 0 DC 1.200000
VBM bm 0 DC 0.800000

* OTA tail bias
VOTA g_vota 0 DC 0.900000

* ---- neuron tail bias (per layer) ----
VT0 g_VT0 0 DC 0.850000

* ===== layer 0: 2 -> 2 (crossbar) =====
* column pair cp0_1/cn0_1: 2 four-quadrant cells + bias row
RA0_0_1P bp cp0_1 1.000000e+06
RB0_0_1P bm cp0_1 1.204218e+04
RB0_0_1N bp cn0_1 1.204218e+04
RA0_0_1N bm cn0_1 1.000000e+06
RA0_1_1P xp1 cp0_1 1.648741e+04
RB0_1_1P xm1 cp0_1 1.000000e+06
RB0_1_1N xp1 cn0_1 1.000000e+06
RA0_1_1N xm1 cn0_1 1.648741e+04
RA0_2_1P xp2 cp0_1 1.000000e+06
RB0_2_1P xm2 cp0_1 1.229067e+04
RB0_2_1N xp2 cn0_1 1.229067e+04
RA0_2_1N xm2 cn0_1 1.000000e+06
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
RFP0_1 tp0_1 cp0_1 13k
RFN0_1 tn0_1 cn0_1 13k
CCP0_1 cp0_1 0 0.1f
CCN0_1 cn0_1 0 0.1f
MDP0_1 om0_1 tp0_1 nt0_1 0 NCH L=1u W=8u
MDN0_1 op0_1 tn0_1 nt0_1 0 NCH L=1u W=8u
RDP0_1 vdd om0_1 114k
RDN0_1 vdd op0_1 114k
MT0_1 nt0_1 g_VT0 0 0 NCH L=1u W=8u
COP0_1 op0_1 0 0.1f
COM0_1 om0_1 0 0.1f

* column pair cp0_2/cn0_2: 2 four-quadrant cells + bias row
RA0_0_2P bp cp0_2 1.000000e+06
RB0_0_2P bm cp0_2 1.882831e+04
RB0_0_2N bp cn0_2 1.882831e+04
RA0_0_2N bm cn0_2 1.000000e+06
RA0_1_2P xp1 cp0_2 5.791031e+04
RB0_1_2P xm1 cp0_2 1.000000e+06
RB0_1_2N xp1 cn0_2 1.000000e+06
RA0_1_2N xm1 cn0_2 5.791031e+04
RA0_2_2P xp2 cp0_2 1.000000e+06
RB0_2_2P xm2 cp0_2 7.022045e+04
RB0_2_2N xp2 cn0_2 7.022045e+04
RA0_2_2N xm2 cn0_2 1.000000e+06
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
RFP0_2 tp0_2 cp0_2 13k
RFN0_2 tn0_2 cn0_2 13k
CCP0_2 cp0_2 0 0.1f
CCN0_2 cn0_2 0 0.1f
MDP0_2 om0_2 tp0_2 nt0_2 0 NCH L=1u W=8u
MDN0_2 op0_2 tn0_2 nt0_2 0 NCH L=1u W=8u
RDP0_2 vdd om0_2 114k
RDN0_2 vdd op0_2 114k
MT0_2 nt0_2 g_VT0 0 0 NCH L=1u W=8u
COP0_2 op0_2 0 0.1f
COM0_2 om0_2 0 0.1f

* neutral solver seed; the data is in the input sources
.IC V(cp0_1)=1.0000 V(cn0_1)=1.0000 V(tp0_1)=1.0000 V(tn0_1)=1.0000 V(op0_1)=1.0000 V(om0_1)=1.0000 V(cp0_2)=1.0000 V(cn0_2)=1.0000 V(tp0_2)=1.0000 V(tn0_2)=1.0000 V(op0_2)=1.0000 V(om0_2)=1.0000

.TRAN 50n 100n

.END