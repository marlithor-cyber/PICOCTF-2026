#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
from pathlib import Path
from textwrap import shorten


SCRIPT_DIR = Path(__file__).resolve().parent
PUBLIC_PATH = SCRIPT_DIR / "public.txt"
RECOVERED_F_PATH = SCRIPT_DIR / "recovered_f.txt"
FLAG_PATH = SCRIPT_DIR / "flag.txt"
ASSETS_TEXT_DIR = SCRIPT_DIR / "assets" / "text_outputs"
REDACTED_FLAG = "picoCTF{...redacted...}"
EXPECTED_PREFIX = "pico" + "CTF{"


def parse_public(path: Path = PUBLIC_PATH) -> tuple[int, int, int, list[int], list[list[int]]]:
    values: dict[str, object] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {"N", "p", "q"}:
            values[key] = int(value)
        elif key in {"h", "ct"}:
            values[key] = ast.literal_eval(value)

    missing = {"N", "p", "q", "h", "ct"} - set(values)
    if missing:
        raise ValueError(f"missing public values: {', '.join(sorted(missing))}")

    n = int(values["N"])
    h = normalize_poly([int(x) for x in values["h"]], n)
    ct = [normalize_poly([int(x) for x in chunk], n) for chunk in values["ct"]]  # type: ignore[index]
    return int(values["N"]), int(values["p"]), int(values["q"]), h, ct


def normalize_poly(poly: list[int], n: int) -> list[int]:
    if len(poly) > n:
        raise ValueError(f"polynomial has {len(poly)} coefficients, expected at most {n}")
    return poly + [0] * (n - len(poly))


def cyclic_convolution(a: list[int], b: list[int], n: int, modulus: int | None = None) -> list[int]:
    out = [0] * n
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            out[(i + j) % n] += ai * bj
    if modulus is not None:
        out = [x % modulus for x in out]
    return out


def center_coeff(x: int, q: int) -> int:
    x %= q
    if x > q // 2:
        x -= q
    return x


def center_coeffs(values: list[int], q: int) -> list[int]:
    return [center_coeff(x, q) for x in values]


def invert_poly_mod_prime(f: list[int], n: int, p: int) -> list[int]:
    matrix = [[f[(row - col) % n] % p for col in range(n)] for row in range(n)]
    rhs = [1] + [0] * (n - 1)

    for col in range(n):
        pivot = None
        for row in range(col, n):
            if matrix[row][col] % p:
                pivot = row
                break
        if pivot is None:
            raise ValueError("polynomial is not invertible modulo p")

        if pivot != col:
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            rhs[col], rhs[pivot] = rhs[pivot], rhs[col]

        inv = pow(matrix[col][col] % p, -1, p)
        matrix[col] = [(value * inv) % p for value in matrix[col]]
        rhs[col] = (rhs[col] * inv) % p

        for row in range(n):
            if row == col:
                continue
            factor = matrix[row][col] % p
            if factor == 0:
                continue
            matrix[row] = [(matrix[row][idx] - factor * matrix[col][idx]) % p for idx in range(n)]
            rhs[row] = (rhs[row] - factor * rhs[col]) % p

    return rhs


def bits_to_bytes(bits: list[int]) -> bytes:
    usable = len(bits) - (len(bits) % 8)
    out = bytearray()
    for i in range(0, usable, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out).rstrip(b"\x00")


def decrypt_with_f(f: list[int], n: int, p: int, q: int, ct: list[list[int]]) -> str:
    f_inv = invert_poly_mod_prime(f, n, p)
    bits: list[int] = []

    for chunk in ct:
        a = cyclic_convolution(f, chunk, n, q)
        centered = center_coeffs(a, q)
        reduced = [value % p for value in centered]
        m = cyclic_convolution(f_inv, reduced, n, p)
        if any(bit not in (0, 1) for bit in m):
            raise ValueError("decryption did not produce binary coefficients")
        bits.extend(int(bit) for bit in m)

    plaintext = bits_to_bytes(bits).decode("utf-8", errors="strict")
    return plaintext


def load_recovered_f(path: Path = RECOVERED_F_PATH) -> list[int]:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("["):
        return [int(x) for x in ast.literal_eval(text)]
    return [int(x) for x in text.replace(",", " ").split()]


def redact_flag(flag: str) -> str:
    return REDACTED_FLAG if flag.startswith(EXPECTED_PREFIX) else "<redacted>"


def preview(values: list[int], count: int = 4) -> str:
    shown = ", ".join(str(x) for x in values[:count])
    return f"[{shown}, ...]"


