"""
xbar_train.py -- the crossbar arm, trained two ways.

EX-SITU (the literature-faithful baseline, and the one the paper reports)
------------------------------------------------------------------------
This is what a crossbar accelerator actually does: train a network in software,
then program the conductances. The device is a memory, not a learner. So the
primary arm trains a float MLP in numpy, maps each weight onto a conductance
pair through xbar_netlist.w_to_g, quantizes to N programmable levels, and then
EVALUATES ON THE SIMULATOR. The accuracy reported is the circuit's accuracy,
not the software model's -- the gap between them is the mapping loss, and it is
reported as its own column because it is the crossbar's characteristic failure
mode.

IN-SITU (for the convergence column only)
-----------------------------------------
For the convergence comparison to mean anything, both arms must be trained by
the same algorithm. components/resistor.py exposes an exact adjoint dV/dR, so
the crossbar can be trained by the identical machinery KFQ uses, with one chain
rule and one bookkeeping correction:

    dV/dG   = -R^2 * dV/dR                    (conductance, not resistance)
    dV/dG_a = sum over BOTH netlist instances  (the four-quadrant cell uses
              each conductance twice: G_a appears from v+ into c+ AND from v-
              into c-, so the logical gradient is the sum of the two)

Getting the second one wrong halves every gradient and still trains, slowly and
wrongly. Gate B is what catches it.

THE PARAMETERIZATION, AND WHY IT IS NOT THE CONDUCTANCE ITSELF
--------------------------------------------------------------
Conductances live in [1e-6, 1e-4] S. Running Adam directly on those would need
a learning rate five orders of magnitude away from the one KFQ uses, and the
convergence comparison would be measuring the learning rate rather than the
architecture. So the optimiser works on a normalised u in [0, 1] with

    G = Gmin + u * (Gmax - Gmin)

which puts both arms on the same scale and lets them share --lr and --batch.
The box is the physical device window; clipping to it is not cosmetic, it is
the programming range.
"""

import argparse
import importlib.util
import json
import os
import sys
import time

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")
sys.path.insert(0, BASE)

import xbar_netlist as X                              # noqa: E402
from simulator_api import eval_chain, run_chain, scratch   # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_model = _load("_kfq_model", os.path.join(KFABRIC, "model.py"))
_ds = _load("_kfq_ds", os.path.join(KFABRIC, "datasets_any.py"))
Adam, softmax, cross_entropy, ce_grad = (_model.Adam, _model.softmax,
                                         _model.cross_entropy, _model.ce_grad)
load_any = _ds.load_any


# ------------------------------------------------------- parameterization ---
def g_window(cfg):
    return 1.0 / cfg["r_off"], 1.0 / cfg["r_on"]


def u_to_res(u, cfg, levels=None):
    """Normalised u in [0, 1] -> programmed resistance, with optional
    quantization to N device states."""
    g_min, g_max = g_window(cfg)
    span = g_max - g_min
    res = {}
    for k, v in u.items():
        x = float(np.clip(v, 0.0, 1.0))
        if levels is not None and levels > 1:
            x = round(x * (levels - 1)) / (levels - 1)
        res[k] = 1.0 / max(g_min + x * span, 1e-15)
    return res


def init_u(layers, seed=0, bias=True, scale=0.25):
    """Start every conductance near the middle of the window.

    Not at the bottom: a conductance at Gmin has a small but nonzero gradient
    and a long climb, and starting the whole array there makes the first epochs
    measure the climb rather than the learning. Centred with a small spread is
    the analogue of KFQ's thbar +- dth initialisation.
    """
    rng = np.random.default_rng(seed)
    params = X.all_params(layers, bias)
    return {p: float(np.clip(0.5 + scale * rng.normal(), 0.02, 0.98))
            for p in params}


def clip_u(u):
    for k in u:
        u[k] = float(np.clip(u[k], 0.0, 1.0))
    return u


