import numpy as np
import pandas as pd
import pytest

from probetraffic.graph.grid import build_grid
from probetraffic.sim.simulate import SimConfig, simulate_day
from probetraffic.matching.hmm import MatchConfig, match_probes
from probetraffic.estimation.segment_speed import estimate_speeds
from probetraffic.estimation.closure_detect import detect_closures


@pytest.fixture(scope="module")
def graph():
    return build_grid()


def test_grid_strongly_connected(graph):
    assert np.isfinite(graph.dist).all()


def test_matching_on_clean_probes_recovers_true_segments(graph):
    day = simulate_day(graph, SimConfig(seed=3, n_trips=150, gps_sigma_m=2.0, dropout=0.0))
    est, _ = match_probes(graph, day["probes"], MatchConfig(sigma_m=2.0))
    key = ["probe_id", "segment_id"]
    hit = est.drop_duplicates(key).merge(day["traversals"].drop_duplicates(key), on=key)
    assert len(hit) / len(est.drop_duplicates(key)) > 0.99


def test_speed_is_length_over_median_travel_time():
    seg = pd.DataFrame({"segment_id": [0], "length_m": [100.0]})
    trav = pd.DataFrame({"probe_id": [1, 2, 3], "segment_id": [0, 0, 0],
                         "entry_s": [0.0, 10.0, 20.0], "exit_s": [10.0, 30.0, 60.0]})
    out = estimate_speeds(trav, seg, t0_s=0.0, bin_s=900, n_bins=1, min_samples=3)
    assert out.n.iloc[0] == 3 and bool(out.published.iloc[0])
    assert out.speed_mps.iloc[0] == pytest.approx(100.0 / 20.0)


def test_closure_flagged_after_expected_volume_exceeds_threshold():
    # 50 segments so the network-wide volume ratio stays close to 1 while one is silent
    expected = np.full((50, 12), 2.0)
    counts = expected.copy()
    counts[0, 4:8] = 0          # segment 0 silent for 4 bins, then reopens
    det = detect_closures(counts, expected, t0_s=0.0, bin_s=300, alpha=1e-3)
    # -ln(1e-3) = 6.9; each empty bin adds 2.0 * 0.98 -> flagged on the 4th empty bin
    assert len(det) == 1
    r = det.iloc[0]
    assert r.segment_id == 0 and r.est_start_s == 1200 and r.flag_s == 2400 and r.cleared_s == 2400


def test_no_closure_when_volume_too_low():
    expected = np.full((2, 12), 0.2)
    counts = expected.copy()
    counts[0, 2:10] = 0
    assert detect_closures(counts, expected, 0.0, 300, alpha=1e-3).empty
