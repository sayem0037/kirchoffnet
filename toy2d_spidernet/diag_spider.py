"""
diag_spider.py -- GATE CHECK for the spidernet crossbar (does it add separating
power?), run BEFORE any adjoint training.

Pushes each dataset through the UNTRAINED crossbar (encoded rails in, read
net1..net_n at 100ns) and compares the linear separability of the state vector
to the raw 2-D feature ceiling.

On top of the ring's gate check, this adds three degeneracy probes that this
particular topology needs:

  clipped  -- fraction of rail voltages pinned at the VLO/VHI clip. High values
              mean the encoder swing overshoots the safe window and data is
              being thrown away before it reaches the circuit.
  nodestd  -- spread ACROSS nodes for a fixed sample. Near zero means the thetas
              are too uniform and all nodes solve the same current balance
              (rank-1 read vector, nothing for the readout to separate).
  maxcorr  -- largest off-diagonal |correlation| between read features. Note a
              structurally high floor here: solving the Level-1 triode balance
              gives net_j = (A_j - sqrt(A_j^2 + 4Q - 8B_j))/4 with
              Q = sum_i v_i^2 SHARED by every node, so the features are
              inherently correlated. Treat this as diagnostic, not pass/fail.

Usage:
  python diag_spider.py --dataset twomoon
  python diag_spider.py --sweep            # grid over encoder/theta constants
"""
import os, argparse
import numpy as np
from sklearn.linear_model import LogisticRegression

from netlist_spider import write_spider_netlist
from simulator_api import eval_chain
from dataset import load_dataset, DATASETS
import spider_common as sc

BASE = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(BASE, "tmp_diagspider.sp")


def states(X, W, b, circ, center=None, swing=None):
    """Forward-only sweep. Returns (S, valid_idx, clipped_fraction)."""
    S, valid, nclip, ntot = [], [], 0, 0
    for i in range(len(X)):
        rails = sc.encode_rails(X[i], W, b) if center is None else \
            _encode(X[i], W, b, center)
        for v in rails.values():
            ntot += 1
            if v <= sc.VLO + 1e-9 or v >= sc.VHI - 1e-9:
                nclip += 1
        write_spider_netlist(sc.circ_dict(circ), rails, NETLIST,
                             n_rails=sc.N_RAILS, n_nodes=sc.N_NODES,
                             ic_center=sc.RAIL_CENTER)
        try:
            v = eval_chain(NETLIST, sc.READ)
            S.append([v[n] for n in sc.READ]); valid.append(i)
        except Exception:
            continue
    S = np.array(S) if S else np.zeros((0, len(sc.READ)))
    return S, np.array(valid, dtype=int), (nclip / max(ntot, 1))


def _encode(x, W, b, center):
    v = np.clip(center + W @ np.asarray(x, float) + b, sc.VLO, sc.VHI)
    return {f"VR{i+1}": float(v[i]) for i in range(sc.N_RAILS)}


def _corr(S):
    Sn = (S - S.mean(0)) / (S.std(0) + 1e-12)
    C = np.corrcoef(Sn.T)
    return float(np.abs(C - np.eye(C.shape[0])).max())


def main(name):
    Xtr, ytr, Xte, yte = load_dataset(name)
    W, b = sc.init_rail_encoder(seed=0)
    circ = sc.circ_init(seed=0)
    print(f"=== {name} | spidernet {sc.N_RAILS} rails x {sc.N_NODES} nodes "
          f"| {sc.N_EDGES} theta edges | read @100ns ===")

    Str, vtr, clip_tr = states(Xtr, W, b, circ)
    Ste, vte, _ = states(Xte, W, b, circ)
    print(f"convergence failures: train {len(Xtr)-len(vtr)}/{len(Xtr)}, "
          f"test {len(Xte)-len(vte)}/{len(Xte)}")

    if len(vtr) == 0:
        print("ABORT: the untrained circuit solved no train sample.")
        return

    raw = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
    st = LogisticRegression(max_iter=5000).fit(Str, ytr[vtr])
    acc_raw_tr, acc_raw_te = raw.score(Xtr, ytr), raw.score(Xte, yte)
    acc_st_tr = st.score(Str, ytr[vtr])
    acc_st_te = st.score(Ste, yte[vte]) if len(vte) else float("nan")

    print("\n=== degeneracy probes ===")
    print(f"  clipped rails      : {clip_tr:.1%} "
          f"{'  <-- HIGH, encoder overshoots the window' if clip_tr > 0.15 else ''}")
    print(f"  across-node std    : {Str.std(1).mean():.4e} "
          f"{'  <-- DEGENERATE' if Str.std(1).mean() < 1e-4 else ''}")
    print(f"  per-node std (data): {np.round(Str.std(0), 5)}")
    print(f"  max |corr| between features: {_corr(Str):.4f}")

    print("\n=== GATE (untrained spidernet) ===")
    print(f"  raw features   : train {acc_raw_tr:.2f}  test {acc_raw_te:.2f}")
    print(f"  spider STATE   : train {acc_st_tr:.2f}  test {acc_st_te:.2f}")
    gain = acc_st_tr - acc_raw_tr
    verdict = "GO -- crossbar helps" if gain > 0.03 else \
        ("MARGINAL -- little added power" if gain > -0.02 else "NO-GO -- state is worse than raw")
    print(f"  --> crossbar adds {gain:+.2f} separability on train ({verdict})")


def sweep():
    """Grid over the encoder/theta constants; prints the gate metrics for each."""
    print(f"{'mode':>7} {'center':>7} {'swing':>6} {'offs':>5} {'th_mu':>6} "
          f"{'th_sd':>6} | {'clip':>6} {'nodestd':>9} {'maxcorr':>8} | "
          f"{'moon':>6} {'circ':>6} {'spir':>6}")
    print("-" * 96)
    data = {n: load_dataset(n) for n in DATASETS}
    for mode in ("frame", "random"):
      for center in (0.9, 1.0):
        for swing, offset in ((0.22, 0.10), (0.30, 0.12), (0.40, 0.15)):
            for th_mu, th_sd in ((2.4, 0.6), (2.6, 0.45)):
                rng = np.random.default_rng(0)
                W, b = sc.init_rail_encoder(seed=0, swing=swing,
                                            offset=offset, mode=mode)
                circ = np.clip(th_mu + th_sd * rng.standard_normal(sc.N_EDGES),
                               1.9, 3.3)
                accs, clip, nstd, mcorr = [], 0.0, 0.0, 0.0
                for n in DATASETS:
                    Xtr, ytr, _, _ = data[n]
                    S, v, c = states(Xtr, W, b, circ, center=center)
                    if len(v) < 5:
                        accs.append(float("nan")); continue
                    lr = LogisticRegression(max_iter=5000).fit(S, ytr[v])
                    accs.append(lr.score(S, ytr[v]))
                    clip, nstd, mcorr = c, S.std(1).mean(), _corr(S)
                print(f"{mode:>7} {center:>7.2f} {swing:>6.2f} {offset:>5.2f} "
                      f"{th_mu:>6.2f} {th_sd:>6.2f} | {clip:>6.1%} {nstd:>9.2e} "
                      f"{mcorr:>8.4f} | "
                      + " ".join(f"{a:>6.2f}" for a in accs))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()
    sweep() if a.sweep else main(a.dataset)
