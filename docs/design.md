# Design notes

## Scope

The repo reproduces one workflow end to end: probes to speeds and closures, measured against ground truth. Each component is the simplest version that is still correct and testable. Improvements are listed at the end rather than half-built.

## Simulator

- **Speeds**: free-flow speed per segment class (30 km/h streets, 50 km/h arterials), times a congestion factor with morning and evening peaks. Severity varies per segment (arterials suffer more), with small multiplicative noise per segment-bin.
- **Demand**: departures follow the same two-peak profile plus a base level. Origin-destination pairs are uniform over nodes, with a minimum trip length.
- **Vehicles**: a per-vehicle speed factor plus per-traversal noise (lognormal). Routing uses shortest travel time at departure, excluding closed segments. If a vehicle reaches a segment that closed after it departed, it reroutes from the current node.
- **Probes**: positions sampled every ~10 s with jitter, gaussian position noise, and random dropout.

## Map-matching

- Candidates are all segments within a radius of the point, nearest first, capped at k.
- Route distance between candidates uses all-pairs node distances. A small backward move along the same segment is treated as standing still (GPS jitter).
- When no transition is feasible, the chain breaks and restarts instead of forcing a bad path.
- Traversal times assume constant speed between two consecutive probes. Only segments with both entry and exit inside the trace are emitted, so first and last partial segments are dropped by design.

## Estimation

- Speeds use the median travel time, not the mean speed. It is robust to stopped vehicles and it converts to a space-mean speed.
- Closures use a Poisson silence test. The expected count is scaled by the network-wide observed/expected ratio in the same bin, which uses only data available at that time and adapts to busy or quiet days.
- The detectability criterion in the evaluation uses the same threshold. If the expected traffic during the closure is below -ln(alpha), even a perfect silence is not significant, and the closure is reported as not detectable rather than as a miss.

## Next steps

1. Load a real OSM extract (Barcelona Eixample), then run qualitative checks with public GPS traces.
2. Temporal smoothing or a Bayesian prior for speeds, to publish low-coverage cells with an uncertainty band.
3. Closure evidence from rerouting: probes on parallel segments that deviate from their shortest path.
4. Rank detected closures by p(closure) x impact (expected volume), to prioritise operator review.
