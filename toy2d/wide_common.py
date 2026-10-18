"""Shared config + random-diverse encoder for the WIDE parallel layer.

Trainable CIRCUIT params per unit = 3 (VTH_j PMOS theta, VB_j tail bias,
VN_j per-unit reference/threshold) -> 3*N total, all trained via the 100ns
backward adjoint. The reference VN_j is now a hardware source (not a software
layer), so the thresholding/diversity lives in the circuit.
"""
import numpy as np
from netlist_wide import theta_names, vbias_names, ref_names, input_names, unit_nodes

N_UNITS = 24
# order matters: circ vectors + BOUNDS follow this concatenation exactly
CIRC_NAMES = theta_names(N_UNITS) + vbias_names(N_UNITS) + ref_names(N_UNITS)
INPUT_SRCS = input_names(N_UNITS)
READ = unit_nodes(N_UNITS)
BOUNDS = ([(0.0, 3.0)]  * N_UNITS    # VTH (PMOS theta)
          + [(0.72, 1.10)] * N_UNITS  # VB  (tail bias)
          + [(0.60, 1.40)] * N_UNITS) # VN  (per-unit reference / threshold)
VLO, VHI = 0.3, 3.0


def init_encoder(seed=0, swing=0.7, offset=0.6):
    """Random-DIVERSE encoder: each unit gets a different linear projection of
    (x0,x1) plus its own offset (so units threshold at different places)."""
    rng = np.random.default_rng(seed)
    W = swing * rng.standard_normal((N_UNITS, 2))
    b = offset * rng.standard_normal(N_UNITS)
    return W, b


def encode_wide(x, W, b):
    """(x0,x1) -> {VINj: clip(1.0 + W[j].x + b[j], VLO, VHI)}."""
    v = np.clip(1.0 + W @ np.asarray(x, float) + b, VLO, VHI)
    return {f"VIN{j+1}": float(v[j]) for j in range(N_UNITS)}


def circ_dict(vec):
    return {n: float(vec[k]) for k, n in enumerate(CIRC_NAMES)}


def circ_init():
    # VTH=1.7 (PMOS load), VB=0.8 (tail), VN=1.0 (neutral reference) per unit
    return np.array([1.7] * N_UNITS + [0.8] * N_UNITS + [1.0] * N_UNITS, dtype=float)
