#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MESSAGE_FILE = BASE_DIR / "message.txt"
RECOVERED_D_FILE = BASE_DIR / "recovered_d.txt"
FLAG_FILE = BASE_DIR / "flag.txt"
TEXT_OUTPUT_DIR = BASE_DIR / "assets" / "text_outputs"
REDACTED_FLAG = "picoCTF" + "{...redacted...}"


def parse_message(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8")
    values: dict[str, int] = {}
    for name in ("n", "e", "c"):
        match = re.search(rf"^\s*{name}\s*=\s*(\d+)\s*$", text, re.MULTILINE)
        if not match:
            raise ValueError(f"Could not find {name} in {path.name}")
        values[name] = int(match.group(1))
    return values["n"], values["e"], values["c"]


def int_to_bytes(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def redact_flag(text: str) -> str:
    match = re.search(r"picoCTF\{[^}]*\}", text)
    if match:
        return REDACTED_FLAG
    return REDACTED_FLAG


def write_text_outputs(lines: list[str]) -> None:
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (TEXT_OUTPUT_DIR / "solve_py_redacted.txt").write_text(
        "$ python3 solve.py\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Decrypt Small Trouble after recovering RSA d.")
    parser.add_argument(
        "--show-flag",
        action="store_true",
        help="print the full flag locally after saving it to flag.txt",
    )
    args = parser.parse_args()

    try:
        n, e, c = parse_message(MESSAGE_FILE)
    except Exception as exc:
        print(f"[-] Failed to parse message.txt: {exc}")
        return 1

    print("[+] Parsed n, e, c")
    print(f"[+] n bits: {n.bit_length()}")
    print(f"[+] e bits: {e.bit_length()}")
    print(f"[+] c bits: {c.bit_length()}")

    if not RECOVERED_D_FILE.exists():
        print("[-] recovered_d.txt was not found")
        print("[*] Run this first:")
        print("    sage solve.sage")
        write_text_outputs(
            [
                "[+] Parsed n, e, c",
                f"[+] n bits: {n.bit_length()}",
                "[-] recovered_d.txt was not found",
                "[*] Run this first: sage solve.sage",
            ]
        )
        return 1

    d_text = RECOVERED_D_FILE.read_text(encoding="utf-8").strip()
    d = int(d_text, 0)
    print("[+] Loaded recovered private exponent")
    print(f"[+] recovered d bits: {d.bit_length()}")

    m = pow(c, d, n)
    plaintext = int_to_bytes(m)
    plaintext_text = plaintext.decode("utf-8", errors="replace")
    FLAG_FILE.write_bytes(plaintext)

    redacted = redact_flag(plaintext_text)
    print(f"[+] plaintext length: {len(plaintext)} bytes")
    print("[+] Decrypted ciphertext successfully")
    print("[+] Full flag saved locally to flag.txt")
    print(f"[+] Redacted flag: {redacted}")

    if args.show_flag:
        print(f"[+] Full flag: {plaintext_text}")

    write_text_outputs(
        [
            "[+] Parsed n, e, c",
            f"[+] n bits: {n.bit_length()}",
            "[+] Loaded recovered private exponent",
            f"[+] recovered d bits: {d.bit_length()}",
            f"[+] plaintext length: {len(plaintext)} bytes",
            "[+] Decrypted ciphertext successfully",
            "[+] Full flag saved locally to flag.txt",
            f"[+] Redacted flag: {redacted}",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
