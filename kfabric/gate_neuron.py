"""
gate_neuron.py -- measure the ARC neuron's transfer curve DIRECTLY.

Gate B returned separability identical to the raw input, to three decimals, and
unchanged across a 2x sweep of the tail current. That is not "the neuron is a bit
too linear" -- it is the signature of an exactly affine feature map, because
logistic regression on an INVERTIBLE AFFINE transform of x is mathematically
identical to logistic regression on x. So no bias value could ever have changed
that number, and enumerating more of them was the wrong move.

This measures the two things that actually determine whether the stage works,
one node at a time, instead of inferring them from a downstream accuracy:

  1. V(n) vs V(p) -- the transfer curve. Drive the summing node directly through
     a single rail and watch the output. A working activation is monotonic AND
     visibly compressive; an affine one is a straight line.
  2. Affine R^2 of the whole feature map, the same test Gate A applied to the
     KRC, so the two are directly comparable (KRC scored 0.953).

It compares the two candidate cells under identical conditions:
     diffpair  -- PMOS input pair + diode-connected NMOS loads
     inverter  -- CMOS inverter on a per-neuron local supply

Usage:  python gate_neuron.py
"""
import argparse
import os

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

import arc_spec as A
from arc_spec import ArcSpec
from netlist_arc import write_arc_netlist
from simulator_api import eval_chain

BASE = os.path.dirname(os.path.abspath(__file__))
NL = os.path.join(BASE, "tmp_gateneuron.sp")


def transfer(neuron, m=4, k=4, vnn=0.62, vbb=2.35, theta=2.4, n=13,
             fan_in=None):
    """Sweep ONE data rail; record (V(p), V(n)) for neuron 1.

    Only one rail moves, so V(p) sweeps while everything else is held: this
    isolates the cell's own transfer curve from the crossbar's mixing.
    """
    spec = ArcSpec(m, k, 2, name="tf", fan_in=fan_in)
    # make sure rail r1 actually reaches neuron 1, or the sweep measures nothing
    if not any(r == "r1" and d == "p1" for r, d, _ in spec.edges):
        spec.edges = [("r1", "p1", 0)] + spec.edges
        spec.edges = [(r, d, i + 1) for i, (r, d, _) in enumerate(spec.edges)]
        spec.n_edges = len(spec.edges)
        from netlist_arc import theta_names
        spec.THETA = theta_names(spec.n_edges)
    th = {nm: theta for nm in spec.THETA}
    refs = {nm: vnn for nm in spec.REFS}
    tails = {nm: vbb for nm in spec.TAILS}
    read = ["n1", "p1"]
    vp, vn = [], []
    for s in np.linspace(A.RAIL_LO, A.RAIL_HI, n):
        data = {f"VR{i+1}": A.RAIL_CENTER for i in range(k)}
        data["VR1"] = float(s)
        write_arc_netlist(th, refs, tails,
                          {f"VS{i+1}": A.RAIL_CENTER for i in range(m)},
                          data, spec.edges, NL, m_state=m, k_data=k,
                          cap=A.CAP, sum_cap=A.SUM_CAP, tstep=A.TSTEP,
                          tstop=A.TSTOP, ic_center=A.IC_CENTER, neuron=neuron)
        vo = eval_chain(NL, read)
        vp.append(vo["p1"]); vn.append(vo["n1"])
    return np.array(vp), np.array(vn)


def curvature(vp, vn):
    """How far is V(n) from a straight line in V(p)? 1 - R^2 of a linear fit."""
    if np.ptp(vp) < 1e-9 or np.ptp(vn) < 1e-9:
        return 0.0, 0.0
    A_ = np.vstack([vp, np.ones_like(vp)]).T
    pred = A_ @ np.linalg.lstsq(A_, vn, rcond=None)[0]
    return float(1.0 - r2_score(vn, pred)), float(np.ptp(vn))


