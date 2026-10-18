* TRAINED circle crossbar, layer 1 of 2 | write-verify run, epoch 80 checkpoint
* rows driven for test sample 0 (row 1 = bias row, x=+1)
* read: V(outp_j)-V(outn_j); ADC full scale 0.108833 V, 8 bit; then tanh(12*d) -> next layer's rows
* 1T1R RESISTIVE CROSSBAR LAYER -- auto-generated
* 3 rows x 16 column pairs | 448 devices | 96 cells
* One weight = two 1T1R cells into a column pair:
*     col+ - col-  =  -Rf * sum_i (G+ - G-) * (v_i - vref)
* Each cell is a select NMOS in series with the programmed resistor, so an
* unselected row contributes no sneak current.
* readout: 2-stage op amp

.MODEL NCH NMOS LEVEL=1 VTO=0.531 KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7
.MODEL PCH PMOS LEVEL=1 VTO=-0.71 KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7

V0 vdd 0 DC 3.3
VREF vref 0 DC 1.000000
VOTA g_vota 0 DC 0.800000

* ---- row drivers (the DACs): vref 1.0 V +- 0.3 V ----
VR1 r1 0 DC 1.300000
VR2 r2 0 DC 1.228019
VR3 r3 0 DC 0.850090

* ---- word lines: asserted rows take part in the read ----
VWL1 wl1 0 DC 3.300000
VWL2 wl2 0 DC 3.300000
VWL3 wl3 0 DC 3.300000

* ---- the array: 2 cells per weight, 1T1R each ----
* column pair cp1/cn1
MSP1_1 r1 wl1 np1_1 0 NCH L=1u W=20u
RCP1_1 np1_1 cp1 1.165229e+04
MSN1_1 r1 wl1 nm1_1 0 NCH L=1u W=20u
RCN1_1 nm1_1 cn1 2.794845e+04
MSP2_1 r2 wl2 np2_1 0 NCH L=1u W=20u
RCP2_1 np2_1 cp1 1.671265e+05
MSN2_1 r2 wl2 nm2_1 0 NCH L=1u W=20u
RCN2_1 nm2_1 cn1 1.070247e+04
MSP3_1 r3 wl3 np3_1 0 NCH L=1u W=20u
RCP3_1 np3_1 cp1 2.291631e+04
MSN3_1 r3 wl3 nm3_1 0 NCH L=1u W=20u
RCN3_1 nm3_1 cn1 1.738689e+04
MPP11 P1_m P1_m vdd vdd PCH L=1u W=16u
MPP12 P1_o1 P1_m vdd vdd PCH L=1u W=16u
MNP11 P1_m cp1 sp1 0 NCH L=1u W=8u
MNP12 P1_o1 vref sp1 0 NCH L=1u W=8u
MTP1 sp1 g_vota 0 0 NCH L=1u W=8u
MPP13 op1 P1_o1 vdd vdd PCH L=1u W=160u
MNP13 op1 g_vota 0 0 NCH L=1u W=40u
MPN11 N1_m N1_m vdd vdd PCH L=1u W=16u
MPN12 N1_o1 N1_m vdd vdd PCH L=1u W=16u
MNN11 N1_m cn1 sn1 0 NCH L=1u W=8u
MNN12 N1_o1 vref sn1 0 NCH L=1u W=8u
MTN1 sn1 g_vota 0 0 NCH L=1u W=8u
MPN13 on1 N1_o1 vdd vdd PCH L=1u W=160u
MNN13 on1 g_vota 0 0 NCH L=1u W=40u
RFP1 op1 cp1 2.000000e+03
RFN1 on1 cn1 2.000000e+03
CP1 cp1 0 10f
CN1 cn1 0 10f

