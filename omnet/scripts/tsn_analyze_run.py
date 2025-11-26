#!/usr/bin/env python3
"""
tsn_analyze_run.py

Unified analysis for a single OMNeT++ TSN run.

- Input:
    - .vec file (vectors)
    - .sca file (scalars)

- Output:
    - summary CSV with per-module latency stats (and packet counts):
      <out_dir>/tsn_summary.csv

Usage:
    python3 tsn_analyze_run.py \
        omnet/results/tsn/General-#0.vec \
        omnet/results/tsn/General-#0.sca \
        omnet/results/tsn
"""

import sys
import csv
import math
from pathlib import Path
import re
from statistics import mean

DELAY_PREFIXES = ("endToEndDelay", "oneWayDelay", "delay")

def parse_scalars(sca_path: Path):
    """
    Minimal scalar parser.

    Returns:
        dict[(module, name)] = float(value)
    """
    scalars = {}
    lines = sca_path.read_text().splitlines()

    for line in lines:
        line = line.strip()
        if not line.startswith("scalar "):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        module = parts[1]
        name = parts[2]
        value_str = parts[3]

        try:
            value = float(value_str)
        except ValueError:
            continue

        scalars[(module, name)] = value

    return scalars


def parse_delays(vec_path: Path):
    """
    Parse delay-related vectors from .vec.

    Returns:
        dict[module] = list of (time, value) samples aggregated
                       across all delay-like vectors for that module.
    """
    lines = vec_path.read_text().splitlines()

    # Map vector id -> (module, name)
    id_to_info = {}
    ids_of_interest = set()

    vec_def_re = re.compile(r'^vector\s+(\d+)\s+([^\s]+)\s+([^\s]+)')

    # First pass: find delay-related vector definitions
    for line in lines:
        m = vec_def_re.match(line)
        if not m:
            continue
        vid = int(m.group(1))
        module = m.group(2)
        name = m.group(3)  # e.g., endToEndDelay:vector

        id_to_info[vid] = (module, name)

        if name.startswith(DELAY_PREFIXES):
            ids_of_interest.add(vid)

    # Second pass: data lines
    per_module_samples = {}

    for line in lines:
        if not line or not line[0].isdigit():
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        try:
            vid = int(parts[0])
        except ValueError:
            continue

        if vid not in ids_of_interest:
            continue

        try:
            t = float(parts[1])
            v = float(parts[2])
        except ValueError:
            continue

        module, _ = id_to_info.get(vid, ("", ""))
        if module == "":
            continue

        per_module_samples.setdefault(module, []).append((t, v))

    return per_module_samples


def latency_stats(samples):
    """
    Compute basic latency stats from a list of (time, value) samples.

    Returns:
        dict with keys: count, min, max, mean, p50, p95
    """
    if not samples:
        return {
            "count": 0,
            "min": math.nan,
            "max": math.nan,
            "mean": math.nan,
            "p50": math.nan,
            "p95": math.nan,
        }

    values = sorted(v for (_, v) in samples)
    n = len(values)

    def percentile(p):
        if n == 0:
            return math.nan
        idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
        return values[idx]

    return {
        "count": n,
        "min": values[0],
        "max": values[-1],
        "mean": mean(values),
        "p50": percentile(50),
        "p95": percentile(95),
    }


def analyze(vec_path: Path, sca_path: Path, out_dir: Path):
    scalars = parse_scalars(sca_path)
    delays  = parse_delays(vec_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "tsn_summary.csv"

    with out_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "module",
            "metric",
            "count",
            "min",
            "max",
            "mean",
            "p50",
            "p95",
            "rcvdPk",
            "sentPk",
        ])

        for module, samples in sorted(delays.items()):
            stats = latency_stats(samples)

            rcvd_pk = scalars.get((module, "rcvdPk:count"), math.nan)
            sent_pk = scalars.get((module, "sentPk:count"), math.nan)

            writer.writerow([
                module,
                "latency",
                stats["count"],
                stats["min"],
                stats["max"],
                stats["mean"],
                stats["p50"],
                stats["p95"],
                rcvd_pk,
                sent_pk,
            ])

    print(f"Wrote summary to {out_csv}")


def main():
    if len(sys.argv) != 4:
        print("Usage: tsn_analyze_run.py <input.vec> <input.sca> <out_dir>")
        sys.exit(1)

    vec_path = Path(sys.argv[1])
    sca_path = Path(sys.argv[2])
    out_dir  = Path(sys.argv[3])

    if not vec_path.is_file():
        print(f"Error: vec file not found: {vec_path}")
        sys.exit(1)
    if not sca_path.is_file():
        print(f"Error: sca file not found: {sca_path}")
        sys.exit(1)

    analyze(vec_path, sca_path, out_dir)


if __name__ == "__main__":
    main()
