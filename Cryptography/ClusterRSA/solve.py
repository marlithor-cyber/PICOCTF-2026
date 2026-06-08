#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
import signal
from pathlib import Path
from typing import Callable


BASE_DIR = Path(__file__).resolve().parent
MESSAGE_FILE = BASE_DIR / "message.txt"
FLAG_FILE = BASE_DIR / "flag.txt"
TEXT_OUTPUT_DIR = BASE_DIR / "assets" / "text_outputs"
REDACTED_FLAG = "picoCTF{...redacted...}"

# Publicly reproducible factorization of the challenge modulus. This is only
# used if sympy is unavailable or factorization times out.
FALLBACK_FACTORS = [
    9671406556917033397931773,
    9671406556917033398314601,
    9671406556917033398439721,
    9671406556917033398454847,
]


class FactorizationTimeout(RuntimeError):
    pass


def parse_message(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8")
    values: dict[str, int] = {}
    for name in ("n", "e", "ct"):
        match = re.search(rf"^\s*{name}\s*=\s*(\d+)\s*$", text, re.MULTILINE)
        if not match:
            raise ValueError(f"missing field {name!r} in {path.name}")
        values[name] = int(match.group(1))
    return values["n"], values["e"], values["ct"]


def shorten_int(value: int, digits: int = 66) -> str:
    text = str(value)
    if len(text) <= digits:
        return text
    return text[:digits] + "..."


def int_to_bytes(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def factor_dict_from_list(factors: list[int]) -> dict[int, int]:
    result: dict[int, int] = {}
    for factor in factors:
        result[factor] = result.get(factor, 0) + 1
    return result


def fallback_factorization(n: int) -> dict[int, int]:
    if math.prod(FALLBACK_FACTORS) != n:
        raise RuntimeError("fallback factors do not match this modulus")
    return factor_dict_from_list(FALLBACK_FACTORS)


def with_timeout(timeout: int, func: Callable[[], dict[int, int]]) -> dict[int, int]:
    if timeout <= 0 or not hasattr(signal, "SIGALRM"):
        return func()

    def handler(signum: int, frame: object) -> None:
        raise FactorizationTimeout("factorization timed out")

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return func()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def factor_modulus(n: int, timeout: int) -> tuple[dict[int, int], str]:
    try:
        from sympy import factorint

        raw_factors = with_timeout(timeout, lambda: factorint(n))
        return {int(p): int(exp) for p, exp in raw_factors.items()}, "sympy.factorint"
    except (ImportError, FactorizationTimeout) as exc:
        factors = fallback_factorization(n)
        return factors, f"fallback factor list ({exc})"


def compute_phi(factors: dict[int, int]) -> int:
    phi = 1
    for p, exp in factors.items():
        phi *= (p - 1) * (p ** (exp - 1))
    return phi


def compute_inverse(e: int, phi: int) -> int:
    try:
        from sympy import mod_inverse

        return int(mod_inverse(e, phi))
    except ImportError:
        return pow(e, -1, phi)


def redact_flag(text: str) -> str:
    if re.search(r"picoCTF\{[^}]*\}", text):
        return REDACTED_FLAG
    return REDACTED_FLAG


def write_text_output(name: str, text: str) -> None:
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (TEXT_OUTPUT_DIR / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def write_clean_text_outputs(n: int, e: int, ct: int) -> None:
    write_text_output(
        "01_files.txt",
        """$ ls -la
-rw-r--r--  message.txt
""",
    )
    write_text_output(
        "02_message_values.txt",
        f"""$ cat message.txt
n = {shorten_int(n)}
e = {e}
ct = {shorten_int(ct)}
""",
    )
    write_text_output(
        "03_factorization.txt",
        """$ python3 solve.py
[+] Loaded n, e, ct
[+] Factoring n
[+] Prime factors found: 4
[+] This is multi-prime RSA
""",
    )
    write_text_output(
        "04_phi_and_private_key.txt",
        """$ python3 solve.py
[+] Computing phi(n) = product(p_i - 1)
[+] Computing d = inverse(e, phi)
[+] Private exponent recovered
""",
    )
    write_text_output(
        "05_decryption.txt",
        """$ python3 solve.py
[+] Decrypting ciphertext
[+] Plaintext recovered
[+] Full flag saved locally to flag.txt
""",
    )
    write_text_output(
        "06_flag_redacted.txt",
        f"""$ cat flag.txt
{REDACTED_FLAG}
""",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the ClusterRSA multi-prime RSA challenge.")
    parser.add_argument(
        "--show-flag",
        action="store_true",
        help="print the full flag locally after saving it to flag.txt",
    )
    parser.add_argument(
        "--factor-timeout",
        type=int,
        default=5,
        help="seconds to allow sympy.factorint before using the known factorization fallback",
    )
    args = parser.parse_args()

    try:
        n, e, ct = parse_message(MESSAGE_FILE)
    except Exception as exc:
        print(f"[-] Could not load message.txt: {exc}")
        return 1

    print("[+] Loaded message file: message.txt")
    print("[+] Loaded n, e, ct")
    print(f"[+] n bit length: {n.bit_length()}")
    print(f"[+] e value: {e}")
    print(f"[+] ciphertext bit length: {ct.bit_length()}")
    print("[+] Factoring n")

    try:
        factors, source = factor_modulus(n, args.factor_timeout)
    except Exception as exc:
        print(f"[-] Could not factor n: {exc}")
        return 1

    factor_count = sum(factors.values())
    bit_lengths = [p.bit_length() for p in sorted(factors)]
    print(f"[+] Factorization source: {source}")
    print(f"[+] Prime factors found: {factor_count}")
    print(f"[+] Factor bit lengths: {bit_lengths}")
    if factor_count > 2:
        print("[+] This is multi-prime RSA")

    print("[+] Computing phi(n) = product(p_i - 1)")
    phi = compute_phi(factors)
    print("[+] phi computed")

    print("[+] Computing d = inverse(e, phi)")
    d = compute_inverse(e, phi)
    print("[+] private exponent computed")

    print("[+] Decrypting ciphertext")
    m = pow(ct, d, n)
    plaintext = int_to_bytes(m)
    plaintext_text = plaintext.decode("utf-8", errors="replace")
    FLAG_FILE.write_bytes(plaintext)

    redacted = redact_flag(plaintext_text)
    print("[+] Plaintext recovered")
    print(f"[+] plaintext length: {len(plaintext)} bytes")
    print("[+] Full flag saved locally to flag.txt")
    print(f"[+] redacted flag: {redacted}")

    if args.show_flag:
        print(f"[+] full flag: {plaintext_text}")

    write_clean_text_outputs(n, e, ct)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
