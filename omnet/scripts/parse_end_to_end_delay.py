#!/usr/bin/env python3
import sys
import csv
import re
from pathlib import Path

DELAY_PREFIXES = ("endToEndDelay", "oneWayDelay", "delay")

def parse_vec_for_delays(vec_path: Path, out_path: Path):
    """
    Parse an OMNeT++ .vec file and extract all vectors whose 'name'
    indicates a delay metric:
      - endToEndDelay*
      - oneWayDelay*
      - delay*
    Output CSV with columns: module,name,time,value
    """
    vec_lines = vec_path.read_text().splitlines()

    # Map: vector_id -> (module, name)
    id_to_info = {}
    ids_of_interest = set()

    # vector <id> <module> <name> ...
    vec_def_re = re.compile(r'^vector\s+(\d+)\s+([^\s]+)\s+([^\s]+)')

    # First pass: discover delay-related vectors
    for line in vec_lines:
        m = vec_def_re.match(line)
        if not m:
            continue
        vid = int(m.group(1))
        module = m.group(2)
        name = m.group(3)  # e.g. endToEndDelay:vector, delay:vector

        id_to_info[vid] = (module, name)

        if name.startswith(DELAY_PREFIXES):
            ids_of_interest.add(vid)

    rows = []

    # Second pass: extract data for those vectors
    for line in vec_lines:
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

        module, name = id_to_info.get(vid, ("", ""))
        rows.append((module, name, t, v))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["module", "name", "time", "value"])
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")

def main():
    if len(sys.argv) != 3:
        print("Usage: parse_end_to_end_delay.py input.vec output.csv")
        sys.exit(1)

    vec_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not vec_path.is_file():
        print(f"Error: input vec file not found: {vec_path}")
        sys.exit(1)

    parse_vec_for_delays(vec_path, out_path)

if __name__ == "__main__":
    main()
