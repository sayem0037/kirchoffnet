"""
xbar_spec.py -- sizing the crossbar's feedback resistors, by measurement.

WHY THIS FILE EXISTS
--------------------
The first end-to-end ex-situ run mapped a 0.983-accuracy software MLP onto the
circuit and got 0.750. That looked like the crossbar's characteristic mapping
loss. It was not. Probing the operating point showed the signal shrinking at
every stage:

    input differential swing            0.400 V
    layer-0 column difference           0.186 V   (stage gain 0.46)
    layer-0 neuron differential         0.399 V
    class scores (layer-1 columns)      0.046 V   (spread over 25 samples)

A network whose output swing is 46 mV is not being read, it is being guessed
at. The cause is Rf: the column current is a sum of n_in terms, so the feedback
resistance that gives unity stage gain at fan-in 5 is wrong at fan-in 8, and a
single number for a whole network cannot be right for any of it. kfabric hit
exactly this with load_r and solved it the same way -- see the load_r docstring
in netlist_kfq.py, which records that fan-in 8 wants ~2.5k and fan-in 64 wants
~200.

Reporting a baseline crippled by its own sizing would be beating a strawman, so
the sizing is solved for before any accuracy number is taken.

THE METHOD
----------
Measured, not derived. The crossbar stage is exactly linear in Rf (Gate A), so
one measurement gives the correction directly:

    Rf_new = Rf_old * (target_swing / measured_swing)

The neuron after it is only approximately linear, and layer l+1's crossbar
resistively LOADS layer l's neuron drains, so the solve is iterated over the
whole stack rather than applied once per layer. Two or three passes converge.

The target for every layer but the last is the input swing itself: each layer
should hand the next one a signal of the size it was designed to receive, which
is the self-consistency condition kfabric's gate_chain.py calls the operating
window. The last layer targets the same swing at its columns, since those are
the class scores.
"""

import argparse
import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import xbar_netlist as X                       # noqa: E402
import xbar_train as T                         # noqa: E402
from simulator_api import eval_chain, scratch   # noqa: E402

RESULTS = os.path.join(BASE, "results")


def _probe_nodes(layers, l):
    """The nodes whose difference carries layer l's signal.

    Inner layers are read at the neuron drains, because that is what the next
    layer actually sees. The last layer is read at its columns, because that is
    what the argmax sees.
    """
    n_out = layers[l][1]
    if l == len(layers) - 1:
        return [(X.tiap(l, j), X.tian(l, j)) for j in range(1, n_out + 1)]
    return [(X.out_node(l, j), X.outn_node(l, j)) for j in range(1, n_out + 1)]


def _row_nodes(layers, l):
    """The row pair nodes feeding layer l (excluding the bias row)."""
    n_in = layers[l][0]
    return [(X.row_p(l, i), X.row_m(l, i)) for i in range(1, n_in + 1)]


def measure_levels(u, Xs, layers, cfg, rf, vref, rd, nl, levels=None):
    """Per-layer row common mode, signal swing, and TIA rail headroom.

    Three things in one sweep because they are measured from the same runs and
    a sizing loop needs all three: the common mode to place vref, the swing to
    place Rf, and the headroom to know whether an amplifier has railed -- which
    is the failure the first version of this loop walked into blind.
    """
    res = T.u_to_res(u, cfg, levels)
    sig = [_probe_nodes(layers, l) for l in range(len(layers))]
    rows = [_row_nodes(layers, l) for l in range(len(layers))]
    tias = [[(X.tiap(l, j), X.tian(l, j))
             for j in range(1, layers[l][1] + 1)] for l in range(len(layers))]

    flat = sorted({nd for grp in (sig, rows, tias)
                   for lp in grp for pr in lp for nd in pr})
    rec = {nd: [] for nd in flat}
    for x in Xs:
        X.write_xbar_netlist(res, x, layers, nl,
                             rf=[f"{r:.6e}" for r in rf], vref=list(vref),
                             rd=[f"{r:.6e}" for r in rd],
                             vtail=cfg["vtail"], vcm=cfg["vcm"],
                             swing=cfg["swing"], ideal_tia=cfg["ideal_tia"],
                             vota=cfg["vota"])
        v = eval_chain(nl, flat)
        for nd in flat:
            rec[nd].append(v[nd])

    def diff_swing(lp):
        d = np.array([[rec[p][k] - rec[m][k] for k in range(len(Xs))]
                      for p, m in lp])
        return float(np.median(np.ptp(d, axis=1)))

    out = []
    for l in range(len(layers)):
        cm = float(np.mean([0.5 * (rec[p][k] + rec[m][k])
                            for p, m in rows[l] for k in range(len(Xs))]))
        tv = np.array([rec[nd][k] for pr in tias[l] for nd in pr
                       for k in range(len(Xs))])
        out.append(dict(row_cm=cm, swing=diff_swing(sig[l]),
                        tia_lo=float(tv.min()), tia_hi=float(tv.max()),
                        railed=bool(tv.min() < 0.15 or tv.max() > X.VDD - 0.15)))
    return out


