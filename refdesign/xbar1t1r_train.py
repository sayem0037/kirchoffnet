"""
xbar1t1r_train.py -- in-situ training of a 1T1R crossbar with the Manhattan rule.

THE LOOP, AND WHAT RUNS WHERE
-----------------------------
Every forward pass is a circuit simulation. Per layer:

    row drivers (DACs) -> 1T1R array -> column currents -> TIA -> column voltages
                                                                   |
                                                                 [ ADC ]
                                                                   |
                                               digital ReLU, requantize, re-encode
                                                                   |
                                                           next layer's rows

That ADC/DAC boundary is the architecture, not a shortcut: a crossbar accelerator leaves
the analog domain at every layer edge and does its activation in digital.

The backward pass is software, and that is also the architecture. On-chip training
demonstrations use a digital controller that reads the measured activations off the
array and computes the gradient SIGN; the array itself only ever does forward MVMs and
accepts write pulses. So this file deliberately does NOT use the simulator's adjoint --
not because it is unavailable, but because real crossbar hardware does not have one.

THE UPDATE
----------
Manhattan rule: one fixed-amplitude pulse per cell, direction set by the sign of the
gradient, magnitude set by the device. A weight is a differential pair, so raising it
means potentiating G+ AND depressing G- -- using both cells keeps each one further from
its rail, where the nonlinear step size collapses.

WHAT TO EXPECT, SO IT IS NOT MISTAKEN FOR A BUG
-----------------------------------------------
Manhattan training is noisy and converges slowly compared with software SGD. Every cell
moves on every step regardless of how small its gradient is, so the weights jitter
permanently instead of settling. That is the honest behaviour of fixed-amplitude updates
and it is a large part of what the weight-trajectory plot is for. It should not be
"fixed" by switching to proportional updates -- that would be modelling hardware nobody
can build.
"""

import argparse
import importlib.util
import json
import os
import sys
import time

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
COMPARE = os.path.join(os.path.dirname(BASE), "compare")
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")
sys.path.insert(0, BASE)
sys.path.insert(0, COMPARE)
# kfabric LAST: datasets_any.py does a bare `from dataset import _raw`, so its directory
# must be importable -- but kfabric also carries its own simulator_api.py, and putting it
# first would shadow compare's (the one with run_metered). Appending keeps both working.
sys.path.append(KFABRIC)

import xbar1t1r_netlist as XB                      # noqa: E402
from xbar1t1r_device import ResistiveDevice        # noqa: E402
from trainlog import TrainLog                      # noqa: E402
from simulator_api import eval_chain, scratch      # noqa: E402
import metrics                                     # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_ds = _load("_ds_any", os.path.join(KFABRIC, "datasets_any.py"))
load_any = _ds.load_any


