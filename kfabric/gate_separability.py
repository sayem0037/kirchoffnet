"""
gate_separability.py -- GATE B. Does the ARC feature map actually separate the
data, BEFORE any expensive training run?

This is the "gate before you train" rule from ../toy2d/README.md section 9, which
credits it with predicting both the wide layer's success and the narrow chain's
failure without spending simulation time. Here it also decides whether adding the
activation stage fixed what Gate A diagnosed.

The comparison that matters, all under an identical logistic read-out:

    raw features            the baseline the circuit must beat to be worth having
    KRC (no activation)     what we measured before: circle 0.70-ish, capped
    ARC (with activation)   this build
    toy2d wide layer        1.00 / 1.00 / 0.97 -- the target, from a frozen
                            24-unit random layer in this repo

If the ARC does not clear the raw baseline on circle by a wide margin, the
activation is still not doing its job and no amount of read-out or sample budget
will rescue it. Better to learn that in two minutes than in two hours.

Usage:
    python gate_separability.py                       # default config, 3 toy sets
    python gate_separability.py --sweep               # M / k / T / swing sweep
"""
import argparse
import itertools
import os

import numpy as np
from sklearn.linear_model import LogisticRegression

from datasets_any import load_any, to_stream
from features import bank_features

BASE = os.path.dirname(os.path.abspath(__file__))

# ../toy2d/README.md section 4: logistic regression on the UNTRAINED 24-unit
# wide-layer state (train separability). This is what "working" looks like.
WIDE_TARGET = {"twomoon": 1.00, "circle": 1.00, "2spirals": 0.97}
# ../toy2d/README.md section 3/4: raw-feature separability, the floor.
RAW_REF = {"twomoon": 0.93, "circle": 0.70, "2spirals": 0.62}


def _logistic(Ftr, ytr, Fte, yte):
    mu, sd = Ftr.mean(0), Ftr.std(0) + 1e-9
    m = LogisticRegression(max_iter=5000, C=1.0)
    m.fit((Ftr - mu) / sd, ytr)
    return (float(m.score((Ftr - mu) / sd, ytr)),
            float(m.score((Fte - mu) / sd, yte)))


def set_bias(vbb=None, vnn=None):
    """Override the neuron bias before building any spec.

    VBB sets the PMOS tail current, and the tail current sets the input pair's
    overdrive Vov ~ sqrt(2 I / kp). The pair only saturates once |V(p) - VNN|
    exceeds ~sqrt(2)*Vov, so a LARGE tail current keeps the neuron linear no
    matter how the rest is tuned. Raising VBB (towards VDD - |VTO_p| = 2.59)
    cuts the current quadratically and is what turns the stage from a linear
    amplifier into a saturating activation.
    """
    import arc_spec as _A
    if vbb is not None:
        _A.VBB_MU = vbb
    if vnn is not None:
        _A.VNN_MU = vnn


def evaluate(dataset, m, k, T, banks, swing, n_train, n_test, seed=0,
             edge_budget=None, cache=True, verbose=False,
             neuron="inverter", fan_in=3):
    Xtr, ytr, Xte, yte, C, spatial = load_any(dataset)
    if n_train and n_train < len(ytr):
        Xtr, ytr = Xtr[:n_train], ytr[:n_train]
    if n_test and n_test < len(yte):
        Xte, yte = Xte[:n_test], yte[:n_test]

    d_in = np.asarray(Xtr).reshape(len(Xtr), -1).shape[1]
    Str, lo, hi = to_stream(Xtr, spatial, mode="repeat", T=T)
    Ste, _, _ = to_stream(Xte, spatial, mode="repeat", T=T, lo=lo, hi=hi)

    kw = dict(d_in=d_in, m_state=m, k_data=k, n_banks=banks, seed=seed,
              swing=swing, edge_budget=edge_budget, cache=cache,
              verbose=verbose, neuron=neuron, fan_in=fan_in)
    Ftr, vtr = bank_features(Str, tag=f"{dataset}_tr", **kw)
    Fte, vte = bank_features(Ste, tag=f"{dataset}_te", **kw)
    if len(vtr) == 0 or len(vte) == 0:
        return None
    raw_tr, raw_te = _logistic(np.asarray(Xtr).reshape(len(Xtr), -1)[vtr], ytr[vtr],
                               np.asarray(Xte).reshape(len(Xte), -1)[vte], yte[vte])
    arc_tr, arc_te = _logistic(Ftr, ytr[vtr], Fte, yte[vte])
    return dict(raw_tr=raw_tr, raw_te=raw_te, arc_tr=arc_tr, arc_te=arc_te,
                n_feat=Ftr.shape[1], n_ok=len(vtr))


