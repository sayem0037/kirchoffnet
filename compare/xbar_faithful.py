"""
xbar_faithful.py -- the crossbar as the literature actually builds it:
analog matrix-vector multiply, DIGITAL activation between layers.

WHY THIS FILE EXISTS
--------------------
The crossbar arm in xbar_train.py keeps the signal analog from input to output,
reusing KFQ's tail-biased differential pair as its neuron. That was a
deliberate choice -- sharing a nonlinearity makes the comparison controlled, so
any difference traces to the synapse rather than to the activation.

It is also not what a resistive-crossbar accelerator does. ISAAC and PUMA go

    analog MVM -> ADC -> digital shift-and-add -> digital ReLU -> DAC -> next tile

The activation is exact digital arithmetic. There is no analog neuron in the
signal path at all.

That deviation cost the baseline real accuracy, and the isolation test said so
before this file existed: the MVM alone tracks the mapped function at r =
0.9992, and adding the analog neuron drops it to r = 0.863. Measured
end-to-end on iris:

    crossbar, analog neuron (xbar_train.py)      0.900     mapping loss 0.083
    crossbar, digital activation (this file)     0.983     mapping loss 0.000
    software reference                           0.983

So the analog-neuron version was losing 8.3 accuracy points to a component a
real crossbar would not have. Reporting only that number would be beating a
strawman on the accuracy axis.

IT ALSO FIXES AN INTERNAL INCONSISTENCY
---------------------------------------
The energy and area model already charged this arm for an ADC per column and a
DAC per row at every layer boundary -- which is the cost of exactly the digital
round trip this file performs. The analog-neuron version was being charged for
converters it never used. This configuration is the self-consistent one: it
pays for the converters AND gets the exact activation they buy.

WHAT THE PAPER SHOULD REPORT
----------------------------
This one, as the primary crossbar row. It makes the comparison honest and the
argument sharper: the crossbar MATCHES on accuracy, and KFQ's advantage is
entirely in energy, area and the data conversion it avoids -- which is a much
more defensible claim than also winning on accuracy.
"""

import argparse
import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import metrics                                   # noqa: E402
import xbar_netlist as X                         # noqa: E402
import xbar_train as T                           # noqa: E402
from simulator_api import eval_chain, scratch    # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def layer_cfg(cfg, l):
    """Per-layer view of a solved sizing spec."""
    def pick(key):
        v = cfg[key]
        return [v[l]] if isinstance(v, (list, tuple)) else [v]
    return dict(cfg, rf=pick("rf"), rd=pick("rd"), vref=pick("vref"))


def run_layer(w, lcfg, xs, n_in, n_out, nl, levels=None):
    """One crossbar layer on the circuit; returns its column differences.

    Reading the columns IS the ADC in this model -- the analog result leaves
    the array here and everything downstream is digital.
    """
    ll = [(n_in, n_out)]
    u = T.map_to_u([w], ll, lcfg)
    res = T.u_to_res(u, lcfg, levels)
    X.write_xbar_netlist(res, xs, ll, nl, rf=lcfg["rf"], rd=lcfg["rd"],
                         vtail=lcfg["vtail"], vref=lcfg["vref"],
                         vcm=lcfg["vcm"], swing=lcfg["swing"],
                         ideal_tia=lcfg["ideal_tia"], vota=lcfg["vota"])
    v = eval_chain(nl, X.read_nodes(ll))
    return np.array([v[p] - v[m] for p, m in X.read_pairs(ll)])


def infer(W, cfg, layers, xs, nl, levels=None, adc_bits=8):
    """Full forward pass: analog MVM per layer, digital activation between.

    The inter-layer signal is quantized to `adc_bits` because it physically
    passes through an ADC and a DAC. Skipping that would model an ideal
    converter and flatter the arm.
    """
    a = np.asarray(xs, dtype=float)
    for l, (n_in, n_out) in enumerate(layers):
        s = run_layer(W[l], layer_cfg(cfg, l), a, n_in, n_out, nl, levels)
        if l == len(layers) - 1:
            return s
        # digital activation, then re-encode for the next tile's DACs
        h = np.tanh(s / (np.abs(s).max() + 1e-12))
        q = 2 ** (adc_bits - 1) - 1
        a = np.clip(np.round(h * q), -q, q) / q
    return s


def main(a):
    ck = a.checkpoint or os.path.join(RESULTS,
                                      f"xbar_exsitu_{a.dataset}_sized.json")
    if not os.path.exists(ck):
        print(f"no sizing/checkpoint at {ck}; run xbar_spec.py and "
              f"xbar_train.py --mode exsitu first.")
        return 1
    d = json.load(open(ck))
    layers = [tuple(t) for t in d["layers"]]
    cfg = d["cfg"]

    kw = dict(n_train=a.n_train, n_test=a.n_test)
    if a.dataset == "mnist":
        kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, _ = T.load_any(a.dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr_w, mn, mx = T.to_pm1(Xtr)
    Xte_w, _, _ = T.to_pm1(Xte, mn, mx)

    W = T.train_software_mlp(Xtr_w, ytr, C, layers, epochs=a.sw_epochs,
                             lr=a.sw_lr, seed=a.seed, hwa_sigma=a.hwa_sigma)
    nl = scratch(f"faith_{a.tag}")

    tr = float(np.mean([np.argmax(infer(W, cfg, layers, Xtr_w[k], nl,
                                        a.levels, a.adc_bits)) == ytr[k]
                        for k in range(len(ytr))]))
    te = float(np.mean([np.argmax(infer(W, cfg, layers, Xte_w[k], nl,
                                        a.levels, a.adc_bits)) == yte[k]
                        for k in range(len(yte))]))
    sw_tr, sw_te = T._sw_acc(W, Xtr_w, ytr), T._sw_acc(W, Xte_w, yte)
    lo, hi = metrics.wilson(te, len(yte))

    print(f"xbar FAITHFUL (analog MVM + digital activation) | {a.dataset} | "
          f"layers={layers} | ADC {a.adc_bits} bit")
    print(f"  software MLP   train {sw_tr:.3f}  test {sw_te:.3f}")
    print(f"  circuit        train {tr:.3f}  test {te:.3f}  "
          f"[{lo:.3f}, {hi:.3f}]   (mapping loss {sw_te - te:+.3f})")

    out = os.path.join(RESULTS, f"xbar_faithful_{a.dataset}_{a.tag}.json")
    json.dump(dict(arm="xbar_faithful", dataset=a.dataset, layers=layers,
                   cfg=cfg, levels=a.levels, adc_bits=a.adc_bits, seed=a.seed,
                   n_train=len(ytr), n_test=len(yte), C=C,
                   converters=X.converter_counts(layers),
                   log=[dict(epoch=0, train=tr, test=te, sw_train=sw_tr,
                             sw_test=sw_te, loss=float("nan"))]),
              open(out, "w"), indent=2)
    print(f"saved -> {out}")
    if os.path.exists(nl):
        os.remove(nl)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--adc-bits", type=int, default=8)
    ap.add_argument("--levels", type=int, default=None)
    ap.add_argument("--sw-epochs", type=int, default=400)
    ap.add_argument("--sw-lr", type=float, default=0.05)
    ap.add_argument("--hwa-sigma", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    sys.exit(main(ap.parse_args()))
