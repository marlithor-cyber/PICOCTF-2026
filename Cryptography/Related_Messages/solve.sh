#!/usr/bin/env bash
set -euo pipefail

echo "[+] Running Franklin-Reiter related message attack with SageMath"
sage solve.sage

echo "[+] Running redacted output helper"
python3 solve.py "$@"
