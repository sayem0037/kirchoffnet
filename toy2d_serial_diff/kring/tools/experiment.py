"""Steps 3 + 5: clean splits, four-way comparison, gradient-free circuit training.

Per (dataset, seed):
  split  : balanced train/val/test drawn with the seed; scaler fit on TRAIN only
  A      : linear classifier on the normalized inputs
  B      : linear classifier on the encoded initial voltages (clipped .IC seeds)
  C      : UNTRAINED ring + trained readout
  D      : TRAINED ring + trained readout
Circuit training = SPSA-style search (adjoint is NOT used: it is wrong, see README) with an inner
closed-form-ish readout refit. A circuit update is accepted only if EVERY training sample simulates
successfully and the objective improves. The checkpoint is chosen on validation using the exact
parameters that get saved; the test set is evaluated once, for the chosen checkpoint only.

usage: python -m kring.tools.experiment <dataset> <seed> <out_dir> [iters] [workers]
(KRING_SIM_SRC must be set)
"""
import json, os, sys, time
import numpy as np
from sklearn.linear_model import LogisticRegression

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
from dataset import _raw
from ring_common import init_seed_encoder, N_STAGES, VLO, VHI, IC_CENTER, CIRC_NAMES, BOUNDS, circ_init
from kring.model import KRingModel
from kring.package import FORMAT_VERSION, save_package
from kring.sim import fingerprint, sim_src_dir
from kring.tools.import_legacy import MODELS, DEVICES

N_TRAIN_PC, N_VAL_PC, N_TEST_PC = 20, 12, 24
LR_C = 10.0
PERT = np.array([0.008] * N_STAGES + [0.004] * N_STAGES + [0.008] * N_STAGES)  # per-param SPSA size (V)


def split_arrays(name, seed):
    X, y = _raw(name)
    rng = np.random.default_rng(1000 + seed)
    sets = {"train": [], "val": [], "test": []}
    for cls in (0, 1):
        idx = rng.permutation(np.where(y == cls)[0])
        a, b = N_TRAIN_PC, N_TRAIN_PC + N_VAL_PC
        sets["train"] += list(idx[:a]); sets["val"] += list(idx[a:b]); sets["test"] += list(idx[b:b + N_TEST_PC])
    return {k: _shuffled(X, y, v, rng) for k, v in sets.items()}


def _shuffled(X, y, idx, rng):
    idx = rng.permutation(np.array(idx))
    return X[idx], y[idx].astype(int)


def fit_lr(F, y):
    mu, sd = F.mean(0), F.std(0) + 1e-9
    lr = LogisticRegression(C=LR_C, max_iter=2000).fit((F - mu) / sd, y)
    return dict(mu=mu, sd=sd, w=lr.coef_[0], b=float(lr.intercept_[0]))


def lr_proba(fit, F):
    z = ((F - fit["mu"]) / fit["sd"]) @ fit["w"] + fit["b"]
    p1 = 1 / (1 + np.exp(-z))
    return np.stack([1 - p1, p1], 1)


def ce(P, y):
    return float(-np.log(P[np.arange(len(y)), y] + 1e-12).mean())


def score(fit, F, y):
    """accuracy with failures (NaN rows) counted WRONG, plus acc on ok rows, fail rate, ce on ok rows."""
    ok = ~np.isnan(F).any(1)
    pred = np.full(len(y), -1)
    if ok.any():
        P = lr_proba(fit, F[ok]); pred[ok] = P.argmax(1)
    return dict(acc_strict=float((pred == y).mean()),
                acc_on_ok=float((pred[ok] == y[ok]).mean()) if ok.any() else None,
                fail_rate=float(1 - ok.mean()), n=len(y),
                ce=ce(lr_proba(fit, F[ok]), y[ok]) if ok.any() else float("inf"))


def encode_all(model, X):
    return np.array([model.encode(x) for x in X])


