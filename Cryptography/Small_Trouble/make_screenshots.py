#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MESSAGE_FILE = BASE_DIR / "message.txt"


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def parse_message_prefixes() -> dict[str, str]:
    if not MESSAGE_FILE.exists():
        return {
            "n": "4904436973...",
            "e": "1830055458...",
            "c": "2389122964...",
        }
    text = MESSAGE_FILE.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for name in ("n", "e", "c"):
        match = re.search(rf"^\s*{name}\s*=\s*(\d+)\s*$", text, re.MULTILINE)
        if match:
            values[name] = match.group(1)[:10] + "..."
    return {
        "n": values.get("n", "4904436973..."),
        "e": values.get("e", "1830055458..."),
        "c": values.get("c", "2389122964..."),
    }


def render_terminal(text: str, output: Path) -> None:
    font = load_font(22)
    lines = text.rstrip("\n").splitlines()
    padding_x = 28
    padding_y = 24
    line_gap = 10
    bbox = font.getbbox("M")
    line_height = bbox[3] - bbox[1] + line_gap

    draw_probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    width = max(int(draw_probe.textlength(line, font=font)) for line in lines) + padding_x * 2
    height = line_height * len(lines) + padding_y * 2
    width = max(width, 760)
    height = max(height, 180)

    image = Image.new("RGB", (width, height), "#0b0f14")
    draw = ImageDraw.Draw(image)
    y = padding_y
    for line in lines:
        color = "#e6edf3"
        if line.startswith("$"):
            color = "#7ee787"
        elif line.startswith("[+]"):
            color = "#79c0ff"
        draw.text((padding_x, y), line, font=font, fill=color)
        y += line_height

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def main() -> int:
    prefixes = parse_message_prefixes()
    screenshots = {
        "01_files.png": """$ ls -la
-rw-r--r--  encryption.py
-rw-r--r--  message.txt
""",
        "02_source_review.png": """$ cat encryption.py
p = getPrime(1048)
q = getPrime(1048)
n = p * q
phi = (p - 1) * (q - 1)
d = getPrime(256)
e = inverse(d, phi)
c = pow(m, e, n)
""",
        "03_message_values.png": f"""$ cat message.txt
n = {prefixes["n"]}
e = {prefixes["e"]}
c = {prefixes["c"]}
""",
        "04_boneh_durfee.png": """$ sage solve.sage
[+] Parsed n, e, c
[+] n bits: 2096
[+] Starting Boneh-Durfee attack
[+] Small private exponent candidate recovered
""",
        "05_decryption.png": """$ python3 solve.py
[+] Loaded recovered private exponent
[+] Decrypted ciphertext successfully
[+] Full flag saved locally to flag.txt
""",
        "06_flag_redacted.png": """$ cat flag.txt
picoCTF{...redacted...}
""",
    }

    for filename, text in screenshots.items():
        render_terminal(text, ASSETS_DIR / filename)
        print(f"[+] Wrote assets/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
