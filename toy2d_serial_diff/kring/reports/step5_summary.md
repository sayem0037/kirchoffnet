# Step 5: does circuit training add value?

Test accuracy (failures counted as wrong), mean ± std over seeds; identical splits per seed.

| dataset | seeds | A: linear on inputs | B: linear on encoded IC | C: untrained ring + readout | D: trained ring + readout | sim fail-rate C / D (test) | D train fails (accepted?) |
|---|---|---|---|---|---|---|---|
| twomoon | 3 | 0.882 ± 0.035 | 0.917 ± 0.045 | 0.951 ± 0.035 | 0.965 ± 0.020 | 0.000 / 0.000 | 3/3 runs fully converged on train+val |
|  ↳ D − C per seed | | | | | -0.021, +0.062, +0.000 | | |
| circle | 3 | 0.479 ± 0.029 | 0.646 ± 0.119 | 0.896 ± 0.074 | 0.944 ± 0.026 | 0.000 / 0.000 | 3/3 runs fully converged on train+val |
|  ↳ D − C per seed | | | | | +0.000, +0.021, +0.125 | | |
| 2spirals | 3 | 0.660 ± 0.043 | 0.722 ± 0.097 | 0.715 ± 0.043 | 0.729 ± 0.061 | 0.000 / 0.000 | 3/3 runs fully converged on train+val |
|  ↳ D − C per seed | | | | | +0.042, +0.000, +0.000 | | |

## Chosen iteration / trainer cost

- 2spirals seed 0: chosen iter 4, 2296 simulations, 45 min wall; val acc C=0.625 D=0.875
- 2spirals seed 1: chosen iter 0, 2296 simulations, 41 min wall; val acc C=0.7916666666666666 D=0.7916666666666666
- 2spirals seed 2: chosen iter 0, 2360 simulations, 50 min wall; val acc C=0.7916666666666666 D=0.7916666666666666
- circle seed 0: chosen iter 0, 2296 simulations, 48 min wall; val acc C=0.9583333333333334 D=0.9583333333333334
- circle seed 1: chosen iter 6, 2296 simulations, 41 min wall; val acc C=1.0 D=1.0
- circle seed 2: chosen iter 6, 2296 simulations, 54 min wall; val acc C=0.7916666666666666 D=0.875
- twomoon seed 0: chosen iter 2, 2360 simulations, 46 min wall; val acc C=1.0 D=1.0
- twomoon seed 1: chosen iter 9, 2360 simulations, 45 min wall; val acc C=0.9166666666666666 D=1.0
- twomoon seed 2: chosen iter 8, 2424 simulations, 53 min wall; val acc C=1.0 D=1.0

## Inference runtime (simulated, this machine)

- 2spirals_s0_trained.json: 1.12 s/sample single process, 0.70 s/sample with 4 workers (includes process start-up)