def measure_swings(u, Xs, layers, cfg, rf, nl, levels=None):
    """Per-layer differential signal swing, in volts.

    Swing is the median over columns of each column's peak-to-peak range across
    the sample batch. Median, not max: one column that happens to saturate
    should not set the sizing for the whole layer.
    """
    res = T.u_to_res(u, cfg, levels)
    pairs = [_probe_nodes(layers, l) for l in range(len(layers))]
    flat = [nd for lp in pairs for pr in lp for nd in pr]

    rec = {nd: [] for nd in flat}
    for x in Xs:
        X.write_xbar_netlist(res, x, layers, nl, rf=[f"{r:.6e}" for r in rf],
                             rd=cfg["rd"], vtail=cfg["vtail"],
                             vref=cfg["vref"], vcm=cfg["vcm"],
                             swing=cfg["swing"], ideal_tia=cfg["ideal_tia"],
                             vota=cfg["vota"])
        v = eval_chain(nl, flat)
        for nd in flat:
            rec[nd].append(v[nd])

    out = []
    for lp in pairs:
        d = np.array([[rec[p][k] - rec[m][k] for k in range(len(Xs))]
                      for p, m in lp])
        out.append(float(np.median(np.ptp(d, axis=1))))
    return out


def size_layers(u, Xs, layers, cfg, levels=None, target=None,
                cm_iters=6, rf_iters=5, rf0=5e3, lo=1e2, hi=2e6,
                rd0=2e5, rd_lo=1e3, rd_hi=1e6, cm_target=None, verbose=True):
    """Solve rd, vref and Rf so every stage carries a full signal.

    THREE KNOBS, SOLVED IN SEQUENCE -- not jointly, and the order matters.

      Phase 1, rd.   rd of layer l sets the common mode of the rows feeding
                     layer l+1, as VDD - rd*Id. At the 200k the KFQ neuron
                     uses, those drains sit at 0.27 V, which is below an NMOS
                     input pair's turn-on: the next layer's amplifiers are off
                     and its column quietly degenerates into a passive
                     resistive load. Solved first, with Rf held small so that
                     nothing rails while the operating point is still moving.
      Phase 2, vref. Placed at each layer's now-settled row common mode, which
                     zeroes the common-mode current through the column. Pinning
                     it at mid-supply instead drives the amplifier output past
                     8 V at fan-in 5.
      Phase 3, Rf.   Scaled by target/measured, with rd and vref frozen. The
                     crossbar stage is exactly linear in Rf (Gate A), so one
                     correction per pass converges quickly.

    Solving all three at once does NOT work, and the failure is instructive:
    vref is always set from the previous pass's common mode, so while rd is
    still moving vref is stale, the TIA sees a standing offset, and it rails.
    The measured trace oscillated 0.0086 -> 0.183 -> 0.612 -> 0.495 -> 0.059
    -> 0.824 V of swing without settling. Freezing each knob before moving the
    next one removes the coupling.

    Returns (rf, rd, vref, history).
    """
    target = target if target is not None else cfg["swing"]
    cm_target = cm_target if cm_target is not None else cfg["vcm"]
    L = len(layers)
    rf = [float(lo * 10)] * L          # small and safe while rd moves
    rd = [float(rd0)] * L
    vref = [float(cfg["vcm"])] * L
    nl = scratch("spec")
    hist = []

    def probe(tag):
        m = measure_levels(u, Xs, layers, cfg, rf, vref, rd, nl, levels)
        hist.append(dict(phase=tag, rf=list(rf), rd=list(rd), vref=list(vref),
                         swing=[d["swing"] for d in m],
                         row_cm=[d["row_cm"] for d in m],
                         railed=[d["railed"] for d in m]))
        if verbose:
            print(f"  {tag:<9}" + "  ".join(
                f"L{l}[Rf={rf[l]:8.4g} rd={rd[l]:8.4g} vref={vref[l]:.2f} "
                f"cm={m[l]['row_cm']:.2f} sw={m[l]['swing']:.4f}"
                f"{' RAIL' if m[l]['railed'] else ''}]" for l in range(L)))
        return m

    # ---- phase 1: place every layer's row common mode
    for it in range(cm_iters):
        m = probe(f"rd {it}")
        moved = 0.0
        for l in range(1, L):
            cm = m[l]["row_cm"]
            drop, want = X.VDD - cm, X.VDD - cm_target
            if drop > 1e-3:
                new_rd = float(np.clip(rd[l - 1] * (want / drop) ** 0.8,
                                       rd_lo, rd_hi))
                moved = max(moved, abs(new_rd - rd[l - 1]) / rd[l - 1])
                rd[l - 1] = new_rd
        if moved < 0.02:
            break

    # ---- phase 2: park each reference at its settled row common mode
    m = probe("vref")
    for l in range(L):
        vref[l] = float(np.clip(m[l]["row_cm"], 0.2, X.VDD - 0.2))

    # ---- phase 3: size the feedback resistors
    for it in range(rf_iters):
        m = probe(f"rf {it}")
        for l in range(L):
            sw = m[l]["swing"]
            if m[l]["railed"]:
                rf[l] = max(lo, rf[l] * 0.4)
            elif sw <= 1e-9:
                rf[l] = min(hi, rf[l] * 4.0)
            else:
                rf[l] = float(np.clip(rf[l] * (target / sw) ** 0.6, lo, hi))

    # ---- phase 4: refresh vref, then re-touch Rf
    #
    # Phase 3 moves the operating point it was solved against. Sizing Rf
    # changes how hard the neuron is driven, which moves its drain common mode,
    # which is the NEXT stage's amplifier input common mode -- so the vref
    # parked in phase 2 goes stale. Measured on iris: vref sat at 0.861 V while
    # the common mode had drifted to 0.731 V, a 130 mV standing offset into
    # every layer-1 amplifier. The circuit still worked (0.917 accuracy) but
    # only tracked the mapped function at r = 0.865; closing this loop is the
    # difference between "mostly right" and "right".
    for it in range(2):
        m = probe(f"refresh {it}")
        for l in range(L):
            vref[l] = float(np.clip(m[l]["row_cm"], 0.2, X.VDD - 0.2))
            sw = m[l]["swing"]
            if m[l]["railed"]:
                rf[l] = max(lo, rf[l] * 0.4)
            elif sw > 1e-9:
                rf[l] = float(np.clip(rf[l] * (target / sw) ** 0.5, lo, hi))

    m = probe("final")
    for l in range(L):
        vref[l] = float(np.clip(m[l]["row_cm"], 0.2, X.VDD - 0.2))

    if os.path.exists(nl):
        os.remove(nl)
    return rf, rd, vref, hist


