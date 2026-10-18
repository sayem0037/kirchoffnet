"""Step-4 validation of the circuit computation itself.

usage: python -m kring.tools.validate <package.json> <points.npy> <report.json> [n_points]
(KRING_SIM_SRC must be set). points.npy: (M,2) raw inputs; the first n_points are used.
"""
import json, sys, time
import numpy as np

from kring.model import KRingModel
from kring.sim import simulate, spice_val


def _maxabs(a, b):
    return float(np.max(np.abs(np.asarray(a) - np.asarray(b))))


def check_gradients(m, pts, eps=2e-3, params=("VTH1", "VTH6", "VB3", "VB8", "VN2", "VN9")):
    names = m.pkg["circuit"]["param_order"]
    rows = []
    for x in pts[:2]:
        base = list(m.pkg["circuit"]["params"])
        r = simulate(m.netlist(x), m.nodes, m.tstop, sens_params=list(params), sim_src=m.sim_src)
        if r["status"] != "ok":
            rows.append(dict(x=list(x), status=r["status"])); continue
        for k, p in enumerate(params):
            idx = names.index(p)
            vals = []
            for sgn in (+1, -1):
                cv = list(base); cv[idx] += sgn * eps
                rr = simulate(m.netlist(x, circ_vec=cv), m.nodes, m.tstop, sim_src=m.sim_src)
                vals.append(rr["v"] if rr["status"] == "ok" else None)
            if None in vals:
                rows.append(dict(x=list(x), param=p, status="fd_failed")); continue
            fd = (np.array(vals[0]) - np.array(vals[1])) / (2 * eps)
            ad = np.array([r["sens"][n][k] for n in m.nodes])
            scale = max(np.max(np.abs(fd)), 1e-9)
            rows.append(dict(x=list(x), param=p, max_abs_err=_maxabs(ad, fd), fd_scale=float(scale),
                             rel_err=_maxabs(ad, fd) / float(scale),
                             adjoint=ad.tolist(), fd=fd.tolist()))
    good = [r["rel_err"] for r in rows if "rel_err" in r]
    return dict(rows=rows, worst_rel_err=max(good) if good else None, n_failed=len(rows) - len(good))


def check_timestep(m, pts):
    base = m.sim["tstep"]
    steps = [base, f"{spice_val(base)*0.5*1e9:g}n", f"{spice_val(base)*0.25*1e9:g}n"]
    out = []
    ref = None
    for ts in steps:
        S, L = [], []
        for x in pts:
            r = simulate(m.netlist(x, tstep=ts), m.nodes, m.tstop, sim_src=m.sim_src)
            S.append(r["v"] if r["status"] == "ok" else [np.nan] * m.n)
            L.append(int(m.readout(r["v"]).argmax()) if r["status"] == "ok" else -1)
        S = np.array(S)
        if ref is None:
            ref = (S, L)
        out.append(dict(tstep=ts, max_state_diff_vs_base=float(np.nanmax(np.abs(S - ref[0]))),
                        label_flips_vs_base=int(sum(a != b for a, b in zip(L, ref[1]))),
                        n_failed=int(np.isnan(S).any(1).sum())))
    return out


def check_ic_reset(m, pts):
    x1, x2 = pts[0], pts[1]
    seeds = m.encode(x1)
    r1 = simulate(m.netlist(x1), m.nodes, m.tstop, sim_src=m.sim_src, want_t0=True)
    r2 = simulate(m.netlist(x2), m.nodes, m.tstop, sim_src=m.sim_src, want_t0=True)
    r1b = simulate(m.netlist(x1), m.nodes, m.tstop, sim_src=m.sim_src, want_t0=True)
    res = dict(statuses=[r1["status"], r2["status"], r1b["status"]])
    if r1["status"] == r2["status"] == r1b["status"] == "ok":
        t0 = np.array([r1["t0"][n] for n in m.nodes])
        res["t0_matches_ic_max_err"] = _maxabs(t0, seeds)
        res["reset_x1_after_x2_max_diff"] = _maxabs(r1["v"], r1b["v"])
        res["internal_dc_node_dm1_x1_vs_x2"] = [r1["t0"]["dm1"], r2["t0"]["dm1"]]
        res["internal_dc_node_tl1_x1_vs_x2"] = [r1["t0"]["tl1"], r2["t0"]["tl1"]]
        res["final_state_x1_vs_x2_max_diff"] = _maxabs(r1["v"], r2["v"])
        res["state_change_t0_to_T_x1"] = _maxabs(t0, r1["v"])
    return res


def check_final_time(m, pts):
    stat, tf = [], []
    for x in pts:
        r = simulate(m.netlist(x), m.nodes, m.tstop, sim_src=m.sim_src)
        stat.append(r["status"]); tf.append(r["t_final"])
    return dict(status_counts={s: stat.count(s) for s in set(stat)},
                t_final_min=min([t for t in tf if t is not None], default=None),
                t_final_max=max([t for t in tf if t is not None], default=None),
                tstop=m.tstop)


def check_repeat_order(m, pts):
    a = m.predict(pts)
    b = m.predict(pts)
    perm = np.random.default_rng(0).permutation(len(pts))
    c = m.predict(pts[perm])
    inv = np.argsort(perm)
    d = m.predict(pts, workers=2)
    ok = a.ok & b.ok & c.ok[inv] & d.ok

    def diff(p, q, ix=slice(None)):
        return float(np.nanmax(np.abs(p.state[ix] - q.state)[ok])) if ok.any() else None
    return dict(n=len(pts), n_ok_all=int(ok.sum()),
                repeat_max_state_diff=diff(a, b),
                shuffled_order_max_state_diff=float(np.nanmax(np.abs(a.state - c.state[inv])[ok])) if ok.any() else None,
                parallel2_max_state_diff=diff(a, d),
                labels_identical=bool((a.label == b.label).all() and (a.label == c.label[inv]).all()
                                      and (a.label == d.label).all()))


def main(pkg_path, pts_path, out_path, n=8):
    m = KRingModel.load(pkg_path)
    pts = np.load(pts_path)[:n]
    rep = {}
    for name, fn in [("final_time_and_status", check_final_time), ("ic_and_reset", check_ic_reset),
                     ("adjoint_vs_finite_difference", check_gradients), ("timestep", check_timestep),
                     ("repeat_order_parallel", check_repeat_order)]:
        t = time.time()
        rep[name] = fn(m, pts)
        print(f"[{name}] {time.time()-t:.0f}s", flush=True)
        json.dump(rep, open(out_path, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "adjoint_vs_finite_difference"}, indent=1))
    g = rep["adjoint_vs_finite_difference"]
    print("gradient worst rel err:", g["worst_rel_err"], "failed:", g["n_failed"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 8)
