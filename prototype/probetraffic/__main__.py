"""CLI: python -m probetraffic run <scenario.yaml> [--out data/outputs] [--report reports]"""
import argparse
from pathlib import Path

from probetraffic.pipeline import load_config, run
from probetraffic.eval.report import write_report


def main():
    ap = argparse.ArgumentParser(prog="probetraffic")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("scenarios", nargs="+")
    r.add_argument("--out", default="data/outputs")
    r.add_argument("--report", default="reports")
    a = ap.parse_args()
    results = []
    for path in a.scenarios:
        cfg = load_config(path)
        name = cfg.get("name", Path(path).stem)
        res = run(cfg, Path(a.out) / name)
        results.append(res)
        print(f"{name}: matching precision {res['matching']['precision']:.3f}, "
              f"speed MAE {res['speed']['mae_kmh']:.2f} km/h, closures {res['closures']}")
    write_report(results, Path(a.report))


if __name__ == "__main__":
    main()
