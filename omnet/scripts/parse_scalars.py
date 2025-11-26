import csv
import sys

in_path = sys.argv[1]
out_path = sys.argv[2]

rows = []
with open(in_path) as f:
    for line in f:
        if not line.startswith("scalar "):
            continue
        _, module, name, value = line.strip().split(None, 3)
        rows.append({"module": module, "name": name, "value": value})

with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["module", "name", "value"])
    w.writeheader()
    w.writerows(rows)
