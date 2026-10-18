"""Freeze a legacy results/<name>_ring_best.json into a kring package (explicit encoder values).

NOTE: this preserves the legacy model AS-IS, including its known flaws (scaler fit on all
data, checkpoint chosen on the test set). It exists only to run validation on it.

usage: python -m kring.tools.import_legacy <dataset> <out.json>   (KRING_SIM_SRC must be set)
"""
import json, os, sys
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
from dataset import _raw                                   # legacy, training-side only
from ring_common import init_seed_encoder, N_STAGES, VLO, VHI, IC_CENTER, CIRC_NAMES
from kring.package import FORMAT_VERSION, save_package
from kring.sim import fingerprint, sim_src_dir

MODELS = [".MODEL NCH NMOS LEVEL=1 VTO=0.531  KP=120u LAMBDA=0.02 GAMMA=0.4 PHI=0.7",
          ".MODEL PCH PMOS LEVEL=1 VTO=-0.71  KP=40u  LAMBDA=0.02 GAMMA=0.4 PHI=0.7"]
DEVICES = dict(md="NCH L=650n W=6u", ms="NCH L=650n W=6u", mt="NCH L=1u W=12u",
               mpd="PCH L=2u W=6u", mps="PCH L=2u W=6u")


def main(name, out):
    d = json.load(open(os.path.join(BASE, "results", f"{name}_ring_best.json")))
    X, _ = _raw(name)
    W, b = init_seed_encoder(seed=0)
    pkg = dict(
        format_version=FORMAT_VERSION,
        classes=[0, 1],
        preprocessing=dict(kind="standardize", mean=X.mean(0).tolist(), std=X.std(0).tolist(),
                           fit_on="LEGACY: all 4096 generated points (includes test)"),
        encoder=dict(kind="affine_clip", center=IC_CENTER, W=W.tolist(), b=b.tolist(),
                     vlo=VLO, vhi=VHI),
        circuit=dict(topology="diffamp_ring_v1", n_stages=N_STAGES, vdd=3.3, cap="1p",
                     models=MODELS, devices=DEVICES,
                     param_order=CIRC_NAMES,
                     params=[d["circ"][n] for n in CIRC_NAMES]),
        simulation=dict(tstep="10n", tstop="100n", method="simulator default",
                        simulator_fingerprint=fingerprint(sim_src_dir())),
        readout=dict(state_mean=d["mu"], state_std=d["sd"], W=d["Wout"], b=d["bout"]),
        provenance=dict(source=f"legacy results/{name}_ring_best.json", dataset=name,
                        legacy_epoch=d["epoch"], legacy_test_acc=d["test_acc"],
                        legacy_train_acc=d["train_acc"],
                        caveats=["checkpoint selected on test set", "scaler fit on all data",
                                 "saved circuit is post-update, metrics were pre-update"]),
    )
    save_package(pkg, out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
