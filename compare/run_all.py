"""
run_all.py -- drive the whole comparison for one or more datasets.

Order matters and is enforced here, because two of the steps are prerequisites
that fail quietly rather than loudly if skipped:

  1. gates          nothing downstream means anything until these pass
  2. cell library   digital_mlp.py refuses to run without it (deliberately --
                    there is no fallback to literature constants)
  3. xbar_spec      Rf, rd and vref are per layer and must be SOLVED. Running
                    the trainer on the scalar defaults produces a circuit whose
                    amplifiers are starved and whose class scores are 46 mV of
                    offset; it still trains, and the number it produces is
                    meaningless.
  4. train arms
  5. measure        hardware metrics, no retraining
  6. table

Each step is skipped if its output already exists, so a re-run only does the
missing work. Use --force to redo everything.

Concurrency note: every netlist writer here takes its scratch file from
simulator_api.scratch(), which puts the pid in the name. Sharing one scratch
file between concurrent workers silently corrupted two result sets earlier in
this project -- nothing errored, the symptom was a log with elapsed times
running backwards -- so if you add a step, use scratch() and pass a distinct
--tag.
"""

import argparse
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")
PY = sys.executable


def run(cmd, cwd=BASE, label=None):
    label = label or " ".join(cmd[1:3])
    print(f"\n{'=' * 72}\n>>> {label}\n{'=' * 72}")
    t0 = time.perf_counter()
    r = subprocess.run([PY] + cmd, cwd=cwd)
    dt = (time.perf_counter() - t0) / 60
    print(f"--- {label}: exit {r.returncode}  [{dt:.1f} min]")
    return r.returncode == 0


def have(path):
    return os.path.exists(os.path.join(RESULTS, path))


def gates(a):
    ok = True
    ok &= run(["verify_metrics.py"], label="Gate C -- energy primitives")
    ok &= run(["verify_xbar.py"], label="Gate A -- crossbar closed form")
    ok &= run(["xbar_train.py", "--check-grad"],
              label="Gate B -- adjoint vs finite differences")
    ok &= run(["digital_cell.py", "--gate"],
              label="Gate D -- digital switching energy")
    if not ok:
        print("\nA GATE FAILED. Stop here: every number downstream of a failed "
              "gate is unsafe to report.")
    return ok


def one_dataset(a, ds, hidden, n_tr, n_te):
    base = ["--dataset", ds, "--n-train", str(n_tr), "--n-test", str(n_te)]

    if a.force or not have(f"xbar_spec_{ds}.json"):
        run(["xbar_spec.py"] + base + ["--hidden", str(hidden), "--save",
                                       "--iters", str(a.spec_iters)],
            label=f"{ds}: solve crossbar operating point")

    if a.force or not have(f"xbar_exsitu_{ds}_{a.tag}.json"):
        run(["xbar_train.py", "--mode", "exsitu"] + base +
            ["--hidden", str(hidden), "--tag", a.tag],
            label=f"{ds}: crossbar ex-situ")

    if a.insitu and (a.force or not have(f"xbar_insitu_{ds}_{a.tag}.json")):
        run(["xbar_train.py", "--mode", "insitu"] + base +
            ["--hidden", str(hidden), "--tag", a.tag,
             "--epochs", str(a.epochs), "--workers", str(a.workers)],
            label=f"{ds}: crossbar in-situ")

    if a.force or not have(f"dmlp_{ds}_{a.tag}.json"):
        run(["digital_mlp.py"] + base + ["--hidden", str(hidden),
                                         "--tag", a.tag],
            label=f"{ds}: digital MLP")

    for arm in ("kfq", "xbar"):
        if a.force or not have(f"hw_{arm}_{ds}_sweep.json"):
            run(["measure_existing.py", "--arm", arm, "--dataset", ds,
                 "--sweep", "--tag", "sweep"],
                label=f"{ds}: hardware metrics, {arm}")

    run(["run_bench.py"] + base + ["--tag", a.tag],
        label=f"{ds}: comparison table")


# Topologies match the ones kfabric already trained, so the KFQ row comes from
# a real checkpoint rather than a re-run.
SPECS = {
    "iris":     dict(hidden=7, n_train=90,  n_test=60),
    "circle":   dict(hidden=8, n_train=300, n_test=300),
    "twomoon":  dict(hidden=8, n_train=300, n_test=300),
    "2spirals": dict(hidden=8, n_train=300, n_test=300),
}


def main(a):
    os.makedirs(RESULTS, exist_ok=True)

    if not a.no_gates and not gates(a):
        return 1

    if a.force or not have("digital_cell_char.json"):
        run(["digital_cell.py"], label="characterise the digital cell library")

    for ds in a.datasets:
        spec = SPECS.get(ds, dict(hidden=8, n_train=300, n_test=300))
        one_dataset(a, ds, spec["hidden"], spec["n_train"], spec["n_test"])

    print(f"\n{'=' * 72}\nall done. Tables in {RESULTS}/bench_*.json")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", nargs="+", default=["iris"])
    ap.add_argument("--tag", default="run")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--spec-iters", type=int, default=12)
    ap.add_argument("--insitu", action="store_true",
                    help="also run the in-situ crossbar arm (slow)")
    ap.add_argument("--no-gates", action="store_true")
    ap.add_argument("--force", action="store_true")
    sys.exit(main(ap.parse_args()))