def affine_r2(neuron, m=8, k=8, T=3, vnn=0.62, vbb=2.35, n_samp=120, seed=0,
              fan_in=None):
    """Gate A's test, applied to the ARC. Directly comparable to the KRC's 0.953."""
    from datasets_any import load_any, to_stream
    from encoder_diverse import init_projection, project_stream
    from features import extract
    from arc_spec import init_params

    Xtr, ytr, Xte, yte, C, spatial = load_any("circle")
    X = np.vstack([np.asarray(Xtr).reshape(len(Xtr), -1),
                   np.asarray(Xte).reshape(len(Xte), -1)])[:n_samp]
    S, _, _ = to_stream(X, None, mode="repeat", T=T)
    spec = ArcSpec(m, k, 2, seed=seed, name="r2", fan_in=fan_in)
    p = init_params(spec)
    p["vnn"][:] = vnn
    p["vbb"][:] = vbb
    W, b = init_projection(X.shape[1], k, seed=seed)
    rails = project_stream(S, W, b)

    nl = os.path.join(BASE, f"tmp_r2_{neuron}.sp")
    V, valid = _extract(spec, p, rails, nl, neuron)
    if os.path.exists(nl):
        os.remove(nl)
    if len(valid) < 20:
        return np.nan, 0
    F = V.reshape(len(valid), -1)
    Xv = X[valid]
    ntr = int(0.7 * len(Xv))
    lin = LinearRegression().fit(Xv[:ntr], F[:ntr])
    return r2_score(F[ntr:], lin.predict(Xv[ntr:]),
                    multioutput="variance_weighted"), len(valid)


def _extract(spec, params, rails, nl, neuron):
    """extract() with the neuron flavour threaded through."""
    from arc_spec import as_dicts, state_to_rails, chunk_to_rails, initial_state
    th, refs, tails = as_dicts(params, spec)
    V, valid = [], []
    for i in range(len(rails)):
        try:
            v = initial_state(spec.m_state)
            traj = []
            for x_t in rails[i]:
                write_arc_netlist(th, refs, tails,
                                  state_to_rails(v, spec.m_state),
                                  chunk_to_rails(x_t, spec.k_data),
                                  spec.edges, nl, m_state=spec.m_state,
                                  k_data=spec.k_data, cap=A.CAP,
                                  sum_cap=A.SUM_CAP, tstep=A.TSTEP,
                                  tstop=A.TSTOP, ic_center=A.IC_CENTER,
                                  neuron=neuron)
                vo = eval_chain(nl, spec.READ)
                v = np.array([vo[nm] for nm in spec.READ])
                traj.append(v)
            V.append(traj); valid.append(i)
        except Exception:
            continue
    return np.array(V), np.array(valid, dtype=int)


def main(a):
    print("GATE B2 -- is the ARC neuron actually a nonlinearity?\n")
    print("For reference, Gate A measured the KRC (no activation) at affine")
    print("R^2 = 0.953. A working activation must score clearly BELOW that.\n")

    print("The summing node's voltage gain is ~1/fan_in, so fan_in is swept")
    print("here: it controls how much signal ever reaches the neuron.\n")
    print(f"{'neuron':>10} {'fan_in':>7} {'V(p) span':>10} {'V(n) span':>10} "
          f"{'curvature':>10} {'affine R2':>10} {'n_ok':>6}")
    print("-" * 70)
    best = None
    for neuron, vnn, vbb, fi in [("diffpair", 0.62, 2.35, 2),
                                 ("diffpair", 0.62, 2.35, 3),
                                 ("diffpair", 0.62, 2.35, 4),
                                 ("diffpair", 0.62, 2.35, None),
                                 ("inverter", 0.90, 2.35, 2),
                                 ("inverter", 0.90, 2.35, 3),
                                 ("inverter", 1.20, 2.35, 2),
                                 ("inverter", 1.20, 2.35, 3)]:
        try:
            vp, vn = transfer(neuron, vnn=vnn, vbb=vbb, fan_in=fi)
            curv, span = curvature(vp, vn)
            r2, n_ok = affine_r2(neuron, vnn=vnn, vbb=vbb, fan_in=fi)
            label = f"{neuron[:4]}/{vnn:.2f}"
            fis = "all" if fi is None else str(fi)
            mark = ""
            if span > 0.05 and (best is None or (1 - r2) > best[0]):
                best, mark = (1 - r2, neuron, vnn, fi), "  <--"
            print(f"{label:>10} {fis:>7} {np.ptp(vp):>10.4f} {span:>10.4f} "
                  f"{curv:>10.4f} {r2:>10.4f} {n_ok:>6}{mark}")
        except Exception as e:
            print(f"{neuron:>10} {str(fi):>7}   FAILED: {str(e)[:36]}")

    print("\ncurvature = 1 - R^2 of a straight-line fit to the transfer curve.")
    print("  ~0.00 means the cell is a linear amplifier (no activation).")
    print("affine R^2 = how well ONE matrix reproduces the whole feature map.")
    print("  KRC scored 0.953; a real activation should drop well below that.")
    if best:
        print(f"\nmost nonlinear: {best[1]} VNN={best[2]} fan_in={best[3]} "
              f"(affine R2 = {1-best[0]:.4f})")
    if os.path.exists(NL):
        os.remove(NL)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    a = ap.parse_args()
    main(a)
