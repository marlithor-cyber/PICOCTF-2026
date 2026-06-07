#!/usr/bin/env bash
set -euo pipefail

echo "[+] Running Boneh-Durfee attack with SageMath"
sage solve.sage

echo "[+] Running RSA decryption helper"
python3 solve.py "$@"
