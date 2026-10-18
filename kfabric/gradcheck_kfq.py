"""
gradcheck_kfq.py -- paper Step 1: is the adjoint gradient the gradient of the
HARDWARE loss, and is the settled readout independent of the time step?

  python gradcheck_kfq.py grad --workers 7      adjoint vs central FD
  python gradcheck_kfq.py dt   --workers 1      time-step / load-cap convergence

`grad` draws many random inputs and parameters (both layers, weights only --
the tails are frozen in training), repeats FD at several eps, and writes every
per-parameter error to results/gradcheck_kfq.json. Pass criterion (set before
running): median relative error < 1 % AND cosine > 0.999, at the best eps.

`dt` re-solves one (theta, x) with different .TRAN step/stop and node
capacitance and reports how far the readout and the gradient move.
"""
import argparse
import json
import multiprocessing as mp
import os
import time

import numpy as np

from model import ce_grad, cross_entropy, softmax
from netlist_kfq import (all_thetas, read_nodes, read_pairs, tail_name,
                         write_kfq_netlist)
from simulator_api import eval_chain, run_chain
from train_kfq import RESULTS, init_params, scratch

_W = {}


def fwd(th, x, layers, cfg, nl, params=None, **net_kw):
    """Score (and Jacobian if `params`) with netlist overrides (cap, tstep, tstop)."""
    write_kfq_netlist(th, x, layers, nl, load_r=cfg["load_r"], rd=cfg["rd"],
                      vtail=cfg["vtail"], vcm=cfg["vcm"], swing=cfg["swing"],
                      **net_kw)
    pairs = read_pairs(layers)
    if params is None:
        v = eval_chain(nl, read_nodes(layers))
        return np.array([v[p] - v[m] for p, m in pairs]), None
    v, sens = run_chain(nl, read_nodes(layers), params)
    sc = np.array([v[p] - v[m] for p, m in pairs])
    J = np.array([[sens[p][q] - sens[m][q] for q in params] for p, m in pairs])
    return sc, J


def loss_of(sc, y, gain):
    return float(cross_entropy(softmax((gain * sc)[None, :]), np.array([y])))


def make_setup(a):
    layers = [(a.n_in, a.hidden), (a.hidden, a.n_out)]
    cfg = dict(load_r=a.load_r, rd=a.rd, vtail=a.vtail, vcm=a.vcm,
               swing=a.swing, gain=a.gain)
    th = init_params(layers, a.thbar, a.dth, a.vtail, seed=a.seed)
    weights = [p for p in all_thetas(layers) if not p.startswith("VT")]
    return layers, cfg, th, weights


def _init(layers, cfg, weights, eps_list, tag, net_kw):
    _W.update(layers=layers, cfg=cfg, weights=weights, eps=eps_list,
              nl=scratch(tag), kw=net_kw)


def _grad_one(arg):
    """One input: adjoint on ALL weights, then FD on the chosen subset."""
    th, x, y, idx = arg
    L, cfg, W, nl, kw = (_W["layers"], _W["cfg"], _W["weights"], _W["nl"],
                         _W["kw"])
    sc, J = fwd(th, x, L, cfg, nl, W, **kw)
    g = cfg["gain"] * (ce_grad(cfg["gain"] * sc, y) @ J)
    out = dict(adj={}, fd={e: {} for e in _W["eps"]})
    for i in idx:
        q, base = W[i], th[W[i]]
        out["adj"][q] = float(g[i])
        for e in _W["eps"]:
            ls = []
            for s in (+1, -1):
                th[q] = base + s * e
                ls.append(loss_of(fwd(th, x, L, cfg, nl, **kw)[0], y,
                                  cfg["gain"]))
            th[q] = base
            out["fd"][e][q] = (ls[0] - ls[1]) / (2 * e)
    return out


