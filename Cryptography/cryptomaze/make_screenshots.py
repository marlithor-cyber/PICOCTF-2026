#!/usr/bin/env python3
"""Generate terminal-style PNG screenshots for the cryptomaze writeup."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR / "assets"
TEXT_DIR = ASSETS_DIR / "text_outputs"
REDACTED_FLAG = "picoCTF{...redacted...}"

SCREENSHOTS = [
    (
        "01_files.png",
        "01_files.txt",
        """$ ls -la
-rw-r--r--  output.txt
""",
    ),
    (
        "02_output_review.png",
        "02_output_review.txt",
        """$ cat output.txt
LFSR Initial State:
[0, 0, 1, 0, 0, 1, 0, 1, ...]
LFSR Taps:
[63, 61, 60, 58]
Encrypted Flag:
8f0e6d0f5b0dc1db201948b9e0cebd8f...
""",
    ),
    (
        "03_lfsr_parameters.png",
        "03_lfsr_parameters.txt",
        """$ python3 solve.py
[+] Loaded LFSR state
[+] State length: 64 bits
[+] Taps: [63, 61, 60, 58]
[+] Target key stream length: 128 bits
""",
    ),
    (
        "04_key_generation.png",
        "04_key_generation.txt",
        """$ python3 solve.py
[+] Generating 128 LFSR bits
[+] Grouping bits into 16 bytes
[+] AES-128 key candidate built
""",
    ),
    (
        "05_aes_decryption.png",
        "05_aes_decryption.txt",
        """$ python3 solve.py
[+] Converted ciphertext from hex to bytes
[+] Decrypting with AES-ECB
[+] Valid plaintext found
[+] Full flag saved locally to flag.txt
""",
    ),
    (
        "06_flag_redacted.png",
        "06_flag_redacted.txt",
        f"""$ cat flag.txt
{REDACTED_FLAG}
""",
    ),
]


def load_font(size: int) -> ImageFont.ImageFont:
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansMono-Regular.ttf",
    ]

    for candidate in font_candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)

    return ImageFont.load_default()


def wrap_line(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    return wrap(line, width=width, break_long_words=False, break_on_hyphens=False) or [line]


def text_for_screenshot(text_name: str, fallback: str) -> str:
    path = TEXT_DIR / text_name
    if path.is_file():
        return path.read_text(encoding="utf-8")

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(fallback.rstrip("\n") + "\n", encoding="utf-8")
    return fallback


def render_terminal(text: str, output_path: Path) -> None:
    font = load_font(22)
    small_font = load_font(16)
    padding_x = 28
    padding_top = 54
    padding_bottom = 28
    max_chars = 118
    line_height = 31

    raw_lines = text.strip("\n").splitlines()
    lines: list[str] = []
    for line in raw_lines:
        lines.extend(wrap_line(line, max_chars))

    width = 1500
    height = padding_top + padding_bottom + max(1, len(lines)) * line_height

    image = Image.new("RGB", (width, height), "#101418")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=8, fill="#101418", outline="#2b333b", width=2)
    draw.rectangle((1, 1, width - 2, 38), fill="#151b21")
    draw.ellipse((22, 14, 34, 26), fill="#ff5f57")
    draw.ellipse((44, 14, 56, 26), fill="#ffbd2e")
    draw.ellipse((66, 14, 78, 26), fill="#28c840")
    draw.text((92, 10), "terminal", font=small_font, fill="#9aa7b2")

    y = padding_top
    for line in lines:
        color = "#d7e0e8"
        if line.startswith("$"):
            color = "#9ee493"
        draw.text((padding_x, y), line, font=font, fill=color)
        y += line_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, text_name, fallback in SCREENSHOTS:
        render_terminal(text_for_screenshot(text_name, fallback), ASSETS_DIR / filename)
        print(f"created assets/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
