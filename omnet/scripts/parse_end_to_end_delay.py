import sys, csv

vec_path = sys.argv[1]
out_path = sys.argv[2]

latency_records = []
current_vec_ids = {}

with open(vec_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        # Header lines: define which vector IDs we care about
        if line.startswith("vector "):
            parts = line.split()
            if len(parts) < 4:
                continue
            vec_id = parts[1]
            module = parts[2]
            name   = parts[3]
            # Match any delay-like name
            if ("endToEndDelay" in name) or ("oneWayDelay" in name) or ("delay" in name):
                current_vec_ids[vec_id] = (module, name)
            continue

        # Data lines: id time value [optional extra columns...]
        parts = line.split()
        if len(parts) >= 3:
            vec_id = parts[0]
            if vec_id in current_vec_ids:
                try:
                    t = float(parts[1])
                    v = float(parts[2])
                except ValueError:
                    continue
                module, name = current_vec_ids[vec_id]
                latency_records.append({
                    "module": module,
                    "name": name,
                    "time": t,
                    "value": v,
                })

with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["module","name","time","value"])
    w.writeheader()
    w.writerows(latency_records)