* column pair cp2/cn2
MSP1_2 r1 wl1 np1_2 0 NCH L=1u W=20u
RCP1_2 np1_2 cp2 1.394630e+04
MSN1_2 r1 wl1 nm1_2 0 NCH L=1u W=20u
RCN1_2 nm1_2 cn2 2.471545e+04
MSP2_2 r2 wl2 np2_2 0 NCH L=1u W=20u
RCP2_2 np2_2 cp2 2.067839e+04
MSN2_2 r2 wl2 nm2_2 0 NCH L=1u W=20u
RCN2_2 nm2_2 cn2 2.078969e+04
MSP3_2 r3 wl3 np3_2 0 NCH L=1u W=20u
RCP3_2 np3_2 cp2 1.949707e+04
MSN3_2 r3 wl3 nm3_2 0 NCH L=1u W=20u
RCN3_2 nm3_2 cn2 2.013644e+04
MPP21 P2_m P2_m vdd vdd PCH L=1u W=16u
MPP22 P2_o1 P2_m vdd vdd PCH L=1u W=16u
MNP21 P2_m cp2 sp2 0 NCH L=1u W=8u
MNP22 P2_o1 vref sp2 0 NCH L=1u W=8u
MTP2 sp2 g_vota 0 0 NCH L=1u W=8u
MPP23 op2 P2_o1 vdd vdd PCH L=1u W=160u
MNP23 op2 g_vota 0 0 NCH L=1u W=40u
MPN21 N2_m N2_m vdd vdd PCH L=1u W=16u
MPN22 N2_o1 N2_m vdd vdd PCH L=1u W=16u
MNN21 N2_m cn2 sn2 0 NCH L=1u W=8u
MNN22 N2_o1 vref sn2 0 NCH L=1u W=8u
MTN2 sn2 g_vota 0 0 NCH L=1u W=8u
MPN23 on2 N2_o1 vdd vdd PCH L=1u W=160u
MNN23 on2 g_vota 0 0 NCH L=1u W=40u
RFP2 op2 cp2 2.000000e+03
RFN2 on2 cn2 2.000000e+03
CP2 cp2 0 10f
CN2 cn2 0 10f

* column pair cp3/cn3
MSP1_3 r1 wl1 np1_3 0 NCH L=1u W=20u
RCP1_3 np1_3 cp3 2.309487e+04
MSN1_3 r1 wl1 nm1_3 0 NCH L=1u W=20u
RCN1_3 nm1_3 cn3 1.453816e+04
MSP2_3 r2 wl2 np2_3 0 NCH L=1u W=20u
RCP2_3 np2_3 cp3 1.492694e+04
MSN2_3 r2 wl2 nm2_3 0 NCH L=1u W=20u
RCN2_3 nm2_3 cn3 1.895720e+04
MSP3_3 r3 wl3 np3_3 0 NCH L=1u W=20u
RCP3_3 np3_3 cp3 1.337884e+04
MSN3_3 r3 wl3 nm3_3 0 NCH L=1u W=20u
RCN3_3 nm3_3 cn3 4.146142e+04
MPP31 P3_m P3_m vdd vdd PCH L=1u W=16u
MPP32 P3_o1 P3_m vdd vdd PCH L=1u W=16u
MNP31 P3_m cp3 sp3 0 NCH L=1u W=8u
MNP32 P3_o1 vref sp3 0 NCH L=1u W=8u
MTP3 sp3 g_vota 0 0 NCH L=1u W=8u
MPP33 op3 P3_o1 vdd vdd PCH L=1u W=160u
MNP33 op3 g_vota 0 0 NCH L=1u W=40u
MPN31 N3_m N3_m vdd vdd PCH L=1u W=16u
MPN32 N3_o1 N3_m vdd vdd PCH L=1u W=16u
MNN31 N3_m cn3 sn3 0 NCH L=1u W=8u
MNN32 N3_o1 vref sn3 0 NCH L=1u W=8u
MTN3 sn3 g_vota 0 0 NCH L=1u W=8u
MPN33 on3 N3_o1 vdd vdd PCH L=1u W=160u
MNN33 on3 g_vota 0 0 NCH L=1u W=40u
RFP3 op3 cp3 2.000000e+03
RFN3 on3 cn3 2.000000e+03
CP3 cp3 0 10f
CN3 cn3 0 10f

* column pair cp4/cn4
MSP1_4 r1 wl1 np1_4 0 NCH L=1u W=20u
RCP1_4 np1_4 cp4 1.574893e+04
MSN1_4 r1 wl1 nm1_4 0 NCH L=1u W=20u
RCN1_4 nm1_4 cn4 3.802575e+04
MSP2_4 r2 wl2 np2_4 0 NCH L=1u W=20u
RCP2_4 np2_4 cp4 1.648367e+04
MSN2_4 r2 wl2 nm2_4 0 NCH L=1u W=20u
RCN2_4 nm2_4 cn4 1.563925e+04
MSP3_4 r3 wl3 np3_4 0 NCH L=1u W=20u
RCP3_4 np3_4 cp4 1.188887e+04
MSN3_4 r3 wl3 nm3_4 0 NCH L=1u W=20u
RCN3_4 nm3_4 cn4 9.644713e+04
MPP41 P4_m P4_m vdd vdd PCH L=1u W=16u
MPP42 P4_o1 P4_m vdd vdd PCH L=1u W=16u
MNP41 P4_m cp4 sp4 0 NCH L=1u W=8u
MNP42 P4_o1 vref sp4 0 NCH L=1u W=8u
MTP4 sp4 g_vota 0 0 NCH L=1u W=8u
MPP43 op4 P4_o1 vdd vdd PCH L=1u W=160u
MNP43 op4 g_vota 0 0 NCH L=1u W=40u
MPN41 N4_m N4_m vdd vdd PCH L=1u W=16u
MPN42 N4_o1 N4_m vdd vdd PCH L=1u W=16u
MNN41 N4_m cn4 sn4 0 NCH L=1u W=8u
MNN42 N4_o1 vref sn4 0 NCH L=1u W=8u
MTN4 sn4 g_vota 0 0 NCH L=1u W=8u
MPN43 on4 N4_o1 vdd vdd PCH L=1u W=160u
MNN43 on4 g_vota 0 0 NCH L=1u W=40u
RFP4 op4 cp4 2.000000e+03
RFN4 on4 cn4 2.000000e+03
CP4 cp4 0 10f
CN4 cn4 0 10f

