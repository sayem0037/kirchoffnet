"""Independent forward cross-check of the in-house simulator against Xyce.

usage: python -m kring.tools.xyce_compare <package.json> <points.npy> <report.json> [n_points] [tstep ...]
(KRING_SIM_SRC must be set; Xyce found via XYCE_EXE or the default install path.)

The same package netlist is run in both simulators. For Xyce the .TRAN card is replaced by a tight-tolerance
adaptive run, so the Xyce answer acts as a dt-independent reference. Two Xyce initialisations are compared:
  dcop : .IC pins h1..hN during the DC solve, then the transient starts from that solution
  uic  : .TRAN ... UIC, all other nodes start at 0
"""
import concurrent.futures as cf, csv, json, os, re, subprocess, sys, tempfile, time
import numpy as np

from kring.model import KRingModel
from kring.sim import simulate

XYCE = os.environ.get("XYCE_EXE", r"C:\Program Files\XyceNF_7.10\bin\Xyce.exe")


def to_xyce(netlist, nodes, tstop, uic):
    """Swap the .TRAN/.END tail for a Xyce analysis block with tight tolerances."""
    body = [l for l in netlist.splitlines() if not re.match(r"\s*\.(TRAN|END)\b", l, re.I)]
    body.append(f".TRAN 0.1n {tstop}" + (" UIC" if uic else ""))
    body.append(".OPTIONS TIMEINT RELTOL=1e-6 ABSTOL=1e-10 METHOD=GEAR")
    body.append(".OPTIONS NONLIN RELTOL=1e-8 ABSTOL=1e-12 MAXSTEP=100")
    body.append(".PRINT TRAN FORMAT=CSV " + " ".join(f"V({n})" for n in nodes))
    body.append(".END")
    return "\n".join(body) + "\n"


def run_xyce(netlist, nodes, tstop, uic=False, timeout=300):
    """Returns dict(status, v, t_final, message); never raises."""
    out = dict(status="error", v=None, t_final=None, message="")
    with tempfile.TemporaryDirectory(prefix="kring_xyce_") as td:
        cir = os.path.join(td, "ring.cir")
        with open(cir, "w") as f:
            f.write(to_xyce(netlist, nodes, tstop, uic))
        try:
            p = subprocess.run([XYCE, cir], capture_output=True, text=True, timeout=timeout, cwd=td)
        except subprocess.TimeoutExpired:
            out["status"] = "timeout"
            return out
        prn = cir + ".csv"
        if p.returncode != 0 or not os.path.exists(prn):
            out["message"] = (p.stdout + p.stderr)[-200:]
            out["status"] = "no_convergence" if "onverge" in out["message"] else "error"
            return out
        rows = list(csv.reader(open(prn)))
        last = [float(x) for x in rows[-1]]
        out["t_final"], out["v"] = last[0], last[1:]
        out["status"] = "ok" if abs(last[0] - tstop) < 1e-6 * tstop and np.isfinite(out["v"]).all() else "incomplete"
    return out


def main(pkg_path, pts_path, out_path, n=12, steps=("10n", "5n", "2.5n", "1n")):
    m = KRingModel.load(pkg_path)
    pts = np.load(pts_path)[:n]
    rep = dict(n=len(pts), xyce=XYCE, steps=list(steps), points=[], summary={})

    def xy(x, uic):
        return run_xyce(m.netlist(x), m.nodes, m.tstop, uic=uic)

    t0 = time.time()
    with cf.ThreadPoolExecutor(4) as ex:
        ref_dc = list(ex.map(lambda x: xy(x, False), pts))
        ref_uic = list(ex.map(lambda x: xy(x, True), pts))
    print(f"xyce done {time.time()-t0:.0f}s", flush=True)

    inh = {}
    for ts in steps:
        inh[ts] = [simulate(m.netlist(x, tstep=ts), m.nodes, m.tstop, sim_src=m.sim_src) for x in pts]
        print(f"in-house {ts} done {time.time()-t0:.0f}s", flush=True)

    def lab(r):
        return int(m.readout(r["v"]).argmax()) if r["status"] == "ok" else -1

    for i, x in enumerate(pts):
        row = dict(x=[float(a) for a in x], xyce_dcop=ref_dc[i]["status"], xyce_uic=ref_uic[i]["status"],
                   label_xyce_dcop=lab(ref_dc[i]), label_xyce_uic=lab(ref_uic[i]))
        for ts in steps:
            r = inh[ts][i]
            row[f"inhouse_{ts}"] = dict(status=r["status"], label=lab(r))
            if r["status"] == "ok" and ref_dc[i]["status"] == "ok":
                row[f"inhouse_{ts}"]["maxdiff_vs_xyce_dcop"] = float(np.max(np.abs(np.array(r["v"]) - ref_dc[i]["v"])))
            if r["status"] == "ok" and ref_uic[i]["status"] == "ok":
                row[f"inhouse_{ts}"]["maxdiff_vs_xyce_uic"] = float(np.max(np.abs(np.array(r["v"]) - ref_uic[i]["v"])))
        rep["points"].append(row)

    def stat(key):
        d = [p[key] for p in rep["points"] if key in p]
        return dict(n=len(d), median=float(np.median(d)) if d else None, max=float(np.max(d)) if d else None)
    for ts in steps:
        for ref in ("dcop", "uic"):
            ok = [p for p in rep["points"] if p["xyce_" + ref] == "ok"]
            flips = sum(p[f"inhouse_{ts}"]["label"] != p["label_xyce_" + ref] for p in ok)
            d = [p[f"inhouse_{ts}"][f"maxdiff_vs_xyce_{ref}"] for p in ok if f"maxdiff_vs_xyce_{ref}" in p[f"inhouse_{ts}"]]
            rep["summary"][f"{ts}_vs_xyce_{ref}"] = dict(
                n_compared=len(d), median_maxdiff=float(np.median(d)) if d else None,
                max_maxdiff=float(np.max(d)) if d else None, label_flips=int(flips), n_xyce_ok=len(ok))
    rep["summary"]["xyce_dcop_vs_uic"] = dict(
        label_flips=sum(a["label_xyce_dcop"] != a["label_xyce_uic"] for a in rep["points"]),
        n_failed_dcop=sum(p["xyce_dcop"] != "ok" for p in rep["points"]),
        n_failed_uic=sum(p["xyce_uic"] != "ok" for p in rep["points"]))
    json.dump(rep, open(out_path, "w"), indent=1)
    print(json.dumps(rep["summary"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 12,
         tuple(sys.argv[5:]) or ("10n", "5n", "2.5n", "1n"))
