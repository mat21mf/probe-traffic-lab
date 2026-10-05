"""Evaluation against simulator ground truth."""
import numpy as np
import pandas as pd


def matching_metrics(est: pd.DataFrame, true: pd.DataFrame) -> dict:
    key = ["probe_id", "segment_id"]
    e = est.drop_duplicates(key)
    # first and last segment of a trip can never be fully observed
    pos = true.groupby("probe_id").cumcount()
    size = true.groupby("probe_id")["segment_id"].transform("size")
    inner = true[(pos > 0) & (pos < size - 1)]
    t = true.drop_duplicates(key)
    tp = e.merge(t, on=key).shape[0]
    rec = e.merge(inner.drop_duplicates(key), on=key).shape[0]
    m = est.merge(true, on=key, suffixes=("_e", "_t"))
    dur_err = ((m.exit_s_e - m.entry_s_e) - (m.exit_s_t - m.entry_s_t)).abs()
    return {"precision": tp / max(len(e), 1),
            "recall_inner": rec / max(len(inner.drop_duplicates(key)), 1),
            "duration_err_median_s": float(dur_err.median())}


def speed_metrics(est: pd.DataFrame, truth: pd.DataFrame) -> dict:
    j = est[est.published].merge(truth, on=["segment_id", "bin"], suffixes=("_e", "_t"))
    ae = (j.speed_mps_e - j.speed_mps_t).abs()
    ape = ae / j.speed_mps_t
    buckets = pd.cut(j.n, [2, 4, 9, np.inf], labels=["3-4", "5-9", "10+"])
    by = (pd.DataFrame({"bucket": buckets, "ae_kmh": ae * 3.6, "ape": ape})
          .groupby("bucket", observed=True)
          .agg(cells=("ae_kmh", "size"), mae_kmh=("ae_kmh", "mean"), mape=("ape", "mean"))
          .reset_index())
    return {"coverage": len(j) / len(truth),
            "mae_kmh": float((ae * 3.6).mean()),
            "mape": float(ape.mean()),
            "by_samples": by}


def closure_metrics(det: pd.DataFrame, true: pd.DataFrame, expected: np.ndarray = None,
                    t0_s: float = 0.0, bin_s: int = 300, alpha: float = 1e-3) -> dict:
    """Event-level closure metrics.

    A true closure counts as detectable when the expected traversal volume
    during the closure window reaches -ln(alpha): with less, even a perfect
    silence would not be statistically surprising.
    """
    if len(true) == 0:
        return {"true": 0, "detectable": 0, "detected": 0, "recall": None,
                "false_alarms": len(det), "precision": None, "latency_median_min": None}
    hits, hits_det, n_detectable, lat, used = 0, 0, 0, [], set()
    for _, c in true.iterrows():
        detectable = True
        if expected is not None:
            b0 = int((c.start_s - t0_s) // bin_s)
            b1 = int((c.end_s - t0_s) // bin_s)
            detectable = expected[int(c.segment_id), b0:b1].sum() >= -np.log(alpha)
            n_detectable += int(detectable)
        d = det[(det.segment_id == c.segment_id) & (det.flag_s >= c.start_s) & (det.est_start_s < c.end_s)]
        if len(d):
            hits += 1
            hits_det += int(detectable)
            lat.append((d.flag_s.min() - c.start_s) / 60)
            used.update(d.index)
    return {"true": len(true),
            "detectable": n_detectable if expected is not None else None,
            "detected": hits, "recall": hits / len(true),
            "recall_detectable": hits_det / n_detectable if n_detectable else None,
            "false_alarms": len(det) - len(used), "precision": len(used) / max(len(det), 1),
            "latency_median_min": float(np.median(lat)) if lat else None}
