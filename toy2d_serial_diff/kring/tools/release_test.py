"""Release test: load a package in a FRESH process and reproduce stored reference predictions.

make reference : python -m kring.tools.release_test make <package.json> <reference.json> <points.npy> [n]
run test       : python -m kring.tools.release_test check <package.json> <reference.json>
(KRING_SIM_SRC must be set.) Exit code 0 = pass.
"""
import json, subprocess, sys
import numpy as np

TOL_STATE_V = 1e-6      # raw ring voltage
TOL_PROBA = 1e-6


def _predict_json(pkg_path, pts, workers):
    from kring import KRingModel
    p = KRingModel.load(pkg_path).predict(np.array(pts), workers=workers)
    return dict(label=p.label.tolist(), status=p.status,
                proba=np.nan_to_num(p.proba, nan=-1).tolist(),
                state=np.nan_to_num(p.state, nan=-1).tolist())


def make(pkg_path, ref_path, pts_path, n=6):
    pts = np.load(pts_path)[: int(n)].tolist()
    out = _predict_json(pkg_path, pts, 1)
    out["points"] = pts
    json.dump(out, open(ref_path, "w"), indent=1)
    print("reference written:", ref_path, "statuses:", sorted(set(out["status"])))


def check(pkg_path, ref_path):
    ref = json.load(open(ref_path))
    bad_inputs = [[float("nan"), 0.0], [float("inf"), 1.0], [0.0, 0.0, 0.0]]
    errs = []
    for workers in (1, 2):
        proc = subprocess.run([sys.executable, "-m", "kring.tools.release_test", "_child",
                               pkg_path, json.dumps(ref["points"]), str(workers)],
                              capture_output=True, text=True, cwd=_root())
        if proc.returncode != 0:
            errs.append(f"child failed (workers={workers}): {proc.stderr[-300:]}"); continue
        got = json.loads(proc.stdout.strip().splitlines()[-1])
        if got["status"] != ref["status"]:
            errs.append(f"workers={workers}: status {got['status']} != {ref['status']}")
        if got["label"] != ref["label"]:
            errs.append(f"workers={workers}: labels differ")
        ds = np.max(np.abs(np.array(got["state"]) - np.array(ref["state"])))
        dp = np.max(np.abs(np.array(got["proba"]) - np.array(ref["proba"])))
        print(f"workers={workers}: max|dstate|={ds:.2e} V (tol {TOL_STATE_V:.0e}), max|dproba|={dp:.2e} (tol {TOL_PROBA:.0e})")
        if ds > TOL_STATE_V or dp > TOL_PROBA:
            errs.append(f"workers={workers}: tolerance exceeded")
    # invalid inputs must fail explicitly, never produce a class
    from kring import KRingModel
    pr = KRingModel.load(pkg_path).predict(np.array(bad_inputs[:2]))
    if pr.status != ["invalid_input"] * 2 or (pr.label != -1).any():
        errs.append(f"invalid inputs not rejected: {pr.status}")
    pr = KRingModel.load(pkg_path)._predict_one(np.array(bad_inputs[2]))
    if pr["status"] != "invalid_input":
        errs.append("wrong-length input not rejected")
    print("RELEASE TEST", "FAILED: " + "; ".join(errs) if errs else "PASSED")
    return 1 if errs else 0


def _root():
    import os
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "make":
        make(*sys.argv[2:])
    elif c == "check":
        sys.exit(check(*sys.argv[2:4]))
    elif c == "_child":
        sys.path.insert(0, _root())
        print(json.dumps(_predict_json(sys.argv[2], json.loads(sys.argv[3]), int(sys.argv[4]))))
