"""
gate_oppoint.py -- find a bias window where the ARC neuron is actually usable.

The first smoke run exposed two coupled problems, and both must be fixed before
any accuracy run is worth starting:

  1. The neuron output sat at ~3.30 V (pinned to VDD) for most of the input
     range, because the summing node V(p) landed at 0.43-0.96 V while the
     per-neuron threshold VNN sat at 0.8-1.26 V. With p < VNN the signal branch
     is off and the PMOS load pulls the output to the rail.

  2. Worse for a RECURRENT core: the output range (2.65-3.30 V) does not overlap
     the legal rail window ([RAIL_LO, RAIL_HI]), so `state_to_rails` clipped
     every fed-back value and the recurrence was dead. toy2d's wide layer never
     hit this because it reads its outputs once and never feeds them back.

So the neuron needs a bias window satisfying three things at once:
    (a) V(n) must LAND INSIDE the rail window, or the feedback is clipped away;
    (b) V(n) must MOVE appreciably as V(p) moves, or it carries no information;
    (c) the transfer must COMPRESS at the extremes, or it is a linear network
        again and the whole rebuild was pointless.

This sweeps VTP (PMOS load bias) and VBB (tail bias) and scores each on all
three. VNN is then centred on the measured V(p) range rather than guessed.

Usage:  python gate_oppoint.py
"""
import argparse
import itertools
import os

import numpy as np

import arc_spec as A
from arc_spec import ArcSpec
from netlist_arc import write_arc_netlist
from simulator_api import eval_chain

BASE = os.path.dirname(os.path.abspath(__file__))
NL = os.path.join(BASE, "tmp_oppoint.sp")


def measure(spec, vbb, vnn, n_pts=9, theta=2.4):
    """Sweep all rails together; return (V(p) means, V(n) means)."""
    M, k = spec.m_state, spec.k_data
    th = {n: theta for n in spec.THETA}
    refs = {n: vnn for n in spec.REFS}
    tails = {n: vbb for n in spec.TAILS}

    read = spec.READ + [f"p{j}" for j in range(1, M + 1)]

    vp, vn = [], []
    for s in np.linspace(A.RAIL_LO, A.RAIL_HI, n_pts):
        write_arc_netlist(th, refs, tails,
                          {f"VS{i+1}": float(s) for i in range(M)},
                          {f"VR{i+1}": float(s) for i in range(k)},
                          spec.edges, NL, m_state=M, k_data=k,
                          cap=A.CAP, sum_cap=A.SUM_CAP, tstep=A.TSTEP,
                          tstop=A.TSTOP, ic_center=A.IC_CENTER)
        vo = eval_chain(NL, read)
        vn.append(np.mean([vo[n] for n in spec.READ]))
        vp.append(np.mean([vo[f"p{j}"] for j in range(1, M + 1)]))
    return np.array(vp), np.array(vn)


def score(vp, vn):
    """(in_window, swing, compression) -> a single comparable number."""
    inside = float(((vn >= A.RAIL_LO) & (vn <= A.RAIL_HI)).mean())
    swing = float(np.ptp(vn))
    g = np.gradient(vn, vp)
    mid = np.abs(g[len(g) // 2 - 1:len(g) // 2 + 2]).mean()
    edge = np.abs(np.r_[g[:2], g[-2:]]).mean()
    compress = float(1.0 - min(edge / max(mid, 1e-9), 2.0) / 2.0)
    usable = min(swing, A.RAIL_HI - A.RAIL_LO) / (A.RAIL_HI - A.RAIL_LO)
    return inside, swing, compress, inside * usable * (0.5 + 0.5 * compress)


def main(m, k):
    spec = ArcSpec(m, k, 2, name="op")
    print(f"ARC operating-point sweep | M={m}, k={k}, E={spec.n_edges}")
    print(f"rail window [{A.RAIL_LO}, {A.RAIL_HI}]  "
          f"-> V(n) must land in here for the recurrence to survive\n")

    # First: where does the summing node actually sit? VNN must track it,
    # because VNN is the threshold the pair compares V(p) against.
    vp0, _ = measure(spec, 1.80, 0.72)
    vnn_c = float(np.mean(vp0))
    print(f"measured V(p) range {vp0.min():.3f} .. {vp0.max():.3f} "
          f"-> centring the VNN sweep on {vnn_c:.3f}\n")

    print(f"{'VBB':>6} {'VNN':>6} {'V(n) min':>9} {'V(n) max':>9} "
          f"{'in win':>7} {'swing':>7} {'compress':>9} {'score':>7}")
    print("-" * 68)
    best = None
    for vbb, dv in itertools.product([1.40, 1.65, 1.90, 2.15, 2.40],
                                     [-0.20, -0.10, 0.0, 0.10, 0.20]):
        vnn = float(np.clip(vnn_c + dv, A.VNN_LO, A.VNN_HI))
        vp, vn = measure(spec, vbb, vnn)
        inside, swing, compress, sc = score(vp, vn)
        flag = ""
        if best is None or sc > best[0]:
            best, flag = (sc, vbb, vnn, vn), "  <-- best"
        print(f"{vbb:>6.2f} {vnn:>6.2f} {vn.min():>9.4f} {vn.max():>9.4f} "
              f"{inside:>7.0%} {swing:>7.4f} {compress:>9.3f} {sc:>7.3f}{flag}")

    sc, vbb, vnn, vn = best
    print(f"\nBEST: VBB={vbb:.2f}  VNN={vnn:.3f}  score={sc:.3f}")
    print(f"      V(n) spans {vn.min():.3f} .. {vn.max():.3f}  "
          f"(rail window {A.RAIL_LO} .. {A.RAIL_HI})")
    if sc < 0.15:
        print("\n  FAIL: no bias in this grid gives an output that both lands in")
        print("  the rail window and swings. The neuron cannot drive its own")
        print("  feedback path -- the topology needs another change, not a retune.")
    else:
        print("\n  Put these into arc_spec.py (VBB_MU / VNN_MU) and re-run")
        print("  `python features.py --smoke`.")
    if os.path.exists(NL):
        os.remove(NL)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", type=int, default=6)
    ap.add_argument("--k", type=int, default=6)
    a = ap.parse_args()
    main(a.m, a.k)
