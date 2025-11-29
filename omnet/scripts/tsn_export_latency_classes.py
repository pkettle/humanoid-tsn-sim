#!/usr/bin/env python3
"""
tsn_export_latency_classes.py

Read the JSON summary produced by parse_end_to_end_delay.py and
emit a tidy CSV with one row per traffic class:

Columns:
  config, class, stream, pcp, present, count, min_ms, mean_ms, max_ms, jitter_ms
"""

import argparse
import csv
import json
import os
from typing import List


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export per-traffic-class latency summary to a tidy CSV."
    )
    parser.add_argument(
        "--in-json",
        default="omnet/results/tsn/tsn_latency_summary.json",
        help="Input JSON file from parse_end_to_end_delay.py",
    )
    parser.add_argument(
        "--out-csv",
        default="omnet/results/tsn/tsn_latency_classes.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--config-name",
        default="FlatThorInetTsn",
        help="Logical config name to tag rows with (e.g., FlatThorInet, FlatThorInetTsn)",
    )

    args = parser.parse_args(argv)

    with open(args.in_json, "r") as f:
        summary = json.load(f)

    classes = summary.get("traffic_classes", {})

    # Ensure output directory exists
    out_dir = os.path.dirname(args.out_csv)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    fieldnames = [
        "config",
        "class",
        "stream",
        "pcp",
        "present",
        "count",
        "min_ms",
        "mean_ms",
        "max_ms",
        "jitter_ms",
    ]

    with open(args.out_csv, "w", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for cls_name, info in classes.items():
            row = {
                "config": args.config_name,
                "class": cls_name,
                "stream": info.get("stream", ""),
                "pcp": info.get("pcp", ""),
                "present": info.get("present", False),
                "count": info.get("count", 0),
                "min_ms": info.get("min_ms", ""),
                "mean_ms": info.get("mean_ms", ""),
                "max_ms": info.get("max_ms", ""),
                "jitter_ms": info.get("jitter_ms", ""),
            }
            writer.writerow(row)

    print(f"Wrote latency class CSV to: {args.out_csv}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
