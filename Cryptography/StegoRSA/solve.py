#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
REDACTED_FLAG = "picoCTF{...redacted...}"


def fail(message: str) -> None:
    print(f"[!] {message}", file=sys.stderr)
    raise SystemExit(1)


def log(message: str) -> None:
    print(f"[*] {message}")


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        fail(f"Missing required tool: {name}")


def candidate_dirs(script_dir: Path) -> list[Path]:
    dirs = [Path.cwd(), script_dir, script_dir.parent.parent, script_dir.parent.parent.parent]
    seen: set[Path] = set()
    result: list[Path] = []
    for directory in dirs:
        resolved = directory.resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            result.append(resolved)
    return result


def find_image(search_dirs: list[Path]) -> Path:
    for directory in search_dirs:
        matches = sorted(
            path for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        if matches:
            return matches[0]
    fail("No image file found. Supported extensions: jpg, jpeg, png")


def find_encrypted_file(search_dirs: list[Path]) -> Path:
    for directory in search_dirs:
        matches = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".enc")
        if matches:
            return matches[0]
    fail("No encrypted .enc file found")


def run_checked(command: list[str], *, stdout=None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            text=True,
            stdout=stdout if stdout is not None else subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or "command failed"
        fail(f"{command[0]} failed: {detail}")


def short_hex(path: Path) -> str:
    data = "".join(path.read_text(encoding="utf-8", errors="replace").split())
    if not data:
        return "..."
    return f"{data[:72]}..."


def private_key_header(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        first_line = handle.readline().strip()
    allowed = {"-----BEGIN PRIVATE KEY-----", "-----BEGIN RSA PRIVATE KEY-----"}
    if first_line not in allowed:
        fail("private.pem does not look like a PEM private key")
    return first_line


def write_text(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_terminal_outputs(out_dir: Path, image_name: str, enc_name: str, comment_short: str, key_header: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    write_text(out_dir / "01_files.txt", [
        "$ ls -la",
        f"-rw-r--r--  {image_name}",
        f"-rw-r--r--  {enc_name}",
    ])

    write_text(out_dir / "02_metadata.txt", [
        f"$ exiftool {image_name}",
        f"File Name                       : {image_name}",
        f"Comment                         : {comment_short}",
    ])

    write_text(out_dir / "03_hex_extraction.txt", [
        f"$ exiftool -s3 -Comment {image_name} > key.hex",
        "$ xxd -r -p key.hex > private.pem",
    ])

    write_text(out_dir / "04_private_key.txt", [
        "$ head private.pem",
        key_header,
        "MIIE...",
    ])

    write_text(out_dir / "05_decryption.txt", [
        f"$ openssl pkeyutl -decrypt -inkey private.pem -in {enc_name} -out flag.txt",
        '$ echo "decryption successful"',
        "decryption successful",
    ])

    write_text(out_dir / "06_flag_redacted.txt", [
        "$ cat flag.txt",
        REDACTED_FLAG,
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover the RSA private key from image metadata and decrypt the flag.")
    parser.add_argument("--show-flag", action="store_true", help="print the full local flag after decryption")
    args = parser.parse_args()

    for tool in ("exiftool", "xxd", "openssl"):
        require_tool(tool)

    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / "assets" / "text_outputs"
    search_dirs = candidate_dirs(script_dir)

    image = find_image(search_dirs)
    enc_file = find_encrypted_file(search_dirs)
    image_name = image.name
    enc_name = enc_file.name

    log(f"Using image: {image_name}")
    log(f"Using encrypted file: {enc_name}")

    log("Inspecting image metadata with exiftool")
    run_checked(["exiftool", str(image)])

    log("Extracting Comment metadata to key.hex")
    comment = run_checked(["exiftool", "-s3", "-Comment", str(image)]).stdout.strip()
    if not comment:
        fail("The Comment metadata field was empty or missing")

    key_hex = Path("key.hex")
    private_pem = Path("private.pem")
    flag_txt = Path("flag.txt")

    key_hex.write_text(comment + "\n", encoding="utf-8")

    log("Converting key.hex to private.pem")
    with private_pem.open("wb") as output:
        try:
            subprocess.run(
                ["xxd", "-r", "-p", str(key_hex)],
                check=True,
                stdout=output,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace").strip() or "hex conversion failed"
            fail(f"xxd failed: {detail}")

    if private_pem.stat().st_size == 0:
        fail("private.pem was not created")

    key_header = private_key_header(private_pem)

    log(f"Decrypting {enc_name} to flag.txt")
    with flag_txt.open("wb") as output:
        try:
            subprocess.run(
                ["openssl", "pkeyutl", "-decrypt", "-inkey", str(private_pem), "-in", str(enc_file)],
                check=True,
                stdout=output,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace").strip() or "decryption failed"
            fail(f"openssl failed: {detail}")

    if flag_txt.stat().st_size == 0:
        fail("Decryption did not produce flag.txt")

    write_terminal_outputs(out_dir, image_name, enc_name, short_hex(key_hex), key_header)

    log("Decryption complete")
    if args.show_flag:
        print(flag_txt.read_text(encoding="utf-8", errors="replace").strip())
    else:
        print(REDACTED_FLAG)
        log("Full flag saved locally in flag.txt. Re-run with --show-flag to print it.")

    log("Sanitized text outputs saved in assets/text_outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
