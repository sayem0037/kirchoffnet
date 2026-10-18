"""Build the release package: FROZEN ring (initial circuit) + trained readout, for the seed with the
best validation accuracy (ties -> lower validation CE -> lower seed). Test accuracy is read from the
stored run result; nothing about the test set is used for selection.

usage: python -m kring.tools.build_frozen <runs_dir> <dataset> <out_dir>   (KRING_SIM_SRC set)
"""
import glob, json, os, sys
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)
from ring_common import init_seed_encoder, circ_init
from kring.package import save_package
from kring.tools.experiment import (split_arrays, fit_lr, build_pkg, Evaluator, KRingModel, N_STAGES)
from kring.tools.experiment import ce  # noqa: F401


def main(runs, name, out_dir, workers=12):
    R = [json.load(open(f)) for f in glob.glob(os.path.join(runs, f"{name}_s*_result.json"))]
    best = min(R, key=lambda r: (-r["C_untrained_val"]["acc_strict"], r["C_untrained_val"]["ce"], r["seed"]))
    seed = best["seed"]
    sp = split_arrays(name, seed)
    Xtr, ytr = sp["train"]
    W, b = init_seed_encoder(seed=seed)
    circ0 = circ_init()
    dummy = fit_lr(np.random.default_rng(0).standard_normal((20, N_STAGES)), np.arange(20) % 2)
    m = KRingModel(build_pkg(name, seed, Xtr, W, b, circ0, dummy), None)
    S, st = m.states(Xtr, workers=workers)
    assert not np.isnan(S).any(), "frozen ring must converge on every training sample"
    fit = fit_lr(S, ytr)
    prov = dict(dataset=name, seed=seed, kind="frozen ring + trained readout (selected by validation acc)",
                splits=best["sizes"], val=best["C_untrained_val"], test=best["C_untrained_ring"],
                train_fail=0, circuit_trained=False,
                evidence="kring/reports/step5_summary.md: circuit training gave no repeatable gain",
                known_limits=["defined at tstep=10n; other steps change states (see validation report)",
                              "inputs outside the training range are unvalidated; failures are reported, not guessed"])
    pkg = build_pkg(name, seed, Xtr, W, b, circ0, fit, prov=prov)
    os.makedirs(out_dir, exist_ok=True)
    save_package(pkg, os.path.join(out_dir, "model.json"))
    np.save(os.path.join(out_dir, "test_points.npy"), sp["test"][0])
    print(name, "seed", seed, "val", best["C_untrained_val"]["acc_strict"], "test", best["C_untrained_ring"]["acc_strict"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
