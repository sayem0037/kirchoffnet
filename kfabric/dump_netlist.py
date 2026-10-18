"""
dump_netlist.py -- write out the ACTUAL netlist a trained run used.

WHY THIS EXISTS
---------------
Training never keeps a netlist. train_kfq.py writes one SPICE deck per sample
into a per-process scratch file (tmp_kfq_<tag>_<pid>.sp), solves it, overwrites
it with the next sample, and deletes it at the end. Every worker has its own,
because sharing one scratch file between concurrent runs silently corrupted two
result sets earlier in this project.

That is fine for training and useless for inspection, so this script rebuilds
the deck exactly, from the checkpoint:

    results/kfq_<dataset>_<tag>.json  holds  layers + cfg + every trained theta

Given those, write_kfq_netlist() is deterministic — the file it produces here is
byte-for-byte what the solver saw for that sample, with the trained weights in
place.

Usage:
    python dump_netlist.py --dataset circle --tag gif --sample 0
    python dump_netlist.py --dataset mnist  --tag m4 --side 4 --sample 3
    python dump_netlist.py --dataset circle --tag gif --epoch 1   # untrained-ish
"""
import argparse
import json
import os

import numpy as np

import train_kfq as T
from datasets_any import load_any
from netlist_kfq import (all_thetas, n_devices, read_pairs, write_kfq_netlist)

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(BASE, "results")
OUTDIR = os.path.join(BASE, "netlists")


def main(a):
    ck = os.path.join(RESULTS, f"kfq_{a.dataset}_{a.tag}.json")
    if not os.path.exists(ck):
        raise SystemExit(f"no checkpoint at {ck}")
    d = json.load(open(ck))
    layers = [tuple(t) for t in d["layers"]]
    cfg = d["cfg"]

    # theta: the final weights, or a specific epoch if snapshots were kept
    if a.epoch is None:
        th = {k: float(v) for k, v in d["theta"].items()}
        which = "final (epoch %d)" % d["log"][-1]["epoch"]
    else:
        snaps = d.get("snapshots") or []
        if not snaps:
            raise SystemExit("this checkpoint has no per-epoch snapshots; "
                             "retrain with --snapshots, or drop --epoch")
        th = {k: float(v) for k, v in snaps[a.epoch - 1].items()}
        which = "end of epoch %d" % a.epoch

    # the data point, mapped through the SAME fixed rescale training used
    kw = dict(n_train=d["n_train"], n_test=d["n_test"])
    if a.dataset == "mnist":
        kw["side"] = a.side
    Xtr, ytr, Xte, yte, C, _ = load_any(a.dataset, **kw)
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    _, mn, mx = T.to_pm1(Xtr)
    src = Xte if a.test else Xtr
    lab = yte if a.test else ytr
    Xw, _, _ = T.to_pm1(src, mn, mx)
    x = Xw[a.sample]

    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, f"{a.dataset}_{a.tag}_sample{a.sample}.sp")
    nd = write_kfq_netlist(th, x, layers, out, load_r=cfg["load_r"],
                           rd=cfg["rd"], vtail=cfg["vtail"], vcm=cfg["vcm"],
                           swing=cfg["swing"])

    # solve it, so the file is reported together with what it produces
    sc, _ = T.forward(th, x, layers, cfg, T.scratch("dump"))
    nl_tmp = T.scratch("dump")
    if os.path.exists(nl_tmp):
        os.remove(nl_tmp)

    topo = "-".join([str(layers[0][0])] + [str(b) for _, b in layers])
    print(f"wrote  {out}")
    print(f"  run       {a.dataset}  tag={a.tag}   weights: {which}")
    print(f"  topology  {topo}   {nd} devices   "
          f"{len(all_thetas(layers))} trainable sources")
    print(f"  operating vcm={cfg['vcm']} swing={cfg['swing']} "
          f"load_R={cfg['load_r']} rd={cfg['rd']} vtail={cfg['vtail']}")
    print(f"  sample    {'test' if a.test else 'train'}[{a.sample}]  "
          f"true class = {int(lab[a.sample])}")
    print(f"  read      {read_pairs(layers)}")
    print(f"  scores    {np.array2string(sc, precision=5)}")
    print(f"  argmax    {int(np.argmax(sc))}  "
          f"({'correct' if int(np.argmax(sc)) == int(lab[a.sample]) else 'wrong'})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="circle")
    ap.add_argument("--tag", default="gif")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--test", action="store_true",
                    help="take the sample from the test split instead")
    ap.add_argument("--epoch", type=int, default=None,
                    help="use the weights from the end of this epoch "
                         "(needs a checkpoint trained with --snapshots)")
    ap.add_argument("--side", type=int, default=4)
    main(ap.parse_args())
