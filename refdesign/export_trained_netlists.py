"""
export_trained_netlists.py -- write the TRAINED 1T1R crossbar as SPICE decks.

The trainer never keeps a netlist: write_layer() regenerates one per solve and the
deck is deleted at the end of the run. This script rebuilds the network from the
final checkpoint of each write-verify run (results/xbar_<ds>_fix_ckpt.json) and emits

    netlists/trained/xbar_<ds>_L1.sp   input layer   (3 rows x 16 column pairs)
    netlists/trained/xbar_<ds>_L2.sp   output layer  (17 rows x 2 column pairs)
    netlists/trained/xbar_<ds>.json    conductances, ADC full scales, sample, check

The row drivers carry data, so a deck is only complete for ONE input. The decks are
written for test sample 0, and L2's rows are the digitized tanh activations that L1's
circuit actually produced for that sample -- the two decks are one real forward pass.
Any other input: call xbar1t1r_netlist.write_layer() with the conductances in the json.

The checkpoint, not the meta file, supplies the ADC full scales: meta 'fs' is the
calibration taken BEFORE training, and the trainer recalibrates every few epochs.

VERIFICATION. The network is rebuilt with the trainer's own CrossbarNet and evaluated
with its own evaluate(), on the trainer's own split, and the test accuracy must match
the last logged epoch. A mismatch means the export is not the trained array.

    python export_trained_netlists.py                 # all three datasets
    python export_trained_netlists.py --dataset circle --no-verify
"""

import argparse
import json
import os

import numpy as np

import xbar1t1r_train as T
from xbar1t1r_device import ResistiveDevice

XB = T.XB
OUT = os.path.join(T.BASE, "netlists", "trained")
DATASETS = ["twomoon", "circle", "2spirals"]


def rebuild(ds):
    """The trained network, the trainer's split, and the run's logged final test acc."""
    with open(os.path.join(T.RESULTS, f"xbar_{ds}_fix_meta.json")) as f:
        meta = json.load(f)
    with open(os.path.join(T.RESULTS, f"xbar_{ds}_fix_ckpt.json")) as f:
        ckpt = json.load(f)

    # same data path as T.main()
    Xtr, ytr, Xte, yte, C, _ = T.load_any(ds, n_train=meta["n_train"],
                                          n_test=meta["n_test"])
    Xtr = np.asarray(Xtr).reshape(len(Xtr), -1)
    Xte = np.asarray(Xte).reshape(len(Xte), -1)
    Xtr, mn, mx = T.to_pm1(Xtr)
    Xte, _, _ = T.to_pm1(Xte, mn, mx)

    dk = meta["device"]
    dev = ResistiveDevice(g_on=dk["g_on"], g_off=dk["g_off"], n_states=dk["n_states"],
                          a_pot=dk["a_pot"], a_dep=dk["a_dep"], nonlinear=dk["nonlinear"],
                          write_sigma=dk["write_sigma"], verify=dk["verify"],
                          verify_tol=dk["verify_tol"], seed=meta["seed"])
    net = T.CrossbarNet(meta["sizes"], dev, rf=meta["rf"], adc_bits=meta["adc_bits"],
                        seed=meta["seed"], act=meta["act"], slope=meta["slope"])
    net.gp = [np.array(g) for g in ckpt["gp"]]
    net.gm = [np.array(g) for g in ckpt["gm"]]
    net.fs = list(ckpt["fs"])

    last = meta["log"][-1]
    assert last["epoch"] == ckpt["epoch"], (last["epoch"], ckpt["epoch"])
    return net, meta, ckpt, Xte, np.asarray(yte), last["test"]


def export(ds, verify=True, sample=0):
    net, meta, ckpt, Xte, yte, logged = rebuild(ds)
    nl = T.scratch(f"export_{ds}", T.BASE)
    try:
        measured = T.evaluate(net, Xte, yte, nl) if verify else None

        # one real forward pass, layer by layer, keeping each layer's row vector
        x = np.clip(Xte[sample], -1.0, 1.0)
        scores, acts, raw = net.forward(x, nl, keep=True)
        paths = []
        for l in range(len(net.sizes) - 1):
            p = os.path.join(OUT, f"xbar_{ds}_L{l + 1}.sp")
            XB.write_layer(net.gp[l], net.gm[l], net.rows_for(acts[l]), nl,
                           rf=net.rf[l])
            with open(nl) as f:
                body = f.read()
            head = (f"* TRAINED {ds} crossbar, layer {l + 1} of {len(net.sizes) - 1} | "
                    f"write-verify run, epoch {ckpt['epoch']} checkpoint\n"
                    f"* rows driven for test sample {sample} (row 1 = bias row, x=+1)\n"
                    f"* read: V(outp_j)-V(outn_j); ADC full scale {net.fs[l]:.6g} V, "
                    f"{net.adc_bits} bit"
                    + (f"; then tanh({net.slope:g}*d) -> next layer's rows\n"
                       if l < len(net.sizes) - 2 else "; argmax = class\n"))
            with open(p, "w") as f:
                f.write(head + body)
            paths.append(p)
    finally:
        if os.path.exists(nl):
            os.remove(nl)

    rec = dict(dataset=ds, source=f"results/xbar_{ds}_fix_ckpt.json",
               epoch=ckpt["epoch"], sizes=net.sizes, rf=net.rf, fs=net.fs,
               adc_bits=net.adc_bits, act=net.act, slope=net.slope,
               v_read=XB.V_READ, vref=XB.VREF_DEFAULT,
               gp=[g.tolist() for g in net.gp], gm=[g.tolist() for g in net.gm],
               sample=dict(index=sample, x=Xte[sample].tolist(), label=int(yte[sample]),
                           rows=[net.rows_for(a).tolist() for a in acts[:-1]],
                           col_diff_V=[r.tolist() for r in raw],
                           scores=np.asarray(scores).tolist(),
                           pred=int(np.argmax(scores))),
               test_acc_logged=logged, test_acc_reexport=measured)
    with open(os.path.join(OUT, f"xbar_{ds}.json"), "w") as f:
        json.dump(rec, f, indent=1)

    ok = "" if measured is None else (
        "  MATCH" if abs(measured - logged) < 1e-9 else "  ** MISMATCH **")
    print(f"{ds:9s} test logged {logged:.4f}  re-simulated "
          f"{'-' if measured is None else f'{measured:.4f}'}{ok}  | sample {sample}: "
          f"label {int(yte[sample])} pred {int(np.argmax(scores))}")
    for p in paths:
        print(f"          {os.path.relpath(p, T.BASE)}")
    return measured is None or abs(measured - logged) < 1e-9


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=DATASETS)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    good = [export(d, not a.no_verify, a.sample) for d in ([a.dataset] if a.dataset
                                                            else DATASETS)]
    raise SystemExit(0 if all(good) else 1)