def build_pkg(name, seed, Xtr, W, b, circ, fit, classes=(0, 1), prov=None, tstep="10n"):
    w = fit["w"]
    return dict(
        format_version=FORMAT_VERSION, classes=list(classes),
        preprocessing=dict(kind="standardize", mean=Xtr.mean(0).tolist(), std=Xtr.std(0).tolist(),
                           fit_on="train split only"),
        encoder=dict(kind="affine_clip", center=IC_CENTER, W=np.asarray(W).tolist(),
                     b=np.asarray(b).tolist(), vlo=VLO, vhi=VHI),
        circuit=dict(topology="diffamp_ring_v1", n_stages=N_STAGES, vdd=3.3, cap="1p", models=MODELS,
                     devices=DEVICES, param_order=CIRC_NAMES, params=[float(v) for v in circ]),
        simulation=dict(tstep=tstep, tstop="100n", method="simulator default",
                        simulator_fingerprint=fingerprint(sim_src_dir())),
        readout=dict(state_mean=fit["mu"].tolist(), state_std=fit["sd"].tolist(),
                     W=[(-w / 2).tolist(), (w / 2).tolist()], b=[-fit["b"] / 2, fit["b"] / 2]),
        provenance=prov or {})


class Evaluator:
    def __init__(self, model, workers):
        self.m, self.workers = model, workers
        self.nsim = 0

    def states(self, X, circ):
        self.nsim += len(X)
        S, st = self.m.states(X, circ_vec=[float(v) for v in circ], workers=self.workers)
        return S, st

    def objective(self, X, y, circ):
        """(nfail*10 + CE of refit readout on ok rows, fit, S)."""
        S, _ = self.states(X, circ)
        ok = ~np.isnan(S).any(1)
        nfail = int((~ok).sum())
        if ok.sum() < 6 or len(set(y[ok])) < 2:
            return nfail * 10 + 5.0, None, S
        fit = fit_lr(S[ok], y[ok])
        return nfail * 10 + ce(lr_proba(fit, S[ok]), y[ok]), fit, S


