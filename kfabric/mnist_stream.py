"""
mnist_stream.py -- real MNIST, downsampled and turned into a STREAM of T chunks.

This is where the architecture's central claim becomes concrete. The reference
ICCAD KirchhoffNet consumes MNIST as 784 simultaneous node voltages, so its
circuit has 834 nodes. Here the same image is delivered to a fixed M-node core as
T successive row-chunks, so the circuit never grows: 784 pixels enter through
k rails over T steps instead of through 784 parallel DACs.

Downsampling to `side` x `side` is a compute concession, not an architectural
one -- it reduces T and k, which are the two things that multiply the SPICE bill.
The row-wise streaming format is the standard "sequential MNIST" benchmark, where
a vanilla RNN reaches ~96.5% and an RNN with a hidden state of only 56 units
reaches ~96%; that is the honest reference point for a 12-node analog core, not
the 99.4% of a 920,272-parameter feed-forward model.

Data source: the MNIST cached at ~/.keras/datasets/mnist.npz (plain npz, loaded
with numpy -- no TensorFlow import).
"""
import os
import numpy as np
from PIL import Image

MNIST_NPZ = os.path.expanduser("~/.keras/datasets/mnist.npz")


def _resize(imgs, side):
    if imgs.shape[1] == side:
        return imgs.astype(np.float64) / 255.0
    out = np.empty((len(imgs), side, side), dtype=np.float64)
    for i, im in enumerate(imgs):
        out[i] = np.asarray(Image.fromarray(im).resize((side, side), Image.BILINEAR))
    return out / 255.0


def load_mnist_stream(side=8, n_train=120, n_test=60, classes=None, seed=0,
                      path=MNIST_NPZ):
    """Returns (Xtr, ytr, Xte, yte) with X of shape (n, T=side, k=side) in [0,1].

    Classes are balanced by construction so a small subset stays informative.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"MNIST not found at {path}. Expected the cached keras npz.")
    d = np.load(path)
    classes = list(range(10)) if classes is None else list(classes)
    rng = np.random.default_rng(seed)

    def take(x, y, n_total):
        per = int(np.ceil(n_total / len(classes)))
        idx = []
        for c in classes:
            pool = np.where(y == c)[0]
            idx.append(rng.choice(pool, size=min(per, len(pool)), replace=False))
        idx = np.concatenate(idx)[:n_total]
        rng.shuffle(idx)
        return _resize(x[idx], side), np.array([classes.index(v) for v in y[idx]])

    Xtr, ytr = take(d["x_train"], d["y_train"], n_train)
    Xte, yte = take(d["x_test"], d["y_test"], n_test)
    return Xtr, ytr, Xte, yte


def as_chunks(X):
    """(n, side, side) -> list of T arrays (n, k): one row-chunk per step."""
    return [X[:, t, :] for t in range(X.shape[1])]


if __name__ == "__main__":
    Xtr, ytr, Xte, yte = load_mnist_stream(side=8, n_train=120, n_test=60)
    print(f"MNIST stream | train {Xtr.shape} labels {np.bincount(ytr)}")
    print(f"             | test  {Xte.shape} labels {np.bincount(yte)}")
    print(f"             | T={Xtr.shape[1]} steps of k={Xtr.shape[2]} rails, "
          f"range [{Xtr.min():.2f}, {Xtr.max():.2f}]")
    print("\nfirst sample, streamed row by row (each row is one core invocation):")
    for t, row in enumerate(Xtr[0]):
        print(f"  t={t}  " + "".join(" .:-=+*#%@"[min(9, int(v * 9.99))] for v in row))
    print(f"  label = {ytr[0]}")
