#!/usr/bin/env bash
set -euo pipefail

echo "[+] Running shift registers solver"
echo "[+] Default mode redacts the recovered flag"
python3 solve.py "$@"
echo "[+] Done"