* column pair cp5/cn5
MSP1_5 r1 wl1 np1_5 0 NCH L=1u W=20u
RCP1_5 np1_5 cp5 3.236539e+04
MSN1_5 r1 wl1 nm1_5 0 NCH L=1u W=20u
RCN1_5 nm1_5 cn5 1.605673e+04
MSP2_5 r2 wl2 np2_5 0 NCH L=1u W=20u
RCP2_5 np2_5 cp5 1.889322e+04
MSN2_5 r2 wl2 nm2_5 0 NCH L=1u W=20u
RCN2_5 nm2_5 cn5 1.889816e+04
MSP3_5 r3 wl3 np3_5 0 NCH L=1u W=20u
RCP3_5 np3_5 cp5 2.483261e+04
MSN3_5 r3 wl3 nm3_5 0 NCH L=1u W=20u
RCN3_5 nm3_5 cn5 2.497439e+04
MPP51 P5_m P5_m vdd vdd PCH L=1u W=16u
MPP52 P5_o1 P5_m vdd vdd PCH L=1u W=16u
MNP51 P5_m cp5 sp5 0 NCH L=1u W=8u
MNP52 P5_o1 vref sp5 0 NCH L=1u W=8u
MTP5 sp5 g_vota 0 0 NCH L=1u W=8u
MPP53 op5 P5_o1 vdd vdd PCH L=1u W=160u
MNP53 op5 g_vota 0 0 NCH L=1u W=40u
MPN51 N5_m N5_m vdd vdd PCH L=1u W=16u
MPN52 N5_o1 N5_m vdd vdd PCH L=1u W=16u
MNN51 N5_m cn5 sn5 0 NCH L=1u W=8u
MNN52 N5_o1 vref sn5 0 NCH L=1u W=8u
MTN5 sn5 g_vota 0 0 NCH L=1u W=8u
MPN53 on5 N5_o1 vdd vdd PCH L=1u W=160u
MNN53 on5 g_vota 0 0 NCH L=1u W=40u
RFP5 op5 cp5 2.000000e+03
RFN5 on5 cn5 2.000000e+03
CP5 cp5 0 10f
CN5 cn5 0 10f

* column pair cp6/cn6
MSP1_6 r1 wl1 np1_6 0 NCH L=1u W=20u
RCP1_6 np1_6 cp6 2.588811e+04
MSN1_6 r1 wl1 nm1_6 0 NCH L=1u W=20u
RCN1_6 nm1_6 cn6 1.337496e+04
MSP2_6 r2 wl2 np2_6 0 NCH L=1u W=20u
RCP2_6 np2_6 cp6 1.305411e+04
MSN2_6 r2 wl2 nm2_6 0 NCH L=1u W=20u
RCN2_6 nm2_6 cn6 6.026413e+04
MSP3_6 r3 wl3 np3_6 0 NCH L=1u W=20u
RCP3_6 np3_6 cp6 2.693540e+04
MSN3_6 r3 wl3 nm3_6 0 NCH L=1u W=20u
RCN3_6 nm3_6 cn6 1.460414e+04
MPP61 P6_m P6_m vdd vdd PCH L=1u W=16u
MPP62 P6_o1 P6_m vdd vdd PCH L=1u W=16u
MNP61 P6_m cp6 sp6 0 NCH L=1u W=8u
MNP62 P6_o1 vref sp6 0 NCH L=1u W=8u
MTP6 sp6 g_vota 0 0 NCH L=1u W=8u
MPP63 op6 P6_o1 vdd vdd PCH L=1u W=160u
MNP63 op6 g_vota 0 0 NCH L=1u W=40u
MPN61 N6_m N6_m vdd vdd PCH L=1u W=16u
MPN62 N6_o1 N6_m vdd vdd PCH L=1u W=16u
MNN61 N6_m cn6 sn6 0 NCH L=1u W=8u
MNN62 N6_o1 vref sn6 0 NCH L=1u W=8u
MTN6 sn6 g_vota 0 0 NCH L=1u W=8u
MPN63 on6 N6_o1 vdd vdd PCH L=1u W=160u
MNN63 on6 g_vota 0 0 NCH L=1u W=40u
RFP6 op6 cp6 2.000000e+03
RFN6 on6 cn6 2.000000e+03
CP6 cp6 0 10f
CN6 cn6 0 10f

