# Evaluation

All metrics compare pipeline outputs with the simulator's ground truth for the same day.

| Metric | Definition |
|---|---|
| Match precision | share of reconstructed (probe, segment) traversals that the vehicle really drove |
| Inner recall | share of true traversals, excluding each trip's first and last segment, that were reconstructed |
| Speed MAE / MAPE | error of published segment-bin speeds against the true profile speed |
| Coverage | published segment-bins / all segment-bins |
| Closures detected / detectable / true | event-level; a detection counts when it is on the right segment and overlaps the closure window |
| False alarms | detected events that overlap no true closure |
| Latency | minutes from closure start to flag |

## Detector tuning

The parameters were chosen with a sweep over 3 seeds (24 injected closures, 4000 trips per day). Totals across the 3 days:

| History days | Smoothing (bins) | alpha | Detected (of 24) | False alarms |
|---|---|---|---|---|
| 3 | 1 | 1e-3 | 17 | 98 |
| 3 | 1 | 1e-4 | 10 | 20 |
| 5 | 3 | 1e-3 | 17 | 65 |
| 5 | 3 | 1e-4 | 11 | 16 |
| 5 | 3 | 1e-5 | 8 | 3 |

The defaults are 5 history days, 3-bin smoothing and alpha = 1e-4. The undetected closures sit on segments with too little expected traffic, and lowering alpha further only removes true detections. More history mostly reduces false alarms, because the expected-count baseline gets less noisy.
