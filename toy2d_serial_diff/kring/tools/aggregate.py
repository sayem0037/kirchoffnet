"""Aggregate runs/*_result.json into the step-5 table (mean +- std over seeds) + inference runtime.

usage: python -m kring.tools.aggregate <runs_dir> <out.md>   (KRING_SIM_SRC set, for the runtime probe)
"""
import glob, json, os, sys, time
import numpy as np


def ms(v):
    v = np.array(v, float)
    return f"{v.mean():.3f} ± {v.std():.3f}"


def main(runs, out):
    rows = []
    L = ["# Step 5: does circuit training add value?", "",
         "Test accuracy (failures counted as wrong), mean ± std over seeds; identical splits per seed.", "",
         "| dataset | seeds | A: linear on inputs | B: linear on encoded IC | C: untrained ring + readout | D: trained ring + readout | sim fail-rate C / D (test) | D train fails (accepted?) |",
         "|---|---|---|---|---|---|---|---|"]
    rt = {}
    for name in ("twomoon", "circle", "2spirals"):
        R = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(runs, f"{name}_s*_result.json")))]
        if not R:
            continue
        g = lambda k: [r[k]["acc_strict"] for r in R if k in r]
        fr = lambda k: [r[k]["fail_rate"] for r in R if k in r]
        acc_ok = sum(r["acceptance"]["train_all_ok"] and r["acceptance"]["val_all_ok"] for r in R)
        L.append(f"| {name} | {len(R)} | {ms(g('A_linear_inputs'))} | {ms(g('B_linear_encoded_ic'))} | "
                 f"{ms(g('C_untrained_ring'))} | {ms(g('D_trained_ring'))} | "
                 f"{np.mean(fr('C_untrained_ring')):.3f} / {np.mean(fr('D_trained_ring')):.3f} | "
                 f"{acc_ok}/{len(R)} runs fully converged on train+val |")
        d = np.array(g('D_trained_ring')) - np.array(g('C_untrained_ring'))
        L.append(f"|  ↳ D − C per seed | | | | | {', '.join(f'{x:+.3f}' for x in d)} | | |")
    L += ["", "## Chosen iteration / trainer cost", ""]
    for f in sorted(glob.glob(os.path.join(runs, "*_result.json"))):
        r = json.load(open(f))
        L.append(f"- {r['dataset']} seed {r['seed']}: chosen iter {r['D_chosen_iter']}, {r['n_sims']} simulations, "
                 f"{r['wall_s']/60:.0f} min wall; val acc C={r.get('C_untrained_val',{}).get('acc_strict')} D={r['D_trained_val']['acc_strict']}")
    # runtime probe on one trained package, single process
    pk = sorted(glob.glob(os.path.join(runs, "*_trained.json")))
    if pk:
        from kring import KRingModel
        m = KRingModel.load(pk[0])
        pts = np.load(pk[0].replace("_trained.json", "_test_points.npy"))[:6]
        t = time.time(); m.predict(pts); one = (time.time() - t) / len(pts)
        t = time.time(); m.predict(pts, workers=4); four = (time.time() - t) / len(pts)
        L += ["", "## Inference runtime (simulated, this machine)", "",
              f"- {os.path.basename(pk[0])}: {one:.2f} s/sample single process, {four:.2f} s/sample with 4 workers (includes process start-up)"]
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
