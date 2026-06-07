from Crypto.Util.number import getPrime, inverse, bytes_to_long
import random

# Generate two large primes (1048 bits each)
p = getPrime(1048)
q = getPrime(1048)
n = p * q
phi = (p - 1) * (q - 1)

# compute d
d = getPrime(256)

# Compute the public exponent
e = inverse(d, phi)

# Encrypt a flag
flag = b'picoCTF{...redacted...}'
m = bytes_to_long(flag)
c = pow(m, e, n)

# Output for the challenge
with open("message.txt", "w") as f:
    f.write(f"n = {n}\n")
    f.write(f"e = {e}\n")
    f.write(f"c = {c}\n")
