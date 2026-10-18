"""Plot Stage 2 curve from stage2_log.csv (monotonic-descent-guard run)."""
import csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ep, loss, tr, te, step = [], [], [], [], []
with open("stage2_log.csv") as f:
    for r in csv.DictReader(f):
        ep.append(int(r["epoch"])); loss.append(float(r["loss"]))
        tr.append(float(r["train_acc"])); te.append(float(r["test_acc"]))
        step.append(r.get("step", "ok"))

rej = [i for i, s in enumerate(step) if s.startswith("reject")]

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].plot(ep, loss, color="#2a78d6", lw=1.8)
ax[0].set_xlabel("Epoch"); ax[0].set_ylabel("Cross-entropy loss (train)")
ax[0].set_title(f"Loss: {loss[0]:.3f} -> {loss[-1]:.3f}  (monotone, no spike)")
ax[0].grid(alpha=0.3)

ax[1].plot(ep, tr, color="#2a78d6", lw=1.8, label="train")
ax[1].plot(ep, te, color="#1baf7a", lw=1.8, label="test")
ax[1].axhline(0.88, color="#c3c2b7", ls="--", lw=1, label="Stage 1 test (0.88)")
ax[1].set_xlabel("Epoch"); ax[1].set_ylabel("Accuracy"); ax[1].set_ylim(0, 1.02)
ax[1].set_title(f"Accuracy: train {tr[-1]:.2f} / test {te[-1]:.2f}")
ax[1].legend(frameon=False, fontsize=8); ax[1].grid(alpha=0.3)

fig.suptitle("KirchhoffNet chain -- Stage 2 (circuit via 100ns adjoint, monotonic-descent guard)")
fig.tight_layout(); fig.savefig("stage2_curve.png", dpi=140)
print(f"epochs={len(ep)}  rejected_steps={len(rej)}  final loss={loss[-1]:.3f} "
      f"train={tr[-1]:.2f} test={te[-1]:.2f}")