* column pair cp7/cn7
MSP1_7 r1 wl1 np1_7 0 NCH L=1u W=20u
RCP1_7 np1_7 cp7 2.817048e+04
MSN1_7 r1 wl1 nm1_7 0 NCH L=1u W=20u
RCN1_7 nm1_7 cn7 1.572053e+04
MSP2_7 r2 wl2 np2_7 0 NCH L=1u W=20u
RCP2_7 np2_7 cp7 2.082028e+04
MSN2_7 r2 wl2 nm2_7 0 NCH L=1u W=20u
RCN2_7 nm2_7 cn7 2.133553e+04
MSP3_7 r3 wl3 np3_7 0 NCH L=1u W=20u
RCP3_7 np3_7 cp7 1.738008e+04
MSN3_7 r3 wl3 nm3_7 0 NCH L=1u W=20u
RCN3_7 nm3_7 cn7 1.780465e+04
MPP71 P7_m P7_m vdd vdd PCH L=1u W=16u
MPP72 P7_o1 P7_m vdd vdd PCH L=1u W=16u
MNP71 P7_m cp7 sp7 0 NCH L=1u W=8u
MNP72 P7_o1 vref sp7 0 NCH L=1u W=8u
MTP7 sp7 g_vota 0 0 NCH L=1u W=8u
MPP73 op7 P7_o1 vdd vdd PCH L=1u W=160u
MNP73 op7 g_vota 0 0 NCH L=1u W=40u
MPN71 N7_m N7_m vdd vdd PCH L=1u W=16u
MPN72 N7_o1 N7_m vdd vdd PCH L=1u W=16u
MNN71 N7_m cn7 sn7 0 NCH L=1u W=8u
MNN72 N7_o1 vref sn7 0 NCH L=1u W=8u
MTN7 sn7 g_vota 0 0 NCH L=1u W=8u
MPN73 on7 N7_o1 vdd vdd PCH L=1u W=160u
MNN73 on7 g_vota 0 0 NCH L=1u W=40u
RFP7 op7 cp7 2.000000e+03
RFN7 on7 cn7 2.000000e+03
CP7 cp7 0 10f
CN7 cn7 0 10f

* column pair cp8/cn8
MSP1_8 r1 wl1 np1_8 0 NCH L=1u W=20u
RCP1_8 np1_8 cp8 2.693966e+04
MSN1_8 r1 wl1 nm1_8 0 NCH L=1u W=20u
RCN1_8 nm1_8 cn8 1.371144e+04
MSP2_8 r2 wl2 np2_8 0 NCH L=1u W=20u
RCP2_8 np2_8 cp8 1.793280e+04
MSN2_8 r2 wl2 nm2_8 0 NCH L=1u W=20u
RCN2_8 nm2_8 cn8 1.788123e+04
MSP3_8 r3 wl3 np3_8 0 NCH L=1u W=20u
RCP3_8 np3_8 cp8 1.532109e+04
MSN3_8 r3 wl3 nm3_8 0 NCH L=1u W=20u
RCN3_8 nm3_8 cn8 1.560229e+04
MPP81 P8_m P8_m vdd vdd PCH L=1u W=16u
MPP82 P8_o1 P8_m vdd vdd PCH L=1u W=16u
MNP81 P8_m cp8 sp8 0 NCH L=1u W=8u
MNP82 P8_o1 vref sp8 0 NCH L=1u W=8u
MTP8 sp8 g_vota 0 0 NCH L=1u W=8u
MPP83 op8 P8_o1 vdd vdd PCH L=1u W=160u
MNP83 op8 g_vota 0 0 NCH L=1u W=40u
MPN81 N8_m N8_m vdd vdd PCH L=1u W=16u
MPN82 N8_o1 N8_m vdd vdd PCH L=1u W=16u
MNN81 N8_m cn8 sn8 0 NCH L=1u W=8u
MNN82 N8_o1 vref sn8 0 NCH L=1u W=8u
MTN8 sn8 g_vota 0 0 NCH L=1u W=8u
MPN83 on8 N8_o1 vdd vdd PCH L=1u W=160u
MNN83 on8 g_vota 0 0 NCH L=1u W=40u
RFP8 op8 cp8 2.000000e+03
RFN8 on8 cn8 2.000000e+03
CP8 cp8 0 10f
CN8 cn8 0 10f

