#!/usr/bin/env python3
"""Solve the picoCTF 2026 cryptomaze challenge."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


SCRIPT_DIR = Path(__file__).resolve().parent
TEXT_OUTPUT_DIR = SCRIPT_DIR / "assets" / "text_outputs"
REDACTED_FLAG = "picoCTF{...redacted...}"
FLAG_PREFIX = ("picoCTF" + "{").encode()


@dataclass(frozen=True)
class ChallengeData:
    path: Path
    state: list[int]
    taps: list[int]
    ciphertext: bytes
    ciphertext_hex: str


@dataclass(frozen=True)
class Convention:
    output_side: str
    shift_direction: str
    output_timing: str
    tap_mode: str

    @property
    def label(self) -> str:
        side = "state[-1]" if self.output_side == "right" else "state[0]"
        shift = "shift right, insert feedback at front" if self.shift_direction == "right" else "shift left, append feedback"
        taps = "direct taps" if self.tap_mode == "direct" else "mirrored taps"
        return f"output {self.output_timing} shift from {side}; {shift}; {taps}"


@dataclass(frozen=True)
class SolveResult:
    convention: Convention
    plaintext: bytes
    key_length: int
    tried: int


def parse_challenge_output(path: Path) -> ChallengeData:
    data = path.read_text(encoding="utf-8")

    state_match = re.search(r"LFSR Initial State:\s*\n(\[.*?\])", data, re.S)
    taps_match = re.search(r"LFSR Taps:\s*\n(\[.*?\])", data, re.S)
    ct_match = re.search(r"Encrypted Flag:\s*\n([0-9a-fA-F]+)", data)

    if not state_match or not taps_match or not ct_match:
        raise ValueError(f"{path.name} does not contain the required cryptomaze fields")

    state = ast.literal_eval(state_match.group(1))
    taps = ast.literal_eval(taps_match.group(1))
    ct_hex = ct_match.group(1).strip()

    if not isinstance(state, list) or not all(bit in (0, 1) for bit in state):
        raise ValueError("LFSR initial state must be a list of 0/1 bits")
    if not isinstance(taps, list) or not all(isinstance(tap, int) for tap in taps):
        raise ValueError("LFSR taps must be a list of integers")
    if len(ct_hex) % 2 != 0:
        raise ValueError("Encrypted flag hex has odd length")

    ciphertext = bytes.fromhex(ct_hex)
    return ChallengeData(path=path, state=state, taps=taps, ciphertext=ciphertext, ciphertext_hex=ct_hex)


def candidate_paths(explicit_path: Path | None) -> list[Path]:
    if explicit_path is not None:
        return [explicit_path]

    roots = [Path.cwd(), SCRIPT_DIR]
    paths: list[Path] = []

    for root in roots:
        paths.extend([root / "output.txt", root / "output"])
    for root in roots:
        paths.extend(sorted(root.glob("*.txt")))

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(path)
    return deduped


def find_output_file(explicit_path: Path | None = None) -> ChallengeData:
    errors: list[str] = []
    for path in candidate_paths(explicit_path):
        if not path.is_file():
            continue
        try:
            return parse_challenge_output(path)
        except ValueError as exc:
            errors.append(str(exc))

    if explicit_path is not None:
        raise FileNotFoundError(f"Could not parse challenge output from {explicit_path}") from None

    searched = "output.txt, output, and *.txt files"
    detail = f" Last parse error: {errors[-1]}" if errors else ""
    raise FileNotFoundError(f"Could not find {searched} containing cryptomaze data.{detail}") from None


def conventions() -> list[Convention]:
    base = [
        ("right", "right", "before"),
        ("right", "right", "after"),
        ("left", "left", "before"),
        ("left", "left", "after"),
    ]
    return [
        Convention(output_side=side, shift_direction=shift, output_timing=timing, tap_mode=tap_mode)
        for tap_mode in ("direct", "mirrored")
        for side, shift, timing in base
    ]


def normalize_taps(taps: list[int], state_len: int, tap_mode: str) -> list[int]:
    if tap_mode == "direct":
        normalized = taps[:]
    elif tap_mode == "mirrored":
        normalized = [state_len - 1 - tap for tap in taps]
    else:
        raise ValueError(f"Unknown tap mode: {tap_mode}")

    for tap in normalized:
        if tap < 0 or tap >= state_len:
            raise ValueError(f"Tap index {tap} is outside the {state_len}-bit state")
    return normalized


def generate_lfsr_bits(initial_state: list[int], taps: list[int], convention: Convention, nbits: int = 128) -> list[int]:
    state = initial_state[:]
    tap_indexes = normalize_taps(taps, len(state), convention.tap_mode)
    bits: list[int] = []

    for _ in range(nbits):
        if convention.output_timing == "before":
            bits.append(state[-1] if convention.output_side == "right" else state[0])

        feedback = 0
        for tap in tap_indexes:
            feedback ^= state[tap]

        if convention.shift_direction == "right":
            state = [feedback] + state[:-1]
        elif convention.shift_direction == "left":
            state = state[1:] + [feedback]
        else:
            raise ValueError(f"Unknown shift direction: {convention.shift_direction}")

        if convention.output_timing == "after":
            bits.append(state[-1] if convention.output_side == "right" else state[0])

    return bits


def bits_to_key(bits: list[int]) -> bytes:
    if len(bits) != 128:
        raise ValueError("AES-128 key derivation requires exactly 128 bits")

    out = bytearray()
    for offset in range(0, 128, 8):
        chunk = bits[offset : offset + 8]
        out.append(int("".join(map(str, chunk)), 2))
    return bytes(out)


def decrypt_candidate(ciphertext: bytes, key: bytes) -> bytes:
    plaintext = AES.new(key, AES.MODE_ECB).decrypt(ciphertext)
    try:
        return unpad(plaintext, AES.block_size)
    except ValueError:
        return plaintext


def recover_plaintext(challenge: ChallengeData) -> SolveResult:
    tried = 0
    for convention in conventions():
        tried += 1
        bits = generate_lfsr_bits(challenge.state, challenge.taps, convention, 128)
        key = bits_to_key(bits)
        plaintext = decrypt_candidate(challenge.ciphertext, key)
        if plaintext.startswith(FLAG_PREFIX):
            return SolveResult(convention=convention, plaintext=plaintext, key_length=len(key), tried=tried)

    raise RuntimeError(f"No valid plaintext found after trying {tried} LFSR conventions")


def preview_list(values: list[int], keep: int = 8) -> str:
    if len(values) <= keep:
        return repr(values)
    return "[" + ", ".join(map(str, values[:keep])) + ", ...]"


def preview_hex(value: str, keep: int = 32) -> str:
    return value if len(value) <= keep else value[:keep] + "..."


def save_text_outputs(challenge: ChallengeData, result: SolveResult) -> None:
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "01_files.txt": "$ ls -la\n-rw-r--r--  output.txt\n",
        "02_output_review.txt": (
            "$ cat output.txt\n"
            "LFSR Initial State:\n"
            f"{preview_list(challenge.state)}\n"
            "LFSR Taps:\n"
            f"{challenge.taps}\n"
            "Encrypted Flag:\n"
            f"{preview_hex(challenge.ciphertext_hex)}\n"
        ),
        "03_lfsr_parameters.txt": (
            "$ python3 solve.py\n"
            "[+] Loaded LFSR state\n"
            f"[+] State length: {len(challenge.state)} bits\n"
            f"[+] Taps: {challenge.taps}\n"
            "[+] Target key stream length: 128 bits\n"
        ),
        "04_key_generation.txt": (
            "$ python3 solve.py\n"
            "[+] Generating 128 LFSR bits\n"
            "[+] Grouping bits into 16 bytes\n"
            "[+] AES-128 key candidate built\n"
        ),
        "05_aes_decryption.txt": (
            "$ python3 solve.py\n"
            "[+] Converted ciphertext from hex to bytes\n"
            "[+] Decrypting with AES-ECB\n"
            "[+] Valid plaintext found\n"
            "[+] Full flag saved locally to flag.txt\n"
        ),
        "06_flag_redacted.txt": f"$ cat flag.txt\n{REDACTED_FLAG}\n",
        "solve_redacted.txt": (
            "$ python3 solve.py\n"
            f"[+] Loaded output file: {challenge.path.name}\n"
            f"[+] State length: {len(challenge.state)} bits\n"
            f"[+] Taps: {challenge.taps}\n"
            f"[+] Ciphertext length: {len(challenge.ciphertext)} bytes\n"
            f"[+] Generated key length: {result.key_length} bytes\n"
            f"[+] LFSR conventions tried: {result.tried}\n"
            f"[+] Successful convention: {result.convention.label}\n"
            f"[+] Redacted flag: {REDACTED_FLAG}\n"
            "[+] Full flag saved locally to flag.txt\n"
        ),
    }

    for filename, text in outputs.items():
        (TEXT_OUTPUT_DIR / filename).write_text(text, encoding="utf-8")


def save_flag(flag: bytes) -> None:
    Path("flag.txt").write_bytes(flag + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Solve the picoCTF 2026 cryptomaze challenge")
    parser.add_argument("--output", type=Path, help="path to output.txt or equivalent challenge output")
    parser.add_argument("--show-flag", action="store_true", help="print the full recovered flag locally")
    args = parser.parse_args()

    challenge = find_output_file(args.output)
    result = recover_plaintext(challenge)
    save_flag(result.plaintext)
    save_text_outputs(challenge, result)

    print(f"[+] Loaded output file: {challenge.path.name}")
    print(f"[+] State length: {len(challenge.state)} bits")
    print(f"[+] Taps: {challenge.taps}")
    print(f"[+] Ciphertext length: {len(challenge.ciphertext)} bytes")
    print(f"[+] Generated key length: {result.key_length} bytes")
    print(f"[+] LFSR conventions tried: {result.tried}")
    print(f"[+] Successful convention: {result.convention.label}")
    if args.show_flag:
        print(f"[+] Full flag: {result.plaintext.decode('utf-8', errors='replace')}")
    else:
        print(f"[+] Redacted flag: {REDACTED_FLAG}")
    print("[+] Full flag saved locally to flag.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
