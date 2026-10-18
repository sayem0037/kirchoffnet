"""WP2: what does the circuit add? Controlled comparison + readout-time sweep (frozen circuit, inference only).

Per (dataset, seed, topology) the SAME split (train/val identical to experiment.py; larger test set) is simulated once with
the full waveform stored, so every readout time comes from one simulation per point.

  raw          : logistic regression on standardized inputs                      (A)
  enc          : logistic regression on encoded .IC voltages = state at t=0       (B)
  ring_t       : logistic regression on ring state at time t, t on the output grid (C(t))
  mlp / svm    : small conventional nonlinear models on the raw inputs (task difficulty reference)
Also per time: R2 of a ridge map state->(x1,x2) on test = how much input information the state still carries.
Failed simulations are NaN rows and count as WRONG in acc_strict.

usage: python -m kring.tools.representation <dataset> <seed> <out_dir> [tstep] [workers] [topology: ring|chain] [n_test_pc]
(KRING_SIM_SRC must be set)
"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
from dataset import _raw
from ring_common import init_seed_encoder, N_STAGES, circ_init
from kring.model import KRingModel
from kring.sim import simulate, spice_val
from kring.tools.experiment import (N_TRAIN_PC, N_VAL_PC, build_pkg, fit_lr, score, encode_all)

N_TEST_PC_DEFAULT = 100


def split_big(name, seed, n_test_pc=N_TEST_PC_DEFAULT):
    """Same train/val as experiment.split_arrays (same RNG order); the test set is a superset of the old one."""
    X, y = _raw(name)
    rng = np.random.default_rng(1000 + seed)
    sets = {"train": [], "val": [], "test": []}
    for cls in (0, 1):
        idx = rng.permutation(np.where(y == cls)[0])
        a, b = N_TRAIN_PC, N_TRAIN_PC + N_VAL_PC
        sets["train"] += list(idx[:a]); sets["val"] += list(idx[a:b]); sets["test"] += list(idx[b:b + n_test_pc])
    out = {}
    for k in ("train", "val", "test"):
        i = rng.permutation(np.array(sets[k]))
        out[k] = (X[i], y[i].astype(int))
    return out


def _wave_job(args):
    pkg, x, sim_src, kw, tstep, tgrid = args
    m = KRingModel(pkg, sim_src)
    r = simulate(m.netlist(x, tstep=tstep, **kw), m.nodes, m.tstop, sim_src=sim_src, want_wave=True)
    if r["status"] != "ok":
        return np.full((len(tgrid), m.n), np.nan), r["status"]
    t, V = r["wave"]
    return np.stack([np.interp(tgrid, t, v) for v in V], 1), "ok"


def waves(model, X, tstep, tgrid, workers, **kw):
    """(len(X), len(tgrid), N) voltages; NaN rows on failure; statuses."""
    jobs = [(model.pkg, x, model.sim_src, kw, tstep, tgrid) for x in X]
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            rows = list(ex.map(_wave_job, jobs, chunksize=2))
    else:
        rows = [_wave_job(j) for j in jobs]
    return np.stack([r[0] for r in rows]), [r[1] for r in rows]


def r2_decode(Ftr, Ztr, Fte, Zte):
    """test R2 of ridge state -> standardized inputs (mean over the 2 coordinates); NaN rows dropped."""
    a, b = ~np.isnan(Ftr).any(1), ~np.isnan(Fte).any(1)
    if a.sum() < 6 or b.sum() < 6:
        return None
    mu, sd = Ftr[a].mean(0), Ftr[a].std(0) + 1e-9
    rg = Ridge(alpha=1.0).fit((Ftr[a] - mu) / sd, Ztr[a])
    P = rg.predict((Fte[b] - mu) / sd)
    ss_res = ((Zte[b] - P) ** 2).sum(0)
    ss_tot = ((Zte[b] - Zte[b].mean(0)) ** 2).sum(0)
    return float(np.mean(1 - ss_res / ss_tot))


def run(name, seed, out_dir, tstep="5n", workers=4, topology="ring", n_test_pc=N_TEST_PC_DEFAULT):
    os.makedirs(out_dir, exist_ok=True)
    t_start = time.time()
    sp = split_big(name, seed, n_test_pc)
    (Xtr, ytr), (Xva, yva), (Xte, yte) = sp["train"], sp["val"], sp["test"]
    W, b = init_seed_encoder(seed=seed)
    dummy = fit_lr(np.random.default_rng(0).standard_normal((20, N_STAGES)), np.arange(20) % 2)
    model = KRingModel(build_pkg(name, seed, Xtr, W, b, circ_init(), dummy, tstep=tstep), None)
    tstop = spice_val("100n")
    tgrid = np.arange(0.0, tstop * (1 + 1e-9), spice_val(tstep))
    res = dict(dataset=name, seed=seed, topology=topology, tstep=tstep, sizes=dict(train=len(ytr), val=len(yva), test=len(yte)),
               t_ns=(tgrid * 1e9).tolist())

    mu, sd = Xtr.mean(0), Xtr.std(0)
    Fn = lambda X: (X - mu) / sd
    res["raw_linear"] = score(fit_lr(Fn(Xtr), ytr), Fn(Xte), yte)
    res["enc_linear"] = score(fit_lr(encode_all(model, Xtr), ytr), encode_all(model, Xte), yte)
    mlp = MLPClassifier((32, 32), max_iter=3000, random_state=seed).fit(Fn(Xtr), ytr)
    svm = SVC(kernel="rbf", C=10.0).fit(Fn(Xtr), ytr)
    res["mlp_ref"] = dict(acc=float(mlp.score(Fn(Xte), yte)))
    res["svm_ref"] = dict(acc=float(svm.score(Fn(Xte), yte)))

    kw = dict(chain=True) if topology == "chain" else {}
    W3 = {}
    for k, X in (("train", Xtr), ("val", Xva), ("test", Xte)):
        W3[k], st = waves(model, X, tstep, tgrid, workers, **kw)
        res[f"status_{k}"] = {s: st.count(s) for s in set(st)}
        print(f"[{name} s{seed} {topology}] {k}: {res[f'status_{k}']}  t={time.time()-t_start:.0f}s", flush=True)

    Ztr, Zte = Fn(Xtr), Fn(Xte)
    rows = []
    for ti in range(len(tgrid)):
        Ftr, Fva, Fte = W3["train"][:, ti], W3["val"][:, ti], W3["test"][:, ti]
        ok = ~np.isnan(Ftr).any(1)
        if ok.sum() < 6 or len(set(ytr[ok])) < 2:
            rows.append(dict(t_ns=float(tgrid[ti] * 1e9), error="too few ok train rows")); continue
        fit = fit_lr(Ftr[ok], ytr[ok])
        rows.append(dict(t_ns=float(tgrid[ti] * 1e9), val=score(fit, Fva, yva), test=score(fit, Fte, yte),
                         r2_input=r2_decode(Ftr, Ztr, Fte, Zte)))
    res["sweep"] = rows
    good = [r for r in rows if "val" in r and r["val"]["fail_rate"] == 0]
    if good:                                   # time chosen on VAL only; test read once at that time
        best = min(good, key=lambda r: r["val"]["ce"])
        res["val_selected"] = dict(t_ns=best["t_ns"], test=best["test"], val=best["val"])
    res["final_time"] = rows[-1]
    res["wall_s"] = time.time() - t_start
    json.dump(res, open(os.path.join(out_dir, f"{name}_s{seed}_{topology}_{tstep}.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(out_dir, f"{name}_s{seed}_{topology}_{tstep}_states.npz"),
                        Xtr=Xtr, ytr=ytr, Xva=Xva, yva=yva, Xte=Xte, yte=yte,
                        Wtr=W3["train"], Wva=W3["val"], Wte=W3["test"], tgrid=tgrid)
    vs = res.get("val_selected", {})
    print(f"[{name} s{seed} {topology}] DONE raw={res['raw_linear']['acc_strict']:.3f} enc={res['enc_linear']['acc_strict']:.3f} "
          f"ring@100n={rows[-1].get('test', {}).get('acc_strict')} ring@val-t={vs.get('test', {}).get('acc_strict')} "
          f"(t={vs.get('t_ns')}ns) mlp={res['mlp_ref']['acc']:.3f} wall={res['wall_s']:.0f}s", flush=True)
    return res


if __name__ == "__main__":
    a = sys.argv
    run(a[1], int(a[2]), a[3], a[4] if len(a) > 4 else "5n", int(a[5]) if len(a) > 5 else 4,
        a[6] if len(a) > 6 else "ring", int(a[7]) if len(a) > 7 else N_TEST_PC_DEFAULT)
