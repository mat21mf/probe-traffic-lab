# AI assistance log

This repo was built with an AI coding assistant (Claude). The assistant drafted the code and docs. I defined the problem and scope, reviewed the design and results, and I own the result. Every number in the README comes from code in this repo, and `make all` reproduces it.

## What was delegated, and how it was verified

| Area | Delegated to the assistant | How it was verified |
|---|---|---|
| Simulator | grid graph, speed profiles, demand, rerouting, probe noise | connectivity check on the graph; probes compared against the true trajectories |
| Map-matching | HMM matcher and traversal reconstruction | compared with the simulator's true traversals: precision, inner recall, duration error |
| Estimation | speed aggregation, Poisson closure detector | unit tests with hand-computed expected values |
| Detector tuning | parameter sweep over 3 seeds | defaults chosen from the trade-off table in docs/evaluation.md |
| Java core | port of the estimation step | golden fixture test plus full-day parity against Python at 1e-9 |
| Docs | README, design notes, ADRs | numbers cross-checked against reports/evaluation.md |

## Where the assistant's first version was wrong or needed judgement

- **Unreachable nodes.** The first grid had 99 unreachable node pairs: alternating one-way streets trap the corners. It was caught by checking the all-pairs distance matrix for infinities. The fix makes the boundary streets two-way arterials, and the constraint is documented in `graph/grid.py`.
- **Library behaviour change.** `groupby().apply()` drops the grouping column in pandas 3, which broke the recall metric. It was replaced with an explicit position filter.
- **Too many false closures.** The first detector raised about 30 false alarms per day with no closures at all. Tuning by eye would have been guesswork, so a sweep over history length, smoothing and alpha replaced it. The chosen defaults trade some recall for 4 false alarms per day, and the remaining misses are explained by a detectability criterion rather than hidden.
- **A test that was right to fail.** A closure unit test with only 2 segments failed. The volume-ratio scaling halves the expectation when one of two segments goes silent. The detector was correct, the fixture was unrealistic, and the fix was a network-sized fixture rather than a change to the detector.
- **Claims not made.** The Java core was not faster than vectorised pandas in a single cold run, so the README makes no performance claim for the port. Its purpose is the production-language contract.

## Where it helped most, and where it did not

- **Helped:** scaffolding, boilerplate (CSV contract I/O, CLI, Makefile, CI), porting well-specified logic between languages, and running sweeps quickly.
- **Did not replace judgement:** choosing what to measure, deciding what counts as a detectable closure, deciding which failures were bugs and which were wrong expectations, and deciding what the README should not claim.
