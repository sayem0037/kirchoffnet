* 1T1R RESISTIVE CROSSBAR LAYER -- auto-generated
* 4 rows x 3 column pairs | 84 devices | 24 cells
* One weight = two 1T1R cells into a column pair:
*     col+ - col-  =  -Rf * sum_i (G+ - G-) * (v_i - vref)
* Each cell is a select NMOS in series with the programmed resistor, so an
* unselected row contributes no sneak current.
* readout: 5T OTA

.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3
VREF vref 0 DC 1.000000
VOTA g_vota 0 DC 0.800000

* ---- row drivers (the DACs): vref 1.0 V +- 0.3 V ----
VR1 r1 0 DC 1.069231
VR2 r2 0 DC 0.930207
VR3 r3 0 DC 1.298326
VR4 r4 0 DC 1.288501

* ---- word lines: asserted rows take part in the read ----
VWL1 wl1 0 DC 3.300000
VWL2 wl2 0 DC 3.300000
VWL3 wl3 0 DC 3.300000
VWL4 wl4 0 DC 3.300000

* ---- the array: 2 cells per weight, 1T1R each ----
* column pair cp1/cn1
MSP1_1 r1 wl1 np1_1 0 NCH L=1u W=20u
RCP1_1 np1_1 cp1 1.561056e+04
MSN1_1 r1 wl1 nm1_1 0 NCH L=1u W=20u
RCN1_1 nm1_1 cn1 1.164374e+04
MSP2_1 r2 wl2 np2_1 0 NCH L=1u W=20u
RCP2_1 np2_1 cp1 3.793287e+05
MSN2_1 r2 wl2 nm2_1 0 NCH L=1u W=20u
RCN2_1 nm2_1 cn1 5.437766e+04
MSP3_1 r3 wl3 np3_1 0 NCH L=1u W=20u
RCP3_1 np3_1 cp1 1.637815e+04
MSN3_1 r3 wl3 nm3_1 0 NCH L=1u W=20u
RCN3_1 nm3_1 cn1 3.260358e+04
MSP4_1 r4 wl4 np4_1 0 NCH L=1u W=20u
RCP4_1 np4_1 cp1 1.068694e+04
MSN4_1 r4 wl4 nm4_1 0 NCH L=1u W=20u
RCN4_1 nm4_1 cn1 7.516511e+04
MPP11 P1_m P1_m vdd vdd PCH L=1u W=16u
MPP12 op1 P1_m vdd vdd PCH L=1u W=16u
MNP11 P1_m vref sp1 0 NCH L=1u W=8u
MNP12 op1 cp1 sp1 0 NCH L=1u W=8u
MTP1 sp1 g_vota 0 0 NCH L=1u W=8u
MPN11 N1_m N1_m vdd vdd PCH L=1u W=16u
MPN12 on1 N1_m vdd vdd PCH L=1u W=16u
MNN11 N1_m vref sn1 0 NCH L=1u W=8u
MNN12 on1 cn1 sn1 0 NCH L=1u W=8u
MTN1 sn1 g_vota 0 0 NCH L=1u W=8u
RFP1 op1 cp1 2.000000e+03
RFN1 on1 cn1 2.000000e+03
CP1 cp1 0 10f
CN1 cn1 0 10f

