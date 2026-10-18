"""
smoke_test.py -- one-shot check that the spidernet is alive and differentiable.

Runs a single encoded data point through the crossbar and prints the full
n_nodes x n_edges adjoint sensitivity matrix dV(net_j, 100ns)/dVTH_k.

What to look for:
  - every V(net_j) finite, and the nodes NOT all equal (else the thetas are too
    uniform -- circ_init jitter collapsed);
  - no ALL-ZERO theta column. A zero column means that edge is cut off
    (theta_k <= V(net_j) + VTO), which makes its gradient exactly zero and the
    parameter untrainable. This is the failure mode the schematic's own default
    values produce for all 16 edges.
  - the matrix should be BLOCK-DIAGONAL: net_j is only reachable from its own
    n_rails thetas, since the crossbar has no node-to-node coupling. So the
    expected nonzero count is n_rails*n_nodes, not n_nodes*n_edges.

Usage:  python smoke_test.py [--dataset twomoon]
"""
import argparse
import numpy as np

from netlist_spider import write_spider_netlist, theta_index
from simulator_api import run_chain
from dataset import load_dataset, DATASETS
from spider_common import (N_RAILS, N_NODES, N_EDGES, CIRC_NAMES, READ,
                           init_rail_encoder, encode_rails, circ_dict, circ_init)


def main(name):
    Xtr, ytr, _, _ = load_dataset(name)
    W, b = init_rail_encoder(seed=0)
    circ = circ_init(seed=0)
    rails = encode_rails(Xtr[0], W, b)

    netlist = "tmp_smoke.sp"
    write_spider_netlist(circ_dict(circ), rails, netlist,
                         n_rails=N_RAILS, n_nodes=N_NODES)
    v_out, sens = run_chain(netlist, READ, CIRC_NAMES)

    print(f"spidernet smoke test | {name} | sample 0 (label {int(ytr[0])})")
    print(f"  {N_RAILS} rails x {N_NODES} nodes = {N_EDGES} edges\n")
    print("  rails :", {k: round(v, 4) for k, v in rails.items()})
    print("  thetas:", np.round(circ, 3), "\n")

    S = np.array([[sens[nd][p] for p in CIRC_NAMES] for nd in READ])
    v = np.array([v_out[nd] for nd in READ])

    print("  V(net_j, 100ns):", np.round(v, 5))
    print(f"  across-node std : {v.std():.4e}"
          f"   {'OK' if v.std() > 1e-4 else 'DEGENERATE -- nodes collapsed'}\n")

    print("  dV(net_j,100ns)/dVTH_k:")
    hdr = "        " + "".join(f"{k+1:>9d}" for k in range(N_EDGES))
    print(hdr)
    for a, nd in enumerate(READ):
        print(f"  {nd:>5} " + "".join(f"{S[a, k]:>9.2e}" for k in range(N_EDGES)))

    dead = [CIRC_NAMES[k] for k in range(N_EDGES) if not np.any(S[:, k])]
    finite = np.all(np.isfinite(S)) and np.all(np.isfinite(v))
    expect_nz = N_RAILS * N_NODES

    print(f"\n  finite            : {finite}")
    print(f"  nonzero entries   : {int((S != 0).sum())}/{S.size} "
          f"(block-diagonal expects {expect_nz})")
    print(f"  |dV/dtheta| max   : {np.abs(S).max():.3e}")
    if dead:
        print(f"  DEAD (zero-gradient) thetas: {dead}")
        print("  -> those edges are cut off; raise THETA_MU or the BOUNDS floor "
              "in spider_common.py")
    else:
        print("  dead thetas       : none -- all edges differentiable")

    # sanity: each node should be driven only by its own rail block
    ok_block = True
    for j in range(1, N_NODES + 1):
        own = {theta_index(i, j, N_RAILS) - 1 for i in range(1, N_RAILS + 1)}
        for k in range(N_EDGES):
            if k not in own and S[j - 1, k] != 0.0:
                ok_block = False
    print(f"  block-diagonal    : {ok_block}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="twomoon", choices=DATASETS)
    main(ap.parse_args().dataset)
