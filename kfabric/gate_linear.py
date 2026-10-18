"""
gate_linear.py -- GATE A. Test the claim that the KRC is a LINEAR network.

Two independent measurements on the EXISTING trained KRC checkpoints, because the
diagnosis has two separable parts and both should be confirmed on their own:

  A1. IS THE CORE AFFINE?
      Fit an ordinary least-squares map  features ~= A.x + b  from the raw input
      to the circuit's own state trajectory, and report held-out R^2. If the core
      applied a real nonlinearity, a linear model could not reproduce its output.
      R^2 ~ 1 means the circuit is doing nothing a single matrix could not do,
      which is exactly what "no activation stage" predicts:

          v_{t+1} ~= W.[v_t ; x_t]      (theta-gated NMOS edges in triode)

      and a composition of affine maps is affine, so T invocations do not help.

  A2. IS THE READ-OUT ALSO THROWING INFORMATION AWAY?
      Compare, on identical splits:
        - logistic regression on the RAW input               (the baseline to beat)
        - logistic regression on the full M x T trajectory   (all the circuit knows)
        - what the shipped fixed-diagonal read-out actually scored
      If the trajectory scores far above the shipped number, the read-out was
      discarding usable information as well. That is a second, independent fault.

A1 and A2 together decide the plan: A1 says whether the ARC rebuild (adding the
diff-amp activation) is necessary, A2 says whether the read-out change is
sufficient on its own. They are not the same question.

Usage:
    python gate_linear.py                  # all available checkpoints
    python gate_linear.py --only mnist_mean
"""
import argparse
import json
import os

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import r2_score

import recurrent
from core_spec import CoreSpec
from recurrent import forward_batch

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")

# (tag, dataset, how the checkpoint was produced)
RUNS = [
    ("mnist_mean", "mnist", "kfabric MNIST 8x8, M=12, T=8, E=240"),
    ("twomoon", "twomoon", "kfabric toy, M=8, T=4, E=80"),
    ("circle", "circle", "kfabric toy, M=8, T=4, E=80"),
    ("2spirals", "2spirals", "kfabric toy, M=8, T=4, E=80"),
]


def _load_ckpt(tag):
    for suffix in ("_any_best.json", "_krc_best.json"):
        p = os.path.join(RESULTS, tag + suffix)
        if os.path.exists(p):
            return json.load(open(p)), suffix
    return None, None


def _streams(dataset, ck, suffix):
    """Rebuild the exact stream the checkpoint was trained on."""
    from datasets_any import load_any, to_stream, default_mode
    if suffix == "_any_best.json":
        Xtr, ytr, Xte, yte, C, spatial = load_any(dataset)
        mode = ck.get("mode") or default_mode(spatial, np.asarray(Xtr).reshape(len(Xtr), -1))
        T = ck["T"]
        Str, lo, hi = to_stream(Xtr, spatial, mode=mode, T=T, k=ck["k_data"])
        Ste, _, _ = to_stream(Xte, spatial, mode=mode, T=T, k=ck["k_data"], lo=lo, hi=hi)
    else:
        from mnist_stream import load_mnist_stream
        Xtr, ytr, Xte, yte = load_mnist_stream(
            side=ck.get("side", 8), n_train=ck.get("n_train", 150),
            n_test=ck.get("n_test", 60), seed=ck.get("seed", 0))
        Str, Ste, C = Xtr, Xte, ck["n_classes"]
        Xtr = Xtr.reshape(len(Xtr), -1)
        Xte = Xte.reshape(len(Xte), -1)
    return (np.asarray(Xtr).reshape(len(Xtr), -1), ytr,
            np.asarray(Xte).reshape(len(Xte), -1), yte, Str, Ste, C)


def _traj(spec, theta, S, nl):
    V, _, valid = forward_batch(spec, theta, S, nl, with_grad=False,
                                trajectories=True)
    return V.reshape(len(valid), -1), valid       # (n, T*M)


