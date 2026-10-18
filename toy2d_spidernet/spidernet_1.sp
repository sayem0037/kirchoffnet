* kirchoff_spidernet -- SPICE port of spidernet_1.txt (Cadence Spectre export)
* Library: Neur_Sam_350 | Cell: kirchoff_spidernet | View: schematic
*
* Topology: 4x4 crossbar. 4 fixed rails v1..v4 x 4 state nodes net1..net4.
* One NMOS per (rail, node) pair: drain = v_i, gate = theta_k, source = net_j,
* bulk = 0. Every one of the 16 edges has its OWN theta -> 16 controllable knobs.
* Each state node carries a cap to ground.
*
* Device/theta assignments below are IDENTICAL to the Spectre export.
* Port notes are marked [P#] and collected at the bottom of the file.

* ---------------------------------------------------------------------------
* [P1] The TSMC 0.35u PDK (mm0355v.scs) cannot be included -- this parser has no
* .INCLUDE/.LIB support. Substituted with the Level-1 Shichman-Hodges card the
* simulator's own testfiles/kirchoffnet.txt uses for this same topology family.
* Note LEVEL=1 ignores body effect (gmb=0) and has no intrinsic capacitance, so
* the only dynamics come from C0..C3 below.
.MODEL NCH NMOS LEVEL=1 VTO=0.55 KP=170e-6

* --- input rails (were: parameters v1=3 v2=3.1 v3=2.9 v4=2.5) --------------
* [P2] No .PARAM / expression support: symbolic `dc=v1` is inlined as a literal.
V9  v1 0 DC 3.0
V8  v2 0 DC 3.1
V7  v3 0 DC 2.9
V6  v4 0 DC 2.5

* --- per-edge theta gate sources -------------------------------------------
* [P3] The export cross-wires V4 (theta2 node) <- dc=theta3 and V3 (theta3 node)
* <- dc=theta2. Values below are written post-swap, i.e. exactly what Spectre
* would have simulated: node theta2 = 1.5, node theta3 = 2.4.
* [P4] theta5..theta16 are never defined in the export's `parameters` line;
* they are given explicit init values here.
V5  theta1  0 DC 2.0
V4  theta2  0 DC 1.5
V3  theta3  0 DC 2.4
V2  theta4  0 DC 1.0
V10 theta5  0 DC 2.0
V11 theta6  0 DC 2.4
V12 theta7  0 DC 1.5
V13 theta8  0 DC 1.0
V14 theta9  0 DC 2.4
V15 theta10 0 DC 1.5
V16 theta11 0 DC 1.0
V17 theta12 0 DC 2.0
V18 theta13 0 DC 2.0
V19 theta14 0 DC 1.0
V20 theta15 0 DC 1.5
V21 theta16 0 DC 2.4

* --- 16 crossbar devices ----------------------------------------------------
* [P5] Spectre `M15 (v2 theta16 net3 0) nch l=350n w=2u ...` -> positional form.
* The parenthesised node list is not understood: "(v2" and "0)" would become
* phantom node names, and "0)" would NOT map to ground.
* [P6] Instance params m/ad/as/pd/ps/nrd/nrs dropped -- they parse fine but
* LEVEL=1 ignores them, and they would add noise entries (M15:AD, ...) to the
* component's differentiable_params list.

* net1 <- all four rails
M1  v1 theta1  net1 0 NCH L=350n W=2u
M0  v2 theta2  net1 0 NCH L=350n W=2u
M3  v3 theta3  net1 0 NCH L=350n W=2u
M2  v4 theta4  net1 0 NCH L=350n W=2u

* net4 <- all four rails
M4  v1 theta5  net4 0 NCH L=350n W=2u
M7  v2 theta6  net4 0 NCH L=350n W=2u
M6  v3 theta7  net4 0 NCH L=350n W=2u
M5  v4 theta8  net4 0 NCH L=350n W=2u

* net2 <- all four rails
M11 v1 theta12 net2 0 NCH L=350n W=2u
M8  v2 theta9  net2 0 NCH L=350n W=2u
M9  v3 theta10 net2 0 NCH L=350n W=2u
M10 v4 theta11 net2 0 NCH L=350n W=2u

* net3 <- all four rails
M12 v1 theta13 net3 0 NCH L=350n W=2u
M15 v2 theta16 net3 0 NCH L=350n W=2u
M14 v3 theta15 net3 0 NCH L=350n W=2u
M13 v4 theta14 net3 0 NCH L=350n W=2u

* --- state-node storage caps ------------------------------------------------
* [P7] Spectre `c=100.0a`. This parser's suffix table (T G MEG K MIL M U N P F)
* has NO atto suffix, so "100.0a" would silently parse as 100 FARADS.
* 100 aF is written as 0.1f.
C0 net1 0 0.1f
C1 net4 0 0.1f
C2 net2 0 0.1f
C3 net3 0 0.1f

* --- analysis ---------------------------------------------------------------
* [P8] Spectre `ic net1=.5` needs the leading dot and the V(node)= form; as-is
* it is dispatched as a source card and throws. Seeded on all four nodes.
.IC V(net1)=0.5 V(net2)=0.5 V(net3)=0.5 V(net4)=0.5

* [P9] Spectre `tran tran stop=1u ...` -> .TRAN TSTEP TSTOP. Without a
* recognised analysis card the parser silently falls back to .OP.
* Step count is kept small: sensitivity=True caches an LU per timestep.
.TRAN 10n 100n

* [P10] Dropped, no equivalents in this dialect: simulator lang=spectre,
* global 0, simulatorOptions, saveOptions, finalTimeOP, the theta1 dc sweep,
* and the modelParameter/element/outputParameter/designParamVals/primitives/
* subckts info lines. In particular sensfile= is irrelevant -- there is no
* .SENS card; sensitivity is the Python kwarg run_simulation_core(..., sensitivity=True).
.END