# ------------------------------------------------------------- forward -----
def forward(u, x, layers, cfg, nl, params=None, levels=None):
    """Class scores, and optionally the Jacobian d(score)/du.

    Returns (scores, J) with J of shape (n_classes, n_params).
    """
    res = u_to_res(u, cfg, levels)
    X.write_xbar_netlist(res, x, layers, nl, rf=cfg["rf"], rd=cfg["rd"],
                         vtail=cfg["vtail"], vref=cfg["vref"],
                         vcm=cfg["vcm"], swing=cfg["swing"],
                         ideal_tia=cfg["ideal_tia"], vota=cfg["vota"])
    pairs = X.read_pairs(layers)

    if params is None:
        v = eval_chain(nl, X.read_nodes(layers))
        return np.array([v[p] - v[m] for p, m in pairs]), None

    inst = X.all_instances(layers, cfg["bias"])
    v, sens = run_chain(nl, X.read_nodes(layers), inst)
    sc = np.array([v[p] - v[m] for p, m in pairs])

    # d(score)/du = d(score)/dR * dR/dG * dG/du
    #             = (sum over the two instances) * (-R^2) * span
    g_min, g_max = g_window(cfg)
    span = g_max - g_min
    J = np.zeros((len(pairs), len(params)))
    for qi, q in enumerate(params):
        r = res[q]
        chain = -(r ** 2) * span
        for nm in X.instances(q):
            for ji, (p, m) in enumerate(pairs):
                J[ji, qi] += (sens[p][nm] - sens[m][nm]) * chain
    return sc, J


def sample_grad(u, x, y, layers, cfg, nl, params, levels=None):
    sc, J = forward(u, x, layers, cfg, nl, params, levels)
    logits = cfg["gain"] * sc
    p = softmax(logits[None, :])[0]
    loss = float(cross_entropy(p[None, :], np.array([y])))
    return loss, cfg["gain"] * (ce_grad(logits, y) @ J), int(np.argmax(sc))


# --------------------------------------------------------- worker plumbing --
_W = {}


def _init_worker(layers, cfg, params, tag, levels):
    _W["layers"], _W["cfg"], _W["params"] = layers, cfg, params
    _W["levels"], _W["nl"] = levels, scratch(tag)


def _work(arg):
    u, x, y = arg
    return sample_grad(u, x, int(y), _W["layers"], _W["cfg"], _W["nl"],
                       _W["params"], _W["levels"])


def _eval_work(arg):
    u, x, y = arg
    sc, _ = forward(u, x, _W["layers"], _W["cfg"], _W["nl"],
                    levels=_W["levels"])
    return int(np.argmax(sc) == y)


def evaluate(u, Xd, y, layers, cfg, nl, levels=None):
    ok = 0
    for k in range(len(Xd)):
        sc, _ = forward(u, Xd[k], layers, cfg, nl, levels=levels)
        ok += int(np.argmax(sc) == y[k])
    return ok / len(Xd)


def to_pm1(Xd, mn=None, mx=None):
    """Identical to kfabric/train_kfq.to_pm1 -- both arms must see the same
    encoded data or the comparison is not controlled."""
    if mn is None:
        mn, mx = Xd.min(0), Xd.max(0)
    span = np.where(mx - mn > 1e-12, mx - mn, 1.0)
    return 2 * np.clip((Xd - mn) / span, 0, 1) - 1, mn, mx



def apply_programming_noise(u, sigma, seed=0):
    """Device programming error, applied ONCE to the programmed array.

    Writing a target conductance into a resistive device does not land exactly
    on target: the achieved value has a spread, conventionally modelled as
    Gaussian with a sigma of a few percent of the conductance window. This is
    the dominant inference-time non-ideality in every published crossbar study,
    alongside drift and read noise.

    Applied ONCE, not per sample. The array is programmed once and then read
    many times, so every test input sees the SAME perturbed weights. Resampling
    per inference would model read noise instead, and would also average away
    across the test set -- making the effect look far smaller than it is.
    """
    if not sigma:
        return dict(u)
    rng = np.random.default_rng(seed)
    return {k: float(np.clip(v + rng.normal(0.0, sigma), 0.0, 1.0))
            for k, v in u.items()}


