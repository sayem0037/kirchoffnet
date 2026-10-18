"""
digital_mlp.py -- the digital prior-art arm: a quantized INT-N MLP.

TWO HALVES, AND THE SEAM BETWEEN THEM IS STATED, NOT HIDDEN
-----------------------------------------------------------
  accuracy / convergence   a bit-accurate INT-N MLP trained in numpy with a
                           straight-through estimator. Real quantization: the
                           forward pass uses the rounded weights and rounded
                           activations the hardware would.
  energy / latency / area  a gate-count model whose per-gate constants were
                           MEASURED in this simulator (digital_cell.py), not
                           quoted from a paper.

The seam is that the datapath is counted rather than simulated. An INT8 MAC is
a few thousand devices over thousands of cycles and a pure-Python MNA solver
cannot carry a whole MLP inference at that size. What it CAN carry is one gate,
exactly, and that is what was measured. So the digital numbers are as
technology-consistent as the analog ones -- same solver, same 0.35 um cards,
same 3.3 V -- and the modelling assumption is confined to the gate counts,
which are written down below and can be argued with directly.

THE DATAPATH, STATED
--------------------
An N x N array multiplier and a ripple-carry accumulation tree:

    partial products      N^2  AND2
    multiplier array      N(N-1)  full adders
    accumulate P products (P-1) adders of width 2N + ceil(log2 P)
    activation            an N-bit LUT read out of SRAM

Two architectures, because the right comparison depends on what is being held
equal:

    parallel  one multiplier per weight. Latency is one multiply plus an adder
              tree, which is the fair match for an analog array that computes
              every product at once. Area is enormous, and that IS the result.
    serial    one MAC per output neuron, fan_in cycles deep. Area is modest,
              latency is fan_in times worse. This is the area-matched point.

Energy is nearly the same either way -- the same switching events happen -- so
the two architectures trade latency against area at roughly fixed energy, and
the paper reports both rather than picking the flattering one.
"""

import argparse
import json
import math
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import digital_cell as DC        # noqa: E402
import metrics                   # noqa: E402
import tech                      # noqa: E402
import xbar_train as T           # noqa: E402  (shares load_any / to_pm1 / Adam)

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)
CHAR = os.path.join(RESULTS, "digital_cell_char.json")


# ============================================================ quantization ===
def quantize(x, bits, scale=None):
    """Symmetric round-to-nearest into a signed N-bit grid."""
    qmax = 2 ** (bits - 1) - 1
    s = scale if scale is not None else (np.max(np.abs(x)) + 1e-12)
    q = np.clip(np.round(x / s * qmax), -qmax, qmax)
    return q / qmax * s, s


def train_int_mlp(Xtr, ytr, Xte, yte, C, layers, bits=8, epochs=400, lr=0.05,
                  seed=0):
    """Quantization-aware training with a straight-through estimator.

    Forward uses the quantized weights and quantized activations, so the
    reported accuracy is what the integer datapath would actually produce; the
    backward pass uses the unrounded values, which is the standard STE and the
    only thing that makes low-bit training converge at all.
    """
    rng = np.random.default_rng(seed)
    P = {f"W{i}": rng.normal(0, 1.0 / np.sqrt(n_in + 1), (n_in + 1, n_out))
         for i, (n_in, n_out) in enumerate(layers)}
    opt = T.Adam(P, lr)

    n = len(Xtr)
    Y = np.zeros((n, C)); Y[np.arange(n), ytr] = 1.0
    hist = []

    for ep in range(1, epochs + 1):
        a, acts = Xtr, []
        for i in range(len(layers)):
            a1 = np.hstack([np.ones((len(a), 1)), a])
            wq, _ = quantize(P[f"W{i}"], bits)
            z = a1 @ wq
            acts.append((a1, z))
            if i < len(layers) - 1:
                a, _ = quantize(np.tanh(z), bits)
            else:
                a = z

        probs = T.softmax(a)
        d = (probs - Y) / n
        grads = {}
        for i in reversed(range(len(layers))):
            a1, z = acts[i]
            grads[f"W{i}"] = a1.T @ d
            if i > 0:
                d = (d @ P[f"W{i}"].T)[:, 1:] * (1 - np.tanh(acts[i - 1][1]) ** 2)
        P = opt.step(P, grads)

        if ep % max(1, epochs // 40) == 0 or ep == epochs:
            hist.append(dict(epoch=ep,
                             train=infer_acc(P, Xtr, ytr, layers, bits),
                             test=infer_acc(P, Xte, yte, layers, bits)))
    return P, hist


def infer(P, Xd, layers, bits):
    a = Xd
    for i in range(len(layers)):
        a1 = np.hstack([np.ones((len(a), 1)), a])
        wq, _ = quantize(P[f"W{i}"], bits)
        z = a1 @ wq
        a = quantize(np.tanh(z), bits)[0] if i < len(layers) - 1 else z
    return a


def infer_acc(P, Xd, y, layers, bits):
    return float(np.mean(np.argmax(infer(P, Xd, layers, bits), 1) == y))


# ============================================================ cost model =====
def gate_counts(layers, bits, bias=True):
    """Switching-event counts for ONE inference, by cell type.

    Counts cell ACTIVATIONS, not instances: this is the energy quantity. Area
    uses instance counts, which differ between the two architectures.
    """
    b = 1 if bias else 0
    and2 = fa = 0
    for n_in, n_out in layers:
        p = n_in + b                       # products per output neuron
        w_acc = 2 * bits + math.ceil(math.log2(max(p, 2)))
        per_mult_and = bits * bits
        per_mult_fa = bits * (bits - 1)
        and2 += p * n_out * per_mult_and
        fa += p * n_out * per_mult_fa
        fa += (p - 1) * n_out * w_acc      # accumulation tree
    n_act = sum(n_out for _, n_out in layers)
    n_weights = sum((n_in + b) * n_out for n_in, n_out in layers)
    return dict(and2=and2, fa=fa, n_act=n_act, n_weights=n_weights)


def load_char(path=CHAR):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found -- run `python digital_cell.py` first. The "
            "digital arm's constants are MEASURED, so there is deliberately "
            "no fallback to literature values here.")
    return json.load(open(path))


