"""Python vs Java parity on the estimation step.

Exports a scenario's matched traversals, segment lengths and expected counts
to the CSV contract, runs both implementations on the same inputs and diffs
the outputs. Optionally writes a small golden fixture (subset of segments)
used by the Java test.

  python scripts/parity_check.py data/outputs/closures --work data/parity [--golden contracts/golden]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "prototype"))
from probetraffic.estimation.segment_speed import estimate_speeds          # noqa: E402
from probetraffic.estimation.closure_detect import count_matrix, detect_closures  # noqa: E402

T0, BIN, NBINS, CBIN, NCB = 21600.0, 900, 64, 300, 192


def export(trav, seg, expected, d: Path):
    d.mkdir(parents=True, exist_ok=True)
    trav[["probe_id", "segment_id", "entry_s", "exit_s"]].to_csv(d / "traversals.csv", index=False,
                                                                 float_format="%.17g")
    seg[["segment_id", "length_m"]].to_csv(d / "segments.csv", index=False, float_format="%.17g")
    s, b = np.nonzero(expected)
    pd.DataFrame({"segment_id": s, "bin": b, "expected": expected[s, b]}).to_csv(
        d / "expected_counts.csv", index=False, float_format="%.17g")


def python_estimate(d: Path, alpha):
    trav = pd.read_csv(d / "traversals.csv")
    seg = pd.read_csv(d / "segments.csv")
    ex = pd.read_csv(d / "expected_counts.csv")
    n_seg = int(seg.segment_id.max()) + 1
    expected = np.zeros((n_seg, NCB))
    expected[ex.segment_id, ex.bin] = ex.expected
    t = time.perf_counter()
    sp = estimate_speeds(trav, seg, T0, BIN, NBINS)
    cl = detect_closures(count_matrix(trav, n_seg, T0, CBIN, NCB), expected, T0, CBIN, alpha=alpha)
    return sp, cl, time.perf_counter() - t


def java_estimate(d: Path, out: Path, alpha):
    cmd = ["java", "-cp", str(ROOT / "core" / "build"), "lab.probetraffic.Main", "estimate",
           "--in", str(d), "--out", str(out), "--alpha", str(alpha)]
    r = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return (pd.read_csv(out / "segment_speeds.csv"), pd.read_csv(out / "closures_detected.csv"),
            r.stdout.strip())


def compare(py_sp, py_cl, j_sp, j_cl, tol=1e-9):
    k = ["segment_id", "bin"]
    a = py_sp.sort_values(k).reset_index(drop=True)
    b = j_sp.sort_values(k).reset_index(drop=True)
    ok_sp = (len(a) == len(b) and (a[k + ["n"]].to_numpy() == b[k + ["n"]].to_numpy()).all()
             and np.allclose(a.speed_mps, b.speed_mps, rtol=tol, atol=tol)
             and (a.published.astype(bool).to_numpy() == b.published.astype(bool).to_numpy()).all())
    c = py_cl.sort_values(["segment_id", "est_start_s"]).reset_index(drop=True)
    e = j_cl.sort_values(["segment_id", "est_start_s"]).reset_index(drop=True)
    ok_cl = len(c) == len(e) and np.allclose(c.to_numpy(dtype=float), e.to_numpy(dtype=float),
                                             rtol=tol, atol=tol)
    return ok_sp, ok_cl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario_dir")
    ap.add_argument("--work", default="data/parity")
    ap.add_argument("--alpha", type=float, default=1e-4)
    ap.add_argument("--golden", default=None, help="write a golden fixture here")
    ap.add_argument("--golden-segments", type=int, default=60)
    a = ap.parse_args()
    src, work = Path(a.scenario_dir), Path(a.work)
    trav = pd.read_parquet(src / "traversals.parquet")
    seg = pd.read_parquet(src / "segments.parquet")
    expected = np.load(src / "expected_counts.npy")

    export(trav, seg, expected, work / "in")
    py_sp, py_cl, py_t = python_estimate(work / "in", a.alpha)
    j_sp, j_cl, j_log = java_estimate(work / "in", work / "java", a.alpha)
    ok_sp, ok_cl = compare(py_sp, py_cl, j_sp, j_cl)
    print(f"traversals={len(trav)} python_estimate_ms={py_t * 1e3:.1f} | java: {j_log}")
    print(f"parity speeds={'OK' if ok_sp else 'FAIL'} ({len(py_sp)} vs {len(j_sp)} cells), "
          f"closures={'OK' if ok_cl else 'FAIL'} ({len(py_cl)} vs {len(j_cl)} events)")

    if a.golden:
        g = Path(a.golden)
        keep = seg.segment_id < a.golden_segments
        export(trav[trav.segment_id < a.golden_segments], seg[keep], expected[: a.golden_segments], g / "in")
        sp, cl, _ = python_estimate(g / "in", a.alpha)
        (g / "expected").mkdir(parents=True, exist_ok=True)
        sp.to_csv(g / "expected" / "segment_speeds.csv", index=False, float_format="%.17g")
        cl.to_csv(g / "expected" / "closures_detected.csv", index=False, float_format="%.17g")
        print(f"golden fixture written to {g} ({len(sp)} speed cells, {len(cl)} closure events)")
    sys.exit(0 if ok_sp and ok_cl else 1)


if __name__ == "__main__":
    main()
