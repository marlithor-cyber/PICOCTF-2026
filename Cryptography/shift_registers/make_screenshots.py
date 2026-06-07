#!/usr/bin/env python3
"""Generate clean terminal-style screenshots from prepared text."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ASSETS_DIR = Path("assets")
TEXT_OUTPUT_DIR = ASSETS_DIR / "text_outputs"
BACKGROUND = "#111827"
FOREGROUND = "#E5E7EB"
PROMPT = "#7DD3FC"
ACCENT = "#A7F3D0"
FONT_SIZE = 22
PADDING_X = 28
PADDING_Y = 24
LINE_SPACING = 10


SCREENSHOTS = {
    "01_files.png": "$ ls -la\n-rw-r--r--  chall.py\n-rw-r--r--  output.txt\n",
    "02_source_review.png": (
        "$ cat chall.py\n"
        "key = bytes_to_long(get_random_bytes(126))\n"
        "lfsr = key & 0xFF\n\n"
        "feedback = b7 ^ b5 ^ b4 ^ b3\n"
        "lfsr = (feedback << 7) | (lfsr >> 1)\n\n"
        "output.append(p ^ ks)\n"
    ),
    "03_ciphertext.png": (
        "$ cat output.txt\n"
        "21c1b705764e4bfdafd01e0bfdbc38d5eadf92991cdd347064e37444e517d661cea9\n"
    ),
    "04_lfsr_bruteforce.png": (
        "$ python3 solve.py\n"
        "[+] Loaded ciphertext\n"
        "[+] LFSR state size: 8 bits\n"
        "[+] Brute-forcing 256 possible seeds\n"
        "[+] Searching for plaintext starting with picoCTF{...redacted...}\n"
    ),
    "05_decryption.png": (
        "$ python3 solve.py\n"
        "[+] Matching seed found\n"
        "[+] Ciphertext decrypted successfully\n"
        "[+] Full flag saved locally to flag.txt\n"
    ),
    "06_flag_redacted.png": "$ cat flag.txt\npicoCTF{...redacted...}\n",
}


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansMono-Regular.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text or " ", font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def render_terminal(text: str, output_path: Path) -> None:
    font = load_font(FONT_SIZE)
    probe = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(probe)
    lines = text.rstrip("\n").splitlines()

    line_height = text_size(draw, "Ag", font)[1] + LINE_SPACING
    max_width = max(text_size(draw, line, font)[0] for line in lines)
    width = max(760, max_width + (PADDING_X * 2))
    height = max(220, (line_height * len(lines)) + (PADDING_Y * 2))

    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)

    y = PADDING_Y
    for line in lines:
        color = FOREGROUND
        if line.startswith("$"):
            color = PROMPT
        elif line.startswith("[+]"):
            color = ACCENT
        draw.text((PADDING_X, y), line, fill=color, font=font)
        y += line_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def write_text_outputs() -> None:
    TEXT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in SCREENSHOTS.items():
        (TEXT_OUTPUT_DIR / name.replace(".png", ".txt")).write_text(text, encoding="utf-8")


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    write_text_outputs()
    for filename, text in SCREENSHOTS.items():
        render_terminal(text, ASSETS_DIR / filename)
        print(f"[+] wrote {ASSETS_DIR / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
