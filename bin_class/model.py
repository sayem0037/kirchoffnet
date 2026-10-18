"""
model.py -- the thin software layers around the circuit, in plain numpy.

  Encoder : features (F) -> input-source voltages (K), affine + clip to a safe
            voltage range. Drives VIN, VREF1..VREFn.
  Readout : circuit state vector (M output-node voltages) -> C class logits,
            affine. Followed by softmax + cross-entropy.
  Adam    : optimizer for any named bundle of numpy arrays.

Circuit params (VTH*, VB*) are NOT here -- they live in the netlist and train
via the 100ns backward adjoint (assembled in train.py). These software layers
supply the linear weighting the analog stages can't express and are trained by
ordinary analytic gradients.
"""

import numpy as np


def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def cross_entropy(probs, y):
    n = len(y)
    return float(-np.log(probs[np.arange(n), y] + 1e-12).mean())


class Encoder:
    """v = clip(W x + b, vlo, vhi). Maps F features -> K source voltages."""

    def __init__(self, n_feat, src_names, b_init, w_scale=0.25, vlo=0.3, vhi=3.0, seed=0):
        self.src_names = list(src_names)
        K = len(src_names)
        rng = np.random.default_rng(seed)
        self.W = w_scale * rng.standard_normal((K, n_feat))
        self.b = np.array([b_init[s] for s in src_names], dtype=float)
        self.vlo, self.vhi = vlo, vhi

    def forward(self, x):
        raw = self.W @ x + self.b
        v = np.clip(raw, self.vlo, self.vhi)
        self._mask = (raw > self.vlo) & (raw < self.vhi)   # clip gradient mask
        self._x = x
        return {s: float(v[k]) for k, s in enumerate(self.src_names)}

    def backward(self, dL_dv):
        """dL_dv: dict {src_name: dL/dvoltage}. Returns grads for W, b."""
        g = np.array([dL_dv.get(s, 0.0) for s in self.src_names]) * self._mask
        gW = np.outer(g, self._x)
        gb = g
        return {"W": gW, "b": gb}


class Readout:
    """logits = W s + b. Maps M-dim circuit state -> C logits."""

    def __init__(self, m_state, n_class, seed=0):
        rng = np.random.default_rng(seed)
        self.W = 0.5 * rng.standard_normal((n_class, m_state))
        self.b = np.zeros(n_class)

    def forward(self, s):
        self._s = s
        return self.W @ s + self.b

    def backward(self, dL_dlogits):
        """Returns grads for W, b, and dL/dstate (to push into the circuit)."""
        gW = np.outer(dL_dlogits, self._s)
        gb = dL_dlogits
        dL_ds = self.W.T @ dL_dlogits
        return {"W": gW, "b": gb}, dL_ds


def ce_grad(logits, y):
    """Softmax cross-entropy gradient wrt logits (single sample)."""
    p = softmax(logits[None, :])[0]
    g = p.copy()
    g[y] -= 1.0
    return g   # dL/dlogits


class Adam:
    """Adam over a dict of numpy arrays (or python floats via 0-d arrays)."""

    def __init__(self, params, lr, betas=(0.9, 0.999), eps=1e-8):
        self.lr, self.b1, self.b2, self.eps = lr, betas[0], betas[1], eps
        self.m = {k: np.zeros_like(np.asarray(v, dtype=float)) for k, v in params.items()}
        self.v = {k: np.zeros_like(np.asarray(v, dtype=float)) for k, v in params.items()}
        self.t = 0

    def step(self, params, grads):
        self.t += 1
        for k in params:
            g = np.asarray(grads[k], dtype=float)
            self.m[k] = self.b1 * self.m[k] + (1 - self.b1) * g
            self.v[k] = self.b2 * self.v[k] + (1 - self.b2) * g * g
            mh = self.m[k] / (1 - self.b1 ** self.t)
            vh = self.v[k] / (1 - self.b2 ** self.t)
            params[k] = params[k] - self.lr * mh / (np.sqrt(vh) + self.eps)
        return params
