#!/usr/bin/env sage
# Related Messages - Franklin-Reiter related message attack.
#
# This script parses output.txt, builds the two related-message polynomials over
# Zmod(N), recovers the shared root with a polynomial GCD, and writes the full
# recovered flag only to local ignored files.

import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = BASE_DIR / "output.txt"
FLAG_FILE = BASE_DIR / "flag.txt"
RECOVERED_M_FILE = BASE_DIR / "recovered_m.txt"
REDACTED_FLAG = "picoCTF{...redacted...}"
E = Integer(0x11)


def parse_output(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    values = [Integer(match) for match in re.findall(r"-?\d+", text)]
    if len(values) != 4:
        raise ValueError("Expected exactly four integers in output.txt: c1, c2, diff, N")
    return values[0], values[1], values[2], values[3]


def int_to_bytes(value):
    value = Integer(value)
    if value == 0:
        return b"\x00"
    return int(value).to_bytes((int(value).bit_length() + 7) // 8, "big")


def polynomial_gcd(a, b):
    # Sage usually handles this directly. The explicit Euclidean loop is kept
    # here as a readable fallback for local Sage builds.
    try:
        return a.gcd(b).monic()
    except Exception:
        while b != 0:
            a, b = b, a % b
        return a.monic()


def recover_root_from_linear_gcd(g, modulus):
    if g.degree() != 1:
        raise ValueError("Expected a linear GCD, got degree %d" % g.degree())

    lc = g.leading_coefficient()
    const = g[0]

    # If g = lc*x + const, the root is -const/lc modulo N.
    return Integer(-const / lc)


def main():
    c1, c2, diff, N = parse_output(OUTPUT_FILE)

    print("[+] Parsed c1, c2, diff, N")
    print("[+] e = %d" % E)
    print("[+] N bit length = %d" % N.nbits())
    print("[+] c1 bit length = %d" % c1.nbits())
    print("[+] c2 bit length = %d" % c2.nbits())
    print("[+] diff = Message - Message_fixed = %d" % diff)
    print("[+] Relation used: Message_fixed = Message - diff")
    print("[+] Building polynomials over Zmod(N)")

    R = PolynomialRing(Zmod(N), names=("x",))
    x = R.gen()

    f1 = x ** E - c1
    f2 = (x - diff) ** E - c2

    print("[+] f1(x) = x^e - c1")
    print("[+] f2(x) = (x - diff)^e - c2")

    g = polynomial_gcd(f1, f2)
    print("[+] gcd degree = %d" % g.degree())

    m = recover_root_from_linear_gcd(g, N)
    plaintext = int_to_bytes(m)

    RECOVERED_M_FILE.write_text(str(m) + "\n", encoding="utf-8")
    FLAG_FILE.write_bytes(plaintext.rstrip(b"\n") + b"\n")

    print("[+] Plaintext recovered")
    print("[+] plaintext length = %d bytes" % len(plaintext))
    print("[+] recovered integer saved to recovered_m.txt")
    print("[+] full flag saved locally to flag.txt")
    print("[+] redacted flag = %s" % REDACTED_FLAG)
    return 0


if __name__ == "__main__":
    raise SystemExit(int(main()))
