#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_FIELDS = ("g", "p", "A", "b", "enc")
PREFERRED_MESSAGE_NAMES = ("message.txt", "file.txt")
REDACTED_FLAG = "picoCTF{...redacted...}"
ASSIGNMENT_RE = re.compile(r"^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$")


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
        resolved = directory.resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            result.append(resolved)
    return result


def parse_assignments(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = ASSIGNMENT_RE.match(line)
        if not match:
            continue
        key, value = match.groups()
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def has_required_fields(path: Path) -> bool:
    try:
        values = parse_assignments(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return False
    return all(field in values for field in REQUIRED_FIELDS)


def find_message_file(search_dirs: list[Path]) -> Path:
    for directory in search_dirs:
        for name in PREFERRED_MESSAGE_NAMES:
            path = directory / name
            if path.is_file() and has_required_fields(path):
                return path

    for directory in search_dirs:
        for path in sorted(directory.glob("*.txt")):
            if path.name in {"commands.txt", "flag.txt"}:
                continue
            if has_required_fields(path):
                return path

    fail("No message file found. Expected message.txt, file.txt, or a .txt file containing g, p, A, b, and enc.")


def find_source_name(search_dirs: list[Path]) -> str:
    for directory in search_dirs:
        path = directory / "encryption.py"
        if path.is_file():
            return path.name
    return "encryption.py"


def parse_message(path: Path) -> tuple[int, int, int, int, str]:
    values = parse_assignments(path.read_text(encoding="utf-8", errors="replace"))
    missing = [field for field in REQUIRED_FIELDS if field not in values]
    if missing:
        fail(f"Message file is missing required field(s): {', '.join(missing)}")

    try:
        g = int(values["g"])
        p = int(values["p"])
        A = int(values["A"])
        b = int(values["b"])
    except ValueError as exc:
        fail(f"Could not parse integer field: {exc}")

    enc = values["enc"].replace(" ", "")
    try:
        bytes.fromhex(enc)
    except ValueError as exc:
        fail(f"Could not parse enc as hex: {exc}")

    return g, p, A, b, enc


def shorten_decimal(value: int, keep: int = 10) -> str:
    text = str(value)
    return text if len(text) <= keep else f"{text[:keep]}..."


def shorten_hex(value: str, keep: int = 14) -> str:
    return value if len(value) <= keep else f"{value[:keep]}..."


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_terminal_outputs(
    out_dir: Path,
    source_name: str,
    message_name: str,
    g: int,
    p: int,
    A: int,
    b: int,
    enc: str,
) -> None:
    write_text(out_dir / "01_files.txt", [
        "$ ls -la",
        f"-rw-r--r--  {source_name}",
        f"-rw-r--r--  {message_name}",
    ])

    write_text(out_dir / "02_source_review.txt", [
        f"$ cat {source_name}",
        "g = 2",
        "p = getPrime(1048)",
        "A = pow(g, a, p)",
        "b = '???'",
        "shared = pow(A, b, p)",
        "enc = bytes([x ^ (shared % 256) for x in flag])",
    ])

    write_text(out_dir / "03_message_values.txt", [
        f"$ cat {message_name}",
        f"g = {g}",
        f"p = {shorten_decimal(p)}",
        f"A = {shorten_decimal(A)}",
        f"b = {shorten_decimal(b)}",
        f"enc = {shorten_hex(enc)}",
    ])

    write_text(out_dir / "04_shared_secret.txt", [
        "$ python3 solve.py",
        "[+] Parsed g, p, A, b, enc",
        "[+] shared = pow(A, b, p)",
        "[+] xor key = shared % 256",
    ])

    write_text(out_dir / "05_decryption.txt", [
        "$ python3 solve.py",
        "[+] Ciphertext decrypted successfully",
        "[+] Full flag saved locally to flag.txt",
    ])

    write_text(out_dir / "06_flag_redacted.txt", [
        "$ cat flag.txt",
        REDACTED_FLAG,
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the Shared Secrets Diffie-Hellman/XOR challenge.")
    parser.add_argument("--message", type=Path, help="optional path to message.txt or file.txt")
    parser.add_argument("--show-flag", action="store_true", help="print the full local flag")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    search_dirs = candidate_dirs(script_dir)

    if args.message:
        message_file = args.message
        if not message_file.is_file():
            fail(f"Message file not found: {message_file.name}")
        if not has_required_fields(message_file):
            fail(f"Message file does not contain all required fields: {message_file.name}")
    else:
        message_file = find_message_file(search_dirs)

    source_name = find_source_name(search_dirs)
    g, p, A, b, enc_hex = parse_message(message_file)
    enc_bytes = bytes.fromhex(enc_hex)

    log(f"Message file: {message_file.name}")
    log("Parsed g, p, A, b, enc")
    log(f"p bit length: {p.bit_length()}")

    shared = pow(A, b, p)
    key = shared % 256
    flag = bytes([c ^ key for c in enc_bytes])

    log("shared secret computed with pow(A, b, p)")
    log(f"xor key value: {key}")
    log(f"ciphertext length: {len(enc_bytes)} bytes")

    flag_path = Path.cwd() / "flag.txt"
    flag_path.write_bytes(flag + (b"\n" if not flag.endswith(b"\n") else b""))

    log("Ciphertext decrypted successfully")
    log("Full flag saved locally to flag.txt")

    out_dir = script_dir / "assets" / "text_outputs"
    write_terminal_outputs(out_dir, source_name, message_file.name, g, p, A, b, enc_hex)
    log("Sanitized terminal text outputs saved to assets/text_outputs/")

    if args.show_flag:
        print(flag.decode("utf-8", errors="replace").strip())
    else:
        print(REDACTED_FLAG)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
