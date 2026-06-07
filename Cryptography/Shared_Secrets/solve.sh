#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[*] Running Shared Secrets solver in redacted mode"
python3 solve.py
echo "[*] Solver finished"
echo "[*] Full flag is saved locally to flag.txt; it is not printed unless --show-flag is used"