def run(name, seed, out_dir, iters=24, workers=12):
    os.makedirs(out_dir, exist_ok=True)
    t_start = time.time()
    sp = split_arrays(name, seed)
    (Xtr, ytr), (Xva, yva), (Xte, yte) = sp["train"], sp["val"], sp["test"]
    W, b = init_seed_encoder(seed=seed)
    circ0 = circ_init()
    # throw-away fit just to instantiate a model object; real readouts are fit below
    dummy = fit_lr(np.random.default_rng(0).standard_normal((20, N_STAGES)), np.arange(20) % 2)
    model = KRingModel(build_pkg(name, seed, Xtr, W, b, circ0, dummy), None)
    ev = Evaluator(model, workers)
    res = dict(dataset=name, seed=seed, sizes=dict(train=len(ytr), val=len(yva), test=len(yte)))

    # A / B: baselines that need no simulation
    fa = fit_lr((Xtr - Xtr.mean(0)) / Xtr.std(0), ytr)
    Fn = lambda X: (X - Xtr.mean(0)) / Xtr.std(0)
    res["A_linear_inputs"] = score(fa, Fn(Xte), yte)
    Etr, Ete = encode_all(model, Xtr), encode_all(model, Xte)
    fb = fit_lr(Etr, ytr)
    res["B_linear_encoded_ic"] = score(fb, Ete, yte)

    # C: untrained ring + trained readout
    obj0, fit0, S0 = ev.objective(Xtr, ytr, circ0)
    res["C_untrained_train_fail"] = int(np.isnan(S0).any(1).sum())
    if fit0 is not None:
        Sva0, _ = ev.states(Xva, circ0)
        Ste0, st_te0 = ev.states(Xte, circ0)
        res["C_untrained_ring"] = score(fit0, Ste0, yte)
        res["C_untrained_val"] = score(fit0, Sva0, yva)
    print(f"[{name} s{seed}] A={res['A_linear_inputs']['acc_strict']:.3f} B={res['B_linear_encoded_ic']['acc_strict']:.3f} "
          f"C={res.get('C_untrained_ring', {}).get('acc_strict')} trainfail0={res['C_untrained_train_fail']}", flush=True)

    # D: SPSA circuit training
    rng = np.random.default_rng(5000 + seed)
    lo, hi = np.array([l for l, _ in BOUNDS]), np.array([h for _, h in BOUNDS])
    cur, cur_obj, cur_fit = circ0.copy(), obj0, fit0
    log = [dict(it=0, obj=cur_obj, accepted=True)]
    Sva, _ = ev.states(Xva, cur)
    vok = ~np.isnan(Sva).any(1)
    best = dict(circ=cur.copy(), key=(int((~vok).sum()), score(fit0, Sva, yva)["ce"] if fit0 else 99.0), it=0)
    for it in range(1, iters + 1):
        d = rng.choice([-1.0, 1.0], size=len(cur))
        cp = np.clip(cur + PERT * d, lo, hi); cm = np.clip(cur - PERT * d, lo, hi)
        op, _, _ = ev.objective(Xtr, ytr, cp)
        om, _, _ = ev.objective(Xtr, ytr, cm)
        cands = [(op, cp), (om, cm)]
        if min(op, om) < 1e3:                        # extrapolate along the better direction
            sgn = 1.0 if op < om else -1.0
            cx = np.clip(cur + sgn * PERT * d * 1.5, lo, hi)
            ox, _, _ = ev.objective(Xtr, ytr, cx)
            cands.append((ox, cx))
        o, c = min(cands, key=lambda t: t[0])
        acc = o < cur_obj - 1e-6
        if acc:
            cur, cur_obj = c, o
            _, cur_fit, _ = ev.objective(Xtr, ytr, cur)      # fit for the exact accepted params
            Sva, _ = ev.states(Xva, cur)
            vok = ~np.isnan(Sva).any(1)
            key = (int((~vok).sum()), score(cur_fit, Sva, yva)["ce"] if cur_fit else 99.0)
            if key < best["key"]:
                best = dict(circ=cur.copy(), key=key, it=it)
        log.append(dict(it=it, obj=float(cur_obj), cand=[float(op), float(om)], accepted=bool(acc)))
        print(f"[{name} s{seed}] it{it:02d} obj={cur_obj:.4f} cand={op:.3f}/{om:.3f} acc={acc} "
              f"best_it={best['it']} nsim={ev.nsim}", flush=True)
    res["D_train_log"] = log

    # evaluate the EXACT saved parameters; test is touched once, here.
    chosen = best["circ"]
    objc, fitc, Str = ev.objective(Xtr, ytr, chosen)
    Svac, _ = ev.states(Xva, chosen)
    t0 = time.time(); Stec, st_tec = ev.states(Xte, chosen); t_test = time.time() - t0
    res["D_trained_ring"] = score(fitc, Stec, yte)
    res["D_trained_val"] = score(fitc, Svac, yva)
    res["D_train_fail"] = int(np.isnan(Str).any(1).sum())
    res["D_chosen_iter"] = best["it"]
    res["D_test_wall_s"] = t_test
    res["acceptance"] = dict(train_all_ok=res["D_train_fail"] == 0,
                             val_all_ok=res["D_trained_val"]["fail_rate"] == 0)
    res["n_sims"] = ev.nsim
    res["wall_s"] = time.time() - t_start
    pkg = build_pkg(name, seed, Xtr, W, b, chosen, fitc,
                    prov=dict(dataset=name, seed=seed, splits=res["sizes"], trainer="SPSA, adjoint unused",
                              chosen_iter=best["it"], val=res["D_trained_val"], test=res["D_trained_ring"],
                              train_fail=res["D_train_fail"], acceptance=res["acceptance"]))
    save_package(pkg, os.path.join(out_dir, f"{name}_s{seed}_trained.json"))
    np.save(os.path.join(out_dir, f"{name}_s{seed}_test_points.npy"), Xte)
    json.dump(res, open(os.path.join(out_dir, f"{name}_s{seed}_result.json"), "w"), indent=1)
    print(f"[{name} s{seed}] DONE A={res['A_linear_inputs']['acc_strict']:.3f} B={res['B_linear_encoded_ic']['acc_strict']:.3f} "
          f"C={res.get('C_untrained_ring', {}).get('acc_strict')} D={res['D_trained_ring']['acc_strict']:.3f}", flush=True)
    return res


if __name__ == "__main__":
    a = sys.argv
    run(a[1], int(a[2]), a[3], int(a[4]) if len(a) > 4 else 24, int(a[5]) if len(a) > 5 else 12)
