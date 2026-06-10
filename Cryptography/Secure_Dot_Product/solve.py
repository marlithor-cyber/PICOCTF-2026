#!/usr/bin/env python3
import argparse
import ast
import hashlib
import random
import re
from dataclasses import dataclass

from pwn import remote
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import unpad
from sympy import Matrix, linsolve


HOST = "lonely-island.picoctf.net"
PORT = 57988
KEY_SIZE = 32
SALT_SIZE = 256
MASK64 = (1 << 64) - 1

SHA512_IV = [
    0x6A09E667F3BCC908,
    0xBB67AE8584CAA73B,
    0x3C6EF372FE94F82B,
    0xA54FF53A5F1D36F1,
    0x510E527FADE682D1,
    0x9B05688C2B3E6C1F,
    0x1F83D9ABFB41BD6B,
    0x5BE0CD19137E2179,
]

SHA512_K = [
    0x428A2F98D728AE22,
    0x7137449123EF65CD,
    0xB5C0FBCFEC4D3B2F,
    0xE9B5DBA58189DBBC,
    0x3956C25BF348B538,
    0x59F111F1B605D019,
    0x923F82A4AF194F9B,
    0xAB1C5ED5DA6D8118,
    0xD807AA98A3030242,
    0x12835B0145706FBE,
    0x243185BE4EE4B28C,
    0x550C7DC3D5FFB4E2,
    0x72BE5D74F27B896F,
    0x80DEB1FE3B1696B1,
    0x9BDC06A725C71235,
    0xC19BF174CF692694,
    0xE49B69C19EF14AD2,
    0xEFBE4786384F25E3,
    0x0FC19DC68B8CD5B5,
    0x240CA1CC77AC9C65,
    0x2DE92C6F592B0275,
    0x4A7484AA6EA6E483,
    0x5CB0A9DCBD41FBD4,
    0x76F988DA831153B5,
    0x983E5152EE66DFAB,
    0xA831C66D2DB43210,
    0xB00327C898FB213F,
    0xBF597FC7BEEF0EE4,
    0xC6E00BF33DA88FC2,
    0xD5A79147930AA725,
    0x06CA6351E003826F,
    0x142929670A0E6E70,
    0x27B70A8546D22FFC,
    0x2E1B21385C26C926,
    0x4D2C6DFC5AC42AED,
    0x53380D139D95B3DF,
    0x650A73548BAF63DE,
    0x766A0ABB3C77B2A8,
    0x81C2C92E47EDAEE6,
    0x92722C851482353B,
    0xA2BFE8A14CF10364,
    0xA81A664BBC423001,
    0xC24B8B70D0F89791,
    0xC76C51A30654BE30,
    0xD192E819D6EF5218,
    0xD69906245565A910,
    0xF40E35855771202A,
    0x106AA07032BBD1B8,
    0x19A4C116B8D2D0C8,
    0x1E376C085141AB53,
    0x2748774CDF8EEB99,
    0x34B0BCB5E19B48A8,
    0x391C0CB3C5C95A63,
    0x4ED8AA4AE3418ACB,
    0x5B9CCA4F7763E373,
    0x682E6FF3D6B2B8A3,
    0x748F82EE5DEFB2FC,
    0x78A5636F43172F60,
    0x84C87814A1F0AB72,
    0x8CC702081A6439EC,
    0x90BEFFFA23631E28,
    0xA4506CEBDE82BDE9,
    0xBEF9A3F7B2C67915,
    0xC67178F2E372532B,
    0xCA273ECEEA26619C,
    0xD186B8C721C0C207,
    0xEADA7DD6CDE0EB1E,
    0xF57D4F7FEE6ED178,
    0x06F067AA72176FBA,
    0x0A637DC5A2C898A6,
    0x113F9804BEF90DAE,
    0x1B710B35131C471B,
    0x28DB77F523047D84,
    0x32CAAB7B40C72493,
    0x3C9EBE0A15C9BEBC,
    0x431D67C49C100D4C,
    0x4CC5D4BECB3E42B6,
    0x597F299CFC657E2A,
    0x5FCB6FAB3AD6FAEC,
    0x6C44198C4A475817,
]


@dataclass
class TrustedVector:
    original: list[int]
    digest_hex: str

    @property
    def length(self) -> int:
        return len(self.original)

    @property
    def sanitized_prefix(self) -> list[int]:
        return [abs(value) for value in self.original]

    @property
    def inner_bytes(self) -> bytes:
        return str(self.original)[1:-1].encode("latin-1")