def analyse(tag, dataset, note):
    ck, suffix = _load_ckpt(tag)
    if ck is None:
        print(f"  (no checkpoint for {tag})")
        return None

    recurrent.READOUT = ck.get("readout", "last")
    M, k, T, C = ck["m_state"], ck["k_data"], ck["T"], ck["n_classes"]
    spec = CoreSpec((k,), C, m_state=M, k_data=k, name=dataset)
    spec.T = T
    theta = np.array(ck["theta"])
    nl = os.path.join(BASE, f"tmp_gateA_{tag}.sp")

    Xtr, ytr, Xte, yte, Str, Ste, C = _streams(dataset, ck, suffix)
    Ftr, vtr = _traj(spec, theta, Str, nl)
    Fte, vte = _traj(spec, theta, Ste, nl)
    Xtr, ytr = Xtr[vtr], ytr[vtr]
    Xte, yte = Xte[vte], yte[vte]

    # --- A1: can one matrix reproduce the whole circuit? ---
    lin = LinearRegression().fit(Xtr, Ftr)
    r2 = r2_score(Fte, lin.predict(Xte), multioutput="variance_weighted")

    # --- A2: how much does the read-out discard? ---
    def logi(A, B):
        m = LogisticRegression(max_iter=4000, C=1.0)
        m.fit(A, ytr)
        return float(m.score(B, yte))

    acc_raw = logi(Xtr, Xte)
    mu, sd = Ftr.mean(0), Ftr.std(0) + 1e-9
    acc_feat = logi((Ftr - mu) / sd, (Fte - mu) / sd)
    shipped = ck["test_acc"]

    print(f"\n{tag}  ({note})")
    print(f"  {'affine R^2 of the circuit (held-out)':<44} {r2:>8.4f}")
    print(f"  {'shipped fixed-diagonal read-out':<44} {shipped:>8.3f}")
    print(f"  {'logistic on raw input':<44} {acc_raw:>8.3f}")
    print(f"  {'logistic on full M x T trajectory':<44} {acc_feat:>8.3f}")
    print(f"  {'features seen by read-out -> available':<44} "
          f"{C:>4} -> {Ftr.shape[1]:<4}")
    if os.path.exists(nl):
        os.remove(nl)
    return dict(tag=tag, r2=r2, shipped=shipped, raw=acc_raw, feat=acc_feat,
                n_feat=Ftr.shape[1], C=C)


def main(only):
    print("GATE A -- is the Kirchhoff Recurrent Core a linear network?\n")
    print("A1: affine R^2 near 1.0 means one matrix reproduces the whole circuit,")
    print("    i.e. there is no activation stage and depth in T buys nothing.")
    print("A2: trajectory accuracy far above the shipped number means the")
    print("    fixed diagonal read-out was discarding usable information too.")
    rows = [r for r in (analyse(t, d, n) for t, d, n in RUNS
                        if only is None or t == only) if r]
    if not rows:
        return

    print("\n" + "=" * 64)
    print("VERDICT")
    mean_r2 = float(np.mean([r["r2"] for r in rows]))
    if mean_r2 > 0.95:
        print(f"  A1 CONFIRMED (mean affine R^2 = {mean_r2:.4f}).")
        print("     The core is affine. Adding the diff-amp activation is")
        print("     NECESSARY -- no read-out or tuning change can fix this.")
    elif mean_r2 > 0.80:
        print(f"  A1 PARTIAL (mean affine R^2 = {mean_r2:.4f}). Mostly linear,")
        print("     with some nonlinearity present. Activation still indicated.")
    else:
        print(f"  A1 REJECTED (mean affine R^2 = {mean_r2:.4f}). The core is")
        print("     genuinely nonlinear; the plan's premise is wrong and the")
        print("     bottleneck must be found elsewhere before building the ARC.")

    gain = [r["feat"] - r["shipped"] for r in rows]
    print(f"\n  A2: trajectory read-out beats the shipped read-out by "
          f"{np.mean(gain):+.3f} on average")
    beats_raw = [r["feat"] - r["raw"] for r in rows]
    print(f"      and the raw input by {np.mean(beats_raw):+.3f}.")
    if np.mean(beats_raw) < 0:
        print("      NOTE: the circuit's features are WORSE than the raw input.")
        print("      A linear map cannot add information -- consistent with A1.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    main(ap.parse_args().only)