def cost_model(layers, bits, arch="parallel", bias=True, char=None):
    """Energy, latency and area for one inference.

    Energy counts every switching cell once per inference plus the SRAM traffic
    for weights and activation LUTs. Latency is a critical path through one
    multiplier and the accumulation tree. Area is instance count times measured
    cell area, plus weight storage.
    """
    char = char or load_char()
    c = char["cells"]
    e_and, e_fa = c["and2"]["e_cycle_j"], c["fa"]["e_cycle_j"]
    t_and, t_fa = c["and2"]["t_pd_s"], c["fa"]["t_pd_s"]
    a_and, a_fa = c["and2"]["area_um2"], c["fa"]["area_um2"]

    g = gate_counts(layers, bits, bias)
    b = 1 if bias else 0

    # ---- energy: independent of architecture, the same events happen
    e_logic = g["and2"] * e_and + g["fa"] * e_fa
    e_sram = (g["n_weights"] * bits + g["n_act"] * bits) * tech.E_SRAM_READ_BIT
    energy = e_logic + e_sram

    # ---- latency: critical path
    fan = max(n_in + b for n_in, _ in layers)
    w_acc = 2 * bits + math.ceil(math.log2(max(fan, 2)))
    t_mult = t_and + (2 * bits - 2) * t_fa
    t_tree = math.ceil(math.log2(max(fan, 2))) * w_acc * t_fa
    t_layer = t_mult + t_tree
    if arch == "parallel":
        latency = len(layers) * t_layer
    else:
        latency = sum((n_in + b) * (t_mult + w_acc * t_fa)
                      for n_in, _ in layers)

    # ---- area: instance counts
    if arch == "parallel":
        n_mult = sum((n_in + b) * n_out for n_in, n_out in layers)
    else:
        n_mult = sum(n_out for _, n_out in layers)
    a_mult = bits * bits * a_and + bits * (bits - 1) * a_fa
    a_acc = n_mult * w_acc * a_fa
    a_mem = g["n_weights"] * bits * tech.A_SRAM_BITCELL * 1e12
    area = dict(logic=n_mult * a_mult, accum=a_acc, sram=a_mem)
    area["total"] = sum(area.values())

    return dict(arch=arch, bits=bits, energy_j=energy, e_logic_j=e_logic,
                e_sram_j=e_sram, latency_s=latency, area=area, gates=g,
                n_multipliers=n_mult)


# ================================================================== main =====
def main(a):
    kw = dict(n_train=a.n_train, n_test=a.n_test)
    if a.dataset == "mnist":
        kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, _ = T.load_any(a.dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr_w, mn, mx = T.to_pm1(Xtr)
    Xte_w, _, _ = T.to_pm1(Xte, mn, mx)

    layers = [(Xtr.shape[1], a.hidden), (a.hidden, C)]
    char = load_char()
    print(f"digital MLP | {a.dataset} | layers={layers} | "
          f"cells measured at {char['node_nm']} nm, {char['vdd']} V")

    out = {}
    for bits in a.bits:
        P, hist = train_int_mlp(Xtr_w, ytr, Xte_w, yte, C, layers, bits=bits,
                                epochs=a.epochs, lr=a.lr, seed=a.seed)
        tr = infer_acc(P, Xtr_w, ytr, layers, bits)
        te = infer_acc(P, Xte_w, yte, layers, bits)
        conv = metrics.epochs_to_converge([h["test"] for h in hist])
        rows = {}
        for arch in a.arch:
            cm = cost_model(layers, bits, arch, char=char)
            rows[arch] = cm
            print(f"  INT{bits:<2} {arch:<8} train {tr:.3f} test {te:.3f}  "
                  f"E={cm['energy_j'] * 1e12:9.2f} pJ  "
                  f"t={cm['latency_s'] * 1e9:8.2f} ns  "
                  f"A={cm['area']['total'] * 1e-6:8.4f} mm^2")
        out[f"int{bits}"] = dict(bits=bits, train=tr, test=te,
                                 convergence=conv, history=hist, cost=rows)

    p = os.path.join(RESULTS, f"dmlp_{a.dataset}_{a.tag}.json")
    json.dump(dict(arm="dmlp", dataset=a.dataset, layers=layers, seed=a.seed,
                   n_train=len(ytr), n_test=len(yte), C=C, results=out),
              open(p, "w"), indent=2)
    print(f"saved -> {p}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--hidden", type=int, default=7)
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--bits", type=int, nargs="+", default=[4, 8])
    ap.add_argument("--arch", nargs="+", default=["parallel", "serial"])
    ap.add_argument("--epochs", type=int, default=400)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    sys.exit(main(ap.parse_args()))
