#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[+] Black Cobra Pepper solver"
echo "[+] Running in redacted mode unless --show-flag is passed"
python3 "$SCRIPT_DIR/solve.py" "$@"
