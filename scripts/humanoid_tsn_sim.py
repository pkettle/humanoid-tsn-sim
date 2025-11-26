#!/usr/bin/env python3
"""
humanoid_tsn_sim.py

Main engine for the `stingray` CLI:

    stingray simulate <topology.yaml> <traffic.yaml> <schedule.yaml> --output <results.json>

Pipeline:
  1. Parse YAML (topology, traffic, schedule)
  2. Generate OMNeT++ NED (tsn_network.ned)
  3. Generate OMNeT++ INI (omnetpp.ini)
  4. Run OMNeT++ in CLI mode: opp_run -u Cmdenv -f omnetpp.ini
  5. (Stub) Run scavetool to extract latency/jitter; emit JSON

Everything is intentionally minimal and human-readable.
"""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is not installed inside the container. "
            "Install pyyaml into the OMNeT++ venv (see Dockerfile.tsn-sim)."
        )
    with path.open("r") as f:
        return yaml.safe_load(f) or {}


# ---------------------------------------------------------------------------
# Node + link mappings (YAML → INET modules)
# ---------------------------------------------------------------------------

def map_node_module(node: Dict[str, Any]) -> str:
    """
    Map a YAML node type to a TSN-capable INET component.
    These module names will be aligned with INET/CoRE4INET once those
    libraries are present in the container.

    Example YAML:
      nodes:
        thor0:
          type: endpoint
          role: thor
        core0:
          type: tsn_switch
          role: core
    """
    t = (node.get("type") or "").lower()
    role = (node.get("role") or "").lower()

    # First pass: treat everything as TSN-capable hosts/switches
    if t in ("switch", "tsn_switch", "bridge"):
        return "inet.node.tsn.TsnSwitch"
    if t in ("endpoint", "device", "host"):
        return "inet.node.tsn.TsnDevice"

    # Role-based fallbacks
    if "thor" in role:
        return "inet.node.tsn.TsnDevice"
    if "zone" in role:
        return "inet.node.tsn.TsnDevice"
    if "actuator" in role:
        return "inet.node.tsn.TsnDevice"

    # Default
    return "inet.node.tsn.TsnDevice"


def map_link_datarate(speed: str) -> str:
    """
    Map YAML speed like '25G', '1G', '100M', '10M' to OMNeT++ datarate strings.
    """
    s = speed.strip().upper()
    if s.endswith("GBPS"):
        return s
    if s.endswith("G"):
        return s[:-1] + "Gbps"
    if s.endswith("MBPS"):
        return s
    if s.endswith("M"):
        return s[:-1] + "Mbps"
    return "1Gbps"


def map_link_delay(link: Dict[str, Any]) -> str:
    """
    Map various YAML delay fields to an OMNeT++ time value.
    """
    if "delay_ns" in link:
        return f'{link["delay_ns"]}ns'
    if "delay_us" in link:
        return f'{link["delay_us"]}us'
    if "delay_ms" in link:
        return f'{link["delay_ms"]}ms'
    return "100ns"


# ---------------------------------------------------------------------------
# NED generation
# ---------------------------------------------------------------------------

