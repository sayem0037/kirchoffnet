"""
train.py  —  Teacher-student SGD using SPICE adjoint sensitivities.

Strategy: train ONLY V2.
  - Teacher: all params identical to student except V2=1.60 (vs student V2=1.70)
  - At tstop=10ns: teacher net4 > student net4 (stronger PMOS → higher voltage)
  - error = student - teacher < 0 for ALL samples (systematic, non-cancelling)
  - sens_V2 = d(net4)/d(V2) < 0 at 10ns (lower V2 → more PMOS → higher net4)
  - grad_V2 = mean(error * sens_V2) > 0 → V2 decreases → student approaches teacher
  - All other params (VB1-VB4, V3-V5) stay fixed at init (VB4=0.80 preserved)

Why only V2?
  Moving any other param at 10ns spoils the 100ns latch: VB4 controls slew rate,
  and reducing it slows the ring so much that at 100ns outputs are still mid-swing.
  The teacher-student target is purely a V2 signal — moving only V2 keeps latch dynamics intact.

Update rule (single-param SGD, fixed step):
    error_i   = student(x_i, 10ns) - teacher(x_i, 10ns)
    g_V2      = mean_i(error_i * sens_V2_i)
    V2       -= LR * sign(g_V2)           # fixed step = LR each epoch

As V2 crosses the bifurcation point (~1.66-1.68V), the boundary sample
IC(net3)=1.1V flips from LOW to HIGH at 100ns, and R²@100ns jumps to ~0.998.
"""

import os, json, csv
import numpy as np

from netlist_writer import write_tran_netlist
from simulator_api  import run_sample, eval_sample
from dataset        import load_dataset

BASE_DIR     = r"D:\Kirchoffnet\kirchoff_claude\binary_reg"
NETLIST_PATH = os.path.join(BASE_DIR, "tmp_tran.sp")
INIT_JSON    = os.path.join(BASE_DIR, "params_init.json")
BEST_JSON    = os.path.join(BASE_DIR, "best_params.json")
LOG_CSV      = os.path.join(BASE_DIR, "train_log.csv")

N_SAMPLES    = 10
EPOCHS       = 200
TSTOP_TRAIN  = "10n"
TSTOP_EVAL   = "1u"     # 1µs = 10τ, ensures full latch settling for all ICs
LR           = 0.001   # fixed step size per epoch for V2 (volts)
TEACHER_V2   = 1.60    # only V2 differs from student
EVAL_BELOW   = 1.705   # skip eval for V2 above this; once below, evaluate every epoch


def load_params():
    with open(INIT_JSON) as f:
        return json.load(f)["params"]


def r2_vs_binary(preds, y_v):
    valid = ~np.isnan(preds)
    if not valid.any():
        return float("nan")
    ss_res = float(np.sum((preds[valid] - y_v[valid]) ** 2))
    ss_tot = float(np.sum((y_v[valid] - y_v[valid].mean()) ** 2))
    return 0.0 if ss_tot < 1e-30 else 1.0 - ss_res / ss_tot


def generate_teacher_targets(X_v, base_params):
    teacher = dict(base_params)
    teacher["V2"] = TEACHER_V2

    print(f"Generating teacher targets at tstop={TSTOP_TRAIN}  (V2={TEACHER_V2}) ...")
    targets = []
    for i in range(len(X_v)):
        ic = {"net4": float(X_v[i, 0]), "net6": float(X_v[i, 1]),
              "net2": float(X_v[i, 2]), "net3": float(X_v[i, 3])}
        write_tran_netlist(teacher, ic, NETLIST_PATH, tstop=TSTOP_TRAIN)
        try:
            v, _ = run_sample(NETLIST_PATH)
            targets.append(float(v))
        except RuntimeError:
            targets.append(float("nan"))

    t = np.array(targets)
    print(f"  Teacher @ {TSTOP_TRAIN}: min={np.nanmin(t):.4f}  "
          f"max={np.nanmax(t):.4f}  mean={np.nanmean(t):.4f}")
    print()
    return t


