#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR / "assets"
TEXT_DIR = ASSETS_DIR / "text_outputs"
REDACTED_FLAG = "picoCTF{...redacted...}"


def parse_output() -> tuple[int, int, int, int] | None:
    path = SCRIPT_DIR / "output.txt"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    values = [int(match) for match in re.findall(r"-?\d+", text)]
    if len(values) != 4:
        return None
    return values[0], values[1], values[2], values[3]


def preview_int(value: int, keep: int = 72) -> str:
    text = str(value)
    return text if len(text) <= keep else f"{text[:keep]}..."


def screenshot_texts() -> list[tuple[str, str, str]]:
    parsed = parse_output()
    if parsed is None:
        c1 = "348636484977258462769261174905336720065667335826159606854922444295..."
        c2 = "201982790559548563915678784397933493721879152787419243871599124287..."
        diff = "-3"
        n = "173348455467725075652504796973602181058272856817195301489097799215..."
    else:
        real_c1, real_c2, real_diff, real_n = parsed
        c1 = preview_int(real_c1)
        c2 = preview_int(real_c2)
        diff = str(real_diff)
        n = preview_int(real_n)

    return [
        ("01_files.png", "01_files.txt", """$ ls -la
-rw-r--r--  chall.py
-rw-r--r--  output.txt
"""),
        ("02_source_review.png", "02_source_review.txt", """$ cat chall.py
e = 0x11
N = p*q

ciphertext = pow(Message, e, N)
ciphertext2 = pow(Message_fixed, e, N)

print(ciphertext, ciphertext2)
print(Message - Message_fixed)
print(N)
"""),
        ("03_output_values.png", "03_output_values.txt", f"""$ cat output.txt
{c1}
{c2}
{diff}
{n}
"""),
        ("04_relation.png", "04_relation.txt", f"""$ python3 solve.py
[+] Parsed c1, c2, diff, N
[+] diff = Message - Message_fixed = {diff}
[+] Relation: Message_fixed = Message - diff
"""),
        ("05_franklin_reiter.png", "05_franklin_reiter.txt", """$ sage solve.sage
[+] e = 17
[+] Building polynomials over Zmod(N)
[+] f1(x) = x^e - c1
[+] f2(x) = (x - diff)^e - c2
[+] gcd degree = 1
[+] Plaintext recovered
"""),
        ("06_flag_redacted.png", "06_flag_redacted.txt", f"""$ cat flag.txt
{REDACTED_FLAG}
"""),
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
    for filename, text_name, fallback in screenshot_texts():
        render_terminal(text_for_screenshot(text_name, fallback), ASSETS_DIR / filename)
        print(f"created assets/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
