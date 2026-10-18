"""
run_kfq.py -- the KFQ benchmark, reported so it cannot flatter itself.

Three rows per dataset, one split, one protocol:

    chance          1 / n_classes
    raw + linear    logistic regression on the raw inputs. This is the bar the
                    circuit must clear, and it is not a formality: on 8x8 MNIST
                    it scores 0.854, and the earlier ARC build reached only
                    0.774-0.782 -- features WORSE than the pixels they came
                    from, which is what condemned that architecture.
    KFQ (argmax)    the circuit. Class scores are node voltage differences
                    V(c+_j) - V(c-_j) off the last column pair; the prediction
                    is argmax over them. No trained read-out anywhere.

Accuracies carry a Wilson 95% interval, which stays honest at small n where the
normal approximation does not.

Usage:
    python run_kfq.py --dataset iris --tag pilot
    python run_kfq.py --dataset mnist --side 8 --tag mnist1
"""
import argparse
import json
import os
import time

import numpy as np
from sklearn.linear_model import LogisticRegression

from datasets_any import load_any

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def wilson(acc, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = (acc + z * z / (2 * n)) / d
    h = z * np.sqrt(acc * (1 - acc) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def main(a):
    import train_kfq as T
    kw = dict(n_train=a.n_train, n_test=a.n_test)
    if a.dataset == "mnist":
        kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)

    rows = [("chance", float("nan"), 1.0 / C)]
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    lr = LogisticRegression(max_iter=8000).fit((Xtr - mu) / sd, ytr)
    rows.append(("raw + linear", float(lr.score((Xtr - mu) / sd, ytr)),
                 float(lr.score((Xte - mu) / sd, yte))))

    ck = a.checkpoint or os.path.join(RESULTS, f"kfq_{a.dataset}_{a.tag}.json")
    secs = 0.0
    if os.path.exists(ck):
        d = json.load(open(ck))
        layers = [tuple(t) for t in d["layers"]]
        cfg, th = d["cfg"], {k: float(v) for k, v in d["theta"].items()}
        Xtr_w, mn, mx = T.to_pm1(Xtr)
        Xte_w, _, _ = T.to_pm1(Xte, mn, mx)
        t0 = time.perf_counter()
        if a.workers > 1:
            import multiprocessing as mp
            pool = mp.Pool(a.workers, initializer=T._init_worker,
                           initargs=(layers, cfg, [], f"bench{a.dataset}"))
            tr = float(np.mean(pool.map(T._eval_work,
                       [(th, Xtr_w[k], int(ytr[k])) for k in range(len(ytr))])))
            te = float(np.mean(pool.map(T._eval_work,
                       [(th, Xte_w[k], int(yte[k])) for k in range(len(yte))])))
            pool.close(); pool.join()
        else:
            nl = T.scratch(f"bench_{a.dataset}")
            tr = T.evaluate(th, Xtr_w, ytr, layers, cfg, nl)
            te = T.evaluate(th, Xte_w, yte, layers, cfg, nl)
            if os.path.exists(nl):
                os.remove(nl)
        secs = time.perf_counter() - t0
        rows.append(("KFQ (argmax)", tr, te))
    else:
        print(f"note: no checkpoint at {ck} -- run train_kfq.py first.\n")

    print(f"{a.dataset}  ({C} classes, {len(ytr)} train / {len(yte)} test)")
    print(f"   {'model':<16} {'train':>7} {'test':>7} {'95% CI':>18}")
    for name, tr, te in rows:
        lo_, hi_ = wilson(te, len(yte))
        trs = "      -" if not np.isfinite(tr) else f"{tr:>7.3f}"
        mark = "  <- >=0.90" if te >= 0.90 else ""
        print(f"   {name:<16} {trs} {te:>7.3f}   [{lo_:.3f}, {hi_:.3f}]{mark}")
    if secs:
        print(f"\n   circuit evaluation: {secs/60:.1f} min for "
              f"{len(ytr)+len(yte)} samples")

    out = os.path.join(RESULTS, f"bench_kfq_{a.dataset}_{a.tag}.json")
    json.dump(dict(dataset=a.dataset, C=C, n_train=len(ytr), n_test=len(yte),
                   rows=rows), open(out, "w"), indent=2)
    print(f"\nsaved -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--checkpoint", default=None)
    main(ap.parse_args())