# ============================================================ the network =====
class CrossbarNet:
    """Two 1T1R layers with a digital activation between them.

    Conductances live here as (n_in, n_out) arrays per layer. They ARE the weights --
    there is no shadow copy in floating point anywhere in this class.
    """

    def __init__(self, sizes, device, rf, adc_bits=8, seed=0, bias=True,
                 act="tanh", slope=12.0):
        self.sizes = list(sizes)                  # e.g. [2, 8, 2]
        self.dev = device
        self.rf = list(rf) if isinstance(rf, (list, tuple)) else [rf] * (len(sizes) - 1)
        self.adc_bits = adc_bits
        self.bias = bool(bias)
        # ACTIVATION. The digital activation is a free choice -- it runs on the
        # controller, not in the array -- but it has to suit the signal it is given.
        #
        # A differential crossbar produces a SIGNED, roughly zero-centred column
        # difference. Putting a ReLU on that kills half the units immediately, and the
        # survivors drift negative and die too: measured active fraction fell from 0.54
        # at initialisation to 0.00 within 25 epochs, on every dataset, and the network
        # sat at chance. tanh is symmetric about zero, has no dead region, and is what
        # the 1T1R MLP literature uses for exactly this reason.
        self.act = act
        # tanh SLOPE. The ADC normalises each column to |d| <~ 0.7, so tanh(2d) -- the
        # first choice -- is nearly linear over the whole signal range and the hidden
        # layer adds almost no nonlinearity: twomoon sat at ~0.87 (a linear classifier's
        # score) and 2spirals at ~0.70. The slope is a digital constant on the
        # controller, so it is free. Measured on the software twin (hidden 16, lr 0.01):
        #     slope   twomoon  circle  2spirals   (mean of last 10 epochs)
        #       2      0.875   0.998    0.670
        #       8      0.941   1.000    0.856
        #      12      0.966   0.997    0.938
        self.slope = float(slope)
        self.gp, self.gm = [], []
        for l in range(len(sizes) - 1):
            p, m = device.init_pair((sizes[l] + int(self.bias), sizes[l + 1]))
            if self.bias:
                # The BIAS cells start at zero weight: G+ == G-.
                #
                # Leaving them random gives every hidden unit an arbitrary constant
                # offset before it has seen any data, and with a ReLU after it that is
                # fatal -- a unit whose offset is negative is off for every input, its
                # gradient is identically zero, and it never comes back. Measured with a
                # random bias row: 6 of 8 hidden units were dead at initialisation and
                # the network sat at chance on all three datasets.
                #
                # Zero-initialised biases are standard practice in software too, for the
                # same reason; here the hardware equivalent is programming both cells of
                # the pair to the same conductance.
                mid = 0.5 * (p[0, :] + m[0, :])
                p[0, :] = mid
                m[0, :] = mid
            self.gp.append(p); self.gm.append(m)
        # ADC full scale per layer, calibrated before training (see calibrate()).
        self.fs = [1.0] * (len(sizes) - 1)

    # ------------------------------------------------------------- hardware ---
    def rows_for(self, xs):
        """Prepend the BIAS ROW: a dedicated row held at full drive (x = +1).

        Without it every hidden unit computes ReLU(w.x), which is positively
        homogeneous -- f(a*x) = a*f(x) for a > 0 -- so argmax over the outputs depends
        only on the DIRECTION of x and the decision boundary can only be a set of rays
        through the origin. `circle` is an inner-vs-outer ring, i.e. purely a question of
        magnitude, and is therefore not merely hard but impossible.

        Measured before this row was added: a 2-8-2 array sat at 0.63 on circle against
        0.50 chance, and a pure-software twin of the same network with the same update
        rule sat at exactly the same place -- which is what proved it was the
        architecture rather than the circuit.

        A dedicated bias row is standard in crossbar designs; it costs one row of cells.
        """
        a = np.asarray(xs, dtype=float)
        return np.concatenate([[1.0], a]) if self.bias else a

    def layer_forward(self, l, xs, nl):
        """One layer on the circuit. Returns the column differences, in volts."""
        XB.write_layer(self.gp[l], self.gm[l], self.rows_for(xs), nl, rf=self.rf[l])
        v = eval_chain(nl, XB.read_nodes(self.sizes[l + 1]))
        return np.array([v[p] - v[m] for p, m in XB.read_pairs(self.sizes[l + 1])])

    def activate(self, d):
        if self.act == "relu":
            return np.maximum(d, 0.0)
        if self.act == "lrelu":
            return np.where(d > 0, d, 0.01 * d)
        return np.tanh(self.slope * d)

    def dactivate(self, a):
        """Derivative at the ACTIVATION OUTPUT (so it needs no stored pre-activation)."""
        if self.act == "relu":
            return (a > 0).astype(float)
        if self.act == "lrelu":
            return np.where(a > 0, 1.0, 0.01)
        return self.slope * (1.0 - a ** 2)

    def adc(self, s, l):
        """Digitize a column reading: scale by the layer's full scale, quantize.

        A real ADC has a fixed input range and finite resolution; both are modelled,
        because 'the converter is ideal' is the assumption that makes analog arrays look
        better than they are.
        """
        q = 2 ** (self.adc_bits - 1) - 1
        x = np.clip(s / max(self.fs[l], 1e-12), -1.0, 1.0)
        return np.round(x * q) / q

    def forward(self, xs, nl, keep=False):
        """Full forward pass. Returns scores, and optionally the per-layer activations
        needed by the backward pass."""
        a = np.clip(np.asarray(xs, dtype=float), -1.0, 1.0)
        acts = [a]
        raw = []
        for l in range(len(self.sizes) - 1):
            s = self.layer_forward(l, a, nl)
            raw.append(s)
            d = self.adc(s, l)
            a = self.activate(d) if l < len(self.sizes) - 2 else d     # digital activation
            acts.append(a)
        return (a, acts, raw) if keep else a

    def transfer(self, l):
        """d(ADC input)/d(weight . row value): the layer's analog gain, SIGN INCLUDED.

        The TIA is inverting -- col+ - col- = -Rf * sum (G+ - G-) * v_read * x -- and the
        ADC then divides by its full scale. So the digitized reading is k * (W^T a) with
        k NEGATIVE. The backward pass must carry that sign: without it the output
        layer's gradient comes out exactly reversed (cosine -1.000 against finite
        differences) and the hidden layer's is right only because two sign errors
        cancel. The array was doing gradient ASCENT on its output layer.
        """
        return -self.rf[l] * XB.V_READ * self.dev.span / max(self.fs[l], 1e-12)

    def full_scale(self, l):
        """The largest column difference the array could physically produce."""
        n_rows = self.sizes[l] + int(self.bias)
        return self.rf[l] * n_rows * self.dev.span * XB.V_READ

    def calibrate(self, X, nl, n=24, headroom=1.5):
        """Set each converter's range from the MEASURED signal, with headroom.

        Getting this wrong twice was instructive, because the two failures look nothing
        alike:

          too SMALL (calibrated from the initial swing, before weights grew):
              the converter saturates. Scores pinned at the rails, score sd exactly
              1.000, loss frozen at 4.0003 -- confidently wrong on every sample.

          too LARGE (the array's absolute physical maximum, every cell at full
          conductance and perfectly aligned -- a state training never reaches):
              the converter is barely used. Measured full scale 0.53 V against an actual
              column swing of 0.02 V, so about 4 of 256 codes carried the entire signal.
              Scores barely varied, the loss sat at ln 2 = 0.693, and a tiny constant
              offset swamped the data: every sample classified as class 0.

        A real converter is matched to the signal distribution it will see, with a few
        tens of percent of headroom. That is what this does, and because the result is
        only a digital scale factor it costs nothing to refresh as training proceeds.
        """
        rng = np.random.default_rng(0)
        idx = rng.choice(len(X), size=min(n, len(X)), replace=False)
        fs = list(self.fs)
        for l in range(len(self.sizes) - 1):
            mags = []
            for k in idx:
                a = np.clip(X[k], -1.0, 1.0)
                for ll in range(l):
                    a = self.activate(self.adc(self.layer_forward(ll, a, nl), ll))
                mags.append(np.abs(self.layer_forward(l, a, nl)))
            m = float(np.percentile(np.concatenate(mags), 99)) * headroom
            fs[l] = float(np.clip(m, 1e-6, self.full_scale(l)))
            self.fs = fs            # later layers must see the updated earlier scales
        return self.fs

    # ------------------------------------------------------------- software ---
    def weights(self, l):
        """The signed weight matrix this layer's conductances represent."""
        return self.dev.weight(self.gp[l], self.gm[l])

    def flat_conductances(self):
        """Every programmed conductance, flat, for the trajectory log."""
        return np.concatenate([np.concatenate([p.ravel(), m.ravel()])
                               for p, m in zip(self.gp, self.gm)])

    def weight_names(self):
        out = []
        for l in range(len(self.sizes) - 1):
            for side in ("Gp", "Gm"):
                for i in range(self.sizes[l] + int(self.bias)):
                    for j in range(self.sizes[l + 1]):
                        out.append(f"L{l}_{side}_{i}_{j}")
        return out


