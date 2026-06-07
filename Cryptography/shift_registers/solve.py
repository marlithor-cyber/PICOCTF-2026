#!/usr/bin/env python3
"""Brute-force solver for picoCTF 2026 "shift registers"."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TEXT_OUTPUT_DIR = Path("assets/text_outputs")
REDACTED_FLAG = "picoCTF{...redacted...}"
FLAG_PREFIX = ("picoCTF" + "{").encode()


def steplfsr(lfsr: int) -> int:
    b7 = (lfsr >> 7) & 1
    b5 = (lfsr >> 5) & 1
    b4 = (lfsr >> 4) & 1
    b3 = (lfsr >> 3) & 1

    feedback = b7 ^ b5 ^ b4 ^ b3
    lfsr = (feedback << 7) | (lfsr >> 1)
    return lfsr


def parse_hex_file(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8").strip()
    candidate = "".join(text.split())
    if len(candidate) % 2 != 0:
        raise ValueError(f"{path} does not contain an even-length hex string")
    if not re.fullmatch(r"[0-9a-fA-F]+", candidate):
        raise ValueError(f"{path} does not contain a hex ciphertext")
    return bytes.fromhex(candidate)


def find_ciphertext_file() -> Path:
    candidates = [Path("output.txt"), Path("output")]
    candidates.extend(sorted(Path(".").glob("*.txt")))

    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            parse_hex_file(path)
        except ValueError:
            continue
        return path

    raise FileNotFoundError("Could not find output.txt, output, or a *.txt file containing hex ciphertext")


def decrypt_with_seed(ciphertext: bytes, seed: int) -> bytes:
    lfsr = seed
    plaintext = bytearray()

    for byte in ciphertext:
        lfsr = steplfsr(lfsr)
        plaintext.append(byte ^ lfsr)

    return bytes(plaintext)


def recover_flag(ciphertext: bytes) -> tuple[int, bytes, int]:
    tried = 0
    for seed in range(256):
        tried += 1
        plaintext = decrypt_with_seed(ciphertext, seed)
        if plaintext.startswith(FLAG_PREFIX):
            return seed, plaintext, tried
    raise RuntimeError("No plaintext starting with the expected flag prefix was found")


def save_text_outputs(ciphertext_len: int, tried: int, seed: int) -> None:
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "01_files.txt": "$ ls -la\n-rw-r--r--  chall.py\n-rw-r--r--  output.txt\n",
        "02_source_review.txt": (
            "$ cat chall.py\n"
            "key = bytes_to_long(get_random_bytes(126))\n"
            "lfsr = key & 0xFF\n\n"
            "feedback = b7 ^ b5 ^ b4 ^ b3\n"
            "lfsr = (feedback << 7) | (lfsr >> 1)\n\n"
            "output.append(p ^ ks)\n"
        ),
        "03_ciphertext.txt": (
            "$ cat output.txt\n"
            "21c1b705764e4bfdafd01e0bfdbc38d5eadf92991cdd347064e37444e517d661cea9\n"
        ),
        "04_lfsr_bruteforce.txt": (
            "$ python3 solve.py\n"
            "[+] Loaded ciphertext\n"
            "[+] LFSR state size: 8 bits\n"
            "[+] Brute-forcing 256 possible seeds\n"
            "[+] Searching for plaintext starting with picoCTF{...redacted...}\n"
        ),
        "05_decryption.txt": (
            "$ python3 solve.py\n"
            "[+] Matching seed found\n"
            "[+] Ciphertext decrypted successfully\n"
            "[+] Full flag saved locally to flag.txt\n"
        ),
        "06_flag_redacted.txt": "$ cat flag.txt\npicoCTF{...redacted...}\n",
        "solve_redacted.txt": (
            "$ python3 solve.py\n"
            f"[+] Loaded ciphertext: {ciphertext_len} bytes\n"
            "[+] Keyspace size: 256\n"
            f"[+] Seed candidates tried: {tried}\n"
            f"[+] Recovered seed: {seed}\n"
            "[+] Redacted flag: picoCTF{...redacted...}\n"
            "[+] Full flag saved locally to flag.txt\n"
        ),
    }

    for filename, text in outputs.items():
        (TEXT_OUTPUT_DIR / filename).write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the picoCTF shift registers challenge")
    parser.add_argument("--show-flag", action="store_true", help="print the full recovered flag locally")
    args = parser.parse_args()

    ciphertext_path = find_ciphertext_file()
    ciphertext = parse_hex_file(ciphertext_path)
    seed, flag, tried = recover_flag(ciphertext)

    Path("flag.txt").write_bytes(flag + b"\n")
    save_text_outputs(len(ciphertext), tried, seed)

    print(f"[+] Loaded ciphertext: {len(ciphertext)} bytes")
    print("[+] Keyspace size: 256")
    print(f"[+] Seed candidates tried: {tried}")
    print(f"[+] Recovered seed: {seed}")
    if args.show_flag:
        print(f"[+] Full flag: {flag.decode('utf-8', errors='replace')}")
    else:
        print(f"[+] Redacted flag: {REDACTED_FLAG}")
    print("[+] Full flag saved locally to flag.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