def rotr(value: int, amount: int) -> int:
    return ((value >> amount) | (value << (64 - amount))) & MASK64


def sha512_padding(message_len: int) -> bytes:
    pad = b"\x80"
    pad += b"\x00" * ((112 - (message_len + 1) % 128) % 128)
    pad += (message_len * 8).to_bytes(16, "big")
    return pad


class SHA512Extender:
    def __init__(self, state: list[int] | None = None, message_len: int = 0):
        self.state = list(SHA512_IV if state is None else state)
        self.message_len = message_len
        self.buffer = b""

    def _compress(self, block: bytes) -> None:
        words = [int.from_bytes(block[index:index + 8], "big") for index in range(0, 128, 8)]
        for index in range(16, 80):
            s0 = rotr(words[index - 15], 1) ^ rotr(words[index - 15], 8) ^ (words[index - 15] >> 7)
            s1 = rotr(words[index - 2], 19) ^ rotr(words[index - 2], 61) ^ (words[index - 2] >> 6)
            words.append((words[index - 16] + s0 + words[index - 7] + s1) & MASK64)

        a, b, c, d, e, f, g, h = self.state
        for index in range(80):
            sum1 = rotr(e, 14) ^ rotr(e, 18) ^ rotr(e, 41)
            choice = (e & f) ^ ((~e) & g)
            temp1 = (h + sum1 + choice + SHA512_K[index] + words[index]) & MASK64
            sum0 = rotr(a, 28) ^ rotr(a, 34) ^ rotr(a, 39)
            majority = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (sum0 + majority) & MASK64

            h = g
            g = f
            f = e
            e = (d + temp1) & MASK64
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & MASK64

        self.state = [
            (current + update) & MASK64
            for current, update in zip(self.state, [a, b, c, d, e, f, g, h])
        ]

    def update(self, data: bytes) -> None:
        self.message_len += len(data)
        self.buffer += data
        while len(self.buffer) >= 128:
            self._compress(self.buffer[:128])
            self.buffer = self.buffer[128:]

    def digest(self) -> bytes:
        clone = SHA512Extender(self.state, self.message_len)
        clone.buffer = self.buffer
        padded = clone.buffer + sha512_padding(clone.message_len)
        for index in range(0, len(padded), 128):
            clone._compress(padded[index:index + 128])
        return b"".join(word.to_bytes(8, "big") for word in clone.state)

    def hexdigest(self) -> str:
        return self.digest().hex()


def extend_sha512(digest_hex: str, original_len: int, extra: bytes) -> tuple[bytes, str]:
    state = [int(digest_hex[index:index + 16], 16) for index in range(0, 128, 16)]
    glue = sha512_padding(original_len)
    extender = SHA512Extender(state=state, message_len=original_len + len(glue))
    extender.update(extra)
    return glue + extra, extender.hexdigest()


def ascii_escape(data: bytes) -> str:
    pieces: list[str] = []
    for byte in data:
        if 32 <= byte <= 126 and byte != 0x5C:
            pieces.append(chr(byte))
        else:
            pieces.append(f"\\x{byte:02x}")
    return "".join(pieces)


def make_query_payload(vector: TrustedVector, suffix: list[int]) -> tuple[str, str]:
    extra = b""
    if suffix:
        extra = b"," + b",".join(str(value).encode("ascii") for value in suffix)
    forged_tail, digest_hex = extend_sha512(
        vector.digest_hex,
        SALT_SIZE + len(vector.inner_bytes),
        extra,
    )
    forged_inner = vector.inner_bytes + forged_tail
    payload = "[" + ascii_escape(forged_inner) + "]"
    return payload, digest_hex


def parse_setup_blob(blob: str) -> tuple[bytes, bytes, list[TrustedVector]]:
    iv_match = re.search(r"IV:\s*([0-9a-fA-F]+)", blob)
    ct_match = re.search(r"Ciphertext:\s*([0-9a-fA-F]+)", blob)
    if not iv_match or not ct_match:
        raise ValueError("failed to parse IV/ciphertext")

    vectors: list[TrustedVector] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line.startswith("("):
            continue
        parsed = ast.literal_eval(line)
        vectors.append(TrustedVector(original=parsed[0], digest_hex=parsed[1]))

    if len(vectors) != 5:
        raise ValueError(f"expected 5 trusted vectors, found {len(vectors)}")

    return bytes.fromhex(iv_match.group(1)), bytes.fromhex(ct_match.group(1)), vectors