# ============================================================= the gradient ===
def softmax(z):
    e = np.exp(z - np.max(z))
    return e / e.sum()


def sample_grad(net, x, y, nl, gain=4.0):
    """Forward on the circuit, backward in software; return per-layer GRADIENTS.

    The magnitudes are kept here and reduced to a sign only at aggregation time, because
    update thresholding needs to know which gradients are large relative to the rest of
    the batch. Only the ordering matters, so the magnitudes never need to be accurate --
    which is why the rule tolerates the array's non-idealities.

    The backward pass uses the MEASURED activations and the PROGRAMMED weights, which is
    what a digital training controller has access to. Only the sign survives, so the
    magnitudes never need to be accurate -- which is exactly why the Manhattan rule is
    robust to the array's non-idealities.
    """
    scores, acts, _ = net.forward(x, nl, keep=True)
    p = softmax(gain * scores)
    onehot = np.zeros_like(p); onehot[y] = 1.0
    loss = float(-np.log(max(p[y], 1e-12)))

    delta = (p - onehot) * gain                    # dL/d(scores)
    signs = [None] * (len(net.sizes) - 1)
    for l in reversed(range(len(net.sizes) - 1)):
        a_in = net.rows_for(acts[l])               # same vector the array actually saw
        delta = delta * net.transfer(l)            # through the inverting TIA + ADC scale
        signs[l] = np.outer(a_in, delta)           # dL/dW for this layer
        if l > 0:
            back = net.weights(l) @ delta          # (n_in+bias,) ...
            if net.bias:
                back = back[1:]                    # ... drop the bias row's slot
            delta = back * net.dactivate(acts[l])  # through the digital activation
    return loss, signs, int(np.argmax(scores))