def run_grad(a):
    layers, cfg, th, W = make_setup(a)
    rng = np.random.default_rng(100 + a.seed)
    eps_list = [float(e) * 1e-3 for e in a.eps_mv]
    # stratify the parameter subset over both layers
    l0 = [i for i, q in enumerate(W) if q.startswith("VA0") or q.startswith("VB0")]
    l1 = [i for i, q in enumerate(W) if q.startswith("VA1") or q.startswith("VB1")]
    jobs = []
    for _ in range(a.n_samples):
        idx = sorted(list(rng.choice(l0, a.n_params // 2, replace=False))
                     + list(rng.choice(l1, a.n_params - a.n_params // 2,
                                       replace=False)))
        jobs.append((dict(th), rng.uniform(-1, 1, a.n_in),
                     int(rng.integers(a.n_out)), idx))
    t0 = time.time()
    kw = dict(cap=a.cap, tstep=a.tstep, tstop=a.tstop)
    if a.workers > 1:
        with mp.Pool(a.workers, _init,
                     (layers, cfg, W, eps_list, "gc", kw)) as p:
            res = p.map(_grad_one, jobs)
    else:
        _init(layers, cfg, W, eps_list, "gc", kw)
        res = [_grad_one(j) for j in jobs]

    report = dict(layers=layers, cfg=cfg, net=kw, thbar=a.thbar, dth=a.dth,
                  seed=a.seed,
                  n_samples=a.n_samples, n_params=a.n_params, per_eps={})
    for e in eps_list:
        ga, gf, par = [], [], []
        for r in res:
            for q, v in r["adj"].items():
                ga.append(v); gf.append(r["fd"][e][q]); par.append(q)
        ga, gf = np.array(ga), np.array(gf)
        rms = float(np.sqrt(np.mean(gf ** 2)))
        rel = np.abs(ga - gf) / np.maximum(np.maximum(np.abs(ga), np.abs(gf)), 1e-12)
        scaled = np.abs(ga - gf) / max(rms, 1e-30)   # error vs typical gradient
        cos = float(ga @ gf / (np.linalg.norm(ga) * np.linalg.norm(gf) + 1e-300))
        # per-sample cosine over its own parameter subset (what an SGD step sees)
        cs = []
        for r in res:
            qa = np.array(list(r["adj"].values()))
            qf = np.array([r["fd"][e][q] for q in r["adj"]])
            cs.append(float(qa @ qf / (np.linalg.norm(qa) * np.linalg.norm(qf) + 1e-300)))
        report["per_eps"][f"{e * 1e3:g}mV"] = dict(
            n=int(len(ga)), cosine_pooled=cos,
            cosine_per_sample_median=float(np.median(cs)),
            cosine_per_sample_min=float(np.min(cs)),
            median_rel_err=float(np.median(rel)),
            median_scaled_err=float(np.median(scaled)),
            p90_scaled_err=float(np.percentile(scaled, 90)),
            max_scaled_err=float(scaled.max()),
            adjoint=ga.tolist(), fd=gf.tolist(), param=par)
    best = min(report["per_eps"].values(), key=lambda d: d["median_rel_err"])
    report["pass"] = bool(best["median_rel_err"] < 0.01
                          and best["cosine_pooled"] > 0.999)
    report["seconds"] = time.time() - t0
    out = os.path.join(RESULTS, f"gradcheck_kfq_{a.cap}_{a.tstep}.json")
    json.dump(report, open(out, "w"), indent=1)
    print(f"{'eps':>8} {'n':>5} {'cos(pooled)':>12} {'cos/sample min':>15} "
          f"{'med rel':>9} {'med scaled':>11} {'p90 scaled':>11}")
    for k, d in report["per_eps"].items():
        print(f"{k:>8} {d['n']:>5} {d['cosine_pooled']:>12.6f} "
              f"{d['cosine_per_sample_min']:>15.6f} {d['median_rel_err']:>9.2e} "
              f"{d['median_scaled_err']:>11.2e} {d['p90_scaled_err']:>11.2e}")
    print(f"\nGRAD CHECK {'PASSED' if report['pass'] else 'FAILED'}  "
          f"({report['seconds']:.0f} s)  -> {out}")


def run_dt(a):
    layers, cfg, th, W = make_setup(a)
    x = np.random.default_rng(7).uniform(-1, 1, a.n_in)
    y = 0
    rng = np.random.default_rng(3)
    pick = [W[i] for i in rng.choice(len(W), a.n_params, replace=False)]
    nl = scratch("dt")
    # (tstep, tstop); the last is the finest and is the reference
    grids = [("50n", "100n"), ("25n", "100n"), ("10n", "100n"), ("5n", "100n"),
             ("100n", "200n"), ("50n", "200n"), ("1n", "100n")]
    rows = []
    for cap in a.caps:
        data = {}
        for ts, te in grids:
            t0 = time.time()
            sc, J = fwd(th, x, layers, cfg, nl, pick, cap=cap, tstep=ts, tstop=te)
            g = cfg["gain"] * (ce_grad(cfg["gain"] * sc, y) @ J)
            data[(ts, te)] = (sc, g, time.time() - t0)
        ref_sc, ref_g, _ = data[grids[-1]]
        for (ts, te), (sc, g, dt) in data.items():
            cos = float(g @ ref_g / (np.linalg.norm(g) * np.linalg.norm(ref_g) + 1e-300))
            rows.append(dict(cap=cap, tstep=ts, tstop=te, seconds=dt,
                             score=sc.tolist(),
                             max_abs_dscore_V=float(np.abs(sc - ref_sc).max()),
                             grad_cos_vs_ref=cos,
                             grad_rel_l2=float(np.linalg.norm(g - ref_g)
                                               / (np.linalg.norm(ref_g) + 1e-300))))
    print(f"{'cap':>6} {'tstep':>6} {'tstop':>6} {'max|dScore| V':>14} "
          f"{'grad cos':>10} {'grad relL2':>11} {'s':>6}")
    for r in rows:
        print(f"{r['cap']:>6} {r['tstep']:>6} {r['tstop']:>6} "
              f"{r['max_abs_dscore_V']:>14.3e} {r['grad_cos_vs_ref']:>10.6f} "
              f"{r['grad_rel_l2']:>11.2e} {r['seconds']:>6.1f}")
    out = os.path.join(RESULTS, "dtconv_kfq.json")
    json.dump(dict(layers=layers, cfg=cfg, rows=rows), open(out, "w"), indent=1)
    print(f"-> {out}")
    if os.path.exists(nl):
        os.remove(nl)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["grad", "dt"])
    ap.add_argument("--n-in", type=int, default=4)
    ap.add_argument("--hidden", type=int, default=7)
    ap.add_argument("--n-out", type=int, default=3)
    ap.add_argument("--n-samples", type=int, default=12)
    ap.add_argument("--n-params", type=int, default=20)
    ap.add_argument("--eps-mv", type=float, nargs="+", default=[0.5, 2.0, 10.0])
    ap.add_argument("--caps", nargs="+", default=["0.1f", "10f"])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--cap", default="0.1f", help="grad mode: node capacitance")
    ap.add_argument("--tstep", default="50n")
    ap.add_argument("--tstop", default="100n")
    ap.add_argument("--seed", type=int, default=0)
    # circuit config = train_kfq.py defaults (iris)
    ap.add_argument("--thbar", type=float, default=1.93)
    ap.add_argument("--dth", type=float, default=0.60)
    ap.add_argument("--vcm", type=float, default=1.00)
    ap.add_argument("--swing", type=float, default=0.40)
    ap.add_argument("--vtail", type=float, default=0.85)
    ap.add_argument("--load-r", dest="load_r", default="6k")
    ap.add_argument("--rd", default="200k")
    ap.add_argument("--gain", type=float, default=4.0)
    a = ap.parse_args()
    run_grad(a) if a.mode == "grad" else run_dt(a)
