#!/usr/bin/env python3
import sys
import csv
from pathlib import Path

def parse_sca(sca_path: Path, out_path: Path):
    """
    Parse an OMNeT++ .sca file and extract all scalar lines.

    OMNeT++ scalar line format (simplified):

        scalar <module> <name> <value> [attrname attrvalue]...

    We keep only:
        module, name, value

    and ignore run/config/attr lines.
    """
    lines = sca_path.read_text().splitlines()
    rows = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # We only care about scalar lines
        if not line.startswith("scalar "):
            continue

        parts = line.split()
        if len(parts) < 4:
            # Expect: scalar <module> <name> <value>
            continue

        # parts[0] = "scalar"
        module = parts[1]
        name   = parts[2]

        # value may be float or int
        value_str = parts[3]
        try:
            value = float(value_str)
        except ValueError:
            # If it’s something odd, just skip it
            continue

        rows.append((module, name, value))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["module", "name", "value"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")

def main():
    if len(sys.argv) != 3:
        print("Usage: parse_scalars.py input.sca output.csv")
        sys.exit(1)

    sca_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not sca_path.is_file():
        print(f"Error: input sca file not found: {sca_path}")
        sys.exit(1)

    parse_sca(sca_path, out_path)

if __name__ == "__main__":
    main()