def threshold_signs(grad, thresh):
    """Manhattan sign with UPDATE THRESHOLDING.

    Plain Manhattan pulses every cell on every step, whatever its gradient. Near a
    solution most gradients are noise, so the array never settles -- it keeps taking
    full-amplitude steps in whichever direction the batch happened to favour. Measured
    without thresholding: circle peaked at 0.850 and ENDED at 0.367, twomoon peaked at
    0.800 and ended at 0.375. The runs were not failing to learn, they were learning and
    then walking away.

    Thresholding is the standard remedy in the in-situ literature: leave a cell alone
    unless its gradient is a meaningful fraction of the largest in that layer this step.
    Cells with nothing to say stop being pushed around, and the array can converge.
    """
    g = np.asarray(grad, dtype=float)
    peak = float(np.max(np.abs(g)))
    if peak <= 0.0:
        return np.zeros_like(g)
    return np.sign(g) * (np.abs(g) >= thresh * peak)


def apply_manhattan(net, grads, lr_pulses, thresh=0.0):
    """One fixed-amplitude pulse per cell that cleared the threshold.

    A weight is (G+ - G-), so to move the weight DOWN (positive gradient) we depress G+
    and potentiate G-. Using both cells halves how far each must travel and keeps them
    away from the rails, where the nonlinear step size collapses to nothing.
    """
    for l, g in enumerate(grads):
        if g is None:
            continue
        s = threshold_signs(g, thresh)
        net.gp[l] = net.dev.manhattan_update(net.gp[l], s, lr_pulses)
        net.gm[l] = net.dev.manhattan_update(net.gm[l], -s, lr_pulses)


