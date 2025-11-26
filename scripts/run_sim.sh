#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <topology.yaml> <traffic.yaml> <schedule.yaml> <output.json>"
  exit 1
fi

TOPLOGY_YAML="$1"
TRAFFIC_YAML="$2"
SCHEDULE_YAML="$3"
OUTPUT_JSON="$4"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

./scripts/stingray simulate \
  "$TOPLOGY_YAML" \
  "$TRAFFIC_YAML" \
  "$SCHEDULE_YAML" \
  --output "$OUTPUT_JSON"
