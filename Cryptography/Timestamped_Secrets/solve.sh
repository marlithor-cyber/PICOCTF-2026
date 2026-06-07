#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[+] Running Timestamped Secrets solver"
echo "[+] Redacted mode is used by default"
echo "[+] Forwarding extra arguments to solve.py"

python3 solve.py "$@"
