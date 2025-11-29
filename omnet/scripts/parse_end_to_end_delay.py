#!/usr/bin/env python3
"""
parse_end_to_end_delay.py

Summarize end-to-end delay per traffic class (CONTROL / SENSOR / TELEMETRY)
from an OMNeT++ CSV-R export produced by opp_scavetool.

It tries two paths:

1) Preferred: use 'statistics' rows with name == 'endToEndDelay'
2) Fallback: use 'vector' rows whose name contains 'endToEndDelay'
   and compute min/mean/max/std (jitter) from the sample values, where each row's
   vecvalue may be a space-separated list of floats.

Jitter is defined as:
    standard deviation of end-to-end delay [ms].
"""

import argparse
import json
import re
import sys
from typing import Dict, Any, List

import pandas as pd

# ---------------------------------------------------------------------------
# Traffic class mapping
# ---------------------------------------------------------------------------

TRAFFIC_CLASSES = [
    {
        "name": "CONTROL",
        "stream": "control",
        "pcp": 7,  # IEEE-aligned highest priority
        # zone[0].app[0] UdpSink
        "module_regex": r"\.zone\[0\]\.app\[0\](\.|$)",
    },
    {
        "name": "SENSOR",
        "stream": "sensor",
        "pcp": 4,
        # zone[1].app[1] UdpSink
        "module_regex": r"\.zone\[1\]\.app\[1\](\.|$)",
    },
    {
        "name": "TELEMETRY",
        "stream": "telemetry",
        "pcp": 1,
        # zone[1].app[2] UdpSink
        "module_regex": r"\.zone\[1\]\.app\[2\](\.|$)",
    },
]


