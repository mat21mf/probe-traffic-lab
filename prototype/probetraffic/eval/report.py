"""Markdown report across scenarios."""
from pathlib import Path


def _f(v, fmt="{:.3f}"):
    return "-" if v is None else fmt.format(v)


def write_report(results: list, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    L = ["# probe-traffic-lab - evaluation report", "",
         "Synthetic ground truth: every metric below is exact. See docs/evaluation.md.", "",
         "## Summary", "",
         "| Scenario | Trips | Probes | Match precision | Inner recall | Speed MAE (km/h) | MAPE | Coverage "
         "| Closures det/detectable/true | False alarms | Latency (min) |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        m, s, c, v = r["matching"], r["speed"], r["closures"], r["volumes"]
        L.append(f"| {r['scenario']} | {v['trips']} | {v['probes']} | {_f(m['precision'])} | "
                 f"{_f(m['recall_inner'])} | {_f(s['mae_kmh'], '{:.2f}')} | {_f(s['mape'], '{:.1%}')} | "
                 f"{_f(s['coverage'], '{:.1%}')} | {c['detected']}/{c.get('detectable', '-')}/{c['true']} | {c['false_alarms']} | "
                 f"{_f(c['latency_median_min'], '{:.0f}')} |")
    L += ["", "## Speed error by samples per segment-bin", ""]
    for r in results:
        L += [f"**{r['scenario']}**", "", "| Samples | Cells | MAE (km/h) | MAPE |", "|---|---|---|---|"]
        for _, b in r["speed"]["by_samples"].iterrows():
            L.append(f"| {b['bucket']} | {b['cells']} | {b['mae_kmh']:.2f} | {b['mape']:.1%} |")
        L.append("")
    L += ["## Timings (seconds)", "", "| Scenario | History (3 days) | Simulate | Match | Estimate |",
          "|---|---|---|---|---|"]
    for r in results:
        t = r["timings"]
        L.append(f"| {r['scenario']} | {t['history_s']:.1f} | {t['simulate_s']:.1f} | "
                 f"{t['match_s']:.1f} | {t['estimate_s']:.2f} |")
    (out / "evaluation.md").write_text("\n".join(L) + "\n")
