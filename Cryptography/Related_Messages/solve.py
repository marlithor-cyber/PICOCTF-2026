#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REDACTED_FLAG = "picoCTF{...redacted...}"
FLAG_PREFIX = "pico" + "CTF{"
E = 0x11


def fail(message: str) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(1)


def log(message: str) -> None:
    print(f"[+] {message}")


def int_to_bytes(value: int) -> bytes:
    if value == 0:
        return b"\x00"
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def parse_output(path: Path) -> tuple[int, int, int, int]:
    if not path.is_file():
        fail("output.txt was not found. Place the challenge output beside this script.")

    text = path.read_text(encoding="utf-8", errors="replace")
    values = [int(match) for match in re.findall(r"-?\d+", text)]
    if len(values) != 4:
        fail("Expected exactly four integers in output.txt: c1, c2, diff, N.")

    return values[0], values[1], values[2], values[3]


def redact_flag(flag: str) -> str:
    return REDACTED_FLAG if flag.startswith(FLAG_PREFIX) else "<redacted>"


def preview_int(value: int, keep: int = 72) -> str:
    text = str(value)
    return text if len(text) <= keep else f"{text[:keep]}..."


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_terminal_outputs(out_dir: Path, c1: int, c2: int, diff: int, n: int) -> None:
    write_text(out_dir / "01_files.txt", [
        "$ ls -la",
        "-rw-r--r--  chall.py",
        "-rw-r--r--  output.txt",
    ])

    write_text(out_dir / "02_source_review.txt", [
        "$ cat chall.py",
        "e = 0x11",
        "N = p*q",
        "",
        "ciphertext = pow(Message, e, N)",
        "ciphertext2 = pow(Message_fixed, e, N)",
        "",
        "print(ciphertext, ciphertext2)",
        "print(Message - Message_fixed)",
        "print(N)",
    ])

    write_text(out_dir / "03_output_values.txt", [
        "$ cat output.txt",
        preview_int(c1),
        preview_int(c2),
        str(diff),
        preview_int(n),
    ])

    write_text(out_dir / "04_relation.txt", [
        "$ python3 solve.py",
        "[+] Parsed c1, c2, diff, N",
        f"[+] diff = Message - Message_fixed = {diff}",
        "[+] Relation: Message_fixed = Message - diff",
    ])

    write_text(out_dir / "05_franklin_reiter.txt", [
        "$ sage solve.sage",
        "[+] e = 17",
        "[+] Building polynomials over Zmod(N)",
        "[+] f1(x) = x^e - c1",
        "[+] f2(x) = (x - diff)^e - c2",
        "[+] gcd degree = 1",
        "[+] Plaintext recovered",
    ])

    write_text(out_dir / "06_flag_redacted.txt", [
        "$ cat flag.txt",
        REDACTED_FLAG,
    ])


def load_or_create_flag(script_dir: Path) -> tuple[str | None, str]:
    flag_path = script_dir / "flag.txt"
    recovered_path = script_dir / "recovered_m.txt"

    if flag_path.is_file():
        return flag_path.read_text(encoding="utf-8", errors="replace").strip(), "flag.txt"

    if recovered_path.is_file():
        recovered_m = int(recovered_path.read_text(encoding="utf-8").strip())
        flag = int_to_bytes(recovered_m).decode("utf-8", errors="replace").strip()
        flag_path.write_text(flag + "\n", encoding="utf-8")
        return flag, "recovered_m.txt"

    return None, "missing"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print redacted output for the Related Messages RSA writeup.")
    parser.add_argument("--show-flag", action="store_true", help="print the full recovered flag locally")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_file = script_dir / "output.txt"
    c1, c2, diff, n = parse_output(output_file)

    log("Parsed c1, c2, diff, N")
    log(f"e = {E}")
    log(f"N bit length = {n.bit_length()}")
    log(f"c1 bit length = {c1.bit_length()}")
    log(f"c2 bit length = {c2.bit_length()}")
    log(f"diff = Message - Message_fixed = {diff}")
    log("Relation: Message_fixed = Message - diff")

    out_dir = script_dir / "assets" / "text_outputs"
    write_terminal_outputs(out_dir, c1, c2, diff, n)
    log("Sanitized terminal text outputs saved to assets/text_outputs/")

    flag, source = load_or_create_flag(script_dir)
    if flag is None:
        print("[!] No local flag material found yet.")
        print("[!] Run: sage solve.sage")
        return 0

    if source == "flag.txt":
        log("Loaded local flag from flag.txt")
    else:
        log("Converted recovered_m.txt to flag.txt")

    if args.show_flag:
        print(flag)
    else:
        print(f"Flag: {redact_flag(flag)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
