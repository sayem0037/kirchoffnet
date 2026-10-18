"""Shared config + the fixed rail encoder for the SPIDERNET crossbar.

Trainable CIRCUIT params = one theta per crossbar edge (n_rails * n_nodes),
all trained via the 100 ns transient adjoint.

Data manipulation is intentionally VERY BASIC, mirroring toy2d_serial_diff:
  before hardware : a fixed linear map turns the 2 features into n_rails input
                    RAIL voltages (encode_rails), centered low and clipped to a
                    safe window.
  after hardware  : standardize the n_nodes read voltages, then a linear softmax
                    readout (done in train_spider.py).

OPERATING-POINT WINDOW -- these constants are not arbitrary. From
netlist_spider.py, every edge must satisfy both:
    (on)     theta_k > V(net_j) + VTO       else dId/dtheta is EXACTLY 0
    (triode) v_i     < theta_k - VTO        else the edge ignores its rail
With rails in ~[0.2, 2.0] centered at 1.0, V(net_j) lands near 1.0, so
theta > 1.55 keeps edges on (BOUNDS floor of 1.9 leaves margin) and rails stay
below theta - 0.55 >= 1.35 for the bulk of the distribution.

For reference, the schematic's own defaults (rails 2.5-3.1 V, thetas 1.0-2.4 V)
violate rule (on) for all 16 edges: every node sits at the rail mean and the
entire sensitivity matrix is zero.
"""
import numpy as np
from netlist_spider import theta_names, rail_names, state_nodes, VTO

N_RAILS = 4
N_NODES = 4
N_EDGES = N_RAILS * N_NODES

# order matters: circ vectors + BOUNDS follow this list exactly
CIRC_NAMES = theta_names(N_RAILS, N_NODES)   # VTH1..VTH16
RAILS = rail_names(N_RAILS)                  # VR1..VR4
READ = state_nodes(N_NODES)                  # net1..net4

BOUNDS = [(1.9, 3.3)] * N_EDGES

VLO, VHI = 0.2, 2.0      # rail clip window
RAIL_CENTER = 1.0        # rails sit low so edges stay in triode
RAIL_SWING = 0.30        # keeps ~96% of rails inside [VLO, VHI] unclipped
RAIL_OFFSET = 0.12
ENCODER_MODE = "frame"   # "frame" (isotropic tight frame) | "random"
THETA_MU, THETA_SD = 2.4, 0.6


def init_rail_encoder(seed=0, swing=RAIL_SWING, offset=RAIL_OFFSET,
                      mode=ENCODER_MODE):
    """Basic fixed linear map: each rail gets its own linear projection of
    (x0,x1) plus an offset, so every rail encodes the point differently.
    Fixed (not trained).

    mode="frame" (default) lays the rail directions on evenly spaced angles
    theta_i = i*pi/N_RAILS, giving a tight frame with W.T @ W = (swing^2 *
    N_RAILS/2) * I. This matters more than it looks. Expanding the closed-form
    node solution to first order,

        net_j ~= B_j/A_j - Q/(2 A_j),      Q = sum_i v_i^2 = ||W x + b||^2

    so a linear readout over the nodes is  linear(x) + kappa * Q(x): a QUADRATIC
    classifier whose quadratic shape is W.T @ W -- fixed by this encoder, NOT
    trainable. The thetas only tune kappa and the linear part. With a random W
    that shape is a lopsided ellipse; with the tight frame it is isotropic, so
    Q is proportional to ||x||^2 and concentric datasets become separable.

    mode="random" keeps the original i.i.d. gaussian map for comparison.
    """
    rng = np.random.default_rng(seed)
    if mode == "frame":
        ang = np.pi * np.arange(N_RAILS) / N_RAILS
        W = swing * np.stack([np.cos(ang), np.sin(ang)], axis=1)
    elif mode == "random":
        W = swing * rng.standard_normal((N_RAILS, 2))
    else:
        raise ValueError(f"unknown encoder mode {mode!r}")
    b = offset * rng.standard_normal(N_RAILS)
    return W, b


def encode_rails(x, W, b):
    """(x0,x1) -> {VR_i: clip(RAIL_CENTER + W[i].x + b[i], VLO, VHI)}."""
    v = np.clip(RAIL_CENTER + W @ np.asarray(x, float) + b, VLO, VHI)
    return {f"VR{i+1}": float(v[i]) for i in range(N_RAILS)}


def circ_dict(vec):
    return {n: float(vec[k]) for k, n in enumerate(CIRC_NAMES)}


def circ_init(seed=0):
    """Thetas jittered around THETA_MU.

    The jitter is REQUIRED, not cosmetic: with all thetas equal, every state
    node solves an identical current balance and returns an identical voltage,
    so the read vector is rank-1 and the readout has nothing to separate.
    """
    rng = np.random.default_rng(seed)
    th = THETA_MU + THETA_SD * rng.standard_normal(N_EDGES)
    lo = np.array([b[0] for b in BOUNDS])
    hi = np.array([b[1] for b in BOUNDS])
    return np.clip(th, lo, hi)
