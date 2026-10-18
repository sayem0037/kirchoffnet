"""
train_kfq.py -- adjoint training of the Kirchhoff Four-Quadrant Network.

WHAT IS AND IS NOT SOFTWARE
---------------------------
Software loads the data, writes the netlist, and takes an argmax. That is the
whole of it. Class scores are node voltage DIFFERENCES read off the last column
pair -- no trained read-out, no feature vector, no logistic regression on top.
Every trainable quantity is a voltage source inside the circuit:

    VA{l}_{i}_{j}, VB{l}_{i}_{j}   the two gates of one signed weight,
                                   dtheta = theta_a - theta_b
    VT{l}                          the layer's differential-pair tail bias,
                                   i.e. its gain

and every gradient comes from the simulator's transient adjoint rather than a
software surrogate of the circuit -- verified at cosine 1.000000 against central
finite differences. One adjoint solve returns dV(node)/dparam for EVERY
parameter, so a training step costs (samples) solves, not (samples x params).

THE GRADIENT
    score_j = V(cp_j) - V(cn_j)
    L       = cross_entropy(softmax(gain * score), y)
    dL/dp   = gain * sum_j (dL/dscore_j) * (dV(cp_j)/dp - dV(cn_j)/dp)

`gain` is a fixed scalar temperature that rescales volts into logits. It cancels
in argmax, so it cannot contribute any classification power of its own.

THE BOX, AND WHY IT IS NOT COSMETIC
-----------------------------------
    conduction   theta - v_row > VTO        else dI/dtheta is EXACTLY zero and
                                            the weight is permanently dead
    saturation   V(col) > theta - VTO       else current depends on the column
                                            voltage and the summing degenerates

Gate 4b failed on the first of these: the neuron drains sat at 1.93 V while
theta was 1.70, so every synapse in layer 2 was cut off and the signal read
0.0000 V. The row common mode is therefore SOLVED for (gate_fq.py) and theta is
clipped to a box around it, so conduction holds by construction.
"""
import argparse
import json
import os
import time

import numpy as np

from model import Adam, ce_grad, cross_entropy, softmax
from netlist_kfq import (VTO_N, all_thetas, read_nodes, read_pairs, tail_name,
                         theta_a, theta_b, n_devices, write_kfq_netlist)
from simulator_api import eval_chain, run_chain

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def scratch(tag):
    """Per-process scratch netlist. Sharing one between concurrent runs
    silently corrupted two result sets earlier in this project, so the pid is
    part of the name and every worker gets its own file."""
    return os.path.join(BASE, f"tmp_kfq_{tag}_{os.getpid()}.sp")


def init_params(layers, thbar, dth, vtail, seed=0):
    """`thbar` may be one value or ONE PER LAYER.

    Per-layer is the correct form: theta_l has to clear the highest row voltage
    of ITS layer (CM_l + swing_l/2 + VTO + margin), and layer 0's rows are data
    sources the designer places while layer 1's rows are the previous neuron's
    drains. Sharing one value left layer 1 with 0.15 V of conduction margin and
    cut off about half its devices, which broke the four-quadrant cancellation
    and returned a 48:1 constant-to-signal ratio at the output.
    """
    rng = np.random.default_rng(seed)
    tb = (list(thbar) if isinstance(thbar, (list, tuple))
          else [float(thbar)] * len(layers))
    if len(tb) != len(layers):
        raise ValueError(f"thbar has {len(tb)} entries for {len(layers)} layers")
    th = {}
    for l, (n_in, n_out) in enumerate(layers):
        thbar = tb[l]
        # 1/sqrt(fan_in) keeps the per-layer Jacobian near unit gain, which is
        # what decides whether depth propagates signal or collapses it.
        s = dth / np.sqrt(n_in)
        for j in range(1, n_out + 1):
            # i = 0 is the bias row (fixed differential reference). Without it
            # the four-quadrant score has no constant term and the network is
            # an odd function -- `circle` sat at exactly chance for 20 epochs.
            for i in range(0, n_in + 1):
                d = float(rng.uniform(-s, s))
                th[theta_a(l, i, j)] = thbar + d / 2
                th[theta_b(l, i, j)] = thbar - d / 2
        th[tail_name(l)] = float(vtail)
    return th


