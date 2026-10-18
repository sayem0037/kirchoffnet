"""Shared config + basic .IC seed-encoder for the CLOSED-LOOP diff-amp ring.

Trainable CIRCUIT params per stage = 3 (VTH_j PMOS theta, VB_j tail bias, VN_j
per-stage reference) -> 3*N total, all trained via the 100 ns transient adjoint.

Data manipulation is intentionally VERY BASIC:
  before hardware : a fixed linear map turns the 2 features into N .IC seed
                    voltages (encode_ic), centered at mid-swing and clipped to a
                    safe voltage window.
  after hardware  : standardize the N read voltages, then a linear softmax readout
                    (done in train_ring.py).
"""
import numpy as np
from netlist_ring import theta_names, vbias_names, ref_names, ring_nodes

N_STAGES = 10
# order matters: circ vectors + BOUNDS follow this concatenation exactly
CIRC_NAMES = theta_names(N_STAGES) + vbias_names(N_STAGES) + ref_names(N_STAGES)
READ = ring_nodes(N_STAGES)
BOUNDS = ([(0.0, 3.0)]  * N_STAGES    # VTH (PMOS theta)
          + [(0.72, 1.10)] * N_STAGES  # VB  (tail bias)
          + [(0.60, 1.40)] * N_STAGES) # VN  (per-stage reference / threshold)

VLO, VHI = 0.3, 3.0
IC_CENTER = 1.65   # mid-supply neutral seed


def init_seed_encoder(seed=0, swing=0.6, offset=0.3):
    """Basic fixed linear map: each of the N ring nodes gets its own linear
    projection of (x0,x1) plus an offset, so every .IC seed encodes the point
    differently. Fixed (not trained)."""
    rng = np.random.default_rng(seed)
    W = swing * rng.standard_normal((N_STAGES, 2))
    b = offset * rng.standard_normal(N_STAGES)
    return W, b


def encode_ic(x, W, b):
    """(x0,x1) -> {h_j: clip(IC_CENTER + W[j].x + b[j], VLO, VHI)}  (the .IC seeds)."""
    v = np.clip(IC_CENTER + W @ np.asarray(x, float) + b, VLO, VHI)
    return {f"h{j+1}": float(v[j]) for j in range(N_STAGES)}


def circ_dict(vec):
    return {n: float(vec[k]) for k, n in enumerate(CIRC_NAMES)}


def circ_init():
    # VTH=1.7 (PMOS load), VB=0.8 (tail), VN=1.0 (neutral reference) per stage.
    # Device sizes match testfiles/kirr.txt; adjust here if the ring latches.
    return np.array([1.7] * N_STAGES + [0.8] * N_STAGES + [1.0] * N_STAGES, dtype=float)
