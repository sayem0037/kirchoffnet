"""
run_bench.py -- the comparison table: arms x {accuracy, convergence, latency,
area, energy}, assembled from results that already exist on disk.

This generalises kfabric/run_kfq.py from 3 rows x 2 columns to N arms x 5
metrics. It deliberately does NOT train anything: training is slow and belongs
in the per-arm scripts, so this reads their checkpoints and composes the table.
Anything missing is reported as missing, with the command that would produce
it, rather than quietly dropped from the table -- a comparison with a silently
absent row is worse than one with a hole in it.

THE PROTOCOL, WHICH IS THE POINT
--------------------------------
Held identical across arms: dataset and split (kfabric/datasets_any.py), the
[-1, 1] input encoding, VDD = 3.3 V, the 0.35 um model cards, the technology
card in tech.py, the settling-window convention, and argmax readout with no
trained software read-out anywhere.

Declared asymmetries, stated in the table rather than hidden:
  * the crossbar needs a DAC per row and an ADC per column per layer; KFQ needs
    none. Converter cost is a separate line, never folded into a total.
  * the digital arm is cell-characterised and op-counted, not simulated end to
    end -- a full INT8 MLP is millions of device-timesteps in a Python solver.
  * the crossbar's primary arm is trained EX-SITU, because that is what a
    crossbar accelerator does; its in-situ arm exists so the convergence column
    compares like with like.

Gate E lives here: every arm must be scored on a bit-identical split, verified
by hashing it, so no arm can be flattered by a lucky partition.
"""

import argparse
import glob
import hashlib
import importlib.util
import json
import os
import sys

import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
KFABRIC = os.path.join(os.path.dirname(BASE), "kfabric")
sys.path.insert(0, BASE)

import metrics                       # noqa: E402
import tech                          # noqa: E402

RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ds = _load("_kfq_ds", os.path.join(KFABRIC, "datasets_any.py"))


# ---------------------------------------------------------------- Gate E ----
def split_hash(Xtr, ytr, Xte, yte):
    """A fingerprint of the exact data every arm must be scored on."""
    h = hashlib.sha256()
    for arr in (Xtr, ytr, Xte, yte):
        a = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
        h.update(str(a.shape).encode())
        h.update(a.tobytes())
    return h.hexdigest()[:16]


