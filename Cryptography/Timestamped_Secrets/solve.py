#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from hashlib import sha256
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


REDACTED_FLAG = "picoCTF{...redacted...}"
DEFAULT_WINDOW = 10000
PREFERRED_MESSAGE_NAMES = ("message.txt", "message")
TIMESTAMP_RE = re.compile(r"around\s+(\d+)\s+UTC", re.IGNORECASE)
CIPHERTEXT_RE = re.compile(r"Ciphertext\s*\(hex\):\s*([0-9a-fA-F]+)", re.IGNORECASE)


def fail(message: str) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(1)


def log(message: str) -> None:
    print(f"[+] {message}")


def candidate_dirs(script_dir: Path) -> list[Path]:
    dirs = [Path.cwd(), script_dir]
    seen: set[Path] = set()
    result: list[Path] = []

    for directory in dirs:
        try:
            resolved = directory.resolve()
        except OSError:
            continue
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            result.append(resolved)

    return result


def has_message_markers(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "Hint:" in text and "Ciphertext (hex):" in text


def find_message_file(search_dirs: list[Path]) -> Path:
    for directory in search_dirs:
        for name in PREFERRED_MESSAGE_NAMES:
            path = directory / name
            if path.is_file() and has_message_markers(path):
                return path

    ignored = {"commands.txt", "flag.txt"}
    for directory in search_dirs:
        for path in sorted(directory.glob("*.txt")):
            if path.name in ignored:
                continue
            if has_message_markers(path):
                return path

    fail("No message file found. Expected message.txt, message, or a .txt file containing Hint: and Ciphertext (hex):.")


def parse_message(path: Path) -> tuple[int, bytes, str]:
    text = path.read_text(encoding="utf-8", errors="replace")

    timestamp_match = TIMESTAMP_RE.search(text)
    if not timestamp_match:
        fail("Could not parse timestamp hint from message file.")

    ciphertext_match = CIPHERTEXT_RE.search(text)
    if not ciphertext_match:
        fail("Could not parse ciphertext hex from message file.")

    timestamp = int(timestamp_match.group(1))
    ct_hex = ciphertext_match.group(1)

    try:
        ciphertext = bytes.fromhex(ct_hex)
    except ValueError as exc:
        fail(f"Ciphertext is not valid hex: {exc}")

    if len(ciphertext) == 0 or len(ciphertext) % AES.block_size != 0:
        fail("Ciphertext length is not a positive multiple of the AES block size.")

    return timestamp, ciphertext, ct_hex


def redact_flag(text: str) -> str:
    return REDACTED_FLAG if text.startswith("picoCTF{") else "<redacted>"


def ciphertext_preview(ct_hex: str, keep: int = 32) -> str:
    return ct_hex if len(ct_hex) <= keep else f"{ct_hex[:keep]}..."


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_terminal_outputs(out_dir: Path, timestamp: int, ct_hex: str) -> None:
    write_text(out_dir / "01_files.txt", [
        "$ ls -la",
        "-rw-r--r--  encryption.py",
        "-rw-r--r--  message.txt",
    ])

    write_text(out_dir / "02_source_review.txt", [
        "$ cat encryption.py",
        "key = sha256(str(timestamp).encode()).digest()[:16]",
        "cipher = AES.new(key, AES.MODE_ECB)",
        "padded = pad(plaintext.encode(), AES.block_size)",
        "ciphertext = cipher.encrypt(padded)",
    ])

    write_text(out_dir / "03_message_hint.txt", [
        "$ cat message.txt",
        f"Hint: The encryption was done around {timestamp} UTC",
        f"Ciphertext (hex): {ciphertext_preview(ct_hex)}",
    ])

    write_text(out_dir / "04_timestamp_bruteforce.txt", [
        "$ python3 solve.py",
        f"[+] Parsed timestamp hint: {timestamp}",
        "[+] Brute-forcing timestamps around the hint",
        f"[+] Trying window: +/- {DEFAULT_WINDOW} seconds",
    ])

    write_text(out_dir / "05_decryption.txt", [
        "$ python3 solve.py",
        "[+] Matching plaintext found",
        "[+] AES key derived from recovered timestamp",
        "[+] Full flag saved locally to flag.txt",
    ])

    write_text(out_dir / "06_flag_redacted.txt", [
        "$ cat flag.txt",
        REDACTED_FLAG,
    ])


def brute_force_timestamp(timestamp: int, ciphertext: bytes, window: int) -> tuple[int, bytes] | None:
    start = timestamp - window
    stop = timestamp + window

    for ts in range(start, stop + 1):
        key = sha256(str(ts).encode()).digest()[:16]
        cipher = AES.new(key, AES.MODE_ECB)

        try:
            plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
        except ValueError:
            continue

        if plaintext.startswith(b"picoCTF{"):
            return ts, plaintext

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the Timestamped Secrets AES timestamp-key challenge.")
    parser.add_argument("--message", type=Path, help="optional path to the challenge message file")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW, help="timestamp brute-force window in seconds")
    parser.add_argument("--show-flag", action="store_true", help="print the full flag locally")
    args = parser.parse_args()

    if args.window < 0:
        fail("--window must be non-negative.")

    script_dir = Path(__file__).resolve().parent
    search_dirs = candidate_dirs(script_dir)

    if args.message:
        message_file = args.message
        if not message_file.is_file():
            fail(f"Message file not found: {message_file}")
        if not has_message_markers(message_file):
            fail("Message file does not contain the expected Hint: and Ciphertext (hex): markers.")
    else:
        message_file = find_message_file(search_dirs)

    timestamp, ciphertext, ct_hex = parse_message(message_file)

    log(f"Message file: {message_file.name}")
    log(f"Parsed timestamp hint: {timestamp}")
    log(f"Ciphertext length: {len(ciphertext)} bytes")
    log(f"Brute-force window: +/- {args.window} seconds")
    log("AES key source: sha256(str(timestamp).encode()).digest()[:16]")
    log("Brute-forcing timestamps around the hint")

    result = brute_force_timestamp(timestamp, ciphertext, args.window)
    if result is None:
        fail("No picoCTF flag found in the requested timestamp window.")

    found_timestamp, plaintext = result
    flag = plaintext.decode("utf-8", errors="replace").strip()

    flag_path = script_dir / "flag.txt"
    flag_path.write_text(flag + "\n", encoding="utf-8")

    log("Matching plaintext found")
    log(f"Found timestamp: {found_timestamp}")
    log("AES key derived from recovered timestamp")
    log("Full flag saved locally to flag.txt")

    out_dir = script_dir / "assets" / "text_outputs"
    write_terminal_outputs(out_dir, timestamp, ct_hex)
    log("Sanitized terminal text outputs saved to assets/text_outputs/")

    if args.show_flag:
        print(flag)
    else:
        print(f"Flag: {redact_flag(flag)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
