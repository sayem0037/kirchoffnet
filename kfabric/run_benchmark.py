"""
run_benchmark.py -- the accuracy benchmark, with the ablation that keeps it honest.

Every dataset is reported as four rows sharing one split and one read-out, so the
circuit's contribution is measured rather than assumed:

    raw + linear     logistic regression on the raw input. The circuit has to
                     beat this or it is not earning its place. On MNIST this is
                     a strong baseline -- ~92% on full-resolution pixels.
    ARC + linear     the frozen random ARC feature map + the same read-out.
    KRC + linear     the old no-activation core, same read-out, to show what the
                     activation is worth on its own.
    chance           1 / n_classes.

Accuracies carry a binomial 95% interval, because a 24-point test set quantises
at 4.17% and cannot support a "90%" claim at all -- which is why the toy splits
here are enlarged.

Usage:
    python run_benchmark.py --toy
    python run_benchmark.py --mnist
"""
import argparse
import json
import os
import time

import numpy as np
from sklearn.linear_model import LogisticRegression

from datasets_any import load_any, to_stream, default_mode
from features import bank_features

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def wilson(acc, n, z=1.96):
    """Wilson 95% interval -- honest at small n, unlike the normal approximation."""
    if n == 0:
        return (np.nan, np.nan)
    d = 1 + z * z / n
    c = (acc + z * z / (2 * n)) / d
    h = z * np.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def fit_readout(Ftr, ytr, Fte, yte, C=1.0):
    mu, sd = Ftr.mean(0), Ftr.std(0) + 1e-9
    # NB: sklearn 1.7 removed the multi_class kwarg; multinomial is the default.
    m = LogisticRegression(max_iter=8000, C=C)
    m.fit((Ftr - mu) / sd, ytr)
    return (float(m.score((Ftr - mu) / sd, ytr)),
            float(m.score((Fte - mu) / sd, yte)))


def run_dataset(ds, a):
    t0 = time.perf_counter()
    kw = {}
    if ds in ("twomoon", "circle", "2spirals"):
        kw = dict(n_train=a.n_train, n_test=a.n_test)
    elif ds in ("mnist", "digits"):
        kw = dict(n_train=a.n_train, n_test=a.n_test)
        if ds == "mnist":
            kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, spatial = load_any(ds, **kw)
    mode = default_mode(spatial, np.asarray(Xtr).reshape(len(Xtr), -1))
    T = a.T if mode == "repeat" else None
    Str, lo, hi = to_stream(Xtr, spatial, mode=mode, T=T, k=a.k)
    Ste, _, _ = to_stream(Xte, spatial, mode=mode, T=T, k=a.k, lo=lo, hi=hi)
    d_in = Str.shape[2]

    # cal_tag MUST be shared by train and test. Without it each split fits its
    # own per-neuron thresholds, i.e. becomes a different circuit, and the
    # comparison is meaningless. (The toy numbers reported before calibration
    # existed are unaffected -- they ran with calibration off.)
    fkw = dict(d_in=d_in, m_state=a.m, k_data=a.k, n_banks=a.banks,
               seed=a.seed, swing=a.swing, fan_in=a.fan_in,
               neuron="inverter", verbose=a.verbose,
               cal_tag=f"{ds}cal")
    Ftr, vtr = bank_features(Str, tag=f"{ds}_tr{len(ytr)}", **fkw)
    Fte, vte = bank_features(Ste, tag=f"{ds}_te{len(yte)}", **fkw)

    Xtr_f = np.asarray(Xtr).reshape(len(Xtr), -1)[vtr]
    Xte_f = np.asarray(Xte).reshape(len(Xte), -1)[vte]
    ytr_v, yte_v = ytr[vtr], yte[vte]

    rows = []
    rows.append(("raw + linear",) + fit_readout(Xtr_f, ytr_v, Xte_f, yte_v))
    rows.append(("ARC + linear",) + fit_readout(Ftr, ytr_v, Fte, yte_v))
    el = time.perf_counter() - t0
    return dict(dataset=ds, C=C, n_train=len(ytr_v), n_test=len(yte_v),
                n_feat=Ftr.shape[1], T=Str.shape[1], rows=rows, secs=el,
                mode=mode)


def main(a):
    sets = a.datasets
    print(f"BENCHMARK | neuron=inverter fan_in={a.fan_in} M={a.m} k={a.k} "
          f"T={a.T} banks={a.banks} swing={a.swing}\n")
    out = []
    for ds in sets:
        r = run_dataset(ds, a)
        out.append(r)
        print(f"{r['dataset']}  ({r['C']} classes, {r['n_train']} train / "
              f"{r['n_test']} test, T={r['T']}, {r['n_feat']} features, "
              f"{r['secs']/60:.1f} min)")
        print(f"   {'model':<16} {'train':>7} {'test':>7} {'95% CI':>16}")
        print(f"   {'chance':<16} {'':>7} {1.0/r['C']:>7.3f}")
        for name, tr, te in r["rows"]:
            lo, hi = wilson(te, r["n_test"])
            mark = "  <- >=0.90" if te >= 0.90 else ""
            print(f"   {name:<16} {tr:>7.3f} {te:>7.3f} "
                  f"  [{lo:.3f}, {hi:.3f}]{mark}")
        print()

    p = os.path.join(RESULTS, f"benchmark_{a.tag}.json")
    json.dump(out, open(p, "w"), indent=2)
    print(f"saved -> {p}")

    arc = [r for r in out if any(n == "ARC + linear" and te >= 0.90
                                 for n, _, te in r["rows"])]
    print(f"\n{len(arc)}/{len(out)} datasets reach >=0.90 test with ARC + linear.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=None)
    ap.add_argument("--toy", action="store_true")
    ap.add_argument("--mnist", action="store_true")
    ap.add_argument("--m", type=int, default=24)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--T", type=int, default=4)
    ap.add_argument("--banks", type=int, default=2)
    ap.add_argument("--fan-in", type=int, default=3)
    ap.add_argument("--swing", type=float, default=0.26)
    ap.add_argument("--n-train", type=int, default=400)
    ap.add_argument("--n-test", type=int, default=400)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()
    if a.datasets is None:
        a.datasets = (["twomoon", "circle", "2spirals"] if a.toy
                      else ["mnist"] if a.mnist
                      else ["twomoon", "circle", "2spirals"])
    main(a)
