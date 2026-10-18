"""
datasets_any.py -- turn ANY classification dataset into a KRC input stream.

The core never changes shape: it has M state nodes and k data rails, and it is
invoked T times. So the only thing a new dataset has to supply is a rule for
cutting its input into T chunks of k values. That rule is the whole of this file,
and it is what makes the architecture dataset-agnostic in practice rather than
just in principle.

    load_any(name)   ->  Xtr, ytr, Xte, yte, n_classes, spatial   (raw features)
    to_stream(X, ...) ->  (n, T, k) array in [0, 1]

Three streaming modes, chosen by `mode`:

  "row"     an image (n, h, w) becomes T = h chunks of k = w.  The natural
            reading order for image data, and the standard sequential-MNIST
            format.
  "chunk"   a flat vector (n, D) is cut into T = ceil(D/k) pieces of k, zero
            padded.  Use when D is large relative to the core.
  "repeat"  a flat vector (n, D) is presented UNCHANGED at all T steps, with
            k = D.  This is the right mode for low-dimensional static inputs
            such as the 2-D toy sets: the core is a continuous-time recurrent
            system driven by a constant input, so T becomes processing depth
            rather than a way of feeding a large input.  With T = 1 it reduces
            to a single feed-forward pass, which is what the recurrence is
            supposed to improve on.

Adding a dataset means adding one entry to REGISTRY. Nothing else in kfabric
changes.

Run `python datasets_any.py` to list what is registered and print the stream
shape each one produces.
"""
import numpy as np

# --------------------------------------------------------------------------
# loaders -- each returns (Xtr, ytr, Xte, yte, n_classes, spatial)
#   X       : (n, D) flat features, or (n, h, w) for image-shaped data
#   spatial : (h, w) if the data is image-shaped, else None
# --------------------------------------------------------------------------

def _toy(name, n_train=None, n_test=None, seed=42):
    """The 2-D toy sets.

    With n_train/n_test given, this bypasses ../toy2d_serial_diff/dataset.py's
    fixed 40/24 split and draws a larger one from the SAME generators. That
    matters for any accuracy claim: a 24-point test set quantises accuracy in
    4.17% steps, so 0.875 and 0.917 differ by a single point and "90%" is not a
    statement the split can support. It is affordable now only because features
    are forward-only and cached.
    """
    if n_train is None and n_test is None:
        from dataset import load_dataset
        Xtr, ytr, Xte, yte = load_dataset(name)
        return Xtr, ytr, Xte, yte, int(max(ytr.max(), yte.max())) + 1, None

    from dataset import _raw
    from sklearn.preprocessing import StandardScaler
    X, y = _raw(name, n=8192)
    X = StandardScaler().fit_transform(X)
    Xtr, ytr, Xte, yte = _split(X, y, n_train or 400, n_test or 400, seed)
    return Xtr, ytr, Xte, yte, int(y.max()) + 1, None


def _mnist(side=8, n_train=150, n_test=60, seed=0):
    from mnist_stream import load_mnist_stream
    Xtr, ytr, Xte, yte = load_mnist_stream(side=side, n_train=n_train,
                                           n_test=n_test, seed=seed)
    return Xtr, ytr, Xte, yte, 10, (side, side)


def _digits(n_train=150, n_test=60, seed=0):
    """sklearn's 8x8 handwritten digits -- a second image set, no download."""
    from sklearn.datasets import load_digits
    d = load_digits()
    X = d.images / 16.0
    y = d.target.astype(np.int64)
    return _split(X, y, n_train, n_test, seed) + (10, (8, 8))


def _iris(n_train=90, n_test=60, seed=0):
    """4 features, 3 classes -- a flat, low-dimensional, non-image set."""
    from sklearn.datasets import load_iris
    from sklearn.preprocessing import StandardScaler
    d = load_iris()
    X = StandardScaler().fit_transform(d.data)
    return _split(X, d.target.astype(np.int64), n_train, n_test, seed) + (3, None)


