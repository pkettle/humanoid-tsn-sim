#!/usr/bin/env python3
"""
tsn_unified_report.py

Unified TSN report per traffic class from the latency summary.

Now computes:
  - active_rate_hz = count / (stopTime - startTime)
  - global_rate_hz = count / sim_time_limit

Active windows are taken directly from the INI semantics:

  *.thor.app[0/1/2].startTime = 0.001s
  *.thor.app[0/1/2].stopTime  = 0.4s
"""

import argparse
import json
import csv
import os
from typing import Dict, Any, List

import math

# Payload sizes per stream (bytes)
PAYLOAD_BYTES = {
    "CONTROL": 512,      # messageLength = 512B
    "SENSOR": 1024,      # messageLength = 1024B
    "TELEMETRY": 1024,   # messageLength = 1024B
}

# Active windows per class (seconds), from INI
ACTIVE_WINDOWS = {
    "CONTROL": (0.001, 0.4),
    "SENSOR": (0.001, 0.4),
    "TELEMETRY": (0.001, 0.4),
}

# Link speed for utilization calculation (in Mbps)
LINK_SPEED_MBPS = 1000.0  # 1 GbE


def build_unified_rows(
    latency_summary: Dict[str, Any],
    config_name: str,
    sim_time_s: float,
) -> List[Dict[str, Any]]:
    """
    Build unified rows combining latency summary + known active windows.
    """
    rows: List[Dict[str, Any]] = []
    classes = latency_summary.get("traffic_classes", {})

    for cls_name, info in classes.items():
        present = info.get("present", False)
        stream = info.get("stream", "")
        pcp = info.get("pcp", "")
        count = int(info.get("count", 0))
        min_ms = info.get("min_ms", "")
        mean_ms = info.get("mean_ms", "")
        max_ms = info.get("max_ms", "")
        jitter_ms = info.get("jitter_ms", "")

        # Default active window = full sim
        start_time, stop_time = ACTIVE_WINDOWS.get(
            cls_name.upper(),
            (0.0, sim_time_s),
        )
        active_duration = max(0.0, stop_time - start_time)
        if active_duration == 0.0:
            active_duration = sim_time_s

        payload_bytes = PAYLOAD_BYTES.get(cls_name.upper(), 0)

        # Global rate over entire sim-time-limit
        if sim_time_s > 0.0 and count > 0:
            global_rate_hz = count / sim_time_s
        else:
            global_rate_hz = 0.0

        # Active rate over [startTime, stopTime]
        if active_duration > 0.0 and count > 0:
            active_rate_hz = count / active_duration
        else:
            active_rate_hz = 0.0

        # Bandwidth over active period
        if active_duration > 0.0 and payload_bytes > 0 and count > 0:
            rx_mbps = count * payload_bytes * 8.0 / active_duration / 1e6
        else:
            rx_mbps = 0.0

        link_util = rx_mbps / LINK_SPEED_MBPS if LINK_SPEED_MBPS > 0 else 0.0

        if not present:
            rows.append({
                "config": config_name,
                "class": cls_name,
                "stream": stream,
                "pcp": pcp,
                "count": 0,
                "min_ms": "",
                "mean_ms": "",
                "max_ms": "",
                "jitter_ms": "",
                "global_rate_hz": "",
                "active_rate_hz": "",
                "rx_mbps": "",
                "link_utilization": "",
                "start_time": "",
                "stop_time": "",
                "active_duration": "",
            })
            continue

        rows.append({
            "config": config_name,
            "class": cls_name,
            "stream": stream,
            "pcp": pcp,
            "count": count,
            "min_ms": min_ms,
            "mean_ms": mean_ms,
            "max_ms": max_ms,
            "jitter_ms": jitter_ms,
            "global_rate_hz": global_rate_hz,
            "active_rate_hz": active_rate_hz,
            "rx_mbps": rx_mbps,
            "link_utilization": link_util,
            "start_time": start_time,
            "stop_time": stop_time,
            "active_duration": active_duration,
        })

    return rows


def print_console_table(rows: List[Dict[str, Any]]) -> None:
    """
    Pretty console table for human readability.

    Shows:
      Mean latency, jitter, ACTIVE rate, GLOBAL rate, Mbps, utilization
    """
    print("\nUnified TSN Report (per traffic class):\n")

    header = (
        f"{'Class':<12} {'Stream':<12} {'PCP':<5} "
        f"{'Mean [ms]':>10} {'Jitter [ms]':>12} "
        f"{'ActRate [Hz]':>14} {'GlobRate [Hz]':>14} "
        f"{'Mbps':>10} {'Util %':>9}"
    )
    print(header)
    print("-" * len(header))

    for r in rows:
        mean_ms = "-" if r["mean_ms"] in ("", None) else f"{float(r['mean_ms']):.3f}"
        jitter_ms = "-" if r["jitter_ms"] in ("", None, "") else f"{float(r['jitter_ms']):.3f}"
        act_rate = "-" if r["active_rate_hz"] in ("", None) else f"{float(r['active_rate_hz']):.1f}"
        glob_rate = "-" if r["global_rate_hz"] in ("", None) else f"{float(r['global_rate_hz']):.1f}"
        mbps = "-" if r["rx_mbps"] in ("", None) else f"{float(r['rx_mbps']):.3f}"
        util = "-" if r["link_utilization"] in ("", None) else f"{float(r['link_utilization'])*100:.4f}"

        print(
            f"{r['class']:<12} {r['stream']:<12} {r['pcp']:<5} "
            f"{mean_ms:>10} {jitter_ms:>12} "
            f"{act_rate:>14} {glob_rate:>14} "
            f"{mbps:>10} {util:>9}"
        )

    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create unified TSN per-class report from latency JSON."
    )
    parser.add_argument(
        "--in-json",
        dest="in_json",
        default="omnet/results/tsn/tsn_latency_summary.json",
        help="Input JSON produced by parse_end_to_end_delay.py",
    )
    parser.add_argument(
        "--out-csv",
        dest="out_csv",
        default="omnet/results/tsn/tsn_unified_report.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--config-name",
        dest="config_name",
        default="FlatThorInetTsn",
        help="Config name label (e.g., FlatThorInetTsn)",
    )
    parser.add_argument(
        "--sim-time",
        dest="sim_time",
        type=float,
        default=0.5,
        help="Simulation time in seconds (sim-time-limit, default: 0.5)",
    )

    args = parser.parse_args()

    # Load latency summary JSON
    with open(args.in_json, "r") as f:
        latency_summary = json.load(f)

    # Build rows with both global + active rates
    rows = build_unified_rows(
        latency_summary=latency_summary,
        config_name=args.config_name,
        sim_time_s=args.sim_time,
    )

    # Console output
    print_console_table(rows)

    # CSV output
    out_dir = os.path.dirname(args.out_csv)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    fieldnames = [
        "config",
        "class",
        "stream",
        "pcp",
        "count",
        "min_ms",
        "mean_ms",
        "max_ms",
        "jitter_ms",
        "global_rate_hz",
        "active_rate_hz",
        "rx_mbps",
        "link_utilization",
        "start_time",
        "stop_time",
        "active_duration",
    ]

    with open(args.out_csv, "w", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote unified TSN report to: {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