def classify_module(module_name: str) -> str:
    """
    Map a full module path to a traffic class name, or "" if none matches.
    """
    for tc in TRAFFIC_CLASSES:
        if re.search(tc["module_regex"], module_name):
            return tc["name"]
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attach_traffic_class(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["traffic_class"] = df["module"].apply(classify_module)
    return df[df["traffic_class"] != ""]


def _summarize_from_stats(stats_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Given a 'statistics' dataframe with columns:
      module, traffic_class, count, min, max, mean, (optional) stddev
    compute per-class bands (seconds → ms), including jitter_ms
    where jitter_ms is the average stddev in milliseconds if available.
    """
    summary: Dict[str, Any] = {"traffic_classes": {}}
    has_stddev = "stddev" in stats_df.columns

    for tc in TRAFFIC_CLASSES:
        name = tc["name"]
        rows = stats_df[stats_df["traffic_class"] == name]

        if rows.empty:
            summary["traffic_classes"][name] = {
                "stream": tc["stream"],
                "pcp": tc["pcp"],
                "present": False,
                "reason": "no matching endToEndDelay statistics found",
            }
            continue

        count = float(rows["count"].sum())
        min_s = float(rows["min"].min())
        max_s = float(rows["max"].max())
        mean_s = float(rows["mean"].mean())

        if has_stddev:
            std_s = float(rows["stddev"].mean())
            jitter_ms = std_s * 1e3
        else:
            jitter_ms = None

        summary["traffic_classes"][name] = {
            "stream": tc["stream"],
            "pcp": tc["pcp"],
            "present": True,
            "count": int(count),
            "min_ms": min_s * 1e3,
            "max_ms": max_s * 1e3,
            "mean_ms": mean_s * 1e3,
            "jitter_ms": jitter_ms,
        }

    return summary


def _summarize_from_vectors(vec_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Given a 'vector' dataframe where vecvalue holds space-separated lists of
    samples (as strings), compute per-class bands (seconds → ms) and jitter_ms.
    """
    value_col = "vecvalue" if "vecvalue" in vec_df.columns else "value"
    if value_col not in vec_df.columns:
        raise RuntimeError(
            "Vector fallback: neither 'vecvalue' nor 'value' column found in CSV-R."
        )

    import numpy as np

    summary: Dict[str, Any] = {"traffic_classes": {}}

    for tc in TRAFFIC_CLASSES:
        name = tc["name"]
        rows = vec_df[vec_df["traffic_class"] == name]

        if rows.empty:
            summary["traffic_classes"][name] = {
                "stream": tc["stream"],
                "pcp": tc["pcp"],
                "present": False,
                "reason": "no matching endToEndDelay vector samples found",
            }
            continue

        # Flatten all samples across all rows for this traffic class
        all_samples: List[float] = []
        for s in rows[value_col].dropna():
            # Each s is something like "0.00102 2.5e-05 0.00101 ..."
            for token in str(s).split():
                try:
                    all_samples.append(float(token))
                except ValueError:
                    continue

        if not all_samples:
            summary["traffic_classes"][name] = {
                "stream": tc["stream"],
                "pcp": tc["pcp"],
                "present": False,
                "reason": "no numeric samples could be parsed from vecvalue",
            }
            continue

        arr = np.array(all_samples, dtype=float)
        count = int(arr.size)
        min_s = float(arr.min())
        max_s = float(arr.max())
        mean_s = float(arr.mean())
        std_s = float(arr.std())  # seconds

        summary["traffic_classes"][name] = {
            "stream": tc["stream"],
            "pcp": tc["pcp"],
            "present": True,
            "count": count,
            "min_ms": min_s * 1e3,
            "max_ms": max_s * 1e3,
            "mean_ms": mean_s * 1e3,
            "jitter_ms": std_s * 1e3,
        }

    return summary


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def compute_latency_bands(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Try statistics first; if not available, fall back to vectors.
    """

    # ---------- Path 1: statistics ----------
    if "type" in df.columns and "name" in df.columns:
        stats_mask = (df["type"] == "statistics") & (df["name"] == "endToEndDelay")
        stats_df = df.loc[stats_mask].copy()

        if not stats_df.empty:
            stats_df = _attach_traffic_class(stats_df)
            if not stats_df.empty:
                return _summarize_from_stats(stats_df)

    # ---------- Path 2: vectors ----------
    if "type" not in df.columns or "name" not in df.columns:
        raise RuntimeError(
            "CSV-R does not contain 'type' or 'name' columns; cannot locate "
            "endToEndDelay vectors or statistics."
        )

    vec_mask = (df["type"] == "vector") & (df["name"].str.contains("endToEndDelay"))
    vec_df = df.loc[vec_mask].copy()

    if vec_df.empty:
        unique_names = sorted(set(df["name"].astype(str)))
        raise RuntimeError(
            "No 'statistics' rows with name 'endToEndDelay' and no 'vector' rows "
            "with name containing 'endToEndDelay' found.\n"
            f"Available names include (first few): {unique_names[:20]}"
        )

    vec_df = _attach_traffic_class(vec_df)
    if vec_df.empty:
        raise RuntimeError(
            "Found endToEndDelay vector rows, but none matched known traffic-class "
            "module patterns. Check TRAFFIC_CLASSES module_regex."
        )

    return _summarize_from_vectors(vec_df)


def print_human_readable(summary: Dict[str, Any]) -> None:
    """
    Print a simple table of per-class latency bands + jitter.
    """
    print("\nPer-traffic-class end-to-end latency bands (ms):\n")
    header = (
        f"{'Class':<10} {'Stream':<10} {'PCP':<5} {'Present':<8} "
        f"{'Count':>8} {'Min [ms]':>12} {'Mean [ms]':>12} {'Max [ms]':>12} {'Jitter [ms]':>14}"
    )
    print(header)
    print("-" * len(header))

    for tc in TRAFFIC_CLASSES:
        name = tc["name"]
        info = summary["traffic_classes"].get(name, {})
        present = info.get("present", False)

        if not present:
            print(
                f"{name:<10} {tc['stream']:<10} {tc['pcp']:<5} "
                f"{'no':<8} "
                f"{'-':>8} {'-':>12} {'-':>12} {'-':>12} {'-':>14}"
            )
            continue

        jitter_ms = info.get("jitter_ms", None)
        jitter_str = f"{jitter_ms:0.3f}" if jitter_ms is not None else "-"

        print(
            f"{name:<10} {info['stream']:<10} {info['pcp']:<5} "
            f"{'yes':<8} "
            f"{info['count']:>8d} "
            f"{info['min_ms']:>12.3f} "
            f"{info['mean_ms']:>12.3f} "
            f"{info['max_ms']:>12.3f} "
            f"{jitter_str:>14}"
        )
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Compute per-traffic-class end-to-end latency bands "
                    "(CONTROL / SENSOR / TELEMETRY) from OMNeT++ CSV-R results."
    )
    parser.add_argument(
        "--results-csv",
        default="results/tsn/tsn_results.csv",
        help="Path to CSV-R file exported by opp_scavetool "
             "(default: results/tsn/tsn_results.csv)",
    )
    parser.add_argument(
        "--out-json",
        default="",
        help="Optional path to write JSON summary. If empty, only prints to stdout.",
    )

    args = parser.parse_args(argv)

    df = pd.read_csv(args.results_csv)
    summary = compute_latency_bands(df)
    print_human_readable(summary)

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Wrote JSON summary to: {args.out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