def recv_setup(io) -> tuple[bytes, bytes, list[TrustedVector]]:
    blob = io.recvuntil(b"Enter your vector: ").decode("latin-1")
    return parse_setup_blob(blob)


def issue_query(io, vector: TrustedVector, suffix: list[int]) -> int:
    payload, digest_hex = make_query_payload(vector, suffix)
    io.sendline(payload.encode("ascii"))
    io.recvuntil(b"Enter its salted hash: ")
    io.sendline(digest_hex.encode("ascii"))
    response = io.recvuntil(b"Enter your vector: ").decode("latin-1")
    match = re.search(r"The computed dot product is:\s*(-?\d+)", response)
    if not match:
        raise ValueError(f"unexpected service response: {response!r}")
    return int(match.group(1))


def recover_tail(io, vector: TrustedVector) -> tuple[int, list[int]]:
    suffix_len = KEY_SIZE - vector.length
    base_suffix = [0] * suffix_len
    base_value = issue_query(io, vector, base_suffix)
    tail = [0] * suffix_len
    for index in range(suffix_len):
        probe = [0] * suffix_len
        probe[index] = 1
        value = issue_query(io, vector, probe)
        tail[index] = value - base_value
    return base_value, tail


def solve_prefix(vectors: list[TrustedVector], base_values: list[int], known_tail: list[int], prefix_len: int) -> list[int] | None:
    rows: list[list[int]] = []
    constants: list[int] = []

    for vector, base_value in zip(vectors, base_values):
        coeffs = vector.sanitized_prefix
        known_offset = sum(coeffs[index] * known_tail[index - prefix_len] for index in range(prefix_len, len(coeffs)))
        rows.append(coeffs[:prefix_len])
        constants.append(base_value - known_offset)

    matrix = Matrix(rows)
    if matrix.rank() < prefix_len:
        return None

    solution_set = list(linsolve((matrix, Matrix(constants))))
    if len(solution_set) != 1:
        return None

    solution = list(solution_set[0])
    prefix: list[int] = []
    for value in solution:
        if not value.is_integer:
            return None
        integer = int(value)
        if not 0 <= integer < 256:
            return None
        prefix.append(integer)
    return prefix


def decrypt_flag(iv: bytes, ciphertext: bytes, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext.decode()


def attempt(io) -> str | None:
    iv, ciphertext, vectors = recv_setup(io)
    vectors.sort(key=lambda item: item.length)

    shortest = vectors[0]
    prefix_len = shortest.length
    if prefix_len > len(vectors):
        return None

    base_values = [0] * len(vectors)
    shortest_base, tail = recover_tail(io, shortest)
    base_values[0] = shortest_base

    for index, vector in enumerate(vectors[1:], start=1):
        base_values[index] = issue_query(io, vector, [0] * (KEY_SIZE - vector.length))

    prefix = solve_prefix(vectors, base_values, tail, prefix_len)
    if prefix is None:
        return None

    key_bytes = bytes(prefix + tail)
    return decrypt_flag(iv, ciphertext, key_bytes)


def self_test() -> None:
    for _ in range(20):
        secret = random.randbytes(SALT_SIZE)
        original = b"1, -2, 3"
        extra = b",0,1,0,0"
        digest_hex = hashlib.sha512(secret + original).hexdigest()
        forged_tail, forged_digest = extend_sha512(digest_hex, SALT_SIZE + len(original), extra)
        assert forged_tail == sha512_padding(SALT_SIZE + len(original)) + extra
        assert forged_digest == hashlib.sha512(secret + original + forged_tail).hexdigest()

    payload = "[" + ascii_escape(b"7, -12" + b"\x80\x00" + b",0,1") + "]"
    decoded = payload.encode().decode("unicode_escape")
    sanitized = "".join(char if char in "0123456789,[]" else "" for char in decoded)
    assert ast.literal_eval(sanitized) == [7, 12, 0, 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--tries", type=int, default=20)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test ok")
        return

    for attempt_index in range(1, args.tries + 1):
        io = remote(args.host, args.port)
        try:
            flag = attempt(io)
            if flag is not None:
                print(flag)
                return
        except EOFError:
            pass
        finally:
            io.close()
        print(f"attempt {attempt_index} failed, retrying")

    raise SystemExit("exhausted attempts without a solvable instance")


if __name__ == "__main__":
    main()