* column pair cp2/cn2
MSP1_2 r1 wl1 np1_2 0 NCH L=1u W=20u
RCP1_2 np1_2 cp2 3.608951e+04
MSN1_2 r1 wl1 nm1_2 0 NCH L=1u W=20u
RCN1_2 nm1_2 cn2 2.312154e+05
MSP2_2 r2 wl2 np2_2 0 NCH L=1u W=20u
RCP2_2 np2_2 cp2 1.226787e+04
MSN2_2 r2 wl2 nm2_2 0 NCH L=1u W=20u
RCN2_2 nm2_2 cn2 1.156675e+04
MSP3_2 r3 wl3 np3_2 0 NCH L=1u W=20u
RCP3_2 np3_2 cp2 1.365744e+04
MSN3_2 r3 wl3 nm3_2 0 NCH L=1u W=20u
RCN3_2 nm3_2 cn2 2.333938e+04
MSP4_2 r4 wl4 np4_2 0 NCH L=1u W=20u
RCP4_2 np4_2 cp2 1.222950e+04
MSN4_2 r4 wl4 nm4_2 0 NCH L=1u W=20u
RCN4_2 nm4_2 cn2 1.483860e+04
MPP21 P2_m P2_m vdd vdd PCH L=1u W=16u
MPP22 op2 P2_m vdd vdd PCH L=1u W=16u
MNP21 P2_m vref sp2 0 NCH L=1u W=8u
MNP22 op2 cp2 sp2 0 NCH L=1u W=8u
MTP2 sp2 g_vota 0 0 NCH L=1u W=8u
MPN21 N2_m N2_m vdd vdd PCH L=1u W=16u
MPN22 on2 N2_m vdd vdd PCH L=1u W=16u
MNN21 N2_m vref sn2 0 NCH L=1u W=8u
MNN22 on2 cn2 sn2 0 NCH L=1u W=8u
MTN2 sn2 g_vota 0 0 NCH L=1u W=8u
RFP2 op2 cp2 2.000000e+03
RFN2 on2 cn2 2.000000e+03
CP2 cp2 0 10f
CN2 cn2 0 10f

* column pair cp3/cn3
MSP1_3 r1 wl1 np1_3 0 NCH L=1u W=20u
RCP1_3 np1_3 cp3 1.977700e+05
MSN1_3 r1 wl1 nm1_3 0 NCH L=1u W=20u
RCN1_3 nm1_3 cn3 1.365451e+04
MSP2_3 r2 wl2 np2_3 0 NCH L=1u W=20u
RCP2_3 np2_3 cp3 1.094537e+04
MSN2_3 r2 wl2 nm2_3 0 NCH L=1u W=20u
RCN2_3 nm2_3 cn3 1.831346e+04
MSP3_3 r3 wl3 np3_3 0 NCH L=1u W=20u
RCP3_3 np3_3 cp3 1.824189e+04
MSN3_3 r3 wl3 nm3_3 0 NCH L=1u W=20u
RCN3_3 nm3_3 cn3 2.629055e+05
MSP4_3 r4 wl4 np4_3 0 NCH L=1u W=20u
RCP4_3 np4_3 cp3 7.867130e+05
MSN4_3 r4 wl4 nm4_3 0 NCH L=1u W=20u
RCN4_3 nm4_3 cn3 1.536765e+04
MPP31 P3_m P3_m vdd vdd PCH L=1u W=16u
MPP32 op3 P3_m vdd vdd PCH L=1u W=16u
MNP31 P3_m vref sp3 0 NCH L=1u W=8u
MNP32 op3 cp3 sp3 0 NCH L=1u W=8u
MTP3 sp3 g_vota 0 0 NCH L=1u W=8u
MPN31 N3_m N3_m vdd vdd PCH L=1u W=16u
MPN32 on3 N3_m vdd vdd PCH L=1u W=16u
MNN31 N3_m vref sn3 0 NCH L=1u W=8u
MNN32 on3 cn3 sn3 0 NCH L=1u W=8u
MTN3 sn3 g_vota 0 0 NCH L=1u W=8u
RFP3 op3 cp3 2.000000e+03
RFN3 on3 cn3 2.000000e+03
CP3 cp3 0 10f
CN3 cn3 0 10f

* solver seed; the data is in the row drivers
.IC V(cp1)=1.0000 V(cn1)=1.0000 V(op1)=1.0000 V(on1)=1.0000 V(cp2)=1.0000 V(cn2)=1.0000 V(op2)=1.0000 V(on2)=1.0000 V(cp3)=1.0000 V(cn3)=1.0000 V(op3)=1.0000 V(on3)=1.0000

.OP

.END