def apply_writeverify(net, grads, lr, acc):
    """Closed-loop in-situ update: program each cell toward a TARGET conductance.

    Two mechanisms, both standard and both necessary:

    1. WRITE-VERIFY. The controller reads the cell back and corrects until it is within
       tolerance, so the update is proportional to the gradient rather than a fixed
       pulse. This is what Li et al. (Nat. Comms 2018) demonstrate.

    2. DIGITAL GRADIENT ACCUMULATION. A desired update is usually SMALLER THAN ONE
       programmable level, and a sub-level write is not a small change -- it is either
       nothing or a whole level of noise. So the residue is held in a digital register
       and the cell is programmed only when the accumulation has grown past one level.
       Without this the array is driven by rounding rather than by gradients; measured,
       it is the difference between a final accuracy of 0.500 and 0.842 on twomoon.

    `acc` is the per-layer residue register, carried across calls.
    """
    step = net.dev.level_step()
    for l, g in enumerate(grads):
        if g is None:
            continue
        acc[l] += -lr * net.dev.span * g
        n = np.trunc(acc[l] / step)
        if np.any(n):
            net.gp[l] = net.dev.write(net.gp[l] + n * step)
            net.gm[l] = net.dev.write(net.gm[l] - n * step)
            acc[l] -= n * step
    return acc


# ========================================================== worker plumbing ===
_W = {}


def _init_worker(state, tag):
    _W["state"] = state
    _W["nl"] = scratch(tag, BASE)


def _rebuild(net_state):
    net = object.__new__(CrossbarNet)
    net.sizes = net_state["sizes"]
    net.dev = ResistiveDevice(**net_state["devkw"])
    net.rf = net_state["rf"]
    net.adc_bits = net_state["adc_bits"]
    net.bias = net_state.get("bias", True)
    net.act = net_state.get("act", "tanh")
    net.slope = net_state.get("slope", 12.0)
    net.fs = net_state["fs"]
    net.gp = [np.array(a) for a in net_state["gp"]]
    net.gm = [np.array(a) for a in net_state["gm"]]
    return net


def _grad_work(arg):
    gp, gm, x, y, gain = arg
    net = _rebuild(dict(_W["state"], gp=gp, gm=gm))
    return sample_grad(net, x, int(y), _W["nl"], gain)


def _eval_work(arg):
    gp, gm, x, y = arg
    net = _rebuild(dict(_W["state"], gp=gp, gm=gm))
    s = net.forward(x, _W["nl"])
    return int(np.argmax(s) == y)


def evaluate(net, X, y, nl):
    ok = 0
    for k in range(len(X)):
        ok += int(np.argmax(net.forward(X[k], nl)) == y[k])
    return ok / len(X)


# =================================================================== main =====
def to_pm1(X, mn=None, mx=None):
    if mn is None:
        mn, mx = X.min(0), X.max(0)
    span = np.where(mx - mn > 1e-12, mx - mn, 1.0)
    return 2 * np.clip((X - mn) / span, 0, 1) - 1, mn, mx


