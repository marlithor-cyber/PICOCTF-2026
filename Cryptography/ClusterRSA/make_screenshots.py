#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MESSAGE_FILE = BASE_DIR / "message.txt"
REDACTED_FLAG = "picoCTF{...redacted...}"


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


def parse_message_values() -> dict[str, str]:
    if not MESSAGE_FILE.exists():
        return {
            "n": "874900289913204769979075249033109993805873770673520135467497...",
            "e": "65537",
            "ct": "263015924211445588225072981277010001173648576304736129787178...",
        }

    text = MESSAGE_FILE.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for name in ("n", "e", "ct"):
        match = re.search(rf"^\s*{name}\s*=\s*(\d+)\s*$", text, re.MULTILINE)
        if match:
            raw = match.group(1)
            values[name] = raw if len(raw) <= 66 else raw[:66] + "..."

    return {
        "n": values.get("n", "874900289913204769979075249033109993805873770673520135467497..."),
        "e": values.get("e", "65537"),
        "ct": values.get("ct", "263015924211445588225072981277010001173648576304736129787178..."),
    }


def render_terminal(text: str, output: Path) -> None:
    font = load_font(22)
    lines = text.rstrip("\n").splitlines()
    padding_x = 28
    padding_y = 24
    line_gap = 10
    line_height = (font.getbbox("M")[3] - font.getbbox("M")[1]) + line_gap

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    width = max(int(probe.textlength(line, font=font)) for line in lines) + padding_x * 2
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
    values = parse_message_values()
    screenshots = {
        "01_files.png": """$ ls -la
-rw-r--r--  message.txt
""",
        "02_message_values.png": f"""$ cat message.txt
n = {values["n"]}
e = {values["e"]}
ct = {values["ct"]}
""",
        "03_factorization.png": """$ python3 solve.py
[+] Loaded n, e, ct
[+] Factoring n
[+] Prime factors found: 4
[+] This is multi-prime RSA
""",
        "04_phi_and_private_key.png": """$ python3 solve.py
[+] Computing phi(n) = product(p_i - 1)
[+] Computing d = inverse(e, phi)
[+] Private exponent recovered
""",
        "05_decryption.png": """$ python3 solve.py
[+] Decrypting ciphertext
[+] Plaintext recovered
[+] Full flag saved locally to flag.txt
""",
        "06_flag_redacted.png": f"""$ cat flag.txt
{REDACTED_FLAG}
""",
    }

    for filename, text in screenshots.items():
        render_terminal(text, ASSETS_DIR / filename)
        print(f"[+] Wrote assets/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
