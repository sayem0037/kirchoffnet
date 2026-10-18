# kring — validated simulated inference for the closed diff-amp ring

Release models (frozen ring + trained linear readout), one per 2-D task, in `models/<task>/`:
`model.json` (everything needed for inference), `reference.json` (stored predictions), `test_points.npy`.

```python
import os; os.environ["KRING_SIM_SRC"] = r"<path to circuit simulator src>"   # or sim_src=... below
from kring import KRingModel
if __name__ == "__main__":                      # required on Windows when workers > 1
    m = KRingModel.load("models/circle/model.json")       # checks the simulator fingerprint
    p = m.predict([[0.1, -0.4], [1.2, 0.3]], workers=4)
    p.label   # int class, -1 on failure     p.proba  # (n,2), NaN on failure
    p.status  # 'ok' | 'invalid_input' | 'no_convergence' | 'nonfinite' | 'incomplete' | 'error'
```

One prediction = standardize (train-split mean/std) -> affine+clip to 10 `.IC` voltages -> fresh netlist in a
private temp dir -> transient to 100 ns at tstep 10 ns -> read h1..h10 -> standardize -> softmax readout.
A failed simulation returns an explicit status and label -1; it is never guessed or dropped.

## Test results (test split never used for selection; failures would count as wrong)

| task | release model test acc (48 pts) | sim failures | linear on inputs (3 seeds) | linear on encoded IC | untrained ring + readout | trained ring + readout |
|---|---|---|---|---|---|---|
| twomoon | 1.000 | 0/48 | 0.882 ± 0.035 | 0.917 ± 0.045 | 0.951 ± 0.035 | 0.965 ± 0.020 |
| circle | 0.958 | 0/48 | 0.479 ± 0.029 | 0.646 ± 0.119 | 0.896 ± 0.074 | 0.944 ± 0.026 |
| 2spirals | 0.708 | 0/48 | 0.660 ± 0.043 | 0.722 ± 0.097 | 0.715 ± 0.043 | 0.729 ± 0.061 |

The release-model column is one seed, picked on validation accuracy, so it is optimistic relative to the
seed-averaged columns. Details: `reports/step5_summary.md`.

**Conclusions**
- The ring (even untrained) clearly beats linear baselines on circle and is at or above them on twomoon. It is NOT better than a linear classifier on the encoded voltages for 2spirals.
- Circuit training gave no repeatable benefit (D−C within noise; on most runs validation picked an early or the initial iterate), so the release models keep the frozen ring.
- Inference speed: about 1.1 s per sample single process (this machine).

## Validation (reports/validate_*_frozen.json, 12 points each)
- All simulations succeeded and reached 100 ns, finite. Repeat, shuffled order and 2-worker runs agree to ~1e-13 V with identical labels. `.IC` is applied at t=0 (error ~5e-7 V); reset is exact (~1e-15 V).
- **Time-step dependence: real.** Halving tstep moves states by ~0.08 V, quartering ~0.12 V; one 2spirals label flipped. The models are defined at tstep = 10 ns only; do not change it without revalidating.
- The `.IC` values are only the starting guess of the simulator's DC solve; the internal nodes at t=0 depend on the input.
- **Adjoint gradients are wrong** (`reports/validate_twomoon_legacy.json`): they shrink in proportion to tstep (0.291 / 0.019 / 0.003 at 10n / 2.5n / 1n) while finite differences are stable (~23–28 V/V). Training here therefore used gradient-free SPSA, and the old `train_ring.py` circuit updates were driven by a wrong gradient.
- The circuit is fragile: 4–8 mV perturbations of the parameters often make the DC solve fail, so circuit tuning is mostly rejected steps.

## Superseded
The legacy `results/circle_ring_best.json` failed 49/64 points (silently skipped in its own metrics). Legacy checkpoints also
fit the scaler on all data, picked the epoch on the test set, and saved post-update circuits with pre-update metrics.
Use `models/` instead.

## Not covered (needed before any hardware claim)
Operating range outside the sampled 2-D training region, device variation, noise, timing/initialization on silicon,
and the solver-vs-hardware gap. The time-step dependence above means "model of the simulator at 10 ns", not of the physics.

## Reproduce
- Experiment: `python -m kring.tools.experiment <dataset> <seed> runs 16 5`; summary: `python -m kring.tools.aggregate runs out.md`
- Release package: `python -m kring.tools.build_frozen runs <dataset> models/<dataset>`
- Release test (fresh process, tolerances 1e-6 V / 1e-6 proba, invalid-input rejection): `python -m kring.tools.release_test check models/<d>/model.json models/<d>/reference.json`
- Validation: `python -m kring.tools.validate <model.json> <points.npy> <report.json> 12`
Set `KRING_SIM_SRC` to the simulator `src` directory; `runs/` holds the 9 experiment results and trained-circuit packages.
