#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = SCRIPT_DIR / "assets"
TEXT_DIR = ASSETS_DIR / "text_outputs"
PUBLIC_PATH = SCRIPT_DIR / "public.txt"
REDACTED_FLAG = "picoCTF{...redacted...}"


def parse_public() -> tuple[int, int, int, list[int], list[list[int]]] | None:
    if not PUBLIC_PATH.is_file():
        return None

    values: dict[str, object] = {}
    for raw_line in PUBLIC_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in {"N", "p", "q"}:
            values[key] = int(value)
        elif key in {"h", "ct"}:
            values[key] = ast.literal_eval(value)

    if not {"N", "p", "q", "h", "ct"}.issubset(values):
        return None

    return (
        int(values["N"]),
        int(values["p"]),
        int(values["q"]),
        [int(x) for x in values["h"]],  # type: ignore[index]
        [[int(x) for x in chunk] for chunk in values["ct"]],  # type: ignore[index]
    )


def list_preview(values: list[int], count: int = 4) -> str:
    shown = ", ".join(str(x) for x in values[:count])
    return f"[{shown}, ...]"


def screenshot_texts() -> list[tuple[str, str, str]]:
    public = parse_public()
    if public is None:
        n, p, q = 48, 3, 509
        h_preview = "[225, 1, 356, 252, ...]"
        ct_preview = "[[98, 69, 304, 429, ...], ...]"
    else:
        n, p, q, h, ct = public
        h_preview = list_preview(h)
        first_ct = list_preview(ct[0]) if ct else "[...]"
        ct_preview = f"[{first_ct}, ...]"

    return [
        (
            "01_files.png",
            "01_files.txt",
            "$ ls -la\n-rw-r--r--  encrypt.py\n-rw-r--r--  public.txt\n",
        ),
        (
            "02_source_review.png",
            "02_source_review.txt",
            "$ cat encrypt.py\n"
            f"N = {n}\n"
            f"p = {p}\n"
            f"q = {q}\n\n"
            "h = p*(f_q_inv*g)\n"
            "c = p*(h*r) + m\n",
        ),
        (
            "03_public_values.png",
            "03_public_values.txt",
            "$ cat public.txt\n"
            f"N = {n}\n"
            f"p = {p}\n"
            f"q = {q}\n"
            f"h = {h_preview}\n"
            f"ct = {ct_preview}\n",
        ),
        (
            "04_ntru_lattice.png",
            "04_ntru_lattice.txt",
            "$ sage solve.sage\n"
            f"[+] Parsed N={n}, p={p}, q={q}\n"
            "[+] Building NTRU lattice\n"
            f"[+] Lattice dimension: {2 * n}\n"
            "[+] Running LLL\n",
        ),
        (
            "05_private_key_recovery.png",
            "05_private_key_recovery.txt",
            "$ sage solve.sage\n"
            "[+] Candidate short vector found\n"
            "[+] Recovered private polynomial f\n"
            "[+] f is invertible modulo p\n",
        ),
        (
            "06_decryption.png",
            "06_decryption.txt",
            "$ python3 solve.py\n"
            "[+] Loaded recovered f\n"
            "[+] Decrypted ciphertext chunks\n"
            "[+] Full flag saved locally to flag.txt\n",
        ),
        (
            "07_flag_redacted.png",
            "07_flag_redacted.txt",
            f"$ cat flag.txt\n{REDACTED_FLAG}\n",
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
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(fallback.rstrip("\n") + "\n", encoding="utf-8")
    return path.read_text(encoding="utf-8")


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
