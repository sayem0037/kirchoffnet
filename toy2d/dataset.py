"""
dataset.py -- the reference repo's 2-D toy datasets, as BINARY CLASSIFICATION.

Same generators as kirchhoffnet/src/utils/testbench.py (twomoon, circle, 2spirals),
but we KEEP the 2-class labels (the reference discarded them for generative density
modeling). 2 features (x, y) -> standardized -> mapped onto 2 circuit input sources.

Small balanced train/test subset (each sample is a SPICE simulation).
"""

import numpy as np
from sklearn.datasets import make_moons, make_circles
from sklearn.preprocessing import StandardScaler

N_PER_CLASS_TRAIN = 20
N_PER_CLASS_TEST  = 12
SEED = 42
DATASETS = ("twomoon", "circle", "2spirals")


def _raw(name, n=4096):
    """Return (points Nx2, labels N) using the reference repo's generators."""
    if name == "twomoon":
        X, y = make_moons(n_samples=n, noise=0.1, random_state=SEED)
    elif name == "circle":
        X, y = make_circles(n_samples=n, noise=0.06, factor=0.5, random_state=SEED)
    elif name == "2spirals":
        rng = np.random.default_rng(SEED)
        m = n // 2
        t = np.sqrt(rng.random((m, 1))) * 540 * (2 * np.pi) / 360
        d1x = -np.cos(t) * t + rng.random((m, 1)) * 0.5
        d1y =  np.sin(t) * t + rng.random((m, 1)) * 0.5
        Xa = np.hstack((d1x, d1y))            # spiral / class 0
        Xb = np.hstack((-d1x, -d1y))          # mirror spiral / class 1
        X = np.vstack((Xa, Xb)) / 3.0
        X += rng.standard_normal(X.shape) * 0.1
        y = np.concatenate([np.zeros(m), np.ones(m)]).astype(int)
    else:
        raise ValueError(f"unknown dataset {name!r}; choose from {DATASETS}")
    return X, y.astype(int)


def load_dataset(name="twomoon"):
    """
    Returns (X_train, y_train, X_test, y_test):
      X_* : (N, 2) standardized features   y_* : (N,) integer labels {0,1}
    """
    X, y = _raw(name)
    X = StandardScaler().fit_transform(X)
    rng = np.random.default_rng(SEED)
    tr, te = [], []
    for cls in (0, 1):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        tr.extend(idx[:N_PER_CLASS_TRAIN])
        te.extend(idx[N_PER_CLASS_TRAIN:N_PER_CLASS_TRAIN + N_PER_CLASS_TEST])
    tr = np.array(tr); te = np.array(te)
    rng.shuffle(tr); rng.shuffle(te)
    return X[tr], y[tr].astype(np.int64), X[te], y[te].astype(np.int64)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    a = ap.parse_args()
    Xtr, ytr, Xte, yte = load_dataset(a.dataset)
    print(f"{a.dataset}: train {Xtr.shape} {np.bincount(ytr)}  test {Xte.shape} {np.bincount(yte)}")
    print(f"  feature ranges x[{Xtr[:,0].min():.2f},{Xtr[:,0].max():.2f}] "
          f"y[{Xtr[:,1].min():.2f},{Xtr[:,1].max():.2f}]")