# ------------------------------------------------------------ ex-situ arm ---
def train_software_mlp(Xtr, ytr, C, layers, epochs=400, lr=0.05, seed=0,
                       hwa_sigma=0.0):
    """A plain float MLP with tanh hidden units, trained in numpy.

    tanh because that is what the differential-pair neuron approximates; a ReLU
    model would map onto hardware that does not exist here and would overstate
    the mapping loss.
    """
    rng = np.random.default_rng(seed)
    W = []
    for n_in, n_out in layers:
        W.append(rng.normal(0, 1.0 / np.sqrt(n_in + 1), (n_in + 1, n_out)))
    P = {f"W{i}": w for i, w in enumerate(W)}
    opt = Adam(P, lr)

    n = len(Xtr)
    Y = np.zeros((n, C))
    Y[np.arange(n), ytr] = 1.0

    rng_n = np.random.default_rng(seed + 1000)
    for _ in range(epochs):
        a = Xtr
        acts = []
        for i in range(len(layers)):
            a1 = np.hstack([np.ones((len(a), 1)), a])
            w = P[f"W{i}"]
            if hwa_sigma:
                # HARDWARE-AWARE TRAINING. Weight noise is injected in the
                # forward pass while the backward pass uses the clean weights;
                # the network then learns a solution that tolerates the spread
                # the devices will actually have. This is the standard
                # mitigation in the analog in-memory literature (e.g. IBM's
                # AIHWKit), it is performed entirely in software, and omitting
                # it means benchmarking a crossbar that nobody would build.
                w = w + rng_n.normal(0.0, hwa_sigma * np.abs(w).max(), w.shape)
            z = a1 @ w
            acts.append((a1, z))
            a = np.tanh(z) if i < len(layers) - 1 else z
        probs = softmax(a)
        d = (probs - Y) / n
        grads = {}
        for i in reversed(range(len(layers))):
            a1, z = acts[i]
            grads[f"W{i}"] = a1.T @ d
            if i > 0:
                d = (d @ P[f"W{i}"].T)[:, 1:] * (1 - np.tanh(acts[i - 1][1]) ** 2)
        P = opt.step(P, grads)

    return [P[f"W{i}"] for i in range(len(layers))]


def layer_sign(l, n_layers, cfg=None):
    """Polarity the mapper must pre-compensate for, per layer.

    MEASURED, not derived -- `xbar_spec.calibrate_signs` drives a one-weight
    probe network and reads which way the output moves. The measured answer for
    this topology is -1 for BOTH a layer read at the neuron and a layer read at
    the columns.

    That is worth spelling out, because the obvious derivation gets it wrong.
    The TIA inverts: V(t+) - V(t-) = -Rf * sum_i (G_a - G_b) * dv_i. The neuron
    looks like it should invert too, and it does not: `om` is the drain of the
    device gated by `tp`, and `op` the drain of the device gated by `tn`, so
    raising tp pulls om DOWN while raising tn pulls op DOWN, and (op - om)
    therefore tracks +(tp - tn). The pair is non-inverting. An inner layer is
    TIA(-) x neuron(+) = -1, and an output layer is TIA(-) alone = -1.

    Two separate wrong answers came out of trusting a derivation here:

        derived sign, broken sizing   iris 0.750   (looked plausible)
        derived sign, fixed sizing    iris 0.000   (perfectly anti-correct)

    The 0.000 is the diagnostic one -- that is what argmax over a negated score
    vector looks like. It only appeared once the biasing was fixed, because the
    earlier configuration's second-layer amplifiers were dead (inputs at 0.27 V,
    below an NMOS pair's turn-on) and a dead amplifier does not invert. Polarity
    depends on the operating point, so it is calibrated after the sizing is
    solved and read from the spec here.

    In silicon this is a wiring choice -- swap the differential output pair.
    Here it is one sign in the mapper, which is the same thing.
    """
    if cfg and "sign_out" in cfg:
        return cfg["sign_out"] if l == n_layers - 1 else cfg["sign_inner"]
    return -1.0


def map_to_u(W, layers, cfg, bias=True):
    """Software weights -> normalised conductance settings.

    Each layer is scaled by its own largest magnitude, so the full device
    window is used in every layer. That is the standard per-tile scaling a real
    mapper does, and skipping it would make deep layers sit in the bottom of
    the window and read as mapping loss that is really a scaling bug.
    """
    u = {}
    for l, (n_in, n_out) in enumerate(layers):
        w = np.asarray(W[l], dtype=float) * layer_sign(l, len(layers), cfg)
        s = float(np.max(np.abs(w))) or 1.0
        for j in range(1, n_out + 1):
            for i in range((0 if bias else 1), n_in + 1):
                wij = w[i if bias else i - 1][j - 1] / s
                # w >= 0 puts the magnitude on G_a, w < 0 on G_b; the other
                # side sits at the bottom of the window (u = 0).
                mag = min(1.0, abs(wij))
                u[X.g_a(l, i, j)] = mag if wij >= 0 else 0.0
                u[X.g_b(l, i, j)] = 0.0 if wij >= 0 else mag
    return u



