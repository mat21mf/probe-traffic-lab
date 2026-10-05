"""Per-segment, per-time-bin speed from matched traversals.

Each traversal is assigned to the bin containing its midpoint. The bin speed
is length / median travel time (robust to outlier traversals). A segment-bin
is published only with at least `min_samples` traversals.
"""
import numpy as np
import pandas as pd


def estimate_speeds(traversals: pd.DataFrame, segments: pd.DataFrame, t0_s: float,
                    bin_s: int, n_bins: int, min_samples: int = 3,
                    vmin_mps: float = 0.5, vmax_mps: float = 40.0) -> pd.DataFrame:
    tr = traversals.merge(segments[["segment_id", "length_m"]], on="segment_id")
    tt = tr.exit_s - tr.entry_s
    tr = tr[(tt > 0)]
    tt = tr.exit_s - tr.entry_s
    v = tr.length_m / tt
    tr = tr[(v >= vmin_mps) & (v <= vmax_mps)].copy()
    tr["tt_s"] = tr.exit_s - tr.entry_s
    tr["bin"] = ((0.5 * (tr.entry_s + tr.exit_s) - t0_s) // bin_s).astype(int)
    tr = tr[(tr.bin >= 0) & (tr.bin < n_bins)]
    agg = tr.groupby(["segment_id", "bin"]).agg(n=("tt_s", "size"), tt_med=("tt_s", "median"),
                                               length_m=("length_m", "first")).reset_index()
    agg["speed_mps"] = agg.length_m / agg.tt_med
    agg["published"] = agg.n >= min_samples
    return agg[["segment_id", "bin", "n", "speed_mps", "published"]]
