"""
netlist_ring.py -- a CLOSED-LOOP SERIES ring of N differential-amplifier stages
(the KirchhoffNet-faithful topology), instead of an open chain or a parallel layer.

Each stage j is a diff-amp whose SIGNAL input is the PREVIOUS stage's output, and
the ring is CLOSED: stage 1's signal input is stage N's output. The data point is
injected as INITIAL CONDITIONS (.IC) on the ring output nodes h1..hN at t=0; the
circuit then evolves for 100 ns and we read those SAME nodes -- exactly the
"input = initial state, output = evolved state" idea of a Neural ODE.

Topology (ring of N stages, closes h{N} -> h1):
    h1 --(signal)--> stage2 -> h2 --> ... -> hN --(signal)--> stage1 -> h1

Per stage j (mirrors testfiles/kirr.txt device cards):
  - signal-branch NMOS gate = h_{j-1}   (previous stage output; h_N for stage 1)
  - dummy-branch  NMOS gate = vn_j       (per-stage TRAINABLE reference source VN_j)
  - tail NMOS gate           = vb_j       (per-stage trainable bias VB_j)
  - PMOS-load gate           = th_j       (per-stage trainable theta VTH_j)
  - output node              = h_j        (with a 1p storage cap; .IC-seeded, read @100ns)

Trainable circuit params per stage = 3 (VTH_j, VB_j, VN_j) -> 3*N total, all trained
via the 100 ns transient adjoint. Data enters ONLY through .IC (no VIN sources).
"""

VDD = 3.3


def theta_names(n):  return [f"VTH{j}" for j in range(1, n + 1)]
def vbias_names(n):  return [f"VB{j}"  for j in range(1, n + 1)]
def ref_names(n):    return [f"VN{j}"  for j in range(1, n + 1)]
def ring_nodes(n):   return [f"h{j}"   for j in range(1, n + 1)]


def write_ring_netlist(circuit_params, ic_seeds, path,
                       n_stages=10, tstep="10n", tstop="100n"):
    """
    circuit_params: {VTH1..N, VB1..N, VN1..N}   (trainable per-stage params)
    ic_seeds      : {h1..hN: volts}             (encoder-driven .IC seeds = the data)
    """
    p, s = circuit_params, ic_seeds
    L = [
        "* KirchhoffNet CLOSED-LOOP series diff-amp ring -- auto-generated", "",
        "* MOSFET models (Level-1 Shichman-Hodges)",
        ".MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
        ".MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7", "",
        "* Fixed supply", f"V0  vdd 0 DC {VDD}", "",
        "* Trainable PMOS-load thetas",
    ]
    for j in range(1, n_stages + 1):
        L.append(f"VTH{j} th{j} 0 DC {p[f'VTH{j}']:.6f}")
    L.append("")
    L.append("* Trainable tail biases")
    for j in range(1, n_stages + 1):
        L.append(f"VB{j} vb{j} 0 DC {p[f'VB{j}']:.6f}")
    L.append("")
    L.append("* Trainable per-stage reference voltages")
    for j in range(1, n_stages + 1):
        L.append(f"VN{j} vn{j} 0 DC {p[f'VN{j}']:.6f}")
    L.append("")
    for j in range(1, n_stages + 1):
        # signal input = previous stage output; stage 1 wraps to stage N (closes the loop)
        vp = f"h{n_stages}" if j == 1 else f"h{j-1}"
        L += [
            f"* stage {j}: signal={vp} ref=vn{j} out=h{j}",
            f"Md{j}  dm{j}  vn{j}  tl{j}  0    NCH L=650n W=6u",
            f"Ms{j}  h{j}   {vp}   tl{j}  0    NCH L=650n W=6u",
            f"Mt{j}  tl{j}  vb{j}  0     0    NCH L=1u   W=12u",
            f"Mpd{j} dm{j}  th{j}  vdd   vdd  PCH L=2u   W=6u",
            f"Mps{j} h{j}   th{j}  vdd   vdd  PCH L=2u   W=6u",
            f"C{j}   h{j}   0      1p", "",
        ]
    ic = ".IC " + " ".join(f"V(h{j})={s[f'h{j}']:.4f}" for j in range(1, n_stages + 1))
    L += ["* seed the ring with the data point at t=0; read h_j at tstop", ic, "",
          f".TRAN {tstep} {tstop}", "", ".END"]
    with open(path, "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    n = 10
    cp = {**{f"VTH{j}": 1.7 for j in range(1, n + 1)},
          **{f"VB{j}": 0.8 for j in range(1, n + 1)},
          **{f"VN{j}": 1.0 for j in range(1, n + 1)}}
    seeds = {f"h{j}": 1.65 for j in range(1, n + 1)}
    write_ring_netlist(cp, seeds, "tmp_ring_demo.sp", n_stages=n)
    print("wrote tmp_ring_demo.sp;  stages:", n,
          "| trainable circuit params:", 3 * n,
          "| read nodes:", ring_nodes(n)[:3], "...")