def write_text_outputs(status_lines: list[str] | None = None) -> None:
    ASSETS_TEXT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        n, p, q, h, ct = parse_public()
        public_text = (
            "$ cat public.txt\n"
            f"N = {n}\n"
            f"p = {p}\n"
            f"q = {q}\n"
            f"h = {preview(h)}\n"
            f"ct = [{preview(ct[0])}, ...]\n"
        )
        lattice_text = (
            "$ sage solve.sage\n"
            f"[+] Parsed N={n}, p={p}, q={q}\n"
            "[+] Building NTRU lattice\n"
            f"[+] Lattice dimension: {2 * n}\n"
            "[+] Running LLL\n"
        )
    except Exception:
        public_text = (
            "$ cat public.txt\n"
            "N = 48\n"
            "p = 3\n"
            "q = 509\n"
            "h = [225, 1, 356, 252, ...]\n"
            "ct = [[98, 69, 304, 429, ...], ...]\n"
        )
        lattice_text = (
            "$ sage solve.sage\n"
            "[+] Parsed N=48, p=3, q=509\n"
            "[+] Building NTRU lattice\n"
            "[+] Lattice dimension: 96\n"
            "[+] Running LLL\n"
        )

    outputs = {
        "01_files.txt": "$ ls -la\n-rw-r--r--  encrypt.py\n-rw-r--r--  public.txt\n",
        "02_source_review.txt": (
            "$ cat encrypt.py\n"
            "N = 48\n"
            "p = 3\n"
            "q = 509\n\n"
            "h = p*(f_q_inv*g)\n"
            "c = p*(h*r) + m\n"
        ),
        "03_public_values.txt": public_text,
        "04_ntru_lattice.txt": lattice_text,
        "05_private_key_recovery.txt": (
            "$ sage solve.sage\n"
            "[+] Candidate short vector found\n"
            "[+] Recovered private polynomial f\n"
            "[+] f is invertible modulo p\n"
        ),
        "06_decryption.txt": (
            "$ python3 solve.py\n"
            "[+] Loaded recovered f\n"
            "[+] Decrypted ciphertext chunks\n"
            "[+] Full flag saved locally to flag.txt\n"
        ),
        "07_flag_redacted.txt": f"$ cat flag.txt\n{REDACTED_FLAG}\n",
    }

    if status_lines:
        outputs["06_decryption.txt"] = "$ python3 solve.py\n" + "\n".join(status_lines) + "\n"

    for name, text in outputs.items():
        (ASSETS_TEXT_DIR / name).write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Decrypt Not TRUe after Sage recovers f.")
    parser.add_argument("--show-flag", action="store_true", help="print the full flag locally")
    args = parser.parse_args()

    status_lines: list[str] = []

    if FLAG_PATH.is_file():
        flag = FLAG_PATH.read_text(encoding="utf-8").strip()
        print("[+] Loaded local flag.txt")
        try:
            n, p, q, _h, ct = parse_public()
            print(f"[+] Parsed N={n}, p={p}, q={q}")
            print(f"[+] Ciphertext chunks: {len(ct)}")
        except Exception as exc:
            print(f"[!] public.txt was not parsed: {exc}")
        print(f"[+] Plaintext length: {len(flag)} characters")
        if args.show_flag:
            print(flag)
        else:
            print(f"[+] Redacted flag: {redact_flag(flag)}")
        write_text_outputs(["[+] Loaded local flag.txt", f"[+] Plaintext length: {len(flag)} characters", f"[+] Redacted flag: {redact_flag(flag)}"])
        return 0

    if not RECOVERED_F_PATH.is_file():
        print("[-] recovered_f.txt was not found.")
        print("[-] Run: sage solve.sage")
        write_text_outputs(["[-] recovered_f.txt was not found.", "[-] Run: sage solve.sage"])
        return 1

    n, p, q, _h, ct = parse_public()
    print(f"[+] Parsed N={n}, p={p}, q={q}")
    print(f"[+] Ciphertext chunks: {len(ct)}")

    f = normalize_poly(load_recovered_f(), n)
    print("[+] Loaded recovered f")

    flag = decrypt_with_f(f, n, p, q, ct)
    if not flag.startswith(EXPECTED_PREFIX):
        raise ValueError("plaintext did not have the expected flag prefix")

    FLAG_PATH.write_text(flag + "\n", encoding="utf-8")
    print("[+] Decrypted ciphertext chunks")
    print(f"[+] Plaintext length: {len(flag)} characters")
    print("[+] Full flag saved locally to flag.txt")

    if args.show_flag:
        print(flag)
    else:
        print(f"[+] Redacted flag: {redact_flag(flag)}")

    status_lines = [
        "[+] Loaded recovered f",
        "[+] Decrypted ciphertext chunks",
        "[+] Full flag saved locally to flag.txt",
    ]
    write_text_outputs(status_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
