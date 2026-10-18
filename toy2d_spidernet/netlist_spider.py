"""
netlist_spider.py -- the KirchhoffNet "spidernet": a fully-connected CROSSBAR of
theta-gated NMOS edges between fixed input rails and capacitive state nodes.

Transliterated from the Cadence Spectre export `spidernet_1.txt` (cell
kirchoff_spidernet, Neur_Sam_350). See spidernet_1.sp for the 1:1 static port and
the full Spectre -> SPICE conversion table.

Topology (n_rails x n_nodes crossbar, every rail reaches every state node):

    v1 ---[M1_1 gate=theta1 ]--- net1      v1 ---[M1_2 gate=theta5 ]--- net2
    v2 ---[M2_1 gate=theta2 ]--- net1      v2 ---[M2_2 gate=theta6 ]--- net2
    v3 ---[M3_1 gate=theta3 ]--- net1      ...
    v4 ---[M4_1 gate=theta4 ]--- net1
                    |                                    |
                   C1                                   C2

Per edge (rail i -> node j): one NMOS, drain = v_i, gate = theta_k, source =
net_j, bulk = 0, with k = (j-1)*n_rails + i. Each state node carries a storage
cap to ground and is read at tstop.

WHY THIS COMPUTES SOMETHING (Level-1 Shichman-Hodges, all edges in triode):
the model does NOT re-designate source/drain, so an edge whose rail sits BELOW
net_j stays on the triode branch with Id < 0 and pulls the node down, while a
rail above pulls it up. Each edge is therefore a theta-gated bidirectional
conductance to its rail, and net_j settles at the current balance

    sum_i [ (theta_ij - VTO - net_j)(v_i - net_j) - 0.5 (v_i - net_j)^2 ] = 0

which solves in closed form (a_ij = theta_ij - VTO) to

    net_j = ( A_j - sqrt(A_j^2 + 4Q - 8 B_j) ) / 4
    A_j = sum_i a_ij     B_j = sum_i a_ij v_i     Q = sum_i v_i^2

i.e. a nonlinear (sqrt-of-quadratic) blend of the rail voltages whose mixing
weights are set by the trainable thetas. Data enters through the rails; the
thetas are the trainable parameters.

TWO OPERATING-POINT RULES the caller must respect (both are hard failures):
  1. An edge with theta_k <= V(net_j) + VTO is fully OFF: gds floors at 1e-12 and
     dId/dtheta is EXACTLY zero -- a dead parameter Adam can never revive. With
     the schematic's own defaults (rails 2.5-3.1 V, thetas 1.0-2.4 V) ALL 16
     edges are off, every node sits at the rail mean, and the whole 4x16
     sensitivity matrix is zero. Keep thetas well above the node voltage.
  2. Edges must stay in TRIODE (v_i < theta_k - VTO). In saturation the edge
     becomes a current source that ignores v_i, which destroys data dependence.
     Keep the rails LOW relative to theta - VTO.
See spider_common.py for a rail/theta window that satisfies both.

NOTE on names: node names (v_i, theta_k, net_j) match the schematic, but the
SOURCE names are VR{i}/VTH{k} rather than the export's V2..V21, because a voltage
source's name IS its differentiable-parameter name in the simulator
(Component.differentiable_params -> [self.name]) and has to be readable from the
training code.
"""

# Level-1 card standing in for the TSMC 0.35u PDK (mm0355v.scs cannot be
# .INCLUDEd by this parser). Same card the simulator's own
# testfiles/kirchoffnet.txt uses for this topology family.
NCH_MODEL = ".MODEL NCH NMOS LEVEL=1 VTO=0.55 KP=170e-6"
VTO = 0.55
DEV_L = "350n"   # from the schematic
DEV_W = "2u"


def theta_index(i, j, n_rails):
    """Edge (rail i, node j), both 1-based -> theta index k (1-based)."""
    return (j - 1) * n_rails + i


def theta_names(n_rails=4, n_nodes=4):
    return [f"VTH{k}" for k in range(1, n_rails * n_nodes + 1)]


def rail_names(n_rails=4):
    return [f"VR{i}" for i in range(1, n_rails + 1)]


def rail_nodes(n_rails=4):
    return [f"v{i}" for i in range(1, n_rails + 1)]


def state_nodes(n_nodes=4):
    return [f"net{j}" for j in range(1, n_nodes + 1)]


def write_spider_netlist(theta_params, rail_sources, path,
                         n_rails=4, n_nodes=4, cap="0.1f",
                         tstep="10n", tstop="100n", ic_center=1.0):
    """
    theta_params : {VTH1..VTH{n_rails*n_nodes}: volts}  (trainable edge gates)
    rail_sources : {VR1..VR{n_rails}: volts}            (encoder-driven data inputs)

    The .IC is a neutral solver seed on every state node, NOT data: with
    cap=0.1f the node time constant is ~1e-13 s, so the state is fully settled
    long before tstop and the readout is a clean operating point.
    """
    p, s = theta_params, rail_sources
    L = [
        "* KirchhoffNet SPIDERNET crossbar -- auto-generated",
        f"* {n_rails} rails x {n_nodes} state nodes = {n_rails * n_nodes} "
        f"theta-gated NMOS edges", "",
        "* MOSFET model (Level-1 Shichman-Hodges; no body effect, no intrinsic C)",
        NCH_MODEL, "",
        "* Encoder-driven input rails (the data point)",
    ]
    for i in range(1, n_rails + 1):
        L.append(f"VR{i} v{i} 0 DC {s[f'VR{i}']:.6f}")
    L += ["", "* Trainable per-edge gate voltages (thetas)"]
    for k in range(1, n_rails * n_nodes + 1):
        L.append(f"VTH{k} theta{k} 0 DC {p[f'VTH{k}']:.6f}")
    L.append("")
    for j in range(1, n_nodes + 1):
        L.append(f"* state node net{j}: fed by every rail through its own theta")
        for i in range(1, n_rails + 1):
            k = theta_index(i, j, n_rails)
            L.append(f"M{i}_{j} v{i} theta{k} net{j} 0 NCH L={DEV_L} W={DEV_W}")
        L += [f"C{j} net{j} 0 {cap}", ""]
    L += ["* neutral solver seed (state is settled by tstop; data is in the rails)",
          ".IC " + " ".join(f"V(net{j})={ic_center:.4f}"
                            for j in range(1, n_nodes + 1)), "",
          f".TRAN {tstep} {tstop}", "", ".END"]
    with open(path, "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    nr, nn = 4, 4
    tp = {f"VTH{k}": 2.4 for k in range(1, nr * nn + 1)}
    rs = {"VR1": 0.6, "VR2": 1.0, "VR3": 1.2, "VR4": 1.5}
    write_spider_netlist(tp, rs, "tmp_spider_demo.sp", n_rails=nr, n_nodes=nn)
    print(f"wrote tmp_spider_demo.sp | {nr} rails x {nn} nodes "
          f"| edges/trainable thetas: {nr * nn} | read: {state_nodes(nn)}")