def main(a):
    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, n_train=a.n_train,
                                        n_test=a.n_test)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr, mn, mx = to_pm1(Xtr)
    Xte, _, _ = to_pm1(Xte, mn, mx)

    dev_kw = dict(g_on=a.g_on, g_off=a.g_off, n_states=a.n_states,
                  a_pot=a.a_pot, a_dep=a.a_dep, nonlinear=not a.linear_device,
                  write_sigma=a.write_sigma, verify=(a.rule == "writeverify"),
                  verify_tol=a.verify_tol, seed=a.seed)
    dev = ResistiveDevice(**dev_kw)
    sizes = [Xtr.shape[1], a.hidden, C]
    net = CrossbarNet(sizes, dev, rf=a.rf, adc_bits=a.adc_bits, seed=a.seed,
                      act=a.act, slope=a.slope)

    nl = scratch(f"xb_{a.tag}", BASE)
    fs = net.calibrate(Xtr, nl, n=a.calib)
    print(f"1T1R crossbar | {a.dataset} | sizes={sizes} | "
          f"{sum(XB.n_devices(sizes[l], sizes[l+1]) for l in range(len(sizes)-1))} devices")
    print(f"  device: {dev.describe()}")
    print(f"  ADC {a.adc_bits} bit, full scale per layer "
          f"{['%.4f' % v for v in fs]} V")

    stem = os.path.join(RESULTS, f"xbar_{a.dataset}_{a.tag}")
    ckpt_path = f"{stem}_ckpt.json"
    ckpt = None
    if a.resume and os.path.exists(ckpt_path):
        with open(ckpt_path) as f:
            ckpt = json.load(f)
        net.gp = [np.array(g) for g in ckpt["gp"]]
        net.gm = [np.array(g) for g in ckpt["gm"]]
        net.fs = fs = list(ckpt["fs"])
        dev.rng.bit_generator.state = ckpt["rng"]
        print(f"  resumed from {ckpt_path} after epoch {ckpt['epoch']}")
    log = TrainLog(stem, net.weight_names(), resume=ckpt is not None,
                   meta=dict(arm="xbar1t1r", dataset=a.dataset, sizes=sizes,
                             device=dev.describe(), rf=net.rf, adc_bits=a.adc_bits,
                             fs=fs, act=a.act, slope=a.slope,
                             n_train=len(ytr), n_test=len(yte), C=C,
                             seed=a.seed, lr_pulses=a.lr_pulses,
                             thresh=a.thresh, lr_decay=a.lr_decay,
                             update_rule=a.rule))

    state = dict(sizes=sizes, devkw=dev_kw, rf=net.rf, adc_bits=a.adc_bits,
                 fs=fs, bias=net.bias, act=net.act, slope=net.slope)
    pool = None
    if a.workers > 1:
        import multiprocessing as mp
        pool = mp.Pool(a.workers, initializer=_init_worker,
                       initargs=(state, f"xw_{a.tag}"))

    acc = [np.zeros_like(net.gp[l]) for l in range(len(sizes) - 1)]
    start = 1
    if ckpt is not None:
        acc = [np.array(g) for g in ckpt["acc"]]
        start = ckpt["epoch"] + 1
    t0 = time.perf_counter()
    for ep in range(start, a.epochs + 1):
        # PULSE DECAY. A fixed-amplitude rule has no way to take smaller steps as it
        # approaches a solution -- gradient magnitude is discarded, so the step never
        # shrinks. Without decay every run here reached a good accuracy and then walked
        # away from it: twomoon peaked at 0.867 and ended at exactly 0.500, i.e. a
        # constant output, on every device setting including a perfectly linear,
        # symmetric, noiseless one. Annealing the pulse count is what lets the array
        # settle, and it is a controller-side schedule, not a device property.
        lr_ep = a.lr_pulses * (a.lr_decay ** (ep - 1))
        order = np.random.default_rng(a.seed + ep).permutation(len(ytr))
        tot, nb = 0.0, 0
        for s0 in range(0, len(order), a.batch):
            bi = order[s0:s0 + a.batch]
            gpl = [g.tolist() for g in net.gp]
            gml = [g.tolist() for g in net.gm]
            args = [(gpl, gml, Xtr[k], int(ytr[k]), a.gain) for k in bi]
            outs = (pool.map(_grad_work, args) if pool else
                    [sample_grad(net, Xtr[k], int(ytr[k]), nl, a.gain)
                     for k in bi])
            agg = [np.mean([o[1][l] for o in outs], axis=0)
                   for l in range(len(sizes) - 1)]
            if a.rule == "manhattan":
                apply_manhattan(net, agg, lr_ep, a.thresh)
            else:
                acc = apply_writeverify(net, agg, lr_ep, acc)
            tot += float(np.mean([o[0] for o in outs])); nb += 1

        if a.recalib and ep % a.recalib == 0:
            net.calibrate(Xtr, nl)
            state["fs"] = net.fs
            if pool:
                pool.close(); pool.join()
                import multiprocessing as mp
                pool = mp.Pool(a.workers, initializer=_init_worker,
                               initargs=(state, f"xw_{a.tag}"))

        gpl = [g.tolist() for g in net.gp]; gml = [g.tolist() for g in net.gm]
        if pool:
            tr = float(np.mean(pool.map(_eval_work,
                [(gpl, gml, Xtr[k], int(ytr[k])) for k in range(len(ytr))])))
            te = float(np.mean(pool.map(_eval_work,
                [(gpl, gml, Xte[k], int(yte[k])) for k in range(len(yte))])))
        else:
            tr = evaluate(net, Xtr, ytr, nl)
            te = evaluate(net, Xte, yte, nl)

        log.log(ep, tot / max(nb, 1), tr, te, net.flat_conductances())
        # CHECKPOINT every epoch: a circuit run takes hours, and one was already lost
        # to a machine restart at epoch ~40 of 90. --resume picks up from here.
        with open(ckpt_path + ".tmp", "w") as f:
            json.dump(dict(epoch=ep, gp=[g.tolist() for g in net.gp],
                           gm=[g.tolist() for g in net.gm],
                           acc=[g.tolist() for g in acc], fs=list(net.fs),
                           rng=dev.rng.bit_generator.state), f)
        os.replace(ckpt_path + ".tmp", ckpt_path)
        mins = (time.perf_counter() - t0) / 60
        lo, hi = metrics.wilson(te, len(yte))
        print(f"  ep {ep:3d}  loss {tot/max(nb,1):.4f}  train {tr:.3f}  "
              f"test {te:.3f} [{lo:.2f},{hi:.2f}]  [{mins:.1f} min]")

    if pool:
        pool.close(); pool.join()
    conv = metrics.epochs_to_converge([r["test"] for r in log.rows])
    out = log.finish(convergence=conv,
                     final_gp=[g.tolist() for g in net.gp],
                     final_gm=[g.tolist() for g in net.gm])
    print(f"  best test {conv['best']:.3f} at epoch {conv['epoch']}")
    print(f"saved -> {out}")
    os.path.exists(nl) and os.remove(nl)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle",
                    choices=["twomoon", "circle", "2spirals"])
    ap.add_argument("--hidden", type=int, default=16)
    ap.add_argument("--n-train", type=int, default=120)
    ap.add_argument("--n-test", type=int, default=120)
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--lr-pulses", type=float, default=0.01,
                    help="step scale. For writeverify this is a learning "
                         "rate; for manhattan it is pulses per update")
    ap.add_argument("--lr-decay", type=float, default=0.99,
                    help="per-epoch pulse-amplitude decay; 1.0 disables")
    ap.add_argument("--recalib", type=int, default=5,
                    help="re-measure converter ranges every N epochs")
    ap.add_argument("--rule", default="writeverify",
                    choices=["writeverify", "manhattan"],
                    help="writeverify = closed-loop proportional updates with digital "
                         "accumulation (the default, and what works); manhattan = "
                         "open-loop fixed-amplitude sign pulses (the cheap hardware "
                         "ablation)")
    ap.add_argument("--verify-tol", type=float, default=0.002,
                    help="residual programming error after write-verify, as a "
                         "fraction of the conductance window")
    ap.add_argument("--thresh", type=float, default=0.2,
                    help="update threshold: skip cells whose |gradient| is below this "
                         "fraction of the layer's largest this step")
    ap.add_argument("--act", default="tanh", choices=["tanh","relu","lrelu"])
    ap.add_argument("--slope", type=float, default=12.0,
                    help="digital tanh slope: a = tanh(slope * d)")
    ap.add_argument("--gain", type=float, default=4.0)
    ap.add_argument("--rf", type=float, default=2e3)
    ap.add_argument("--adc-bits", type=int, default=8)
    ap.add_argument("--calib", type=int, default=16)
    ap.add_argument("--g-on", type=float, default=1e-4)
    ap.add_argument("--g-off", type=float, default=1e-6)
    ap.add_argument("--n-states", type=int, default=64)
    ap.add_argument("--a-pot", type=float, default=0.06)
    ap.add_argument("--a-dep", type=float, default=0.05)
    ap.add_argument("--write-sigma", type=float, default=0.02)
    ap.add_argument("--linear-device", action="store_true",
                    help="disable update nonlinearity (ablation only)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--resume", action="store_true",
                    help="continue from results/xbar_<dataset>_<tag>_ckpt.json")
    sys.exit(main(ap.parse_args()))