def load_split(dataset, n_train, n_test, side=8):
    kw = dict(n_train=n_train, n_test=n_test)
    if dataset == "mnist":
        kw["side"] = side
    Xtr, ytr, Xte, yte, C, _ = _ds.load_any(dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    return Xtr, ytr, Xte, yte, C


# ------------------------------------------------------------ arm readers ---
def _newest(pattern):
    hits = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return hits[0] if hits else None


def read_kfq(dataset):
    ck = _newest(os.path.join(KFABRIC, "results", f"kfq_{dataset}_*.json"))
    if not ck:
        return None
    d = json.load(open(ck))
    log = d.get("log", [])
    te = [r["test"] for r in log if "test" in r]
    return dict(arm="KFQ (ours)", source=os.path.basename(ck),
                train=(log[-1].get("train") if log else None),
                test=(te[-1] if te else None),
                best=(max(te) if te else None),
                conv=metrics.epochs_to_converge(te),
                n_params=len(d.get("theta", {})),
                trained="in-situ adjoint",
                hw_key=("kfq", dataset))


def read_xbar(dataset, mode):
    ck = _newest(os.path.join(RESULTS, f"xbar_{mode}_{dataset}_*.json"))
    if not ck:
        return None
    d = json.load(open(ck))
    log = d.get("log", [])
    te = [r["test"] for r in log if "test" in r]
    row = dict(arm=f"XBAR {mode}", source=os.path.basename(ck),
               train=(log[-1].get("train") if log else None),
               test=(te[-1] if te else None),
               best=(max(te) if te else None),
               conv=metrics.epochs_to_converge(te),
               n_params=len(d.get("u", {})),
               trained=("software + programmed" if mode == "exsitu"
                        else "in-situ adjoint"),
               hw_key=("xbar", dataset))
    if log and "sw_test" in log[-1]:
        row["sw_test"] = log[-1]["sw_test"]
        row["mapping_loss"] = log[-1]["sw_test"] - log[-1]["test"]
    return row


def read_dmlp(dataset, bits, arch):
    ck = _newest(os.path.join(RESULTS, f"dmlp_{dataset}_*.json"))
    if not ck:
        return None
    d = json.load(open(ck))
    key = f"int{bits}"
    if key not in d["results"]:
        return None
    r = d["results"][key]
    cm = r["cost"].get(arch)
    if cm is None:
        return None
    return dict(arm=f"DMLP INT{bits} {arch}", source=os.path.basename(ck),
                train=r["train"], test=r["test"], best=r["convergence"]["best"],
                conv=r["convergence"], n_params=cm["gates"]["n_weights"],
                trained="software (quantization-aware)",
                hw=dict(latency_s=cm["latency_s"], energy_j=cm["energy_j"],
                        area_um2=cm["area"]["total"],
                        area_breakdown=cm["area"],
                        converters=dict(adc=0, dac=0),
                        note="op-counted from measured cells"))


def read_hw(arm, dataset, cap):
    """Measured hardware metrics, if measure_existing.py has been run."""
    ck = _newest(os.path.join(RESULTS, f"hw_{arm}_{dataset}_*.json"))
    if not ck:
        return None
    d = json.load(open(ck))
    rows = d["rows"]
    pick = min(rows, key=lambda r: abs(r["cap_f"] - cap))
    e = pick["energy"]
    return dict(latency_s=pick["latency_s"],
                energy_j=e.get("total_with_conv", e["total"]),
                energy_core_j=e["total"], converters_j=e.get("converters", 0.0),
                power_w=e["p_avg"], area_um2=pick["area"]["total"],
                area_breakdown=pick["area"], devices=pick["devices"],
                converters=pick["converters"], cap_f=pick["cap_f"])


# ================================================================== main =====
def main(a):
    Xtr, ytr, Xte, yte, C = load_split(a.dataset, a.n_train, a.n_test, a.side)
    sh = split_hash(Xtr, ytr, Xte, yte)
    n_te = len(yte)

    print(f"\n{a.dataset}  --  {C} classes, {len(ytr)} train / {n_te} test")
    print(f"technology: {tech.NODE_NM} nm, VDD = {tech.VDD} V, "
          f"load = {a.cap * 1e15:.1f} fF")
    print(f"Gate E split fingerprint: {sh}")

    rows, missing = [], []

    chance = dict(arm="chance", test=1.0 / C, trained="-")
    rows.append(chance)

    for name, fn in (("KFQ", lambda: read_kfq(a.dataset)),
                     ("XBAR exsitu", lambda: read_xbar(a.dataset, "exsitu")),
                     ("XBAR insitu", lambda: read_xbar(a.dataset, "insitu"))):
        r = fn()
        if r is None:
            missing.append(name)
        else:
            rows.append(r)

    for bits in a.bits:
        for arch in a.arch:
            r = read_dmlp(a.dataset, bits, arch)
            if r is None:
                missing.append(f"DMLP INT{bits} {arch}")
            else:
                rows.append(r)

    # attach measured hardware metrics
    for r in rows:
        if "hw_key" in r:
            hw = read_hw(*r["hw_key"], cap=a.cap)
            if hw:
                r["hw"] = hw
            else:
                missing.append(f"hardware metrics for {r['arm']}")

    # ---------------------------------------------------------- the table ---
    print(f"\n{'arm':<24} {'test':>7} {'95% CI':>16} {'ep':>4} "
          f"{'latency':>11} {'energy':>11} {'area':>11}")
    print("-" * 92)
    for r in rows:
        te = r.get("test")
        ci = ("       -" if te is None
              else "[{:.2f},{:.2f}]".format(*metrics.wilson(te, n_te)))
        hw = r.get("hw", {})
        lat = hw.get("latency_s")
        en = hw.get("energy_j")
        ar = hw.get("area_um2")
        ep = (r.get("conv") or {}).get("epoch")
        print(f"{r['arm']:<24} "
              f"{'   -   ' if te is None else f'{te:7.3f}'} {ci:>16} "
              f"{'   -' if ep is None else f'{ep:4d}'} "
              f"{'          -' if lat is None else f'{lat * 1e9:8.3f} ns'} "
              f"{'          -' if en is None else f'{en * 1e12:8.2f} pJ'} "
              f"{'          -' if ar is None else f'{ar:7.0f} um2'}")

    # -------------------------------------------------------- the asymmetry -
    print("\nconverters per inference (the architectural difference):")
    for r in rows:
        hw = r.get("hw", {})
        cv = hw.get("converters")
        if cv is None:
            continue
        ej = hw.get("converters_j", 0.0)
        print(f"  {r['arm']:<24} ADC {cv.get('adc', 0):3d}  "
              f"DAC {cv.get('dac', 0):3d}   "
              f"conversion energy {ej * 1e12:8.2f} pJ "
              f"({100 * ej / max(hw.get('energy_j', 1e-30), 1e-30):5.1f}% of total)")

    for r in rows:
        if "mapping_loss" in r:
            print(f"\n{r['arm']}: software {r['sw_test']:.3f} -> "
                  f"circuit {r['test']:.3f}  (mapping loss "
                  f"{r['mapping_loss']:+.3f})")

    if missing:
        print("\nNOT IN THIS TABLE (run these to fill the holes):")
        cmds = {
            "KFQ": f"cd ../kfabric && python train_kfq.py --dataset {a.dataset}",
            "XBAR exsitu": f"python xbar_spec.py --dataset {a.dataset} --save && "
                           f"python xbar_train.py --mode exsitu --dataset {a.dataset}",
            "XBAR insitu": f"python xbar_train.py --mode insitu --dataset {a.dataset}",
        }
        for m in dict.fromkeys(missing):
            hint = cmds.get(m)
            if hint is None and m.startswith("DMLP"):
                hint = f"python digital_mlp.py --dataset {a.dataset}"
            if hint is None and m.startswith("hardware"):
                arm = "kfq" if "KFQ" in m else "xbar"
                hint = f"python measure_existing.py --arm {arm} --dataset {a.dataset} --sweep"
            print(f"  - {m:<34} {hint or ''}")

    out = os.path.join(RESULTS, f"bench_{a.dataset}_{a.tag}.json")
    json.dump(dict(dataset=a.dataset, C=C, n_train=len(ytr), n_test=n_te,
                   split_hash=sh, cap_f=a.cap, tech=tech.CARD,
                   rows=rows, missing=list(dict.fromkeys(missing))),
              open(out, "w"), indent=2, default=float)
    print(f"\nsaved -> {out}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="iris")
    ap.add_argument("--n-train", type=int, default=90)
    ap.add_argument("--n-test", type=int, default=60)
    ap.add_argument("--side", type=int, default=8)
    ap.add_argument("--bits", type=int, nargs="+", default=[4, 8])
    ap.add_argument("--arch", nargs="+", default=["parallel", "serial"])
    ap.add_argument("--cap", type=float, default=tech.C_LOAD_DEFAULT)
    ap.add_argument("--tag", default="run")
    sys.exit(main(ap.parse_args()))