def clip_params(th, box, tail_box, tail_fixed=None):
    """Clip weights to their conduction/saturation box, and hold the tail
    biases if they are frozen.

    THE TAIL BIAS IS NOT A FREE PARAMETER. It sets the differential pair's
    current, and that current sets BOTH the stage gain AND -- through
    rd * I_d -- the common mode of the drains, which are the next layer's rows.
    Training it therefore moves the inter-layer operating point.

    Measured: on MNIST the optimiser drove VT0 from 0.78 to its floor 0.65 in a
    single epoch. That drops I_tail to 6.8 uA, so rd*I_d = 0.51 V and the
    neuron common mode RISES to 2.79 V, while layer 1's synapses need
    v < theta - VTO = 1.41 V to conduct. The whole second layer cut itself off
    mid-training and the run sat at chance (train 0.100, loss 2.5567 against
    ln 10 = 2.3026).

    Gain and level shift are coupled through the same resistor, so until they
    are decoupled in silicon the tails are held at the value gate_fq.py solved
    for.
    """
    lo, hi = box
    tlo, thi = tail_box
    for k in th:
        if k.startswith("VT"):
            th[k] = (float(tail_fixed) if tail_fixed is not None
                     else float(np.clip(th[k], tlo, thi)))
        else:
            th[k] = float(np.clip(th[k], lo, hi))
    return th


def forward(th, x, layers, cfg, nl, params=None):
    write_kfq_netlist(th, x, layers, nl, load_r=cfg["load_r"], rd=cfg["rd"],
                      vtail=cfg["vtail"], vcm=cfg["vcm"], swing=cfg["swing"])
    pairs = read_pairs(layers)
    if params is None:
        v = eval_chain(nl, read_nodes(layers))
        return np.array([v[p] - v[m] for p, m in pairs]), None
    v, sens = run_chain(nl, read_nodes(layers), params)
    sc = np.array([v[p] - v[m] for p, m in pairs])
    J = np.array([[sens[p][q] - sens[m][q] for q in params] for p, m in pairs])
    return sc, J


def sample_grad(th, x, y, layers, cfg, nl, params):
    sc, J = forward(th, x, layers, cfg, nl, params)
    logits = cfg["gain"] * sc
    p = softmax(logits[None, :])[0]
    loss = float(cross_entropy(p[None, :], np.array([y])))
    return loss, cfg["gain"] * (ce_grad(logits, y) @ J), int(np.argmax(sc))


_W = {}


def _init_worker(layers, cfg, params, tag):
    _W["layers"], _W["cfg"], _W["params"] = layers, cfg, params
    _W["nl"] = scratch(tag)


def _work(arg):
    th, x, y = arg
    return sample_grad(th, x, int(y), _W["layers"], _W["cfg"], _W["nl"],
                       _W["params"])


def _eval_work(arg):
    th, x, y = arg
    sc, _ = forward(th, x, _W["layers"], _W["cfg"], _W["nl"])
    return int(np.argmax(sc) == y)


def evaluate(th, X, y, layers, cfg, nl):
    ok = 0
    for k in range(len(X)):
        sc, _ = forward(th, X[k], layers, cfg, nl)
        ok += int(np.argmax(sc) == y[k])
    return ok / len(X)


def to_pm1(X, mn=None, mx=None):
    """Map features to [-1, 1], the four-quadrant cell's signal range. A fixed
    affine rescale, identical for train and test -- not a learned layer."""
    if mn is None:
        mn, mx = X.min(0), X.max(0)
    span = np.where(mx - mn > 1e-12, mx - mn, 1.0)
    return 2 * np.clip((X - mn) / span, 0, 1) - 1, mn, mx