def _split(X, y, n_train, n_test, seed):
    """Balanced class-stratified split, independent RNG streams for train/test.

    Independent streams matter: with one sequential RNG, changing n_train
    silently changes which test samples are drawn, so a plotting script that
    guesses n_train would score the model on a different test set.
    """
    classes = np.unique(y)
    rtr = np.random.default_rng(seed)
    rte = np.random.default_rng(seed + 10_000)
    per_tr = int(np.ceil(n_train / len(classes)))
    per_te = int(np.ceil(n_test / len(classes)))
    itr, ite = [], []
    for c in classes:
        pool = np.where(y == c)[0]
        pick = rtr.permutation(pool)
        itr.append(pick[:per_tr])
        ite.append(pick[per_tr:per_tr + per_te])
    itr = np.concatenate(itr)[:n_train]
    ite = np.concatenate(ite)[:n_test]
    rtr.shuffle(itr)
    rte.shuffle(ite)
    return X[itr], y[itr], X[ite], y[ite]


REGISTRY = {
    "twomoon":  lambda **kw: _toy("twomoon", **kw),
    "circle":   lambda **kw: _toy("circle", **kw),
    "2spirals": lambda **kw: _toy("2spirals", **kw),
    "mnist":    _mnist,
    "digits":   _digits,
    "iris":     _iris,
}

# datasets whose inputs are 2-D and can therefore have a decision boundary drawn
PLANAR = ("twomoon", "circle", "2spirals")


def load_any(name, **kw):
    if name not in REGISTRY:
        raise ValueError(f"unknown dataset {name!r}; choose from "
                         f"{tuple(REGISTRY)}")
    return REGISTRY[name](**kw)


# --------------------------------------------------------------------------
# streaming
# --------------------------------------------------------------------------

def default_mode(spatial, X):
    """row for images, repeat for small flat inputs, chunk for large ones."""
    if spatial is not None:
        return "row"
    return "repeat" if X.shape[1] <= 8 else "chunk"


def to_stream(X, spatial=None, mode="auto", T=None, k=None, lo=None, hi=None):
    """Any dataset -> (n, T, k) in [0, 1].

    `lo`/`hi` are the per-feature min/max used for scaling. Pass the TRAINING
    set's values when converting a test set (or a plotting grid) so both are
    scaled identically; leave them None to compute from X itself.
    """
    X = np.asarray(X, float)
    if mode == "auto":
        mode = default_mode(spatial, X.reshape(len(X), -1))

    if mode == "row":
        if spatial is None and X.ndim != 3:
            raise ValueError("mode='row' needs image-shaped data")
        A = X if X.ndim == 3 else X.reshape(len(X), *spatial)
        flat = A.reshape(len(A), -1)
        lo, hi = _bounds(flat, lo, hi)
        A = ((A - lo.reshape(A.shape[1:])) /
             (hi - lo).reshape(A.shape[1:])).clip(0, 1)
        return A, lo, hi

    flat = X.reshape(len(X), -1)
    lo, hi = _bounds(flat, lo, hi)
    S = ((flat - lo) / (hi - lo)).clip(0, 1)

    if mode == "repeat":
        T = T or 1
        return np.repeat(S[:, None, :], T, axis=1), lo, hi

    if mode == "chunk":
        if not k:
            raise ValueError("mode='chunk' needs k")
        T = int(np.ceil(S.shape[1] / k))
        pad = T * k - S.shape[1]
        if pad:
            S = np.hstack([S, np.full((len(S), pad), 0.5)])
        return S.reshape(len(S), T, k), lo, hi

    raise ValueError(f"unknown mode {mode!r}")


def _bounds(flat, lo, hi):
    if lo is None or hi is None:
        lo, hi = flat.min(0), flat.max(0)
        hi = np.where(hi - lo < 1e-9, lo + 1.0, hi)
    return np.asarray(lo, float), np.asarray(hi, float)


if __name__ == "__main__":
    print(f"{'dataset':<10} {'classes':>7} {'train/test':>12} {'mode':>8} "
          f"{'stream (n,T,k)':>18}")
    print("-" * 60)
    for name in REGISTRY:
        try:
            Xtr, ytr, Xte, yte, C, sp = load_any(name)
        except Exception as e:
            print(f"{name:<10} unavailable: {str(e)[:40]}")
            continue
        m = default_mode(sp, Xtr.reshape(len(Xtr), -1))
        T = 4 if m == "repeat" else None
        S, _, _ = to_stream(Xtr, sp, mode=m, T=T, k=8)
        print(f"{name:<10} {C:>7} {f'{len(ytr)}/{len(yte)}':>12} {m:>8} "
              f"{str(S.shape):>18}")
