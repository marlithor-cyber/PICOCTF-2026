#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PT1_HEX = "72616e646f6d64617461313131313131"
REDACTED_FLAG = "picoCTF{...redacted...}"
FLAG_PREFIX = "picoCTF" + "{"
PREFERRED_OUTPUT_NAMES = ("output.txt", "output")
HEX_LINE_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def fail(message: str) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(1)


def log(message: str) -> None:
    print(f"[+] {message}")


def xor_bytes(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        fail("Cannot XOR byte strings with different lengths.")
    return bytes(a ^ b for a, b in zip(left, right))


def gmul(a: int, b: int) -> int:
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        high_bit = a & 0x80
        a = (a << 1) & 0xff
        if high_bit:
            a ^= 0x1b
        b >>= 1
    return p


def to_matrix(block: bytes) -> list[list[int]]:
    if len(block) != 16:
        fail("AES-like block transform expects exactly 16 bytes.")

    state = [[0] * 4 for _ in range(4)]
    for i, value in enumerate(block):
        row = i % 4
        col = i // 4
        state[row][col] = value
    return state


def from_matrix(state: list[list[int]]) -> bytes:
    out = bytearray()
    for col in range(4):
        for row in range(4):
            out.append(state[row][col] & 0xff)
    return bytes(out)


def shift_rows(state: list[list[int]]) -> list[list[int]]:
    state[1] = state[1][1:] + state[1][:1]
    state[2] = state[2][2:] + state[2][:2]
    state[3] = state[3][3:] + state[3][:3]
    return state


def inverse_shift_rows(state: list[list[int]]) -> list[list[int]]:
    state[1] = state[1][-1:] + state[1][:-1]
    state[2] = state[2][-2:] + state[2][:-2]
    state[3] = state[3][-3:] + state[3][:-3]
    return state


def mix_columns(state: list[list[int]]) -> list[list[int]]:
    mixed = [[0] * 4 for _ in range(4)]

    for col in range(4):
        s0 = state[0][col]
        s1 = state[1][col]
        s2 = state[2][col]
        s3 = state[3][col]

        mixed[0][col] = gmul(0x02, s0) ^ gmul(0x03, s1) ^ s2 ^ s3
        mixed[1][col] = s0 ^ gmul(0x02, s1) ^ gmul(0x03, s2) ^ s3
        mixed[2][col] = s0 ^ s1 ^ gmul(0x02, s2) ^ gmul(0x03, s3)
        mixed[3][col] = gmul(0x03, s0) ^ s1 ^ s2 ^ gmul(0x02, s3)

    return mixed


def inverse_mix_columns(state: list[list[int]]) -> list[list[int]]:
    mixed = [[0] * 4 for _ in range(4)]

    for col in range(4):
        s0 = state[0][col]
        s1 = state[1][col]
        s2 = state[2][col]
        s3 = state[3][col]

        mixed[0][col] = gmul(0x0e, s0) ^ gmul(0x0b, s1) ^ gmul(0x0d, s2) ^ gmul(0x09, s3)
        mixed[1][col] = gmul(0x09, s0) ^ gmul(0x0e, s1) ^ gmul(0x0b, s2) ^ gmul(0x0d, s3)
        mixed[2][col] = gmul(0x0d, s0) ^ gmul(0x09, s1) ^ gmul(0x0e, s2) ^ gmul(0x0b, s3)
        mixed[3][col] = gmul(0x0b, s0) ^ gmul(0x0d, s1) ^ gmul(0x09, s2) ^ gmul(0x0e, s3)

    return mixed


def zero_key_forward(block: bytes) -> bytes:
    state_bytes = block

    for _ in range(1, 10):
        state = to_matrix(state_bytes)
        shift_rows(state)
        state = mix_columns(state)
        state_bytes = from_matrix(state)

    state = to_matrix(state_bytes)
    shift_rows(state)
    return from_matrix(state)


def zero_key_inverse(block: bytes) -> bytes:
    state = to_matrix(block)
    inverse_shift_rows(state)
    state_bytes = from_matrix(state)

    for _ in range(9):
        state = to_matrix(state_bytes)
        state = inverse_mix_columns(state)
        inverse_shift_rows(state)
        state_bytes = from_matrix(state)

    return state_bytes


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


def parse_ciphertext_lines(path: Path) -> tuple[bytes, bytes] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    hex_lines = [line.strip() for line in lines if HEX_LINE_RE.fullmatch(line.strip())]
    if len(hex_lines) < 2:
        return None

    try:
        return bytes.fromhex(hex_lines[0]), bytes.fromhex(hex_lines[1])
    except ValueError:
        return None


def find_output_file(search_dirs: list[Path]) -> tuple[Path, bytes, bytes]:
    for directory in search_dirs:
        for name in PREFERRED_OUTPUT_NAMES:
            path = directory / name
            if path.is_file():
                parsed = parse_ciphertext_lines(path)
                if parsed is not None:
                    return path, parsed[0], parsed[1]

    ignored = {"commands.txt", "flag.txt"}
    for directory in search_dirs:
        for path in sorted(directory.glob("*.txt")):
            if path.name in ignored:
                continue
            parsed = parse_ciphertext_lines(path)
            if parsed is not None:
                return path, parsed[0], parsed[1]

    fail("No output file found. Expected output.txt, output, or a .txt file with two 32-hex-character ciphertext lines.")


def load_ciphertexts(path_arg: Path | None, script_dir: Path) -> tuple[Path, bytes, bytes]:
    if path_arg is not None:
        parsed = parse_ciphertext_lines(path_arg)
        if parsed is None:
            fail(f"Could not parse two 32-hex-character ciphertext lines from {path_arg}.")
        return path_arg, parsed[0], parsed[1]

    return find_output_file(candidate_dirs(script_dir))


def redact_flag(text: str) -> str:
    return REDACTED_FLAG if text.startswith(FLAG_PREFIX) else "<redacted>"


def write_text(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_terminal_outputs(out_dir: Path, c1: bytes, c2: bytes) -> None:
    write_text(out_dir / "01_files.txt", [
        "$ ls -la",
        "-rw-r--r--  chall.py",
        "-rw-r--r--  output.txt",
    ])

    write_text(out_dir / "02_source_review.txt", [
        "$ cat chall.py",
        "def sub_word(word):",
        "    return word",
        "",
        "def rcon(word):",
        "    return word",
        "",
        "def sub_bytes(state):",
        "    return state",
        "",
        'pt1 = "72616e646f6d64617461313131313131"',
        "print(AES(pt1, key))",
        "print(AES(flag, key))",
    ])

    write_text(out_dir / "03_output_values.txt", [
        "$ cat output.txt",
        c1.hex(),
        c2.hex(),
    ])

    write_text(out_dir / "04_missing_sbox.txt", [
        "$ python3 solve.py",
        "[+] sub_bytes is identity",
        "[+] sub_word is identity",
        "[+] rcon is identity",
        "[+] The cipher is now linear over GF(2)",
    ])

    write_text(out_dir / "05_linear_attack.txt", [
        "$ python3 solve.py",
        "[+] Known plaintext: randomdata1111111",
        "[+] Computing F(known_plaintext) with zero key",
        "[+] Recovering key-dependent mask",
        "[+] Removing mask from flag ciphertext",
    ])

    write_text(out_dir / "06_decryption.txt", [
        "$ python3 solve.py",
        "[+] Applying inverse zero-key transform",
        "[+] Flag block recovered",
        "[+] Full flag saved locally to flag.txt",
    ])

    write_text(out_dir / "07_flag_redacted.txt", [
        "$ cat flag.txt",
        REDACTED_FLAG,
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the Black Cobra Pepper custom AES-like linear cipher.")
    parser.add_argument("--output", type=Path, help="optional path to output.txt")
    parser.add_argument("--show-flag", action="store_true", help="print the full flag locally")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_file, c_known, c_flag = load_ciphertexts(args.output, script_dir)

    if len(c_known) != 16 or len(c_flag) != 16:
        fail("Both ciphertexts must be exactly one 16-byte block.")

    known_plaintext = bytes.fromhex(PT1_HEX)
    if len(known_plaintext) != 16:
        fail("Known plaintext must be exactly one 16-byte block.")

    log(f"Loaded output file: {output_file.name}")
    log(f"Known plaintext: {known_plaintext.decode('ascii')}")
    log(f"Ciphertext lengths: known={len(c_known)} bytes, flag={len(c_flag)} bytes")
    log("sub_bytes is identity")
    log("sub_word is identity")
    log("rcon is identity")
    log("The cipher is now linear over GF(2)")
    log("Computing F(known_plaintext) with zero key")

    f_known = zero_key_forward(known_plaintext)
    log("Zero-key transform computed")

    mask = xor_bytes(c_known, f_known)
    log("Recovering key-dependent mask")
    log("Key-dependent mask recovered")

    f_flag = xor_bytes(c_flag, mask)
    log("Removing mask from flag ciphertext")
    log("Applying inverse zero-key transform")

    flag_bytes = zero_key_inverse(f_flag)
    log("Inverse transform applied")
    log("Flag block recovered")

    flag = flag_bytes.decode("utf-8", errors="replace").strip("\x00\r\n ")
    flag_path = script_dir / "flag.txt"
    flag_path.write_text(flag + "\n", encoding="utf-8")

    log(f"Plaintext length: {len(flag_bytes)} bytes")
    log("Full flag saved locally to flag.txt")

    out_dir = script_dir / "assets" / "text_outputs"
    write_terminal_outputs(out_dir, c_known, c_flag)
    log("Sanitized terminal text outputs saved to assets/text_outputs/")

    if args.show_flag:
        print(flag)
    else:
        log(f"Redacted flag: {redact_flag(flag)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
