# probe-traffic-lab - evaluation report

Synthetic ground truth: every metric below is exact. See docs/evaluation.md.

## Summary

| Scenario | Trips | Probes | Match precision | Inner recall | Speed MAE (km/h) | MAPE | Coverage | Closures det/detectable/true | False alarms | Latency (min) |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 4000 | 53662 | 1.000 | 0.982 | 2.31 | 6.2% | 17.2% | 0/0/0 | 4 | - |
| closures | 4000 | 54051 | 1.000 | 0.982 | 2.28 | 6.2% | 17.2% | 6/5/8 | 4 | 49 |
| sparse | 1200 | 15995 | 1.000 | 0.982 | 2.49 | 7.2% | 3.3% | 2/0/8 | 1 | 73 |
| noisy | 4000 | 22139 | 0.973 | 0.793 | 3.08 | 8.7% | 13.0% | 4/4/8 | 4 | 43 |

## Speed error by samples per segment-bin

**baseline**

| Samples | Cells | MAE (km/h) | MAPE |
|---|---|---|---|
| 3-4 | 2424 | 2.61 | 6.8% |
| 5-9 | 1682 | 2.04 | 5.7% |
| 10+ | 388 | 1.57 | 4.9% |

**closures**

| Samples | Cells | MAE (km/h) | MAPE |
|---|---|---|---|
| 3-4 | 2444 | 2.51 | 6.6% |
| 5-9 | 1676 | 2.09 | 5.8% |
| 10+ | 365 | 1.60 | 5.1% |

**sparse**

| Samples | Cells | MAE (km/h) | MAPE |
|---|---|---|---|
| 3-4 | 727 | 2.56 | 7.2% |
| 5-9 | 141 | 2.16 | 6.9% |
| 10+ | 2 | 1.77 | 5.3% |

**noisy**

| Samples | Cells | MAE (km/h) | MAPE |
|---|---|---|---|
| 3-4 | 1891 | 3.36 | 9.2% |
| 5-9 | 1203 | 2.80 | 8.2% |
| 10+ | 288 | 2.45 | 7.7% |

## Timings (seconds)

| Scenario | History (3 days) | Simulate | Match | Estimate |
|---|---|---|---|---|
| baseline | 26.3 | 1.6 | 3.5 | 0.04 |
| closures | 26.4 | 2.0 | 3.7 | 0.04 |
| sparse | 8.5 | 0.7 | 1.0 | 0.03 |
| noisy | 16.6 | 1.8 | 1.8 | 0.04 |
