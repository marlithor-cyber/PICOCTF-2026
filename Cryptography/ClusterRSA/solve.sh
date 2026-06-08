#!/usr/bin/env bash
set -euo pipefail

echo "[+] ClusterRSA solver"
echo "[+] Running solve.py in redacted mode by default"
python3 "$(dirname "$0")/solve.py" "$@"