def score_fidelity(u, W, Xd, layers, cfg, nl, levels=None):
    """How faithfully the circuit reproduces the software model it was
    programmed from: Pearson r between circuit class scores and software
    logits, over a sample of inputs.

    This is the diagnostic that separates the two reasons an ex-situ arm can
    score badly. A LOW r means the circuit is not computing the mapped
    function -- a sizing, biasing or polarity fault, i.e. our bug and an unfair
    baseline. A HIGH r with a lower accuracy means the circuit IS computing the
    mapped function and the loss is genuine quantization and device
    nonlinearity, which is the crossbar's real and reportable cost.

    Without it a 0.767 and a 0.000 look like the same kind of result. They were
    not: both were polarity and biasing faults, and only this number says so
    directly.

    WHAT TO EXPECT. Measured on iris, isolating the two halves of the network:

        4 -> 3,  crossbar only, no neuron   r = 0.9992, circuit 0.983 = sw 0.983
        4 -> 7 -> 3, crossbar+neuron+xbar   r = 0.8628, circuit 0.900 vs 0.983

    The MVM itself is essentially exact. The whole of the mapping loss enters
    with the NEURON: the tail-biased differential pair does not have the same
    transfer shape as the ideal tanh the software model was trained against.
    That is a genuine analog effect rather than a setup fault -- and it is a
    fair one, because KFQ uses the identical neuron and pays the identical
    price. So r near 1.0 is the right expectation for a single linear stage,
    and r in the mid-0.8s is the right expectation once a real neuron is in the
    path; the threshold below is set accordingly.
    """
    sw, ck = [], []
    for x in Xd:
        a = np.asarray(x, dtype=float)[None, :]
        for i in range(len(layers)):
            a1 = np.hstack([np.ones((1, 1)), a])
            z = a1 @ W[i]
            a = np.tanh(z) if i < len(layers) - 1 else z
        sw.append(a[0])
        sc, _ = forward(u, x, layers, cfg, nl, levels=levels)
        ck.append(sc)
    sw = np.asarray(sw).ravel()
    ck = np.asarray(ck).ravel()
    if sw.std() < 1e-12 or ck.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(sw, ck)[0, 1])


