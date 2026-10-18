"""
digital_train.py -- fixed-point MLP, trained the way the reference designs do it.

THE FLOW
--------
This is the published hardware/software split for a digital MLP accelerator: train in
software with the quantization in the loop, export integer weights, run bit-accurate
inference on the hardware. Training does not happen on the chip and is not supposed to.

    float master weights
        |  quantize to N bits in the FORWARD pass (straight-through estimator
        |  passes the gradient through the rounding unchanged)
        v
    integer weights  --->  digital_verify.py  --->  gate-level netlist at .OP

The quantization is real: the forward pass uses the rounded weights and rounded
activations the datapath would, so the accuracy reported here is the accuracy the
integer hardware produces, not an optimistic float number.

WHY ReLU HERE AND tanh IN THE ANALOG ARM
----------------------------------------
Each arm follows its own literature. ReLU is the standard activation in digital
accelerators -- it is a sign test and a mux, essentially free in logic. The crossbar
arm uses tanh because its column output is a signed, zero-centred differential voltage
and a ReLU on that kills half the units outright. The activation is a property of each
design, not a knob tuned per arm.
"""

import argparse
import importlib.util
import os
import sys
import time

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
COMPARE = os.path.join(os.path.dirname(BASE), "compare")
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")
sys.path.insert(0, BASE)
sys.path.insert(0, COMPARE)
sys.path.append(KFABRIC)

from trainlog import TrainLog                      # noqa: E402
import metrics                                     # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


load_any = _load("_ds_any2", os.path.join(KFABRIC, "datasets_any.py")).load_any


# ============================================================ fixed point =====
def q_scale(x, bits):
    """Per-tensor symmetric scale: the power of two that keeps |x| inside range.

    A power of two because the hardware rescale is then a shift, which is what a
    fixed-point datapath actually does -- an arbitrary scale would need a multiplier.
    """
    qmax = 2 ** (bits - 1) - 1
    peak = float(np.max(np.abs(x))) if np.size(x) else 1.0
    if peak <= 0:
        return 1.0
    return 2.0 ** np.ceil(np.log2(peak / qmax))


def quantize(x, bits, scale=None):
    """Round to the integer grid and return the DEQUANTIZED value plus its scale."""
    s = q_scale(x, bits) if scale is None else scale
    qmax = 2 ** (bits - 1) - 1
    q = np.clip(np.round(x / s), -qmax, qmax)
    return q * s, s


def to_int(x, bits, scale):
    qmax = 2 ** (bits - 1) - 1
    return np.clip(np.round(x / scale), -qmax, qmax).astype(np.int64)


# ================================================================ network =====
def softmax(z):
    e = np.exp(z - np.max(z))
    return e / e.sum()


class FixedPointMLP:
    """2 -> H -> C with ReLU, trained quantization-aware."""

    def __init__(self, sizes, bits=8, seed=0):
        self.sizes = list(sizes)
        self.bits = bits
        rng = np.random.default_rng(seed)
        self.W = []
        for l in range(len(sizes) - 1):
            w = rng.normal(0, 1.0 / np.sqrt(sizes[l] + 1), (sizes[l] + 1, sizes[l + 1]))
            w[0, :] = 0.0                      # zero bias, as always
            self.W.append(w)

    def qweights(self):
        out = []
        for w in self.W:
            wq, s = quantize(w, self.bits)
            out.append((wq, s))
        return out

    def forward(self, x, keep=False):
        a = np.asarray(x, dtype=float)
        acts, pre = [a], []
        for l, w in enumerate(self.W):
            wq, _ = quantize(w, self.bits)
            a1 = np.concatenate([[1.0], a])
            z = a1 @ wq
            pre.append(z)
            if l < len(self.W) - 1:
                a = np.maximum(z, 0.0)
                a, _ = quantize(a, self.bits)   # the activation bus is N bits too
            else:
                a = z
            acts.append(a)
        return (a, acts, pre) if keep else a

    def accuracy(self, X, y):
        return float(np.mean([np.argmax(self.forward(X[k])) == y[k]
                              for k in range(len(y))]))

    def flat_weights(self):
        return np.concatenate([w.ravel() for w in self.W])

    def weight_names(self):
        out = []
        for l, w in enumerate(self.W):
            for i in range(w.shape[0]):
                for j in range(w.shape[1]):
                    out.append(f"L{l}_w_{i}_{j}")
        return out

    def export_int(self):
        """Integer weights and their scales -- what gets written to the hardware."""
        out = []
        for w in self.W:
            s = q_scale(w, self.bits)
            out.append(dict(q=to_int(w, self.bits, s).tolist(), scale=float(s)))
        return out