def bias_sweep(a):
    """Sweep the tail bias against the metric that actually matters."""
    import arc_spec as _A
    print("GATE B -- neuron tail-bias sweep\n")
    print("VBB sets the PMOS tail current; more current = larger input-pair")
    print("overdrive = the pair never leaves its linear region. Higher VBB")
    print("(towards 2.59) means less current and a genuinely saturating cell.\n")
    hdr = (f"{'VBB':>6} {'I_tail':>9} {'Vov_in':>8} "
           + " ".join(f"{d[:8]:>8}" for d in a.datasets) + f" {'mean':>7}")
    print(hdr); print("-" * len(hdr))
    best = None
    for vbb in a.sweep_vbb:
        set_bias(vbb=vbb, vnn=a.vnn)
        # Level-1 estimates, printed so the electrical story is visible
        vov_t = max(_A.VDD - vbb - 0.71, 0.0)
        i_tail = 0.5 * 40e-6 * 12.0 * vov_t ** 2
        vov_in = float(np.sqrt(max(2 * (i_tail / 2) / (40e-6 * 9.23), 0.0)))
        scores = []
        for ds in a.datasets:
            r = evaluate(ds, a.m, a.k, a.T, a.banks, a.swing, a.n_train,
                         a.n_test, seed=a.seed, edge_budget=a.edge_budget,
                         cache=False)
            scores.append(np.nan if r is None else r["arc_tr"])
        mean = float(np.nanmean(scores))
        flag = ""
        if best is None or mean > best[0]:
            best, flag = (mean, vbb), "  <--"
        print(f"{vbb:>6.2f} {i_tail*1e6:>8.1f}u {vov_in:>8.3f} "
              + " ".join(f"{s:>8.3f}" for s in scores) + f" {mean:>7.3f}{flag}")
    print(f"\nbest mean train separability {best[0]:.3f} at VBB={best[1]:.2f}")
    print(f"raw-feature reference mean: "
          f"{np.mean([RAW_REF[d] for d in a.datasets]):.3f}  "
          f"| wide-layer target mean: "
          f"{np.mean([WIDE_TARGET[d] for d in a.datasets]):.3f}")


def main(a):
    sets = a.datasets
    set_bias(vbb=a.vbb, vnn=a.vnn)
    print("GATE B -- does the ARC feature map separate the data?\n")
    print(f"config: neuron={a.neuron}, fan_in={a.fan_in}")
    print(f"config: M={a.m} neurons, k={a.k} rails, T={a.T} steps, "
          f"R={a.banks} banks, swing={a.swing}")
    print(f"        {a.n_train} train / {a.n_test} test, "
          f"features = M*T*R = {a.m * a.T * a.banks}\n")
    hdr = (f"{'dataset':<10} {'raw tr':>7} {'ARC tr':>7} {'ARC te':>7} "
           f"{'raw ref':>8} {'wide tgt':>9} {'verdict':>9}")
    print(hdr); print("-" * len(hdr))

    ok = 0
    for ds in sets:
        r = evaluate(ds, a.m, a.k, a.T, a.banks, a.swing, a.n_train, a.n_test,
                     seed=a.seed, edge_budget=a.edge_budget, verbose=a.verbose,
                     neuron=a.neuron, fan_in=a.fan_in)
        if r is None:
            print(f"{ds:<10}   all samples failed to solve")
            continue
        tgt = WIDE_TARGET.get(ds, np.nan)
        good = r["arc_tr"] >= tgt - 0.08
        ok += good
        print(f"{ds:<10} {r['raw_tr']:>7.3f} {r['arc_tr']:>7.3f} "
              f"{r['arc_te']:>7.3f} {RAW_REF.get(ds, np.nan):>8.2f} "
              f"{tgt:>9.2f} {'PASS' if good else 'below':>9}")

    print(f"\n{ok}/{len(sets)} datasets reach the wide layer's separability.")
    if ok < len(sets):
        print("Below target means the activation is still not doing enough work.")
        print("Try --sweep before spending time on a full accuracy run.")


def sweep(a):
    set_bias(vbb=a.vbb, vnn=a.vnn)
    print("GATE B sweep -- picking M / k / swing by measurement, not guess\n")
    hdr = (f"{'M':>3} {'k':>3} {'T':>3} {'R':>2} {'swing':>6} {'feat':>5} "
           + " ".join(f"{d[:8]:>8}" for d in a.datasets))
    print(hdr); print("-" * len(hdr))
    best = None
    for m, k, sw in itertools.product(a.sweep_m, a.sweep_k, a.sweep_swing):
        scores = []
        for ds in a.datasets:
            r = evaluate(ds, m, k, a.T, a.banks, sw, a.n_train, a.n_test,
                         seed=a.seed, edge_budget=a.edge_budget)
            scores.append(np.nan if r is None else r["arc_tr"])
        mean = float(np.nanmean(scores))
        flag = ""
        if best is None or mean > best[0]:
            best, flag = (mean, m, k, sw), "  <--"
        print(f"{m:>3} {k:>3} {a.T:>3} {a.banks:>2} {sw:>6.2f} "
              f"{m*a.T*a.banks:>5} "
              + " ".join(f"{s:>8.3f}" for s in scores) + flag)
    print(f"\nbest mean train separability {best[0]:.3f} at "
          f"M={best[1]}, k={best[2]}, swing={best[3]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+",
                    default=["twomoon", "circle", "2spirals"])
    ap.add_argument("--m", type=int, default=12)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--T", type=int, default=3)
    ap.add_argument("--banks", type=int, default=1)
    ap.add_argument("--swing", type=float, default=0.26)
    ap.add_argument("--n-train", type=int, default=40)
    ap.add_argument("--n-test", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--edge-budget", type=int, default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--neuron", default="inverter",
                    choices=["inverter", "diffpair"])
    ap.add_argument("--fan-in", type=int, default=3)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--bias-sweep", action="store_true")
    ap.add_argument("--vbb", type=float, default=None)
    ap.add_argument("--vnn", type=float, default=None)
    ap.add_argument("--sweep-vbb", nargs="+", type=float,
                    default=[1.90, 2.10, 2.25, 2.35, 2.45, 2.52])
    ap.add_argument("--sweep-m", nargs="+", type=int, default=[8, 12, 16])
    ap.add_argument("--sweep-k", nargs="+", type=int, default=[8, 16])
    ap.add_argument("--sweep-swing", nargs="+", type=float,
                    default=[0.26, 0.45])
    a = ap.parse_args()
    if a.bias_sweep:
        bias_sweep(a)
    elif a.sweep:
        sweep(a)
    else:
        main(a)
