"""End-to-end scenario runner: simulate, match, estimate, evaluate, report."""
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from probetraffic.graph.grid import build_grid
from probetraffic.sim.simulate import SimConfig, bin_edges, simulate_day, truth_speeds, make_closures
from probetraffic.matching.hmm import MatchConfig, match_probes
from probetraffic.estimation.segment_speed import estimate_speeds
from probetraffic.estimation.closure_detect import count_matrix, expected_from_history, detect_closures
from probetraffic.eval.metrics import matching_metrics, speed_metrics, closure_metrics


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def run(cfg: dict, out_dir: Path) -> dict:
    timings = {}
    g = build_grid(**cfg.get("graph", {}))
    sim = SimConfig(**cfg.get("sim", {}))
    mcfg = MatchConfig(**cfg.get("matching", {}))
    est = cfg.get("estimation", {})
    det = cfg.get("closures", {})
    edges = bin_edges(sim)
    t0, n_bins = float(edges[0]), len(edges) - 1
    rng = np.random.default_rng(sim.seed)
    speeds = truth_speeds(g, sim, rng)

    # history days: same speed regime, no closures, different demand draws
    t = time.time()
    history = []
    for k in range(det.get("history_days", 3)):
        h = simulate_day(g, SimConfig(**{**asdict(sim), "seed": sim.seed + 100 + k, "n_closures": 0,
                                        "closure_ids": []}),
                         closures=make_closures(g, SimConfig(n_closures=0), rng), speeds=speeds)
        history.append(match_probes(g, h["probes"], mcfg)[0])
    timings["history_s"] = time.time() - t
    cbin = det.get("count_bin_s", 300)
    n_cb = int((edges[-1] - edges[0]) // cbin)
    expected = expected_from_history(history, g.n_segments, t0, cbin, n_cb,
                                     smooth_bins=det.get("smooth_bins", 1))

    vol = pd.Series(expected.sum(axis=1), index=g.segments.segment_id)
    closures = make_closures(g, sim, np.random.default_rng(sim.seed + 7), volume_hint=vol)
    t = time.time()
    day = simulate_day(g, sim, closures=closures, speeds=speeds)
    timings["simulate_s"] = time.time() - t

    t = time.time()
    trav, _ = match_probes(g, day["probes"], mcfg)
    timings["match_s"] = time.time() - t

    t = time.time()
    seg_speeds = estimate_speeds(trav, g.segments, t0, sim.bin_s, n_bins,
                                 min_samples=est.get("min_samples", 3))
    counts = count_matrix(trav, g.n_segments, t0, cbin, n_cb)
    detected = detect_closures(counts, expected, t0, cbin, alpha=det.get("alpha", 1e-3))
    timings["estimate_s"] = time.time() - t

    res = {"scenario": cfg.get("name", "unnamed"),
           "volumes": {"trips": sim.n_trips, "probes": len(day["probes"]),
                       "true_traversals": len(day["traversals"]), "matched_traversals": len(trav)},
           "matching": matching_metrics(trav, day["traversals"]),
           "speed": speed_metrics(seg_speeds, day["truth_speeds"]),
           "closures": closure_metrics(detected, day["closures"], expected, t0, cbin,
                                       alpha=det.get("alpha", 1e-3)),
           "timings": timings}

    out_dir.mkdir(parents=True, exist_ok=True)
    day["probes"].to_parquet(out_dir / "probes.parquet", index=False)
    day["traversals"].to_parquet(out_dir / "traversals_true.parquet", index=False)
    day["truth_speeds"].to_parquet(out_dir / "truth_speeds.parquet", index=False)
    day["closures"].to_parquet(out_dir / "closures_true.parquet", index=False)
    trav.to_parquet(out_dir / "traversals.parquet", index=False)
    seg_speeds.to_parquet(out_dir / "segment_speeds.parquet", index=False)
    detected.to_parquet(out_dir / "closures_detected.parquet", index=False)
    np.save(out_dir / "expected_counts.npy", expected)
    g.segments.to_parquet(out_dir / "segments.parquet", index=False)
    return res