* column pair cp9/cn9
MSP1_9 r1 wl1 np1_9 0 NCH L=1u W=20u
RCP1_9 np1_9 cp9 1.528143e+04
MSN1_9 r1 wl1 nm1_9 0 NCH L=1u W=20u
RCN1_9 nm1_9 cn9 2.947513e+04
MSP2_9 r2 wl2 np2_9 0 NCH L=1u W=20u
RCP2_9 np2_9 cp9 1.645216e+04
MSN2_9 r2 wl2 nm2_9 0 NCH L=1u W=20u
RCN2_9 nm2_9 cn9 1.687235e+04
MSP3_9 r3 wl3 np3_9 0 NCH L=1u W=20u
RCP3_9 np3_9 cp9 2.388086e+04
MSN3_9 r3 wl3 nm3_9 0 NCH L=1u W=20u
RCN3_9 nm3_9 cn9 2.466359e+04
MPP91 P9_m P9_m vdd vdd PCH L=1u W=16u
MPP92 P9_o1 P9_m vdd vdd PCH L=1u W=16u
MNP91 P9_m cp9 sp9 0 NCH L=1u W=8u
MNP92 P9_o1 vref sp9 0 NCH L=1u W=8u
MTP9 sp9 g_vota 0 0 NCH L=1u W=8u
MPP93 op9 P9_o1 vdd vdd PCH L=1u W=160u
MNP93 op9 g_vota 0 0 NCH L=1u W=40u
MPN91 N9_m N9_m vdd vdd PCH L=1u W=16u
MPN92 N9_o1 N9_m vdd vdd PCH L=1u W=16u
MNN91 N9_m cn9 sn9 0 NCH L=1u W=8u
MNN92 N9_o1 vref sn9 0 NCH L=1u W=8u
MTN9 sn9 g_vota 0 0 NCH L=1u W=8u
MPN93 on9 N9_o1 vdd vdd PCH L=1u W=160u
MNN93 on9 g_vota 0 0 NCH L=1u W=40u
RFP9 op9 cp9 2.000000e+03
RFN9 on9 cn9 2.000000e+03
CP9 cp9 0 10f
CN9 cn9 0 10f

* column pair cp10/cn10
MSP1_10 r1 wl1 np1_10 0 NCH L=1u W=20u
RCP1_10 np1_10 cp10 1.676395e+04
MSN1_10 r1 wl1 nm1_10 0 NCH L=1u W=20u
RCN1_10 nm1_10 cn10 2.682801e+04
MSP2_10 r2 wl2 np2_10 0 NCH L=1u W=20u
RCP2_10 np2_10 cp10 2.496136e+04
MSN2_10 r2 wl2 nm2_10 0 NCH L=1u W=20u
RCN2_10 nm2_10 cn10 1.788114e+04
MSP3_10 r3 wl3 np3_10 0 NCH L=1u W=20u
RCP3_10 np3_10 cp10 2.222696e+04
MSN3_10 r3 wl3 nm3_10 0 NCH L=1u W=20u
RCN3_10 nm3_10 cn10 1.145941e+04
MPP101 P10_m P10_m vdd vdd PCH L=1u W=16u
MPP102 P10_o1 P10_m vdd vdd PCH L=1u W=16u
MNP101 P10_m cp10 sp10 0 NCH L=1u W=8u
MNP102 P10_o1 vref sp10 0 NCH L=1u W=8u
MTP10 sp10 g_vota 0 0 NCH L=1u W=8u
MPP103 op10 P10_o1 vdd vdd PCH L=1u W=160u
MNP103 op10 g_vota 0 0 NCH L=1u W=40u
MPN101 N10_m N10_m vdd vdd PCH L=1u W=16u
MPN102 N10_o1 N10_m vdd vdd PCH L=1u W=16u
MNN101 N10_m cn10 sn10 0 NCH L=1u W=8u
MNN102 N10_o1 vref sn10 0 NCH L=1u W=8u
MTN10 sn10 g_vota 0 0 NCH L=1u W=8u
MPN103 on10 N10_o1 vdd vdd PCH L=1u W=160u
MNN103 on10 g_vota 0 0 NCH L=1u W=40u
RFP10 op10 cp10 2.000000e+03
RFN10 on10 cn10 2.000000e+03
CP10 cp10 0 10f
CN10 cn10 0 10f

