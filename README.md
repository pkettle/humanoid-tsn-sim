# Humanoid TSN Simulation --- Baseline README (Updated)

## Overview

This repository defines the **Humanoid TSN Simulation Framework**, an
environment for evaluating **deterministic Ethernet topologies** for
next‑generation humanoid robots (Thor/Orin + AURIX safety islands +
zonal controllers).\
The framework enables:

-   Zonal humanoid networking (1--25 GbE)
-   TSN scheduling (802.1Qbv, Qbu, Qci)
-   Multi‑zone UDP sensor traffic
-   Switch‑to‑Thor deterministic paths
-   Traffic shaping + latency analysis
-   Baseline comparison of flattened vs zonal architectures

This baseline uses:

-   **OMNeT++ 6.2**
-   **INET Framework** (built inside Docker)
-   A custom **FlatThorInet** topology (Thor → Core → Access → Zones)

This README captures the **working baseline**, including verified UDP
packet flow and end‑to‑end latency extraction.

------------------------------------------------------------------------

## Repository Structure
.
├── configs
│   ├── schedule_2ms_cycle.yaml
│   ├── topology_aurix_safety.yaml
│   ├── topology_flattened_thor.yaml
│   └── traffic_baseline.yaml
├── docker
│   ├── docker-compose.yml
│   └── Dockerfile.tsn-sim
├── omnet
│   ├── flat_thor_inet.ned
│   ├── omnetpp_flat_thor_inet.ini
│   ├── results
│   │   ├── all_vectors.csv
│   │   ├── endToEndDelay_scalars.txt
│   │   ├── General-#0.sca
│   │   ├── General-#0.vci
│   │   ├── General-#0.vec
│   │   ├── latency_parsed.csv
│   │   ├── packetReceived_scalars.txt
│   │   ├── packetSent_scalars.txt
│   │   ├── scalars.csv
│   │   └── scalars_parsed.csv
│   └── scripts
│       ├── parse_end_to_end_delay.py
│       └── parse_scalars.py
├── omnetpp.ini
├── prompt.chatgpt
├── README.md
└── scripts
    ├── humanoid_tsn_sim.py
    ├── run_sim.sh
    ├── stingray
    └── sweep_architectures.py


------------------------------------------------------------------------

## 1. Project Goals (Baseline Milestone)

This commit captures the **first full working baseline** of the Humanoid
TSN Simulation environment.

### ✔ Current Achievements

-   Fully containerized OMNeT++ 6.2 + INET build\
-   Clean, validated flattened Thor network topology (`FlatThorInet`)\
-   Successful simulation runtime under Cmdenv\
-   UDP traffic successfully flowing from Thor → Access → Zones\
-   MAC/Channel counters operational\
-   End‑to‑end delay vectors recorded and parsed\
-   Latency parsed into CSV via `parse_end_to_end_delay.py`\
-   Scalar metrics parsed via `parse_scalars.py`

### ❗ Current Limitations

-   TSN (Qbv/Qci/Qbu) not yet enabled\
-   YAML schedule files not yet mapped to switch configuration\
-   Only best‑effort (non‑TSN) baseline currently captured

This README documents the validated baseline before enabling TSN.

------------------------------------------------------------------------

## 2. Build Environment (Docker)

The simulation is entirely containerized and reproducible.

### Build:

``` bash
docker compose -f docker/docker-compose.yml build
```

### Start an interactive session:

``` bash
docker compose -f docker/docker-compose.yml run --rm tsn-sim
```

You will enter the OMNeT++ environment:

    (omnetpp/.venv) omnetpp-:/workspace$

------------------------------------------------------------------------

## 3. Running the Simulation

Execute:

``` bash
opp_run -u Cmdenv   -n "/root/inet/src:/workspace"   -l INET   omnet/omnetpp_flat_thor_inet.ini
```

A successful baseline run ends with output like:

    Simulation time limit reached -- at t=0.5s
    End.

Results appear in:

    omnet/results/

------------------------------------------------------------------------

## 4. Inspecting Output

### Export vectors:

``` bash
opp_scavetool x -F CSV-R   -o omnet/results/all_vectors.csv   omnet/results/General-#0.vec
```

### Export scalars:

``` bash
python3 scripts/parse_scalars.py   omnet/results/General-#0.sca   omnet/results/scalars_parsed.csv
```

### Extract end‑to‑end latency:

``` bash
python3 omnet/scripts/parse_end_to_end_delay.py   omnet/results/General-#0.vec   omnet/results/latency_parsed.csv
```

Example parsed latency:

    FlatThorInet.zone[0].app[0],endToEndDelay:vector,84.0,0.00102
    FlatThorInet.zone[0].app[0],endToEndDelay:vector,110.0,0.00201
    ...

Latency increases \~1--19 ms over a 0.5 s run in best‑effort Ethernet.

------------------------------------------------------------------------

## 5. Project Status + Next Steps

### Immediate next steps

1.  Bind YAML topology → OMNeT++ auto‑generation\
2.  Bind YAML traffic → OMNeT++ app config\
3.  Bind YAML schedule → Qbv gate control list\
4.  Add TSN‑capable switches (`TsnSwitch`)\
5.  Generate TSN vs best‑effort comparative metrics

### Medium‑term

-   Add realistic multimodal humanoid traffic (IMU, F/T, joint
    encoders)\
-   Introduce HSB (Holoscan Bridge) GPU node\
-   Multi‑GbE scaling tests

### Long‑term

-   Multi‑zone TSN deterministic pipelines\
-   Architecture sweeps for 60‑DOF humanoids\
-   Complete end‑to‑end latency + jitter envelope generation

------------------------------------------------------------------------

## 6. Known Issues

  Component        Status   Notes
  ---------------- -------- -----------------
  Docker build     ✔        Stable
  Topology load    ✔        Valid syntax
  UDP traffic      ✔        Packets flowing
  MAC counters     ✔        Operational
  Latency export   ✔        Working
  TSN features     ⏳       Pending

------------------------------------------------------------------------

## 7. Maintainer

This project is part of **Stingray** humanoid architecture R&D.\
For design, debugging, and modeling assistance:\
**ChatGPT (Stingray Mode)** collaborates directly within this workflow.

------------------------------------------------------------------------

## 8. Stingray Mode Continuation Prompt

You are now in ChatGPT Stingray Mode. Resume the "Humanoid TSN
Simulation" project.

Project state: - OMNeT++ 6.2 + INET built inside Docker. - FlatThorInet
topology loads and runs cleanly. - UDP traffic operational. - MAC
counters + latency metrics validated. - YAML interface exists but is not
yet connected.

Next tasks: 1. Bind YAML → NED/INI generation. 2. Implement TSN (Qbv)
switch variant. 3. Enable schedule import & deterministic windowing. 4.
Export latency/queueing metrics under TSN. 5. Maintain Stingray‑style
modular organization.

Continue from this exact state.