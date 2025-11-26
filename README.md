# **Humanoid TSN Simulation — Baseline README**

## **Overview**

This repository defines the **Humanoid TSN Simulation Framework**, an early-stage environment for evaluating **deterministic Ethernet topologies** for next-generation humanoid robots (Thor/Orin + AURIX safety islands + zonal controllers).  
The goal is to produce a scalable simulation environment for:

- Zonal humanoid networking (1–25 GbE)
- TSN scheduling (802.1Qbv, Qbu, Qci)
- Multi-zone UDP sensor traffic
- Switch-to-Thor deterministic paths
- Traffic shaping + latency analysis
- Baseline measurement of “flattened Thor” architectures

This baseline uses:

- **OMNeT++ 6.2**
- **INET Framework** (cloned & built inside Docker)
- A custom **FlatThorInet** topology (Thor → Core → Access → Zones)

This README documents the **current working state**, build/run instructions, and known limitations.

---

## **Repository Structure**

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
│   └── omnetpp_flat_thor_inet.ini
├── results/
│   └── flat_thor_inet/
├── scripts/
│   ├── run_sim.sh
│   ├── humanoid_tsn_sim.py
│   ├── sweep_architectures.py
│   └── stingray/
└── README.md
```

---

# **1. Project Goals (Baseline Milestone)**

This commit captures the **first complete end-to-end execution** of OMNeT++ inside a Docker environment:

### ✔ **Current Achievements**
- Fully containerized OMNeT++ 6.2 + INET build  
- Custom flattened Thor network topology (`flat_thor_inet.ned`)  
- Working simulation run with OMNeT++ Cmdenv  
- Results exported (`*.vec`, `*.vci`, `*.sca`, `*.elog`)  
- 465 simulation vectors confirmed  
- Tools for post-processing (`opp_scavetool`) validated  

### ❗ **Current Limitations**
- UdpBasicApp is configured but **no UDP packets are being generated yet**  
- Ethernet MAC counters remain idle (`txPk`, `rxPk`, `throughput`)  
- No latency, jitter, or utilization metrics  
- TSN features not wired into the topology  

This README serves as a stable baseline before enabling traffic and TSN scheduling.

---

# **2. Build Environment (Docker)**

The project uses a dedicated Docker image that includes:

- OMNeT++ 6.2  
- INET cloned and built from GitHub  
- Python (for YAML config loading)  
- `opp_makemake`, `opp_run`, `opp_scavetool` available inside container  

### **Build the container**

```bash
docker compose -f docker/docker-compose.yml build
```

### **Start an interactive OMNeT++ session**

```bash
docker compose -f docker/docker-compose.yml run --rm tsn-sim
```

You will be dropped into:

```
(omnetpp/.venv) omnetpp-:/workspace$
```

This is the environment where all OMNeT++ commands run.

---

# **3. Running the Simulation**

### **From inside the container**

```bash
opp_run -u Cmdenv   -n /root/inet/src:/workspace   -l INET   /workspace/omnet/omnetpp_flat_thor_inet.ini
```

You should see:

```
Setting up network "omnet.FlatThorInet"...
Simulation time limit reached -- at t=0.01s
End.
```

Results appear under:

```
results/flat_thor_inet/
```

---

# **4. Inspecting Output**

### **Export all vectors into a readable CSV**

```bash
opp_scavetool x   -F CSV-R   -o /workspace/results/flat_thor_inet/all_vectors.csv   /workspace/results/flat_thor_inet/General-\#0.vec
```

### **Preview first lines**

```bash
head /workspace/results/flat_thor_inet/all_vectors.csv
```

### **Search for specific modules**

```bash
grep "FlatThorInet.zone0" all_vectors.csv
grep "FlatThorInet.thor"  all_vectors.csv
grep "mac" all_vectors.csv
```

### **Expected behavior (baseline)**

- 465 vectors produced  
- Many built-in vectors populated (queues, rates, etc.)  
- Application & MAC vectors currently remain empty (`vectime="", vecvalue=""`)  
  → UDP apps not yet injecting traffic in this INET variant  

This is the starting point for debugging traffic injection.

---

# **5. Project Status + Next Steps**

### **Immediate next steps**
1. Align `UdpBasicApp` with correct StandardHost fields  
2. Confirm packet injection from zones → core → thor  
3. Validate MAC-level counters  
4. Export end-to-end delay vectors  

### **Medium-term**
- Integrate TSN modules (Qbv, Qbu, Qci)  
- Ingest YAML schedule configurations  
- Build realistic humanoid traffic models (IMU, joint encoders, F/T sensors)  
- Introduce HSB (Holoscan Bridge) GPU node  

### **Long-term**
- Architecture sweeps  
- Latency/jitter envelopes for 60-DOF workloads  
- Compare flattened vs zonal architectures  
- Scaling to multi-GbE and multi-path TSN topologies  

---

# **6. Known Issues at This Baseline**

| Component      | Status | Notes |
|----------------|--------|-------|
| Docker build   | ✔ | Stable, INET compiled |
| Topology load  | ✔ | FlatThorInet loads cleanly |
| Simulation run | ✔ | Completes 10ms timeline |
| Vector export  | ✔ | 465 vectors exported |
| UdpBasicApp    | ❌ | Configured but not sending packets |
| MAC counters   | ❌ | No transmitted/received frames |
| TSN features   | ⏳ | Not yet integrated |

---

# **7. Maintainer**

This project is part of the **Stingray** humanoid control & networking architecture research.  
For design, debugging, and architecture modeling assistance:  
**ChatGPT (Stingray Mode)** is integrated into this workflow.

# 8.7 Stingray Mode Continuation Prompt

You are now in ChatGPT Stingray Mode. Resume the “Humanoid TSN Simulation” project.

Project state:
- OMNeT++ 6.2 + INET built inside Docker.
- FlatThorInet topology loads and runs.
- 465 vectors exported but UdpBasicApp sends no packets.
- Need to fix UDP generation and validate MAC counters.
- YAML front-end (topology/traffic/schedule) exists but not yet mapped into OMNeT++.

Next tasks:
1. Diagnose and repair UdpBasicApp configuration.
2. Produce working end-to-end traffic through FlatThorInet.
3. Export latency and queueing metrics.
4. Prepare migration path to TSN (802.1Qbv) switch + YAML schedule.
5. Maintain all configs in Stingray Mode coding style.

Continue from this exact state.