* column pair cp11/cn11
MSP1_11 r1 wl1 np1_11 0 NCH L=1u W=20u
RCP1_11 np1_11 cp11 2.152761e+04
MSN1_11 r1 wl1 nm1_11 0 NCH L=1u W=20u
RCN1_11 nm1_11 cn11 2.692078e+04
MSP2_11 r2 wl2 np2_11 0 NCH L=1u W=20u
RCP2_11 np2_11 cp11 2.146784e+04
MSN2_11 r2 wl2 nm2_11 0 NCH L=1u W=20u
RCN2_11 nm2_11 cn11 1.535162e+04
MSP3_11 r3 wl3 np3_11 0 NCH L=1u W=20u
RCP3_11 np3_11 cp11 1.457779e+04
MSN3_11 r3 wl3 nm3_11 0 NCH L=1u W=20u
RCN3_11 nm3_11 cn11 2.311583e+04
MPP111 P11_m P11_m vdd vdd PCH L=1u W=16u
MPP112 P11_o1 P11_m vdd vdd PCH L=1u W=16u
MNP111 P11_m cp11 sp11 0 NCH L=1u W=8u
MNP112 P11_o1 vref sp11 0 NCH L=1u W=8u
MTP11 sp11 g_vota 0 0 NCH L=1u W=8u
MPP113 op11 P11_o1 vdd vdd PCH L=1u W=160u
MNP113 op11 g_vota 0 0 NCH L=1u W=40u
MPN111 N11_m N11_m vdd vdd PCH L=1u W=16u
MPN112 N11_o1 N11_m vdd vdd PCH L=1u W=16u
MNN111 N11_m cn11 sn11 0 NCH L=1u W=8u
MNN112 N11_o1 vref sn11 0 NCH L=1u W=8u
MTN11 sn11 g_vota 0 0 NCH L=1u W=8u
MPN113 on11 N11_o1 vdd vdd PCH L=1u W=160u
MNN113 on11 g_vota 0 0 NCH L=1u W=40u
RFP11 op11 cp11 2.000000e+03
RFN11 on11 cn11 2.000000e+03
CP11 cp11 0 10f
CN11 cn11 0 10f

* column pair cp12/cn12
MSP1_12 r1 wl1 np1_12 0 NCH L=1u W=20u
RCP1_12 np1_12 cp12 1.599237e+04
MSN1_12 r1 wl1 nm1_12 0 NCH L=1u W=20u
RCN1_12 nm1_12 cn12 3.241176e+04
MSP2_12 r2 wl2 np2_12 0 NCH L=1u W=20u
RCP2_12 np2_12 cp12 1.450532e+04
MSN2_12 r2 wl2 nm2_12 0 NCH L=1u W=20u
RCN2_12 nm2_12 cn12 9.840967e+04
MSP3_12 r3 wl3 np3_12 0 NCH L=1u W=20u
RCP3_12 np3_12 cp12 1.610577e+04
MSN3_12 r3 wl3 nm3_12 0 NCH L=1u W=20u
RCN3_12 nm3_12 cn12 1.643704e+04
MPP121 P12_m P12_m vdd vdd PCH L=1u W=16u
MPP122 P12_o1 P12_m vdd vdd PCH L=1u W=16u
MNP121 P12_m cp12 sp12 0 NCH L=1u W=8u
MNP122 P12_o1 vref sp12 0 NCH L=1u W=8u
MTP12 sp12 g_vota 0 0 NCH L=1u W=8u
MPP123 op12 P12_o1 vdd vdd PCH L=1u W=160u
MNP123 op12 g_vota 0 0 NCH L=1u W=40u
MPN121 N12_m N12_m vdd vdd PCH L=1u W=16u
MPN122 N12_o1 N12_m vdd vdd PCH L=1u W=16u
MNN121 N12_m cn12 sn12 0 NCH L=1u W=8u
MNN122 N12_o1 vref sn12 0 NCH L=1u W=8u
MTN12 sn12 g_vota 0 0 NCH L=1u W=8u
MPN123 on12 N12_o1 vdd vdd PCH L=1u W=160u
MNN123 on12 g_vota 0 0 NCH L=1u W=40u
RFP12 op12 cp12 2.000000e+03
RFN12 on12 cn12 2.000000e+03
CP12 cp12 0 10f
CN12 cn12 0 10f

