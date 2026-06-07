from random import randint
from sage.all import *

N = 48
p = 3
q = 509

R = PolynomialRing(ZZ, 'x')
x = R.gen()
R_modq = PolynomialRing(Integers(q), 'x').quotient(x**N - 1, 'xbar')
R_modp = PolynomialRing(Integers(p), 'x').quotient(x**N - 1, 'xbar')

def gen_poly():
    return R([randint(-1,1) for _ in range(N)])

def gen_msg(text):
    binary_str = ''.join(format(ord(char), '08b') for char in text)
    
    padding_length = (N - (len(binary_str) % N)) % N
    binary_str += '0' * padding_length
    
    chunks = [binary_str[i:i+N] for i in range(0, len(binary_str), N)]
    
    polynomials = [
        R([int(bit) for bit in chunk])
        for chunk in chunks
    ]
    
    return polynomials

def encrypt(h, m): 
    r = gen_poly()
    return R_modq(p*(h*r) + m)

def generate_keys():
    while True:
        # Random ternary polynomials f and g
        f = gen_poly()
        g = gen_poly()
        
        # Check if f is invertible modulo p and q
        try:
            f_p_inv = R_modp(f)**-1
            f_q_inv = R_modq(f)**-1
            break
        except:
            continue

    h = R_modq(p*(f_q_inv*g))
    
    private_key = (f, g, f_p_inv, f_q_inv)
    public_key = h
    return public_key, private_key

with open("flag.txt", "r") as f:
    flag = f.read().strip()

public_key, private_key = generate_keys()
print(f"h = {public_key.list()}")

ciphertext = []
encoded = gen_msg(flag)
for part in encoded:
    ciphertext.append(encrypt(public_key, part))
ct = [c.list() for c in ciphertext]
print(f"ct = {ct}")

with open("public.txt", "w") as f:
    f.write(f"N = {N}\n")
    f.write(f"p = {p}\n")
    f.write(f"q = {q}\n")
    f.write(f"h = {public_key.list()}\n")
    f.write(f"ct = {ct}\n")