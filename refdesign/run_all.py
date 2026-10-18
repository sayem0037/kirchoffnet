"""
run_all.py -- verification, both arms, all datasets, then the figures.

Order is enforced because the verification steps are cheap and everything downstream of
a failed one is unsafe to report. Each training step is skipped if its log already
exists, so a re-run only does the missing work; --force redoes everything.

The crossbar is the cost driver: in-situ training is a circuit solve per sample per
epoch plus the evaluation pass, about 0.75 min/epoch at 120 train / 120 test on 8
workers. The digital arm trains in seconds, because only its VERIFICATION touches the
simulator -- that is the architecture, not a shortcut.
"""

import argparse
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
PY = sys.executable


def run(cmd, label):
    print()
    print("=" * 72)
    print(f">>> {label}")
    print("=" * 72)
    t0 = time.perf_counter()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([PY] + cmd, cwd=BASE, env=env)
    print(f"--- {label}: exit {r.returncode}  "
          f"[{(time.perf_counter()-t0)/60:.1f} min]")
    return r.returncode == 0


def have(name):
    return os.path.exists(os.path.join(RESULTS, name))


def main(a):
    os.makedirs(RESULTS, exist_ok=True)

    if not a.no_verify:
        ok = run(["verify_xbar1t1r.py"], "V1/V2/V4 -- crossbar architecture")
        ok &= run(["digital_verify.py"], "V3 -- gate-level logic + DC ceiling")
        if not ok:
            print()
            print("A VERIFICATION FAILED. Everything downstream is unsafe to report.")
            return 1

    for ds in a.datasets:
        if a.force or not have(f"xbar_{ds}_{a.tag}_log.csv"):
            run(["xbar1t1r_train.py", "--dataset", ds, "--tag", a.tag,
                 "--epochs", str(a.xbar_epochs),
                 "--n-train", str(a.n_train), "--n-test", str(a.n_test),
                 "--hidden", str(a.hidden), "--workers", str(a.workers)],
                f"{ds}: 1T1R crossbar, in-situ Manhattan")

        if a.force or not have(f"digital_{ds}_{a.tag}_log.csv"):
            run(["digital_train.py", "--dataset", ds, "--tag", a.tag,
                 "--epochs", str(a.digital_epochs),
                 "--n-train", str(a.n_train), "--n-test", str(a.n_test),
                 "--hidden", str(a.hidden), "--bits", str(a.bits)],
                f"{ds}: fixed-point MLP, quantization-aware")

    run(["make_plots.py", "--datasets"] + list(a.datasets) + ["--tag", a.tag],
        "figures: accuracy vs epoch, weight convergence")

    print()
    print(f"done. logs in {RESULTS}, figures in {os.path.join(BASE, 'figs')}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+",
                    default=["twomoon", "circle", "2spirals"])
    ap.add_argument("--tag", default="run")
    ap.add_argument("--hidden", type=int, default=8)
    ap.add_argument("--n-train", type=int, default=120)
    ap.add_argument("--n-test", type=int, default=120)
    ap.add_argument("--bits", type=int, default=8)
    ap.add_argument("--xbar-epochs", type=int, default=50)
    ap.add_argument("--digital-epochs", type=int, default=60)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--force", action="store_true")
    sys.exit(main(ap.parse_args()))