def calibrate_signs(cfg, levels=None, verbose=True):
    """MEASURE the polarity of each kind of stage, rather than deriving it.

    A layer's transfer sign is fixed by its topology -- the TIA inverts, and
    the neuron's differential pair inverts again -- so a stage read at the
    neuron should be non-inverting and one read at the columns should invert.
    That reasoning is right, and relying on it was still a mistake twice:

      * hand-derived sign, broken sizing   iris 0.750  (looked plausible)
      * hand-derived sign, fixed sizing    iris 0.000  (perfectly anti-correct)

    The second number is the tell. The derivation had been calibrated against a
    configuration whose second-layer amplifiers were DEAD -- inputs at 0.27 V,
    below an NMOS pair's turn-on -- so that column behaved as a passive
    resistive load and did not invert. Fix the bias and the real inversion came
    back, taking the accuracy from 0.767 to exactly 0.000.

    So the sign is measured on a one-weight probe network: drive a known
    positive weight with a known positive differential input and read which way
    the output moves. Two numbers, valid for any depth, because polarity is a
    property of the stage and not of the stack.

    Returns (s_inner, s_out): the multiplier the mapper must apply to a layer
    read at the neuron, and to a layer read at the columns.
    """
    layers = [(1, 1)]
    res = {X.g_a(0, 1, 1): 1.0 / (1.0 / cfg["r_on"]),
           X.g_b(0, 1, 1): 1.0 / (1.0 / cfg["r_off"])}

    def _rd_rf(key, default):
        v = cfg.get(key, default)
        return v[0] if isinstance(v, (list, tuple)) else v

    nl = scratch("sign")
    out = {}
    for tag, nodes in (("inner", (X.out_node(0, 1), X.outn_node(0, 1))),
                       ("out", (X.tiap(0, 1), X.tian(0, 1)))):
        d = []
        for xv in (-1.0, 1.0):
            X.write_xbar_netlist(res, [xv], layers, nl,
                                 rf=_rd_rf("rf", "5k"), rd=_rd_rf("rd", "200k"),
                                 vtail=cfg["vtail"],
                                 vref=_rd_rf("vref", cfg["vcm"]),
                                 vcm=cfg["vcm"], swing=cfg["swing"],
                                 ideal_tia=cfg["ideal_tia"], vota=cfg["vota"],
                                 bias=False)
            v = eval_chain(nl, list(nodes))
            d.append(v[nodes[0]] - v[nodes[1]])
        slope = d[1] - d[0]
        out[tag] = -1.0 if slope < 0 else 1.0
        if verbose:
            print(f"  polarity {tag:<6}: d(out)/d(in) = {slope:+.4e} "
                  f"-> sign {out[tag]:+.0f}")
    if os.path.exists(nl):
        os.remove(nl)
    return out["inner"], out["out"]


