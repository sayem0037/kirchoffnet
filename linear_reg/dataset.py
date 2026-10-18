"""
dataset.py  —  Binary threshold dataset tuned to circuit physics.

At tstop=100ns only Block D's params (V2, VB4) have non-zero adjoint sensitivity.
Block D compares IC(net3) vs VN=1.0V through a differential pair whose linear
active range is VN ± 0.22V = [0.78, 1.22V].

  IC(net3) < VN  →  net4 → HIGH (3.3V)
  IC(net3) > VN  →  net4 → LOW  (~0.4V)

To shift the threshold from VN=1.0V to 1.2V (boundary below 1.22V active limit):
  V2 needs to decrease ~0.023V (from 1.7V to 1.677V) so PMOS supplies enough
  current to keep IC(net3)=1.1V in the HIGH state.

Dataset (10 samples, boundary at 1.2V):
  IC(net3) in [0.3, 1.1] → class 1 (target 3.3V)   [5 samples]
  IC(net3) in [1.3, 3.0] → class 0 (target 0.3V)   [5 samples]

  Sample at IC(net3)=1.1V is initially WRONG at VN=1.0V threshold:
    circuit → LOW (1.1 > 1.0) but target = HIGH (1.1 < 1.2 boundary)
  After training V2 decreases ~0.023V → threshold shifts to 1.2V → all correct.

  Other 3 ICs fixed at VN=1.0V (balanced) so Block D is the sole latch arbiter.
"""

import numpy as np

Y_LOW  = 0.3   # class 0 target (circuit LOW attractor ≈ 0.4V)
Y_HIGH = 3.3   # class 1 target (circuit HIGH attractor = VDD)

BOUNDARY = 1.2  # true IC(net3) boundary in volts  (within diff-pair active range)


def load_dataset(n_samples=10, random_seed=42):
    """
    Return (X_v, y_v):
      X_v[:,0..2] = IC(net4), IC(net6), IC(net2) = 1.0V (balanced, Block D decides)
      X_v[:,3]    = IC(net3) — the variable feature that determines the label
      y_v         = {0.3, 3.3} V
    """
    # 5 class-1 and 5 class-0 samples, IC(net3) spans [0.3, 3.0] with gap at 1.2V boundary
    ic_net3 = np.array([0.3, 0.6, 0.9, 1.1,  # class 1: IC(net3) < 1.2V
                         1.3, 1.6, 2.0, 2.4, 2.7, 3.0])  # class 0: IC(net3) > 1.2V
    ic_net3 = ic_net3[:n_samples]          # allow fewer samples if requested

    y_v = np.where(ic_net3 < BOUNDARY, Y_HIGH, Y_LOW)

    vn  = 1.0
    X_v = np.column_stack([
        np.full(len(ic_net3), vn),   # IC(net4) = VN = balanced
        np.full(len(ic_net3), vn),   # IC(net6) = VN = balanced
        np.full(len(ic_net3), vn),   # IC(net2) = VN = balanced
        ic_net3,                      # IC(net3) = the classification feature
    ])

    return X_v, y_v