def train():
    X_v, y_v    = load_dataset()
    base_params = load_params()
    student     = dict(base_params)   # all params at init

    teacher_t = generate_teacher_targets(X_v, base_params)

    print(f"SGD (V2 only) | {N_SAMPLES} samples | {EPOCHS} epochs | LR={LR}")
    print(f"  Train tstop={TSTOP_TRAIN} (MSE vs teacher)  |  Eval tstop={TSTOP_EVAL} (R2 vs binary labels)")
    print(f"  All params frozen except V2  |  VB4 stays at {student['VB4']:.2f}")
    print()
    print(f"{'Ep':>3}  {'train_MSE':>10}  {'R2@100ns':>9}  {'V2':>8}  note")
    print("-" * 52)

    best_r2 = -float("inf")

    with open(LOG_CSV, "w", newline="") as log_file:
        writer = csv.writer(log_file)
        writer.writerow(["epoch", "train_mse", "r2_100ns", "V2"])

        for epoch in range(1, EPOCHS + 1):
            g_V2   = 0.0
            ss_res = 0.0
            count  = 0

            # ── Forward + adjoint at 10ns (V2 gradient only) ─────
            for i in range(N_SAMPLES):
                if np.isnan(teacher_t[i]):
                    continue
                ic = {"net4": float(X_v[i, 0]), "net6": float(X_v[i, 1]),
                      "net2": float(X_v[i, 2]), "net3": float(X_v[i, 3])}
                write_tran_netlist(student, ic, NETLIST_PATH, tstop=TSTOP_TRAIN)
                try:
                    v_pred, sens = run_sample(NETLIST_PATH)
                except RuntimeError:
                    continue

                error   = v_pred - teacher_t[i]
                g_V2   += error * sens["V2"]
                ss_res += error ** 2
                count  += 1
                if epoch == 1 and i < 3:
                    print(f"  [dbg ep1 s{i}] v_pred={v_pred:.4f} teacher={teacher_t[i]:.4f} "
                          f"error={error:.4f} sens_V2={sens['V2']:.4e} contribution={error*sens['V2']:.4e}")

            if count == 0:
                print(f"{epoch:>3}  all samples failed")
                continue

            train_mse = ss_res / count
            g_V2     /= count

            if epoch == 1:
                print(f"  [dbg ep1] g_V2={g_V2:.6e}  sign={'+' if g_V2>0 else '-'}")

            # ── Update only V2, fixed step = LR ─────────────────
            # sensitivity=True gives physically correct dV/dV2 < 0 for non-saturated samples.
            # g_V2 > 0 means decreasing V2 reduces MSE, so standard descent: V2 -= LR*sign(g_V2)
            if abs(g_V2) > 1e-30:
                student["V2"] -= LR * (g_V2 / abs(g_V2))
            student["V2"] = float(np.clip(student["V2"], 0.0, 3.0))

            # ── Evaluate at 100ns vs binary labels ───────────────
            # Skip expensive 100ns eval until V2 is near the bifurcation region.
            if student["V2"] > EVAL_BELOW:
                r2_100 = float("nan")
            else:
                preds_100 = []
                for i in range(N_SAMPLES):
                    ic = {"net4": float(X_v[i, 0]), "net6": float(X_v[i, 1]),
                          "net2": float(X_v[i, 2]), "net3": float(X_v[i, 3])}
                    write_tran_netlist(student, ic, NETLIST_PATH,
                                       tstep="10n", tstop=TSTOP_EVAL)
                    try:
                        preds_100.append(eval_sample(NETLIST_PATH))
                    except Exception:
                        preds_100.append(float("nan"))

                r2_100 = r2_vs_binary(np.array(preds_100), y_v)

                if student["V2"] <= EVAL_BELOW and abs(student["V2"] - EVAL_BELOW) < 0.0015:
                    for i, (p, y) in enumerate(zip(preds_100, y_v)):
                        print(f"  [eval first s{i}] v100={p:.4f} target={y:.1f} "
                              f"IC_net3={X_v[i, 3]:.1f}")

            flag = ""
            if not np.isnan(r2_100) and r2_100 > best_r2:
                best_r2 = r2_100
                with open(BEST_JSON, "w") as bf:
                    json.dump({"r2": best_r2, "params": dict(student)}, bf, indent=2)
                flag = "  *"

            r2_str = f"{r2_100:9.4f}" if not np.isnan(r2_100) else "    (skip)"
            writer.writerow([epoch, f"{train_mse:.6f}",
                             f"{r2_100:.4f}" if not np.isnan(r2_100) else "nan",
                             f"{student['V2']:.5f}"])
            log_file.flush()

            print(f"{epoch:>3}  {train_mse:>10.5f}  {r2_str}  "
                  f"{student['V2']:>8.5f}{flag}")

            # Stop when train MSE has converged to near-zero (V2 ≈ teacher V2)
            if train_mse < 1e-4:
                print(f"\n  Train MSE < 1e-4 at epoch {epoch}. Converged.")
                break

    print(f"\nDone.  Best R2 @ 100ns = {best_r2:.4f}  ({best_r2*100:.1f}%)")
    return student


if __name__ == "__main__":
    train()
