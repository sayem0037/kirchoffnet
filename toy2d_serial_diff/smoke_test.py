"""Smoke test: does the closed 10-stage ring converge and give non-zero
VTH/VB/VN sensitivities at 100 ns? Run from inside toy2d_serial_diff/."""
import os
import numpy as np
from netlist_ring import write_ring_netlist
from simulator_api import run_chain, eval_chain
from ring_common import N_STAGES, CIRC_NAMES, READ, circ_dict, circ_init, init_seed_encoder, encode_ic

NETLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_smoke.sp")

W, b = init_seed_encoder(seed=0)
circ = circ_init()
x = np.array([0.8, -1.2])           # one arbitrary standardized-ish point
seeds = encode_ic(x, W, b)

print("IC seeds:", {k: round(v, 3) for k, v in seeds.items()})
write_ring_netlist(circ_dict(circ), seeds, NETLIST, n_stages=N_STAGES)

# 1) forward: do all 10 nodes converge to finite values at 100 ns?
try:
    v = eval_chain(NETLIST, READ)
    vals = np.array([v[n] for n in READ])
    print("\nforward V(h_j,100ns):", np.round(vals, 4))
    print("all finite:", bool(np.all(np.isfinite(vals))),
          "| spread (max-min):", round(float(vals.max() - vals.min()), 4))
except Exception as e:
    print("FORWARD FAILED:", repr(e)); raise

# 2) adjoint: are the VTH/VB/VN sensitivities non-zero (ring not latched/dead)?
v_out, sens = run_chain(NETLIST, READ, CIRC_NAMES)
S = np.array([[sens[nd][p] for p in CIRC_NAMES] for nd in READ])  # (10 nodes, 30 params)
print("\nsensitivity block shape:", S.shape)
print("non-zero sensitivities:", int(np.count_nonzero(S)), "/", S.size)
print("max |dV/dparam|:", float(np.max(np.abs(S))))
print("per-family max |sens|: VTH=%.3e VB=%.3e VN=%.3e" % (
    np.max(np.abs(S[:, 0:N_STAGES])),
    np.max(np.abs(S[:, N_STAGES:2*N_STAGES])),
    np.max(np.abs(S[:, 2*N_STAGES:3*N_STAGES]))))

ok = np.all(np.isfinite(vals)) and np.max(np.abs(S)) > 1e-9
print("\nSMOKE TEST:", "PASS" if ok else "FAIL (latched/dead or non-convergent)")