# ------------------------------------------------------------- Gate B ------
def check_grad(a):
    """Adjoint dV/dG against central finite differences in u-space."""
    layers = [(4, 5), (5, 3)]
    cfg = a.cfg
    params = X.all_params(layers, cfg["bias"])
    u = init_u(layers, seed=0, bias=cfg["bias"])
    x = np.random.default_rng(1).uniform(-1, 1, 4)
    y, nl = 1, scratch("chkB")

    loss0, g_adj, _ = sample_grad(u, x, y, layers, cfg, nl, params)
    print("GATE B -- adjoint vs central finite differences (crossbar, dV/dG)")
    print(f"layers={layers}  params={len(params)}  loss={loss0:.6f}\n")
    print(f"{'param':>14} {'adjoint':>13} {'finite diff':>13} {'rel err':>10}")
    print("-" * 54)

    ga, gf = [], []
    idx = list(range(0, len(params), max(1, len(params) // a.n_fd)))[:a.n_fd]
    for i in idx:
        q, base = params[i], u[params[i]]
        ls = []
        for sgn in (+1, -1):
            u[q] = base + sgn * a.eps
            sc, _ = forward(u, x, layers, cfg, nl)
            ls.append(float(cross_entropy(
                softmax((cfg["gain"] * sc)[None, :]), np.array([y]))))
        u[q] = base
        fd = (ls[0] - ls[1]) / (2 * a.eps)
        ga.append(g_adj[i]); gf.append(fd)
        den = max(abs(fd), abs(g_adj[i]), 1e-12)
        print(f"{q:>14} {g_adj[i]:>13.6e} {fd:>13.6e} "
              f"{abs(fd - g_adj[i]) / den:>10.2e}")

    ga, gf = np.array(ga), np.array(gf)
    cos = float(ga @ gf / (np.linalg.norm(ga) * np.linalg.norm(gf) + 1e-300))
    print(f"\ncosine(adjoint, finite-diff) = {cos:.6f}")
    ok = cos > 0.99
    print("\nGATE B " + ("PASSED -- in-situ training optimises the HARDWARE."
                         if ok else "FAILED -- do not train in-situ."))
    if os.path.exists(nl):
        os.remove(nl)
    return 0 if ok else 1


# -------------------------------------------------------------- cfg / CLI ---
def make_cfg(a):
    """Build the circuit config, preferring a solved sizing spec when one
    exists.

    Rf and vref are PER LAYER and must be solved for, not guessed: the column
    current is a sum over fan-in, so one Rf cannot be right for two layers, and
    vref has to sit at each layer's row common mode or that layer's amplifiers
    rail. Running with the scalar defaults is a diagnostic mode, not a
    reportable one -- with them an iris network read 46 mV of class-score
    spread and lost 0.23 accuracy that had nothing to do with the crossbar.
    """
    cfg = dict(rf=a.rf, rd=a.rd, vtail=a.vtail, vref=a.vref, vcm=a.vcm,
               swing=a.swing, gain=a.gain, bias=True, ideal_tia=a.ideal_tia,
               vota=a.vota, r_on=a.r_on, r_off=a.r_off)
    spec = getattr(a, "spec", None)
    if spec is None:
        cand = os.path.join(RESULTS, f"xbar_spec_{a.dataset}.json")
        spec = cand if os.path.exists(cand) else None
    if spec:
        d = json.load(open(spec))
        cfg["rf"] = [f"{r:.6e}" for r in d["rf"]]
        cfg["vref"] = list(d["vref"])
        if "rd" in d:
            cfg["rd"] = [f"{r:.6e}" for r in d["rd"]]
        if "sign_inner" in d:
            cfg["sign_inner"] = float(d["sign_inner"])
            cfg["sign_out"] = float(d["sign_out"])
        print(f"  sizing from {os.path.basename(spec)}: "
              f"Rf={[f'{r:.3g}' for r in d['rf']]} "
              f"rd={[f'{r:.3g}' for r in d.get('rd', [])]} "
              f"vref={[round(v, 3) for v in d['vref']]}")
    return cfg


def main(a):
    a.cfg = make_cfg(a)
    if a.check_grad:
        return check_grad(a)

    kw = dict(n_train=a.n_train, n_test=a.n_test)
    if a.dataset == "mnist":
        kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr_w, mn, mx = to_pm1(Xtr)
    Xte_w, _, _ = to_pm1(Xte, mn, mx)

    layers = [(Xtr.shape[1], a.hidden), (a.hidden, C)]
    params = X.all_params(layers, True)
    print(f"xbar {a.mode} | {a.dataset} | layers={layers} | "
          f"devices={X.n_devices(layers, True, a.ideal_tia)} | "
          f"conductances={len(params)} | levels={a.levels}")

    nl = scratch(f"xbar_{a.tag}")
    log, t0 = [], time.perf_counter()

    if a.mode == "exsitu":
        W = train_software_mlp(Xtr_w, ytr, C, layers, epochs=a.sw_epochs,
                               lr=a.sw_lr, seed=a.seed, hwa_sigma=a.hwa_sigma)
        u = map_to_u(W, layers, a.cfg)
        u = apply_programming_noise(u, a.prog_sigma, seed=a.seed)
        sw_tr = _sw_acc(W, Xtr_w, ytr)
        sw_te = _sw_acc(W, Xte_w, yte)
        tr = evaluate(u, Xtr_w, ytr, layers, a.cfg, nl, a.levels)
        te = evaluate(u, Xte_w, yte, layers, a.cfg, nl, a.levels)
        r = score_fidelity(u, W, Xte_w[:a.n_fid], layers, a.cfg, nl, a.levels)
        print(f"  HWA noise sigma {a.hwa_sigma:.3f} (training) | "
              f"programming sigma {a.prog_sigma:.3f} (inference)")
        print(f"  software MLP   train {sw_tr:.3f}  test {sw_te:.3f}")
        print(f"  mapped circuit train {tr:.3f}  test {te:.3f}   "
              f"(mapping loss {sw_te - te:+.3f})")
        print(f"  score fidelity r = {r:+.4f}   "
              + ("circuit tracks the mapped function"
                 if r > 0.8 else
                 "LOW -- the circuit is NOT computing the mapped function; "
                 "treat this as a setup fault, not a crossbar result"))
        log.append(dict(epoch=0, loss=float("nan"), train=tr, test=te,
                        sw_train=sw_tr, sw_test=sw_te, fidelity=r,
                        hwa_sigma=a.hwa_sigma, prog_sigma=a.prog_sigma,
                        minutes=(time.perf_counter() - t0) / 60))
    else:
        u = init_u(layers, seed=a.seed)
        opt = Adam(u, a.lr)
        pool = None
        if a.workers > 1:
            import multiprocessing as mp
            pool = mp.Pool(a.workers, initializer=_init_worker,
                           initargs=(layers, a.cfg, params,
                                     f"xb{a.tag}", a.levels))
        for ep in range(1, a.epochs + 1):
            order = np.random.default_rng(a.seed + ep).permutation(len(ytr))
            tot, nb = 0.0, 0
            for s in range(0, len(order), a.batch):
                bi = order[s:s + a.batch]
                args = [(u, Xtr_w[k], int(ytr[k])) for k in bi]
                outs = (pool.map(_work, args) if pool else
                        [sample_grad(u, Xtr_w[k], int(ytr[k]), layers, a.cfg,
                                     nl, params, a.levels) for k in bi])
                gsum = np.mean([o[1] for o in outs], axis=0)
                tot += float(np.mean([o[0] for o in outs])); nb += 1
                u = clip_u(opt.step(u, dict(zip(params, gsum))))

            if ep % a.eval_every == 0 or ep == a.epochs:
                if pool:
                    tr = float(np.mean(pool.map(_eval_work,
                        [(u, Xtr_w[k], int(ytr[k])) for k in range(len(ytr))])))
                    te = float(np.mean(pool.map(_eval_work,
                        [(u, Xte_w[k], int(yte[k])) for k in range(len(yte))])))
                else:
                    tr = evaluate(u, Xtr_w, ytr, layers, a.cfg, nl, a.levels)
                    te = evaluate(u, Xte_w, yte, layers, a.cfg, nl, a.levels)
                mins = (time.perf_counter() - t0) / 60
                print(f"  ep {ep:3d}  loss {tot / max(nb,1):.4f}  "
                      f"train {tr:.3f}  test {te:.3f}  [{mins:.1f} min]")
                log.append(dict(epoch=ep, loss=tot / max(nb, 1), train=tr,
                                test=te, minutes=mins))
        if pool:
            pool.close(); pool.join()

    out = os.path.join(RESULTS, f"xbar_{a.mode}_{a.dataset}_{a.tag}.json")
    json.dump(dict(arm=f"xbar_{a.mode}", dataset=a.dataset, layers=layers,
                   cfg=a.cfg, levels=a.levels, seed=a.seed,
                   n_train=len(ytr), n_test=len(yte), C=C,
                   devices=X.n_devices(layers, True, a.ideal_tia),
                   converters=X.converter_counts(layers),
                   u={k: float(v) for k, v in u.items()}, log=log),
              open(out, "w"), indent=2)
    print(f"saved -> {out}")
    if os.path.exists(nl):
        os.remove(nl)
    return 0


def _sw_acc(W, Xd, y):
    a = Xd
    for i in range(len(W)):
        a1 = np.hstack([np.ones((len(a), 1)), a])
        z = a1 @ W[i]
        a = np.tanh(z) if i < len(W) - 1 else z
    return float(np.mean(np.argmax(a, 1) == y))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["exsitu", "insitu"], default="exsitu")
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--hidden", type=int, default=7)
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--lr", type=float, default=0.02)
    ap.add_argument("--sw-epochs", type=int, default=400)
    ap.add_argument("--sw-lr", type=float, default=0.05)
    ap.add_argument("--prog-sigma", type=float, default=0.0,
                    help="device programming error, std as a fraction of the "
                         "conductance window; applied once at mapping")
    ap.add_argument("--hwa-sigma", type=float, default=0.0,
                    help="hardware-aware training: weight-noise std injected "
                         "in the software forward pass")
    ap.add_argument("--levels", type=int, default=None,
                    help="conductance states; omit for continuous")
    ap.add_argument("--gain", type=float, default=4.0)
    ap.add_argument("--rf", default="2.5k")
    ap.add_argument("--rd", default="200k")
    ap.add_argument("--vtail", type=float, default=0.85)
    ap.add_argument("--vref", type=float, default=1.65)
    ap.add_argument("--vcm", type=float, default=1.0)
    ap.add_argument("--swing", type=float, default=0.4)
    ap.add_argument("--vota", type=float, default=0.9)
    ap.add_argument("--r-on", type=float, default=X.R_ON_DEFAULT)
    ap.add_argument("--r-off", type=float, default=X.R_OFF_DEFAULT)
    ap.add_argument("--ideal-tia", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--eval-every", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--spec", default=None,
                    help="sizing JSON from xbar_spec.py; "
                         "defaults to results/xbar_spec_<dataset>.json")
    ap.add_argument("--check-grad", action="store_true")
    ap.add_argument("--n-fid", type=int, default=30,
                    help="samples used for the ex-situ fidelity check")
    ap.add_argument("--n-fd", type=int, default=10)
    ap.add_argument("--eps", type=float, default=2e-3)
    sys.exit(main(ap.parse_args()))
