# probe-traffic-lab

Turning noisy, sparse GPS probes into per-segment speeds and road-closure flags, evaluated against exact ground truth.

The pipeline is prototyped in Python. The production-style estimation step is re-implemented in Java behind a fixed data contract, and CI enforces that both implementations produce identical outputs.

```
 road graph --> simulated trips --> noisy probes --> HMM map-matching --> traversals --> speeds + closures --> evaluation
               (known speeds,       (GPS noise,      (Python)             (CSV/Parquet    (Python prototype     (vs ground truth)
                injected closures)   gaps, dropouts)                       contract)       AND Java core)
```

## Why synthetic ground truth

Real probe data has no true per-segment speed and no complete list of closures. The simulator drives trips over a street graph with speed profiles and closures that are known exactly, so every metric below is exact rather than estimated. Vehicles route on travel times at departure and reroute around closures they encounter.

The default graph is a 13x13 Eixample-like grid: 130 m blocks, alternating one-way streets and two-way arterials, 408 directed segments. The graph loader is the only part that would change for a real OSM extract.

## Results

Four scenarios, one simulated day each (06:00-22:00). From `reports/evaluation.md`:

| Scenario | Trips | Match precision | Speed MAE | Coverage | Closures detected / detectable / true | False alarms |
|---|---|---|---|---|---|---|
| baseline | 4000 | 1.000 | 2.3 km/h | 17.2% | - | 4 |
| closures | 4000 | 1.000 | 2.3 km/h | 17.2% | 6 / 5 / 8 | 4 |
| sparse | 1200 | 1.000 | 2.5 km/h | 3.3% | 2 / 0 / 8 | 1 |
| noisy (20 m GPS, 20 s sampling, 25% dropout) | 4000 | 0.973 | 3.1 km/h | 13.0% | 4 / 4 / 8 | 4 |

What the numbers say:

- **Map-matching is not the bottleneck.** Precision stays at or above 97% even with 20 m noise and 20 s sampling.
- **Speed error falls with samples per cell** (see the per-bucket tables in the report). Coverage, meaning which segment-bins have enough probes to publish, is the real constraint at low penetration.
- **Closures are detected when they are detectable.** A closure is "detectable" when the traffic expected during it is large enough that silence is statistically surprising. Every detectable closure was found in every scenario. The misses are low-volume segments, where no silence-based method can decide, and they need a different signal.
- **The false-alarm vs latency trade-off is explicit.** The alpha sweep is in `docs/evaluation.md`.

## How it works

1. **Map-matching** (`prototype/probetraffic/matching/hmm.py`): an HMM in the style of Newson and Krumm. The emission is gaussian on point-to-segment distance. The transition is exponential on the difference between route distance and straight-line distance, with physically impossible transitions forbidden. Decoding uses Viterbi with chain restarts. Segment entry and exit times are interpolated between probes, and only fully observed traversals are kept.
2. **Speeds** (`estimation/segment_speed.py`): length divided by median travel time per segment and 15-minute bin, published only with at least 3 traversals.
3. **Closures** (`estimation/closure_detect.py`): a Poisson silence test. Expected counts per segment and 5-minute bin come from 5 history days, smoothed in time and scaled by today's network-wide volume. A segment is flagged when the cumulative expected volume over its silent bins reaches -ln(alpha), and cleared at the next observed traversal.
4. **Java core** (`core/`): the same estimation step, dependency-free Java 21, reading and writing the CSV contract in `contracts/`.

## Run it

```
make setup        # pip install -e ".[dev]"
make test         # Python unit tests
make core-test    # compile Java core, run golden fixture test
make eval         # four scenarios -> reports/evaluation.md   (about 2 min)
make parity       # full simulated day through Python and Java, outputs must match
```

Requires Python 3.11+ and JDK 21.

## Layout

```
configs/scenarios/   scenario definitions (YAML)
prototype/           Python package probetraffic: graph, sim, matching, estimation, eval
core/                Java implementation of the estimation step
contracts/           CSV/Parquet schemas and the golden fixture shared by both implementations
scripts/             parity check and golden fixture generation
reports/             generated evaluation report
docs/                design notes, evaluation details, decision records, AI-assistance log
```

## Limitations

- Synthetic city, synthetic demand. Real probe fleets have heterogeneous sampling, parked vehicles and GPS multipath in urban canyons. None of that is modelled yet.
- Speeds use static 15-minute bins and no temporal smoothing or prior, so low-coverage cells are simply not published.
- Closure detection uses only missing traversals. Combining it with rerouting evidence on neighbouring segments is the obvious next step.

See `docs/design.md` for details and next steps.