* column pair cp13/cn13
MSP1_13 r1 wl1 np1_13 0 NCH L=1u W=20u
RCP1_13 np1_13 cp13 1.397039e+04
MSN1_13 r1 wl1 nm1_13 0 NCH L=1u W=20u
RCN1_13 nm1_13 cn13 3.703106e+05
MSP2_13 r2 wl2 np2_13 0 NCH L=1u W=20u
RCP2_13 np2_13 cp13 1.847494e+04
MSN2_13 r2 wl2 nm2_13 0 NCH L=1u W=20u
RCN2_13 nm2_13 cn13 2.948990e+04
MSP3_13 r3 wl3 np3_13 0 NCH L=1u W=20u
RCP3_13 np3_13 cp13 1.881553e+04
MSN3_13 r3 wl3 nm3_13 0 NCH L=1u W=20u
RCN3_13 nm3_13 cn13 2.148390e+04
MPP131 P13_m P13_m vdd vdd PCH L=1u W=16u
MPP132 P13_o1 P13_m vdd vdd PCH L=1u W=16u
MNP131 P13_m cp13 sp13 0 NCH L=1u W=8u
MNP132 P13_o1 vref sp13 0 NCH L=1u W=8u
MTP13 sp13 g_vota 0 0 NCH L=1u W=8u
MPP133 op13 P13_o1 vdd vdd PCH L=1u W=160u
MNP133 op13 g_vota 0 0 NCH L=1u W=40u
MPN131 N13_m N13_m vdd vdd PCH L=1u W=16u
MPN132 N13_o1 N13_m vdd vdd PCH L=1u W=16u
MNN131 N13_m cn13 sn13 0 NCH L=1u W=8u
MNN132 N13_o1 vref sn13 0 NCH L=1u W=8u
MTN13 sn13 g_vota 0 0 NCH L=1u W=8u
MPN133 on13 N13_o1 vdd vdd PCH L=1u W=160u
MNN133 on13 g_vota 0 0 NCH L=1u W=40u
RFP13 op13 cp13 2.000000e+03
RFN13 on13 cn13 2.000000e+03
CP13 cp13 0 10f
CN13 cn13 0 10f

* column pair cp14/cn14
MSP1_14 r1 wl1 np1_14 0 NCH L=1u W=20u
RCP1_14 np1_14 cp14 5.078732e+04
MSN1_14 r1 wl1 nm1_14 0 NCH L=1u W=20u
RCN1_14 nm1_14 cn14 1.491216e+04
MSP2_14 r2 wl2 np2_14 0 NCH L=1u W=20u
RCP2_14 np2_14 cp14 3.596384e+04
MSN2_14 r2 wl2 nm2_14 0 NCH L=1u W=20u
RCN2_14 nm2_14 cn14 1.189565e+04
MSP3_14 r3 wl3 np3_14 0 NCH L=1u W=20u
RCP3_14 np3_14 cp14 9.429264e+04
MSN3_14 r3 wl3 nm3_14 0 NCH L=1u W=20u
RCN3_14 nm3_14 cn14 1.231110e+04
MPP141 P14_m P14_m vdd vdd PCH L=1u W=16u
MPP142 P14_o1 P14_m vdd vdd PCH L=1u W=16u
MNP141 P14_m cp14 sp14 0 NCH L=1u W=8u
MNP142 P14_o1 vref sp14 0 NCH L=1u W=8u
MTP14 sp14 g_vota 0 0 NCH L=1u W=8u
MPP143 op14 P14_o1 vdd vdd PCH L=1u W=160u
MNP143 op14 g_vota 0 0 NCH L=1u W=40u
MPN141 N14_m N14_m vdd vdd PCH L=1u W=16u
MPN142 N14_o1 N14_m vdd vdd PCH L=1u W=16u
MNN141 N14_m cn14 sn14 0 NCH L=1u W=8u
MNN142 N14_o1 vref sn14 0 NCH L=1u W=8u
MTN14 sn14 g_vota 0 0 NCH L=1u W=8u
MPN143 on14 N14_o1 vdd vdd PCH L=1u W=160u
MNN143 on14 g_vota 0 0 NCH L=1u W=40u
RFP14 op14 cp14 2.000000e+03
RFN14 on14 cn14 2.000000e+03
CP14 cp14 0 10f
CN14 cn14 0 10f

* column pair cp15/cn15
MSP1_15 r1 wl1 np1_15 0 NCH L=1u W=20u
RCP1_15 np1_15 cp15 2.383031e+04
MSN1_15 r1 wl1 nm1_15 0 NCH L=1u W=20u
RCN1_15 nm1_15 cn15 1.566234e+04
MSP2_15 r2 wl2 np2_15 0 NCH L=1u W=20u
RCP2_15 np2_15 cp15 3.823664e+04
MSN2_15 r2 wl2 nm2_15 0 NCH L=1u W=20u
RCN2_15 nm2_15 cn15 1.519506e+04
MSP3_15 r3 wl3 np3_15 0 NCH L=1u W=20u
RCP3_15 np3_15 cp15 1.359586e+04
MSN3_15 r3 wl3 nm3_15 0 NCH L=1u W=20u
RCN3_15 nm3_15 cn15 2.228169e+04
MPP151 P15_m P15_m vdd vdd PCH L=1u W=16u
MPP152 P15_o1 P15_m vdd vdd PCH L=1u W=16u
MNP151 P15_m cp15 sp15 0 NCH L=1u W=8u
MNP152 P15_o1 vref sp15 0 NCH L=1u W=8u
MTP15 sp15 g_vota 0 0 NCH L=1u W=8u
MPP153 op15 P15_o1 vdd vdd PCH L=1u W=160u
MNP153 op15 g_vota 0 0 NCH L=1u W=40u
MPN151 N15_m N15_m vdd vdd PCH L=1u W=16u
MPN152 N15_o1 N15_m vdd vdd PCH L=1u W=16u
MNN151 N15_m cn15 sn15 0 NCH L=1u W=8u
MNN152 N15_o1 vref sn15 0 NCH L=1u W=8u
MTN15 sn15 g_vota 0 0 NCH L=1u W=8u
MPN153 on15 N15_o1 vdd vdd PCH L=1u W=160u
MNN153 on15 g_vota 0 0 NCH L=1u W=40u
RFP15 op15 cp15 2.000000e+03
RFN15 on15 cn15 2.000000e+03
CP15 cp15 0 10f
CN15 cn15 0 10f

