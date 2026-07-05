"""
dataset.py  —  5+5 balanced binary dataset for KirchhoffNet.

Circuit physics:
  Block D compares IC(net3) vs VN=1.0V.
  Dataset boundary = 1.2V (gap between 1.1V and 1.3V).
  One hard sample at IC(net3)=1.1V is initially WRONG.

  Ring nodes net4/net6/net2 are initialized near their target-attractor values
  so the ring escapes the symmetric 1.2V metastable state:
    HIGH attractor: net4=3.3V, net6=0.3V, net2=3.3V, net3=0.3V
    LOW  attractor: net4=0.3V, net6=3.3V, net2=0.3V, net3=3.3V
  Using IC values 2.5V / 0.5V as soft pushes toward each attractor.
"""

import numpy as np

Y_HIGH   = 3.3   # HIGH attractor target
Y_LOW    = 0.3   # LOW  attractor target
BOUNDARY = 1.2   # classification boundary in volts

IC_HIGH = [0.3, 0.5, 0.7, 0.9, 1.1]   # IC(net3) values -> target HIGH
IC_LOW  = [1.3, 1.6, 1.9, 2.2, 2.5]   # IC(net3) values -> target LOW

# Other ring-node ICs biased toward target attractor to escape metastable symmetric state
_IC4_HIGH, _IC6_HIGH, _IC2_HIGH = 2.5, 0.5, 2.5   # net4 HIGH attractor side
_IC4_LOW,  _IC6_LOW,  _IC2_LOW  = 0.5, 2.5, 0.5   # net4 LOW  attractor side


def load_dataset():
    """
    Return (X_v, y_v):
      X_v : shape (10, 4) — columns are IC(net4), IC(net6), IC(net2), IC(net3)
      y_v : shape (10,)   — targets in {Y_LOW, Y_HIGH}
    """
    ic_net3 = np.array(IC_HIGH + IC_LOW)
    y_v     = np.where(ic_net3 < BOUNDARY, Y_HIGH, Y_LOW)
    n_high  = len(IC_HIGH)
    n       = len(ic_net3)

    ic4 = np.array([_IC4_HIGH]*n_high + [_IC4_LOW]*(n - n_high))
    ic6 = np.array([_IC6_HIGH]*n_high + [_IC6_LOW]*(n - n_high))
    ic2 = np.array([_IC2_HIGH]*n_high + [_IC2_LOW]*(n - n_high))

    X_v = np.column_stack([ic4, ic6, ic2, ic_net3])
    return X_v, y_v


if __name__ == "__main__":
    X_v, y_v = load_dataset()
    print("Binary dataset — 5 HIGH + 5 LOW")
    print(f"  Boundary : {BOUNDARY} V")
    print(f"  SS_tot   : {np.sum((y_v - y_v.mean())**2):.4f}")
    print()
    print(f"  {'#':>2}  {'IC(net3)':>9}  {'IC(net4)':>9}  {'target':>7}  class")
    for i in range(len(y_v)):
        cls = "HIGH" if y_v[i] == Y_HIGH else "LOW"
        print(f"  {i:>2}  {X_v[i,3]:>9.1f}  {X_v[i,0]:>9.1f}  {y_v[i]:>7.1f}  {cls}")