def generate_ned(topology: Dict[str, Any], network_name: str = "HumanoidTsnNetwork") -> str:
    """
    Generate a simple NED network from the YAML topology.

    Expected topology shape (first iteration):

      nodes:
        thor0:
          type: endpoint
          role: thor
        core0:
          type: tsn_switch
          role: core

      links:
        - name: thor0_to_core0
          endpoints: [thor0, core0]
          speed: 25G
          delay_ns: 100
    """
    nodes = topology.get("nodes", {})
    links = topology.get("links", [])

    lines: List[str] = []
    lines.append("package humanoidtsn;")
    lines.append("")
    lines.append("import inet.node.tsn.TsnDevice;")
    lines.append("import inet.node.tsn.TsnSwitch;")
    lines.append("import ned.DatarateChannel;")
    lines.append("")
    lines.append(f"network {network_name}")
    lines.append("{")
    lines.append("    parameters:")
    lines.append('        @display("bgb=900,600");')
    lines.append("")
    lines.append("    submodules:")

    # Submodules – simple grid layout
    x_step = 150
    for idx, (name, node) in enumerate(nodes.items()):
        module_type = map_node_module(node)
        x = 100 + (idx % 5) * x_step
        y = 100 + (idx // 5) * 120
        lines.append(f"        {name}: {module_type} {{")
        lines.append(f'            @display("p={x},{y}");')
        lines.append("        }")

    lines.append("")
    lines.append("    channels:")

    # Channels – one DatarateChannel per link
    for i, link in enumerate(links):
        lname = link.get("name") or f"link{i}"
        datarate = map_link_datarate(str(link.get("speed", "1G")))
        delay = map_link_delay(link)
        chan_name = f"{lname}Channel"
        lines.append(f"        {chan_name}: DatarateChannel {{")
        lines.append(f"            datarate = {datarate};")
        lines.append(f"            delay = {delay};")
        lines.append("        }")

    lines.append("")
    lines.append("    connections allowunconnected:")

    # Connections
    for i, link in enumerate(links):
        lname = link.get("name") or f"link{i}"
        chan_name = f"{lname}Channel"
        eps = link.get("endpoints", [])
        if len(eps) == 2:
            a, b = eps
            # Using ethg++ as a generic Ethernet gate vector; adjust once real INET TSN types are in.
            lines.append(f"        {a}.ethg++ <--> {chan_name} <--> {b}.ethg++;")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# INI generation (TSN/Qbv scaffolding)
# ---------------------------------------------------------------------------

def generate_qbv_ini(schedule: Dict[str, Any]) -> List[str]:
    """
    Generate TSN Qbv gate schedule snippets from YAML.

    Expected schedule YAML (first pass):

      switches:
        - name: core0
          queues:
            - traffic_class: 0
              offset_ms: 0.0
              durations_ms: [1.0, 1.0]
            - traffic_class: 1
              offset_ms: 1.0
              durations_ms: [1.0, 1.0]
    """
    switches = schedule.get("switches", [])
    out: List[str] = []

    for sw in switches:
        swname = sw["name"]
        queues = sw.get("queues", [])
        if not queues:
            continue

        out.append(f"*.{swname}.eth[*].macLayer.queue.numTrafficClasses = {len(queues)}")

        for q in queues:
            tc = int(q["traffic_class"])
            offset_ms = float(q.get("offset_ms", 0.0))
            durations_ms = q.get("durations_ms", [])
            dlist = "[" + ",".join(f"{d}ms" for d in durations_ms) + "]"

            out.append(f"*.{swname}.eth[*].macLayer.queue.transmissionGate[{tc}].offset = {offset_ms}ms")
            out.append(f"*.{swname}.eth[*].macLayer.queue.transmissionGate[{tc}].durations = {dlist}")

        out.append("")

    return out


def generate_ini(
    topology: Dict[str, Any],
    traffic: Dict[str, Any],
    schedule: Dict[str, Any],
    ned_filename: str,
    network_name: str = "HumanoidTsnNetwork",
) -> str:
    """
    Generate omnetpp.ini for the TSN network.

    For now we:
      - set the network name
      - set a sim-time-limit
      - set a global NED path (current directory)
      - inject Qbv schedule config
      - leave traffic config as a TODO stub
    """
    lines: List[str] = []

    lines.append("[General]")
    lines.append(f"network = {network_name}")
    lines.append("sim-time-limit = 10ms")
    lines.append("")
    # IMPORTANT: global option, not per-object; and path is a directory, not a file
    lines.append("ned-path = .")
    lines.append("")

    # Qbv schedule injection
    lines.append("# === TSN/Qbv schedule ===")
    lines.extend(generate_qbv_ini(schedule))
    lines.append("")

    # Traffic placeholder
    lines.append("# === Traffic (placeholder) ===")
    lines.append("# TODO: map YAML traffic into actual INET/TSN apps")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# OMNeT++ runner with robust opp_run lookup
# ---------------------------------------------------------------------------

def _find_opp_run_executable() -> str:
    """
    Search for the OMNeT++ 'opp_run' binary.

    Search order:
      1. PATH
      2. $OMNETPP_ROOT/bin/opp_run
      3. /opt/omnetpp/bin/opp_run (legacy/manual)
      4. /root/omnetpp/bin/opp_run (official container)
    """
    from_path = shutil.which("opp_run")
    if from_path:
        return from_path

    env_root = os.environ.get("OMNETPP_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root) / "bin" / "opp_run")

    candidates.append(Path("/opt/omnetpp/bin/opp_run"))
    candidates.append(Path("/root/omnetpp/bin/opp_run"))

    for cand in candidates:
        if cand.exists() and cand.is_file():
            return str(cand)

    raise RuntimeError(
        "Could not find `opp_run`.\n"
        "Checked PATH, $OMNETPP_ROOT/bin, /opt/omnetpp/bin, and /root/omnetpp/bin.\n"
        "Ensure OMNeT++ is installed or use the official OMNeT++ container base image."
    )


def run_opp_run(ini_path: Path, cwd: Path) -> None:
    """
    Run OMNeT++ in CLI mode.

        opp_run -u Cmdenv -f omnetpp.ini
    """
    opp_run_exe = _find_opp_run_executable()
    cmd = [opp_run_exe, "-u", "Cmdenv", "-f", str(ini_path)]
    print(f"[stingray] Running OMNeT++: {' '.join(cmd)} (cwd={cwd})")
    subprocess.run(cmd, cwd=str(cwd), check=True)


# ---------------------------------------------------------------------------
# scavetool stub
# ---------------------------------------------------------------------------

def extract_metrics_with_scavetool(run_dir: Path) -> Dict[str, Any]:
    """
    Minimal stub – just reports what .sca/.vec files exist.
    Replace with real scavetool integration once TSN flows are defined.
    """
    scalar_files = list(run_dir.glob("*.sca"))
    vector_files = list(run_dir.glob("*.vec"))

    if not scalar_files and not vector_files:
        return {
            "status": "ok",
            "note": "No .sca/.vec files produced yet. Likely no INET/TSN modules or sim errors.",
        }

    return {
        "status": "ok",
        "scalars": [p.name for p in scalar_files],
        "vectors": [p.name for p in vector_files],
        "note": "scavetool extraction not yet implemented",
    }


# ---------------------------------------------------------------------------
# Simulation wrapper
# ---------------------------------------------------------------------------

def simulate(topology_path: Path, traffic_path: Path, schedule_path: Path, output_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    gen_dir = project_root / "results" / "_generated"
    gen_dir.mkdir(parents=True, exist_ok=True)

    topology = load_yaml(topology_path)
    traffic = load_yaml(traffic_path)
    schedule = load_yaml(schedule_path)

    ned_path = gen_dir / "tsn_network.ned"
    ini_path = gen_dir / "omnetpp.ini"

    print(f"[stingray] Generating NED → {ned_path}")
    ned_path.write_text(generate_ned(topology))

    print(f"[stingray] Generating INI → {ini_path}")
    ini_path.write_text(generate_ini(topology, traffic, schedule, ned_path.name))

    # Run OMNeT++
    run_opp_run(ini_path, cwd=gen_dir)

    # Extract metrics (stub)
    metrics = extract_metrics_with_scavetool(gen_dir)

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[stingray] Writing JSON → {output_path}")
    output_path.write_text(json.dumps(metrics, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stingray",
        description="TSN simulation CLI for humanoid zonal networks (YAML → OMNeT++).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sim = sub.add_parser("simulate", help="Run a TSN simulation from YAML configs.")
    sim.add_argument("topology", type=str)
    sim.add_argument("traffic", type=str)
    sim.add_argument("schedule", type=str)
    sim.add_argument("--output", "-o", type=str, default="results/run.json")

    return parser


def main(argv=None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "simulate":
        simulate(
            Path(args.topology),
            Path(args.traffic),
            Path(args.schedule),
            Path(args.output),
        )
    else:
        parser.error("Unknown command")


if __name__ == "__main__":
    main()
