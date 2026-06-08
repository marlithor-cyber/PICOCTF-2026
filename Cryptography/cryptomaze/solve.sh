#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[*] Starting cryptomaze solver"
echo "[*] Redacted mode is used unless --show-flag is provided"
python3 solve.py "$@"
