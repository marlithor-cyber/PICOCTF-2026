#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export DOT_SAGE="${DOT_SAGE:-/tmp/sage-dot}"
mkdir -p "$DOT_SAGE"

echo "[+] Running Sage NTRU lattice recovery"

if command -v sage >/dev/null 2>&1; then
    sage solve.sage
elif [ -f "$HOME/miniforge3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
    conda activate sage
    sage solve.sage
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
    conda activate sage
    sage solve.sage
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate sage
    sage solve.sage
else
    echo "[-] SageMath was not found."
    echo "[-] Install SageMath or run: conda activate sage"
    exit 1
fi

echo "[+] Running Python redacted flag helper"
python3 solve.py "$@"