def train_step(net, x, y, lr, gain=4.0):
    """One sample. Straight-through estimator: forward quantized, backward not."""
    scores, acts, pre = net.forward(x, keep=True)
    p = softmax(gain * scores)
    oh = np.zeros_like(p); oh[y] = 1.0
    loss = float(-np.log(max(p[y], 1e-12)))

    delta = (p - oh) * gain
    for l in reversed(range(len(net.W))):
        a1 = np.concatenate([[1.0], acts[l]])
        g = np.outer(a1, delta)
        if l > 0:
            back = (net.W[l] @ delta)[1:]
            delta = back * (pre[l - 1] > 0)     # through ReLU
        net.W[l] -= lr * g                      # update the FLOAT master weights
    return loss, int(np.argmax(scores))


def to_pm1(X, mn=None, mx=None):
    if mn is None:
        mn, mx = X.min(0), X.max(0)
    span = np.where(mx - mn > 1e-12, mx - mn, 1.0)
    return 2 * np.clip((X - mn) / span, 0, 1) - 1, mn, mx


# =================================================================== main =====
def main(a):
    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, n_train=a.n_train,
                                        n_test=a.n_test)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr, mn, mx = to_pm1(Xtr)
    Xte, _, _ = to_pm1(Xte, mn, mx)

    sizes = [Xtr.shape[1], a.hidden, C]
    net = FixedPointMLP(sizes, bits=a.bits, seed=a.seed)
    print(f"fixed-point MLP | {a.dataset} | sizes={sizes} | INT{a.bits} | ReLU")

    stem = os.path.join(RESULTS, f"digital_{a.dataset}_{a.tag}")
    log = TrainLog(stem, net.weight_names(),
                   meta=dict(arm="digital", dataset=a.dataset, sizes=sizes,
                             bits=a.bits, n_train=len(ytr), n_test=len(yte),
                             C=C, seed=a.seed, lr=a.lr, act="relu",
                             update_rule="QAT + straight-through estimator"))

    t0 = time.perf_counter()
    for ep in range(1, a.epochs + 1):
        lr = a.lr * (a.lr_decay ** (ep - 1))
        order = np.random.default_rng(a.seed + ep).permutation(len(ytr))
        L = []
        for k in order:
            l_, _ = train_step(net, Xtr[k], int(ytr[k]), lr, a.gain)
            L.append(l_)
        tr = net.accuracy(Xtr, ytr)
        te = net.accuracy(Xte, yte)
        log.log(ep, float(np.mean(L)), tr, te, net.flat_weights())
        if ep % a.report == 0 or ep == 1:
            lo, hi = metrics.wilson(te, len(yte))
            print(f"  ep {ep:3d}  loss {np.mean(L):.4f}  train {tr:.3f}  "
                  f"test {te:.3f} [{lo:.2f},{hi:.2f}]  "
                  f"[{(time.perf_counter()-t0)/60:.2f} min]")

    conv = metrics.epochs_to_converge([r["test"] for r in log.rows])
    out = log.finish(convergence=conv, int_weights=net.export_int())
    print(f"  best test {conv['best']:.3f} at epoch {conv['epoch']}")
    print(f"saved -> {out}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle",
                    choices=["twomoon", "circle", "2spirals"])
    ap.add_argument("--hidden", type=int, default=8)
    ap.add_argument("--n-train", type=int, default=120)
    ap.add_argument("--n-test", type=int, default=120)
    ap.add_argument("--bits", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--lr-decay", type=float, default=0.98)
    ap.add_argument("--gain", type=float, default=4.0)
    ap.add_argument("--report", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    sys.exit(main(ap.parse_args()))
