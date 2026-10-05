# Data contract between prototype and core

| File | Columns | Notes |
|---|---|---|
| traversals.csv | probe_id, segment_id, entry_s, exit_s | seconds since midnight; one row per fully observed traversal |
| segments.csv | segment_id, length_m | |
| expected_counts.csv | segment_id, bin, expected | 5-minute bins from 06:00; sparse (zero cells omitted) |
| segment_speeds.csv (out) | segment_id, bin, n, speed_mps, published | 15-minute bins from 06:00, sorted by segment_id, bin |
| closures_detected.csv (out) | segment_id, est_start_s, flag_s, cleared_s | |

Floats are written with round-trip precision (%.17g). `golden/` holds a subset (segments 0-159 of the closures scenario) with expected outputs produced by the Python prototype.
