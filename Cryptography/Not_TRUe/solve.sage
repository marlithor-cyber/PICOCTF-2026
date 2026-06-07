#!/usr/bin/env sage
from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PUBLIC_PATH = SCRIPT_DIR / "public.txt"
RECOVERED_F_PATH = SCRIPT_DIR / "recovered_f.txt"
FLAG_PATH = SCRIPT_DIR / "flag.txt"
REDACTED_FLAG = "picoCTF{...redacted...}"
EXPECTED_PREFIX = "pico" + "CTF{"


def normalize_poly(poly, n):
    poly = [Integer(x) for x in poly]
    if len(poly) > n:
        raise ValueError("polynomial has too many coefficients")
    return poly + [Integer(0)] * (n - len(poly))


def parse_public(path=PUBLIC_PATH):
    values = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in ("N", "p", "q"):
            values[key] = Integer(value)
        elif key in ("h", "ct"):
            values[key] = ast.literal_eval(value)

    required = set(["N", "p", "q", "h", "ct"])
    missing = required - set(values)
    if missing:
        raise ValueError("missing public values: {}".format(", ".join(sorted(missing))))

    n = Integer(values["N"])
    h = normalize_poly(values["h"], n)
    ct = [normalize_poly(chunk, n) for chunk in values["ct"]]
    return n, Integer(values["p"]), Integer(values["q"]), h, ct


def cyclic_convolution(a, b, n, modulus=None):
    out = [Integer(0)] * n
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            out[(i + j) % n] += Integer(ai) * Integer(bj)
    if modulus is not None:
        out = [Integer(x) % modulus for x in out]
    return out


def center_coeff(x, q):
    x = Integer(x) % q
    if x > q // 2:
        x -= q
    return Integer(x)


def center_coeffs(values, q):
    return [center_coeff(x, q) for x in values]


def h_matrix(h, n, q):
    h = [Integer(x) % q for x in h]
    return Matrix(ZZ, n, n, lambda i, j: h[(j - i) % n])


def build_ntru_lattice(h, n, q):
    hmat = h_matrix(h, n, q)
    basis = Matrix(ZZ, 2 * n, 2 * n)

    for i in range(n):
        basis[i, i] = 1
        for j in range(n):
            basis[i, n + j] = hmat[i, j]

    for i in range(n):
        basis[n + i, n + i] = q

    return basis


def invert_poly_mod_prime(f, n, p):
    field = GF(p)
    matrix = Matrix(field, n, n, lambda row, col: field(f[(row - col) % n]))
    target = vector(field, [1] + [0] * (n - 1))
    solution = matrix.solve_right(target)
    return [Integer(x) for x in solution]


def bits_to_bytes(bits):
    usable = len(bits) - (len(bits) % 8)
    out = bytearray()
    for i in range(0, usable, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | int(bit)
        out.append(value)
    return bytes(out).rstrip(b"\x00")


def decrypt_with_f(f, n, p, q, ct):
    f_inv = invert_poly_mod_prime(f, n, p)
    bits = []

    for chunk in ct:
        a = cyclic_convolution(f, chunk, n, q)
        centered = center_coeffs(a, q)
        reduced = [Integer(x) % p for x in centered]
        m = cyclic_convolution(f_inv, reduced, n, p)
        if any(bit not in (0, 1) for bit in m):
            raise ValueError("decryption did not produce binary coefficients")
        bits.extend([int(bit) for bit in m])

    return bits_to_bytes(bits).decode("utf-8")


def coefficient_summary(f):
    neg = sum(1 for x in f if x == -1)
    zero = sum(1 for x in f if x == 0)
    pos = sum(1 for x in f if x == 1)
    other = len(f) - neg - zero - pos
    return "-1: {}, 0: {}, 1: {}, other: {}".format(neg, zero, pos, other)


def candidate_vectors(row, n):
    halves = [
        [Integer(row[i]) for i in range(n)],
        [Integer(row[n + i]) for i in range(n)],
    ]

    for half in halves:
        if max(abs(x) for x in half) <= 1 and any(x != 0 for x in half):
            yield half
            yield [-x for x in half]


def validate_candidate(f, n, p, q, ct):
    try:
        invert_poly_mod_prime(f, n, p)
    except Exception:
        return None

    try:
        plaintext = decrypt_with_f(f, n, p, q, ct)
    except Exception:
        return None

    if not plaintext.startswith(EXPECTED_PREFIX):
        return None
    return plaintext


def main():
    n, p, q, h, ct = parse_public()
    print("[+] Parsed N={}, p={}, q={}".format(n, p, q))
    print("[+] Ciphertext chunks: {}".format(len(ct)))

    print("[+] Building NTRU lattice")
    basis = build_ntru_lattice(h, n, q)
    print("[+] Lattice dimension: {}".format(basis.nrows()))

    print("[+] Running LLL")
    reduced = basis.LLL()
    print("[+] LLL finished")

    checked = 0
    seen = set()

    for row_index in range(reduced.nrows()):
        row = reduced.row(row_index)
        for f in candidate_vectors(row, n):
            key = tuple(int(x) for x in f)
            if key in seen:
                continue
            seen.add(key)
            checked += 1

            plaintext = validate_candidate(f, n, p, q, ct)
            if plaintext is None:
                continue

            print("[+] Candidate short vector found")
            print("[+] Number of candidate short vectors checked: {}".format(checked))
            print("[+] Recovered private polynomial f")
            print("[+] f coefficient summary: {}".format(coefficient_summary(f)))
            print("[+] f is invertible modulo p")
            RECOVERED_F_PATH.write_text(str([int(x) for x in f]) + "\n", encoding="utf-8")
            FLAG_PATH.write_text(plaintext + "\n", encoding="utf-8")
            print("[+] Decryption success")
            print("[+] Full flag saved locally to flag.txt")
            print("[+] Redacted flag: {}".format(REDACTED_FLAG))
            return 0

    print("[-] Number of candidate short vectors checked: {}".format(checked))
    print("[-] No valid private key candidate found")
    return 1


if __name__ == "__main__":
    result = int(main())
    if result != 0:
        raise SystemExit(result)
