"""Closure detection from missing traversals.

Expected traversal counts per segment and count-bin come from history days
(lambda). Today's expectation is lambda scaled by the network-wide volume
ratio in the same bin, so it adapts to busier or quieter days using only
data available at that bin.

For each segment, consecutive empty bins accumulate expected volume L. Under
a Poisson model P(no traversals | open) = exp(-L); the segment is flagged
closed when L >= -ln(alpha). The flag clears at the first bin with an
observed traversal.
"""
import numpy as np
import pandas as pd


def count_matrix(traversals: pd.DataFrame, n_seg: int, t0_s: float, bin_s: int, n_bins: int):
    b = ((traversals.entry_s - t0_s) // bin_s).astype(int).to_numpy()
    s = traversals.segment_id.to_numpy()
    ok = (b >= 0) & (b < n_bins)
    m = np.zeros((n_seg, n_bins))
    np.add.at(m, (s[ok], b[ok]), 1)
    return m


def expected_from_history(history: list, n_seg, t0_s, bin_s, n_bins, smooth_bins: int = 1):
    """Mean count per segment-bin over history days, optionally smoothed in time
    with a centred moving average of `smooth_bins` bins (edge-normalised)."""
    m = np.mean([count_matrix(h, n_seg, t0_s, bin_s, n_bins) for h in history], axis=0)
    if smooth_bins > 1:
        k = np.ones(smooth_bins)
        num = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, m)
        den = np.convolve(np.ones(m.shape[1]), k, mode="same")
        m = num / den[None, :]
    return m


def detect_closures(counts: np.ndarray, expected: np.ndarray, t0_s: float, bin_s: int,
                    alpha: float = 1e-3) -> pd.DataFrame:
    tot_e = expected.sum(axis=0)
    ratio = np.where(tot_e > 0, counts.sum(axis=0) / np.maximum(tot_e, 1e-9), 1.0)
    lam = expected * ratio[None, :]
    thr = -np.log(alpha)
    rows = []
    for s in range(counts.shape[0]):
        acc, first, flagged = 0.0, None, None
        for b in range(counts.shape[1]):
            if counts[s, b] == 0:
                if first is None:
                    first, acc = b, 0.0
                acc += lam[s, b]
                if flagged is None and acc >= thr:
                    flagged = b
            else:
                if flagged is not None:
                    rows.append((s, t0_s + first * bin_s, t0_s + (flagged + 1) * bin_s, t0_s + b * bin_s))
                first, flagged, acc = None, None, 0.0
        if flagged is not None:
            rows.append((s, t0_s + first * bin_s, t0_s + (flagged + 1) * bin_s, t0_s + counts.shape[1] * bin_s))
    return pd.DataFrame(rows, columns=["segment_id", "est_start_s", "flag_s", "cleared_s"])
