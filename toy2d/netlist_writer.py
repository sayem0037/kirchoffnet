"""
netlist_writer.py
-----------------
Generates an OPEN feedforward chain of differential-amplifier stages (NOT a
closed ring). Opening the loop removes the positive feedback that made the
ring bistable/latching, so the 100ns transient output is a smooth, analog
function of the inputs and parameters -- with non-zero backward-adjoint
sensitivity for every trainable parameter.

Topology (n_blocks stages):
    nin --[stage1]--> h1 --[stage2]--> h2 --...--> h{n} (= output)

Each stage i is a differential amplifier:
  - signal-branch NMOS gate = the stage's signal input (nin, or h{i-1})
  - dummy-branch  NMOS gate = vref{i}   (a per-stage reference -- a feature
                                          injection point, held DC source)
  - tail NMOS gate           = vb{i}     (trainable bias)
  - PMOS loads gate          = th{i}     (trainable theta)
  - stage output             = h{i}      (with a storage cap for the transient)

Two groups of DC sources:
  * circuit_params (TRAINABLE, via 100ns backward adjoint):
        VTH1..VTHn  (PMOS-load thetas)   VB1..VBn  (tail biases)
  * input_sources (driven by the software encoder each forward pass):
        VIN         (drives nin, the chain's front input)
        VREF1..VREFn (per-stage references = feature injection points)

A .IC on the dynamic h-nodes seeds a genuine transient that evolves toward
the input-driven equilibrium; we read it at 100ns (~1 time-constant), so the
readout is a real transient value (matches the required 100ns TRAN + backward
transient adjoint mechanism), not the trivially-settled DC point.
"""

VDD = 3.3


def theta_names(n_blocks):
    return [f"VTH{i}" for i in range(1, n_blocks + 1)]


def vbias_names(n_blocks):
    return [f"VB{i}" for i in range(1, n_blocks + 1)]


def input_source_names(n_blocks):
    return ["VIN"] + [f"VREF{i}" for i in range(1, n_blocks + 1)]


def output_nodes(n_blocks):
    return [f"h{i}" for i in range(1, n_blocks + 1)]


def _build_circuit_lines(circuit_params, input_sources, n_blocks):
    p = circuit_params
    s = input_sources
    lines = [
        "* MOSFET models (Level-1 Shichman-Hodges)",
        ".MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
        ".MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
        "",
        "* Fixed supply",
        f"V0  vdd 0 DC {VDD}",
        "",
        "* Encoder-driven input sources (front input + per-stage references)",
        f"VIN  nin 0 DC {s['VIN']:.6f}",
    ]
    for i in range(1, n_blocks + 1):
        lines.append(f"VREF{i} vref{i} 0 DC {s[f'VREF{i}']:.6f}")
    lines.append("")
    lines.append("* Trainable PMOS-load thetas")
    for i in range(1, n_blocks + 1):
        lines.append(f"VTH{i} th{i} 0 DC {p[f'VTH{i}']:.6f}")
    lines.append("")
    lines.append("* Trainable tail biases")
    for i in range(1, n_blocks + 1):
        lines.append(f"VB{i} vb{i} 0 DC {p[f'VB{i}']:.6f}")
    lines.append("")

    for i in range(1, n_blocks + 1):
        sig_in = "nin" if i == 1 else f"h{i-1}"
        lines += [
            f"* Stage {i}: signal={sig_in}  ref=vref{i}  out=h{i}",
            f"Md{i}  d{i}  vref{i}  t{i}  0    NCH L=650n W=6u",
            f"Ms{i}  h{i}  {sig_in}  t{i}  0    NCH L=650n W=6u",
            f"Mt{i}  t{i}  vb{i}    0     0    NCH L=1u   W=12u",
            f"Mpd{i} d{i}  th{i}    vdd   vdd  PCH L=2u   W=6u",
            f"Mps{i} h{i}  th{i}    vdd   vdd  PCH L=2u   W=6u",
            f"C{i}   h{i}  0        0.1f",
            "",
        ]
    return lines


def write_chain_netlist(circuit_params, input_sources, path,
                        n_blocks=4, tstep="10n", tstop="100n", ic_value=1.65):
    """
    circuit_params: {VTH1..VTHn, VB1..VBn}  (trainable circuit knobs)
    input_sources : {VIN, VREF1..VREFn}     (encoder-driven, per forward pass)
    """
    ic_line = ".IC " + " ".join(f"V(h{i})={ic_value:.4f}" for i in range(1, n_blocks + 1))
    lines = (
        ["* KirchhoffNet OPEN feedforward chain -- auto-generated", ""]
        + _build_circuit_lines(circuit_params, input_sources, n_blocks)
        + [
            "* Seed a transient from a neutral state; read at tstop (~1 tau)",
            ic_line,
            "",
            f".TRAN {tstep} {tstop}",
            "",
            ".END",
        ]
    )
    with open(path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    n = 4
    cp = {**{f"VTH{i}": 1.7 for i in range(1, n + 1)},
          **{f"VB{i}": 0.8 for i in range(1, n + 1)}}
    isrc = {"VIN": 1.65, **{f"VREF{i}": 1.0 for i in range(1, n + 1)}}
    write_chain_netlist(cp, isrc, "tmp_chain_demo.sp", n_blocks=n)
    print("wrote tmp_chain_demo.sp")
    print("theta params :", theta_names(n))
    print("vbias params :", vbias_names(n))
    print("input sources:", input_source_names(n))
    print("output nodes :", output_nodes(n))