def solve_for(dataset, hidden, n_train, n_test, side=8, seed=0, n_probe=24,
              iters=5, **cfg_over):
    """Full sizing run for one dataset: map a software MLP, then size."""
    # spec="" means "do not load a sizing file": this IS the solver that
    # produces one, and letting make_cfg pick up its own previous output would
    # make each run start from the last one instead of from the defaults.
    a = argparse.Namespace(rf="5k", rd="200k", vtail=0.85, vref=1.0, vcm=1.0,
                           swing=0.4, gain=4.0, ideal_tia=False, vota=0.9,
                           r_on=X.R_ON_DEFAULT, r_off=X.R_OFF_DEFAULT,
                           dataset=dataset, spec="")
    for k, v in cfg_over.items():
        setattr(a, k, v)
    cfg = T.make_cfg(a)

    kw = dict(n_train=n_train, n_test=n_test)
    if dataset == "mnist":
        kw["side"] = side
    Xtr, ytr, _, _, C, _ = T.load_any(dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xw, _, _ = T.to_pm1(Xtr)

    layers = [(Xtr.shape[1], hidden), (hidden, C)]
    W = T.train_software_mlp(Xw, ytr, C, layers, seed=seed)
    u = T.map_to_u(W, layers, cfg)

    rng = np.random.default_rng(seed)
    probe = Xw[rng.choice(len(Xw), size=min(n_probe, len(Xw)), replace=False)]

    print(f"sizing {dataset} layers={layers}")
    rf, rd, vref, hist = size_layers(u, probe, layers, cfg,
                                     cm_iters=iters, rf_iters=iters)

    # Polarity is calibrated with the SOLVED sizing in place, never with the
    # defaults: a stage whose amplifier is starved does not invert, so the sign
    # is a property of the operating point and must be measured after it is
    # fixed.
    sized = dict(cfg, rf=[f"{r:.6e}" for r in rf],
                 rd=[f"{r:.6e}" for r in rd], vref=list(vref))
    s_inner, s_out = calibrate_signs(sized)

    return dict(dataset=dataset, layers=layers, rf=rf, rd=rd, vref=vref,
                sign_inner=s_inner, sign_out=s_out, history=hist, cfg=cfg)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--hidden", type=int, default=7)
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-probe", type=int, default=24)
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args()

    out = solve_for(a.dataset, a.hidden, a.n_train, a.n_test, a.side,
                    a.seed, a.n_probe, a.iters)
    print("\nRf   per layer: " + " ".join(f"{r:.4g}" for r in out["rf"]))
    print("rd   per layer: " + " ".join(f"{r:.4g}" for r in out["rd"]))
    print("vref per layer: " + " ".join(f"{v:.3f}" for v in out["vref"]))
    print(f"polarity: inner {out['sign_inner']:+.0f}  "
          f"output {out['sign_out']:+.0f}")
    if a.save:
        os.makedirs(RESULTS, exist_ok=True)
        p = os.path.join(RESULTS, f"xbar_spec_{a.dataset}.json")
        json.dump(out, open(p, "w"), indent=2)
        print(f"saved -> {p}")
