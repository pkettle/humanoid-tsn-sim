# Humanoid TSN Simulation — Baseline + TSN README

## Overview

This repository defines the **Humanoid TSN Simulation Framework**, an early-stage environment for evaluating **deterministic Ethernet (TSN) architectures** for next‑generation humanoid robots. These simulations target architectures combining:

- **Thor/Orin** central compute  
- **AURIX** safety microcontrollers  
- **Zonal controllers**  
- **Deterministic Ethernet paths (1–25 GbE)**  
- **TSN features** such as 802.1Qbv (Time-Aware Shaper)

Two topologies now exist:

1. **FlatThorInet** — baseline (best-effort Ethernet)  
2. **FlatThorInetTsn** — TSN-capable (TsnSwitch with gates initially always open)

---

## Repository Structure

```
humanoid-tsn-sim/
├── configs/
│   ├── topology_flattened_thor.yaml
│   ├── topology_aurix_safety.yaml
│   ├── traffic_baseline.yaml
│   └── schedule_2ms_cycle.yaml
├── docker/
│   ├── Dockerfile.tsn-sim
│   └── docker-compose.yml
├── omnet/
│   ├── flat_thor_inet.ned
│   ├── flat_thor_inet_tsn.ned
│   ├── omnetpp_flat_thor_inet.ini
│   └── omnetpp_flat_thor_inet_tsn.ini
├── results/
│   ├── baseline/
│   └── tsn/
├── scripts/
│   ├── run_sim.sh
│   ├── parse_scalars.py
│   ├── parse_end_to_end_delay.py
│   ├── humanoid_tsn_sim.py
│   ├── sweep_architectures.py
│   └── stingray/
└── README.md
```

---

# 1. Project Goals

The simulation framework is designed to evaluate:

- Zonal Ethernet architectures for humanoids  
- Latency & jitter under best-effort vs. TSN (Qbv)  
- Multi-zone UDP sensor/actuator traffic  
- Deterministic switch scheduling under 2ms/1ms/500µs cycles  
- Scaling toward 60+ DOF locomotion workloads  

### Current Achievements
- ✔ Fully containerized OMNeT++ 6.2 + INET build  
- ✔ Baseline network: `FlatThorInet`  
- ✔ TSN network: `FlatThorInetTsn` (TsnSwitch inserted)  
- ✔ UDP packet generation fixed (thor → zone)  
- ✔ End-to-end delay exported for both baseline & TSN  
- ✔ Channel stats, throughput, drops, utilization exported  
- ✔ NED + INI fully validated under Docker  

### Current Limitations
- TSN gates are present but **configured “always open”**  
- No real Qbv schedule applied yet  
- YAML → INI mapping not integrated  
- No multi-priority queues or shaping yet  

---

# 2. Build Environment (Docker)

Build container:

```bash
docker compose -f docker/docker-compose.yml build
```

Run OMNeT++ environment:

```bash
docker compose -f docker/docker-compose.yml run --rm tsn-sim
```

---

# 3. Running Simulations

## Baseline (best-effort Ethernet)
```bash
opp_run -u Cmdenv -n "/root/inet/src:/workspace" -l INET omnet/omnetpp_flat_thor_inet.ini
```

## TSN (TsnSwitch)
```bash
opp_run -u Cmdenv -n "/root/inet/src:/workspace" -l INET omnet/omnetpp_flat_thor_inet_tsn.ini
```

---

# 4. Parsing Results

### Scalars → CSV
```bash
python3 omnet/scripts/parse_scalars.py omnet/results/baseline/General-#0.sca omnet/results/baseline/scalars_parsed.csv
```

### Latency → CSV
```bash
python3 omnet/scripts/parse_end_to_end_delay.py omnet/results/baseline/General-#0.vec omnet/results/baseline/latency_parsed.csv
```

Same for `results/tsn/`.

---

# 5. Current Observations

Both baseline and TSN-open‑gate runs show:

- ~401 packets delivered  
- Throughput ~4.5 Mb/s  
- End‑to‑end delay grows 1 ms → ~19 ms  
- TSN (with open gates) matches best‑effort behavior exactly  

This validates correct TSN topology setup.

---

# 6. TSN Model Status

- `TsnSwitch` inserted in core and access layers  
- Egress gate control enabled  
- Bitrates explicitly set  
- No schedule yet (Qbv not applied)

Ready for gate‑timing insertion.

---

# 7. Next Steps

### Phase A — Introduce Qbv (2 ms cycle)
- Add gateStates and gateTimes arrays  
- Apply to `coreSwitch` and `accessSwitch`  
- Validate shaping

### Phase B — YAML → INI generator

### Phase C — Scaling to humanoid workloads  
- Multi-zone  
- Mixed flows  
- Latency bands

---

# 8. Stingray Mode Continuation Prompt

```
You are now in ChatGPT Stingray Mode. Resume the “Humanoid TSN Simulation” project.

Project state:
- Baseline and TSN networks both working.
- UDP + latency recording validated.
- TSN gates active but always-open.
- Next step: introduce 2 ms Qbv schedule and YAML→INI mapping.

Continue from this exact state.
```

---

# 9. Maintainer

This project is part of the **Stingray Humanoid Networking Architecture** research effort.