def check_grad(a):
    layers = [(4, 5), (5, 3)]
    cfg = a.cfg
    params = all_thetas(layers)
    th = init_params(layers, a.thbar[0] if isinstance(a.thbar, list) else a.thbar, a.dth, a.vtail, seed=0)
    x = np.random.default_rng(1).uniform(-1, 1, 4)
    y, nl = 1, scratch("chk")
    loss0, g_adj, _ = sample_grad(th, x, y, layers, cfg, nl, params)
    print("GATE 5 -- adjoint vs central finite differences (four-quadrant)")
    print(f"layers={layers}  params={len(params)}  loss={loss0:.6f}\n")
    print(f"{'param':>14} {'adjoint':>13} {'finite diff':>13} {'rel err':>10}")
    print("-" * 54)
    ga, gf = [], []
    for i in list(range(0, len(params), max(1, len(params) // a.n_fd)))[:a.n_fd]:
        q, base = params[i], th[params[i]]
        ls = []
        for sgn in (+1, -1):
            th[q] = base + sgn * a.eps
            sc, _ = forward(th, x, layers, cfg, nl)
            ls.append(float(cross_entropy(
                softmax((cfg["gain"] * sc)[None, :]), np.array([y]))))
        th[q] = base
        fd = (ls[0] - ls[1]) / (2 * a.eps)
        ga.append(g_adj[i]); gf.append(fd)
        den = max(abs(fd), abs(g_adj[i]), 1e-12)
        print(f"{q:>14} {g_adj[i]:>13.6e} {fd:>13.6e} "
              f"{abs(fd - g_adj[i]) / den:>10.2e}")
    ga, gf = np.array(ga), np.array(gf)
    cos = float(ga @ gf / (np.linalg.norm(ga) * np.linalg.norm(gf) + 1e-300))
    print(f"\ncosine(adjoint, finite-diff) = {cos:.6f}")
    print("\nGATE 5 " + ("PASSED -- training optimises the HARDWARE."
                         if cos > 0.99 else "FAILED -- do not train."))
    if os.path.exists(nl):
        os.remove(nl)


def train(a):
    from datasets_any import load_any
    kw = dict(n_train=a.n_train, n_test=a.n_test)
    if a.dataset == "mnist":
        kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr, mn, mx = to_pm1(Xtr)
    Xte, _, _ = to_pm1(Xte, mn, mx)
    d_in = Xtr.shape[1]

    layers = [(d_in, a.hidden), (a.hidden, C)]
    cfg = a.cfg
    params = all_thetas(layers)
    tb = a.thbar if len(a.thbar) > 1 else a.thbar[0]
    th = init_params(layers, tb, a.dth, a.vtail, seed=a.seed)
    nl = scratch(a.dataset)

    # The softmax temperature must match the circuit's actual score scale, and
    # that scale varies by more than an order of magnitude with fan-in and
    # load_r (iris ~0.2 V, a 64-input layer ~0.006 V). Guessing it per dataset
    # is how `circle` first ran at a temperature that made every logit
    # indistinguishable. So measure it once, at init, on a few samples.
    # It is a FIXED scalar, never trained, and cancels in argmax -- it cannot
    # contribute classification power of its own.
    if a.gain <= 0:
        probe = [forward(th, Xtr[k], layers, cfg, nl)[0]
                 for k in range(min(12, len(Xtr)))]
        sd = float(np.std(np.asarray(probe)))
        cfg["gain"] = float(a.logit_target / max(sd, 1e-9))
        print(f"auto gain: score std {sd:.5f} V -> gain {cfg['gain']:.1f} "
              f"(target logit spread {a.logit_target})")

    print(f"KFQ {a.dataset}: {d_in} -> {a.hidden} -> {C}  "
          f"({n_devices(layers)} devices, {len(params)} trainable sources)")
    print(f"vcm={cfg['vcm']:.3f} V  thbar={tb} V  swing={cfg['swing']} "
          f"load_R={cfg['load_r']} rd={cfg['rd']} vtail={cfg['vtail']}")
    print(f"{len(ytr)} train / {len(yte)} test, {a.epochs} epochs, "
          f"batch {a.batch}, lr {a.lr}")

    opt = Adam({k: np.array(v) for k, v in th.items()}, lr=a.lr)
    P = {k: np.array(float(v)) for k, v in th.items()}
    log, snaps, t0 = [], [], time.perf_counter()
    rng = np.random.default_rng(a.seed)

    pool = None
    if a.workers > 1:
        import multiprocessing as mp
        pool = mp.Pool(a.workers, initializer=_init_worker,
                       initargs=(layers, cfg, params, a.dataset))
        print(f"{a.workers} workers, each with its own scratch netlist")
    print(flush=True)

    best_te = 0.0
    try:
        for ep in range(1, a.epochs + 1):
            order = rng.permutation(len(ytr))
            ep_loss, ep_ok, n = 0.0, 0, 0
            for b0 in range(0, len(order), a.batch):
                bat = order[b0:b0 + a.batch]
                th_now = {q: float(P[q]) for q in P}
                jobs = [(th_now, Xtr[k], int(ytr[k])) for k in bat]
                res = (pool.map(_work, jobs) if pool
                       else [sample_grad(th_now, Xtr[k], int(ytr[k]), layers,
                                         cfg, nl, params) for k in bat])
                G = {k: 0.0 for k in P}
                for (loss, g, pred), k in zip(res, bat):
                    ep_loss += loss; ep_ok += int(pred == ytr[k]); n += 1
                    for qi, q in enumerate(params):
                        G[q] += g[qi] / len(bat)
                P = opt.step(P, {k: np.array(G[k]) for k in P})
                P = {k: np.array(v) for k, v in clip_params(
                    {q: float(P[q]) for q in P}, (a.th_lo, a.th_hi),
                    (a.tail_lo, a.tail_hi),
                    None if a.train_tails else a.vtail).items()}

            th_now = {q: float(P[q]) for q in P}
            if ep % a.eval_every == 0 or ep == a.epochs:
                te = (float(np.mean(pool.map(_eval_work,
                      [(th_now, Xte[k], int(yte[k]))
                       for k in range(len(yte))]))) if pool
                      else evaluate(th_now, Xte, yte, layers, cfg, nl))
                best_te = max(best_te, te)
            else:
                te = float("nan")
            el = (time.perf_counter() - t0) / 60
            log.append(dict(epoch=ep, loss=ep_loss / n, train=ep_ok / n,
                            test=te, minutes=el))
            print(f"  epoch {ep:>3}  loss {ep_loss/n:.4f}  "
                  f"train {ep_ok/n:.3f}  "
                  f"test {'  -  ' if not np.isfinite(te) else f'{te:.3f}'}"
                  f"   [{el:.1f} min]", flush=True)
            if a.snapshots:
                # Keep every epoch's weights so the decision boundary can be
                # animated afterwards. Without this only the final theta
                # survives and the training evolution is unrecoverable
                # without a full retrain.
                snaps.append({k: float(v) for k, v in P.items()})
            json.dump(dict(dataset=a.dataset, layers=layers, C=C, cfg=cfg,
                           thbar=a.thbar, n_train=len(ytr), n_test=len(yte),
                           log=log, snapshots=snaps,
                           theta={k: float(v) for k, v in P.items()}),
                      open(os.path.join(
                          RESULTS, f"kfq_{a.dataset}_{a.tag}.json"), "w"),
                      indent=2)
    finally:
        if pool:
            pool.close(); pool.join()

    print(f"\nbest test {best_te:.3f}")
    print(f"saved -> results/kfq_{a.dataset}_{a.tag}.json")


def main(a):
    lr_ = a.load_r if len(a.load_r) > 1 else a.load_r[0]
    a.cfg = dict(load_r=lr_, rd=a.rd, vtail=a.vtail, vcm=a.vcm,
                 swing=a.swing, gain=a.gain)
    check_grad(a) if a.check_grad else train(a)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--hidden", type=int, default=7)
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--lr", type=float, default=0.02)
    ap.add_argument("--gain", type=float, default=4.0,
                    help="softmax temperature; <=0 measures it from the "
                         "circuit at init")
    ap.add_argument("--logit-target", dest="logit_target", type=float,
                    default=2.0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--eval-every", dest="eval_every", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    # operating point -- from gate_fq.py, which SOLVES for vcm/thbar
    ap.add_argument("--thbar", type=float, nargs="+", default=[1.93],
                    help="weight common mode; one value or one PER LAYER "
                         "(theta must clear ITS layer's highest row)")
    ap.add_argument("--dth", type=float, default=0.60)
    ap.add_argument("--vcm", type=float, default=1.00)
    ap.add_argument("--swing", type=float, default=0.40)
    ap.add_argument("--vtail", type=float, default=0.85)
    ap.add_argument("--load-r", dest="load_r", nargs="+", default=["6k"],
                    help="column load; one value or one PER LAYER (the DC "
                         "drop scales with fan-in, so a 64-input layer and a "
                         "16-input layer need different values)")
    ap.add_argument("--rd", default="200k")
    ap.add_argument("--th-lo", dest="th_lo", type=float, default=1.40)
    ap.add_argument("--th-hi", dest="th_hi", type=float, default=2.60)
    ap.add_argument("--tail-lo", dest="tail_lo", type=float, default=0.65)
    ap.add_argument("--tail-hi", dest="tail_hi", type=float, default=1.20)
    ap.add_argument("--snapshots", action="store_true",
                    help="store theta after every epoch so the decision "
                         "boundary can be animated later")
    ap.add_argument("--train-tails", dest="train_tails", action="store_true",
                    help="let the optimiser move the diff-pair tail biases. "
                         "OFF by default: the tail sets the inter-layer common "
                         "mode, and training it cut off a whole layer on MNIST")
    ap.add_argument("--check-grad", action="store_true")
    ap.add_argument("--n-fd", type=int, default=10)
    ap.add_argument("--eps", type=float, default=2e-3)
    main(ap.parse_args())
