"""
netlist_wide.py -- a WIDE parallel layer of N differential-amplifier "neurons"
(a 1-hidden-layer analog network), instead of the narrow series chain.

Each unit j is an independent diff-amp:
  - signal-branch NMOS gate = VIN_j   (a per-unit input voltage; encoder-driven)
  - dummy-branch  NMOS gate = vn_j     (per-unit TRAINABLE reference source VN_j)
  - tail NMOS gate           = vb_j     (trainable bias)
  - PMOS-load gate           = th_j     (trainable theta)
  - output node              = u_j      (with a storage cap)

Circuit-focused: each unit's reference/threshold VN_j is a TRAINABLE circuit
source (trained via the 100ns adjoint), so the diversity + thresholding lives in
the hardware, not a software layer. Trainable circuit params per unit = 3
(VTH_j, VB_j, VN_j).

The units are NOT connected to each other -> N different nonlinear features of
the inputs. A linear readout over u_1..u_N can then draw a curved (piecewise)
boundary that wraps a circle / follows spirals -- exactly like an N-unit hidden
layer. Diversity comes from the (trainable) encoder giving each unit a different
linear projection of (x, y), plus per-unit trainable th_j / vb_j.

Read u_1..u_N at 100 ns via a .TRAN seeded from a neutral .IC.
"""

VDD = 3.3


def theta_names(n):   return [f"VTH{j}" for j in range(1, n + 1)]
def vbias_names(n):   return [f"VB{j}"  for j in range(1, n + 1)]
def ref_names(n):     return [f"VN{j}"  for j in range(1, n + 1)]   # per-unit trainable refs
def input_names(n):   return [f"VIN{j}" for j in range(1, n + 1)]
def unit_nodes(n):    return [f"u{j}"   for j in range(1, n + 1)]


def write_wide_netlist(circuit_params, input_sources, path,
                       n_units=12, tstep="10n", tstop="100n", ic_value=1.65):
    """
    circuit_params: {VTH1..N, VB1..N, VN1..N}   (trainable per-unit params)
    input_sources : {VIN1..N}                   (encoder-driven per-unit inputs)
    """
    p, s = circuit_params, input_sources
    L = [
        "* KirchhoffNet WIDE parallel diff-amp layer (per-unit trainable refs) -- auto-generated", "",
        "* MOSFET models (Level-1 Shichman-Hodges)",
        ".MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
        ".MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7", "",
        "* Fixed supply", f"V0  vdd 0 DC {VDD}", "",
        "* Encoder-driven per-unit inputs",
    ]
    for j in range(1, n_units + 1):
        L.append(f"VIN{j} in{j} 0 DC {s[f'VIN{j}']:.6f}")
    L.append("")
    L.append("* Trainable PMOS-load thetas")
    for j in range(1, n_units + 1):
        L.append(f"VTH{j} th{j} 0 DC {p[f'VTH{j}']:.6f}")
    L.append("")
    L.append("* Trainable tail biases")
    for j in range(1, n_units + 1):
        L.append(f"VB{j} vb{j} 0 DC {p[f'VB{j}']:.6f}")
    L.append("")
    L.append("* Trainable per-unit reference voltages")
    for j in range(1, n_units + 1):
        L.append(f"VN{j} vn{j} 0 DC {p[f'VN{j}']:.6f}")
    L.append("")
    for j in range(1, n_units + 1):
        L += [
            f"* unit {j}: signal=in{j} ref=vn{j} out=u{j}",
            f"Md{j}  d{j}  vn{j}  t{j}  0    NCH L=650n W=6u",
            f"Ms{j}  u{j}  in{j}  t{j}  0    NCH L=650n W=6u",
            f"Mt{j}  t{j}  vb{j}  0     0    NCH L=1u   W=12u",
            f"Mpd{j} d{j}  th{j}  vdd   vdd  PCH L=2u   W=6u",
            f"Mps{j} u{j}  th{j}  vdd   vdd  PCH L=2u   W=6u",
            f"C{j}   u{j}  0      0.1f", "",
        ]
    ic = ".IC " + " ".join(f"V(u{j})={ic_value:.4f}" for j in range(1, n_units + 1))
    L += ["* seed transient from a neutral state; read u_j at tstop", ic, "",
          f".TRAN {tstep} {tstop}", "", ".END"]
    with open(path, "w") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    n = 12
    cp = {**{f"VTH{j}": 1.7 for j in range(1, n + 1)},
          **{f"VB{j}": 0.8 for j in range(1, n + 1)},
          **{f"VN{j}": 1.0 for j in range(1, n + 1)}}
    isr = {f"VIN{j}": 1.65 for j in range(1, n + 1)}
    write_wide_netlist(cp, isr, "tmp_wide_demo.sp", n_units=n)
    print("wrote tmp_wide_demo.sp;  units:", n,
          "| trainable circuit params:", 3 * n,
          "| read nodes:", unit_nodes(n)[:3], "...")