* column pair cp16/cn16
MSP1_16 r1 wl1 np1_16 0 NCH L=1u W=20u
RCP1_16 np1_16 cp16 4.992703e+04
MSN1_16 r1 wl1 nm1_16 0 NCH L=1u W=20u
RCN1_16 nm1_16 cn16 1.493787e+04
MSP2_16 r2 wl2 np2_16 0 NCH L=1u W=20u
RCP2_16 np2_16 cp16 1.939151e+04
MSN2_16 r2 wl2 nm2_16 0 NCH L=1u W=20u
RCN2_16 nm2_16 cn16 1.488886e+04
MSP3_16 r3 wl3 np3_16 0 NCH L=1u W=20u
RCP3_16 np3_16 cp16 1.001439e+04
MSN3_16 r3 wl3 nm3_16 0 NCH L=1u W=20u
RCN3_16 nm3_16 cn16 4.681294e+04
MPP161 P16_m P16_m vdd vdd PCH L=1u W=16u
MPP162 P16_o1 P16_m vdd vdd PCH L=1u W=16u
MNP161 P16_m cp16 sp16 0 NCH L=1u W=8u
MNP162 P16_o1 vref sp16 0 NCH L=1u W=8u
MTP16 sp16 g_vota 0 0 NCH L=1u W=8u
MPP163 op16 P16_o1 vdd vdd PCH L=1u W=160u
MNP163 op16 g_vota 0 0 NCH L=1u W=40u
MPN161 N16_m N16_m vdd vdd PCH L=1u W=16u
MPN162 N16_o1 N16_m vdd vdd PCH L=1u W=16u
MNN161 N16_m cn16 sn16 0 NCH L=1u W=8u
MNN162 N16_o1 vref sn16 0 NCH L=1u W=8u
MTN16 sn16 g_vota 0 0 NCH L=1u W=8u
MPN163 on16 N16_o1 vdd vdd PCH L=1u W=160u
MNN163 on16 g_vota 0 0 NCH L=1u W=40u
RFP16 op16 cp16 2.000000e+03
RFN16 on16 cn16 2.000000e+03
CP16 cp16 0 10f
CN16 cn16 0 10f

* solver seed; the data is in the row drivers
.IC V(cp1)=1.0000 V(cn1)=1.0000 V(op1)=1.0000 V(on1)=1.0000 V(cp2)=1.0000 V(cn2)=1.0000 V(op2)=1.0000 V(on2)=1.0000 V(cp3)=1.0000 V(cn3)=1.0000 V(op3)=1.0000 V(on3)=1.0000 V(cp4)=1.0000 V(cn4)=1.0000 V(op4)=1.0000 V(on4)=1.0000 V(cp5)=1.0000 V(cn5)=1.0000 V(op5)=1.0000 V(on5)=1.0000 V(cp6)=1.0000 V(cn6)=1.0000 V(op6)=1.0000 V(on6)=1.0000 V(cp7)=1.0000 V(cn7)=1.0000 V(op7)=1.0000 V(on7)=1.0000 V(cp8)=1.0000 V(cn8)=1.0000 V(op8)=1.0000 V(on8)=1.0000 V(cp9)=1.0000 V(cn9)=1.0000 V(op9)=1.0000 V(on9)=1.0000 V(cp10)=1.0000 V(cn10)=1.0000 V(op10)=1.0000 V(on10)=1.0000 V(cp11)=1.0000 V(cn11)=1.0000 V(op11)=1.0000 V(on11)=1.0000 V(cp12)=1.0000 V(cn12)=1.0000 V(op12)=1.0000 V(on12)=1.0000 V(cp13)=1.0000 V(cn13)=1.0000 V(op13)=1.0000 V(on13)=1.0000 V(cp14)=1.0000 V(cn14)=1.0000 V(op14)=1.0000 V(on14)=1.0000 V(cp15)=1.0000 V(cn15)=1.0000 V(op15)=1.0000 V(on15)=1.0000 V(cp16)=1.0000 V(cn16)=1.0000 V(op16)=1.0000 V(on16)=1.0000

.OP

.END
