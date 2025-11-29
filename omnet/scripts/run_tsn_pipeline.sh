#!/usr/bin/env bash
set -euo pipefail

# End-to-end TSN pipeline:
#   1) Run OMNeT++ TSN config
#   2) Export results to CSV-R
#   3) Compute per-traffic-class latency + jitter
#   4) Export tidy per-class CSV
#   5) Export unified TSN report (latency + jitter + bandwidth + utilization)

WORKDIR="/workspace"
cd "${WORKDIR}"

INI="omnet/omnetpp_flat_thor_inet_tsn.ini"
RESULT_DIR="omnet/results/tsn"
CSV_R="${RESULT_DIR}/tsn_results.csv"
JSON="${RESULT_DIR}/tsn_latency_summary.json"
CLASSES_CSV="${RESULT_DIR}/tsn_latency_classes.csv"
UNIFIED_CSV="${RESULT_DIR}/tsn_unified_report.csv"
SIM_TIME=0.5   # seconds, matches sim-time-limit in INI

echo "[TSN-PIPELINE] Cleaning previous TSN results..."
rm -f "${RESULT_DIR}"/*.sca \
      "${RESULT_DIR}"/*.vec \
      "${CSV_R}" \
      "${JSON}" \
      "${CLASSES_CSV}" \
      "${UNIFIED_CSV}" || true

echo "[TSN-PIPELINE] Running OMNeT++ TSN simulation..."
opp_run -u Cmdenv -n "/root/inet/src:/workspace" \
  -l INET "${INI}"

echo "[TSN-PIPELINE] Exporting scalars + vectors to CSV-R..."
/root/omnetpp/bin/opp_scavetool export \
  -F CSV-R \
  -o "${CSV_R}" \
  "${RESULT_DIR}"/*.sca \
  "${RESULT_DIR}"/*.vec

echo "[TSN-PIPELINE] Computing per-traffic-class latency bands..."
python omnet/scripts/parse_end_to_end_delay.py \
  --results-csv "${CSV_R}" \
  --out-json "${JSON}"

echo "[TSN-PIPELINE] Exporting tidy per-class latency CSV..."
python omnet/scripts/tsn_export_latency_classes.py \
  --in-json "${JSON}" \
  --out-csv "${CLASSES_CSV}" \
  --config-name FlatThorInetTsn

echo "[TSN-PIPELINE] Exporting unified TSN report..."
python omnet/scripts/tsn_unified_report.py \
  --in-json "${JSON}" \
  --out-csv "${UNIFIED_CSV}" \
  --config-name FlatThorInetTsn \
  --sim-time "${SIM_TIME}"



echo "[TSN-PIPELINE] Done."
echo "  JSON      : ${JSON}"
echo "  CLASSES   : ${CLASSES_CSV}"
echo "  UNIFIED   : ${UNIFIED_CSV}"
