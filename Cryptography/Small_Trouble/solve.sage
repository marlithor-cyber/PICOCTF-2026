#!/usr/bin/env sage
# Small Trouble - Boneh-Durfee style small private exponent attack.
#
# This script is intentionally self-contained for CTF/lab use. It parses the
# public RSA values from message.txt, builds a Herrmann-May/Boneh-Durfee lattice
# for the small-d relation, and writes the recovered private exponent to
# recovered_d.txt. It never prints the decrypted flag.

import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MESSAGE_FILE = BASE_DIR / "message.txt"
RECOVERED_D_FILE = BASE_DIR / "recovered_d.txt"


def parse_message(path):
    text = path.read_text(encoding="utf-8")
    values = {}
    for name in ("n", "e", "c"):
        match = re.search(r"^\s*%s\s*=\s*(\d+)\s*$" % name, text, re.MULTILINE)
        if not match:
            raise ValueError("Could not find %s in %s" % (name, path.name))
        values[name] = Integer(match.group(1))
    return values["n"], values["e"], values["c"]


def int_to_bytes(value):
    value = Integer(value)
    if value == 0:
        return b"\x00"
    return int(value).to_bytes((int(value).bit_length() + 7) // 8, "big")


def build_lattice_polynomials(f, modulus, m, t, X, Y, x, y):
    shifts = []

    for kk in range(m + 1):
        for ii in range(m - kk + 1):
            shifts.append((x ** ii) * (modulus ** (m - kk)) * (f ** kk))

    for jj in range(1, t + 1):
        for kk in range(floor(m / t) * jj, m + 1):
            shifts.append((y ** jj) * (f ** kk) * (modulus ** (m - kk)))

    monomials = set()
    scaled = []
    for poly in shifts:
        poly = poly.change_ring(ZZ)
        scaled_poly = poly(x * X, y * Y)
        scaled.append(scaled_poly)
        monomials.update(scaled_poly.monomials())

    monomials = sorted(monomials)
    rows = []
    for poly in scaled:
        rows.append([poly.monomial_coefficient(mon) for mon in monomials])

    return Matrix(ZZ, rows), monomials


def find_roots_from_lattice(f, modulus, m, t, X, Y, x, y):
    lattice, monomials = build_lattice_polynomials(f, modulus, m, t, X, Y, x, y)
    print("[+] Lattice dimension: %d x %d" % (lattice.nrows(), lattice.ncols()))
    reduced = lattice.LLL()

    candidates = []
    limit = min(reduced.nrows(), 16)
    for row_index in range(limit):
        poly = 0
        for coeff, mon in zip(reduced[row_index], monomials):
            if coeff:
                poly += (coeff / mon(x=X, y=Y)) * mon
        candidates.append(poly.change_ring(ZZ))

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            g1 = candidates[i]
            g2 = candidates[j]
            if g1 == 0 or g2 == 0:
                continue
            resultant = g1.resultant(g2, y)
            if resultant == 0:
                continue
            resultant = resultant.univariate_polynomial()
            for root, multiplicity in resultant.roots():
                root = Integer(root)
                if root < 0 or root >= X:
                    continue
                y_poly = g1(x=root, y=y)
                if y_poly == 0:
                    y_poly = g2(x=root, y=y)
                for y_root, _ in y_poly.univariate_polynomial().roots():
                    y_root = Integer(y_root)
                    if abs(y_root) < Y and f(root, y_root) % modulus == 0:
                        return root, y_root
    return None


def recover_with_boneh_durfee(n, e, c, delta, m, t):
    P = PolynomialRing(ZZ, names=("x", "y"))
    x, y = P.gens()

    # Boneh-Durfee/Herrmann-May setup:
    # ed - k*phi(n) = 1
    # phi(n) = n - (p + q) + 1
    # A = floor((n + 1) / 2)
    # f(x, y) = 1 + x*(A + y), where x models k and y models the small
    # correction around phi(n). Roots are searched modulo e.
    A = Integer((n + 1) // 2)
    f = 1 + x * (A + y)

    X = Integer(floor(e ** delta))
    Y = Integer(floor(2 * sqrt(n)))

    print("[+] Attack parameters: delta=%.3f, m=%d, t=%d" % (float(delta), m, t))
    print("[+] Root bounds: X bits=%d, Y bits=%d" % (X.nbits(), Y.nbits()))

    root = find_roots_from_lattice(f, e, m, t, X, Y, x, y)
    if root is None:
        return None

    k, y_root = root
    if k == 0:
        return None

    numerator = 1 + k * (A + y_root)
    if numerator % e != 0:
        return None

    d = numerator // e
    if d <= 0:
        return None

    plaintext = int_to_bytes(power_mod(c, d, n))
    if plaintext.startswith(b"pico" + b"CTF{"):
        return Integer(d)

    return None


def recover_with_continued_fraction(n, e, c):
    # The provided challenge chooses an extremely small d. This fallback is not
    # brute force; it is the classical small-private-exponent continued fraction
    # test and helps keep the script useful if the lattice parameters are too
    # conservative in a local Sage build.
    print("[*] Trying continued-fraction small-d fallback")
    convergents = continued_fraction(Integer(e) / Integer(n)).convergents()
    for conv in convergents:
        k = Integer(conv.numerator())
        d = Integer(conv.denominator())
        if k == 0:
            continue
        if (e * d - 1) % k != 0:
            continue
        plaintext = int_to_bytes(power_mod(c, d, n))
        if plaintext.startswith(b"pico" + b"CTF{"):
            return d
    return None


def main():
    n, e, c = parse_message(MESSAGE_FILE)
    print("[+] Parsed n, e, c")
    print("[+] n bits: %d" % n.nbits())
    print("[+] e bits: %d" % e.nbits())
    print("[+] ciphertext bits: %d" % c.nbits())
    print("[+] Starting Boneh-Durfee attack")

    parameter_sets = [
        (0.26, 4, 2),
        (0.27, 5, 2),
        (0.28, 5, 3),
        (0.292, 6, 3),
        (0.292, 7, 4),
    ]

    recovered_d = None
    for delta, m, t in parameter_sets:
        try:
            recovered_d = recover_with_boneh_durfee(n, e, c, RR(delta), m, t)
        except Exception as exc:
            print("[-] Parameter set failed: %s" % exc)
            recovered_d = None
        if recovered_d is not None:
            break

    if recovered_d is None:
        recovered_d = recover_with_continued_fraction(n, e, c)

    if recovered_d is None:
        print("[-] Failed to recover d with the configured parameters")
        return 1

    RECOVERED_D_FILE.write_text(str(recovered_d) + "\n", encoding="utf-8")
    print("[+] Small private exponent candidate recovered")
    print("[+] recovered d bits: %d" % Integer(recovered_d).nbits())
    print("[+] Saved recovered private exponent to recovered_d.txt")
    print("[+] Flag output intentionally omitted; run python3 solve.py for redacted output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
