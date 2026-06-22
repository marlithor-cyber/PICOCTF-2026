# bytemancy 0

**Category:** General Skills
**Difficulty:** Easy
**Author:** LT "syreal" Jones

---

## Challenge Description

The challenge asks us to send the correct bytes to a remote program.

When connecting to the service, it displays:

```text
Send me ASCII DECIMAL 101, 101, 101, side-by-side, no space.
```

The goal is to understand what these ASCII decimal values represent, then send the correct input to the server.

---

## Source Code Analysis

I started by checking the provided source code:

```bash
cat app.py
```

The important condition is:

```python
if user_input == "\x65\x65\x65":
```

This means the program expects the exact string made of three bytes:

```text
\x65 \x65 \x65
```

In Python, `\x65` represents a byte written in hexadecimal notation.
So the next step is to convert hexadecimal `65` into decimal.

---

## Converting Hexadecimal `65` to Decimal

I used a hexadecimal calculator to convert `0x65` into decimal.

![Hex 65 to decimal](assets/hex_65_to_decimal.png)

The calculator shows:

```text
Hex Value: 65
Decimal Value: 101
```

So:

```text
0x65 = 101 decimal
```

This matches the challenge prompt, which asks for ASCII decimal `101`.

---

## Converting ASCII Decimal `101` to Text

Next, I used CyberChef to convert the ASCII decimal values into characters.

CyberChef recipe:

```text
From Decimal
Delimiter: Space
```

Input:

```text
101 101 101
```

![ASCII 101 to eee](assets/ascii_101_to_eee.png)

The output was:

```text
eee
```

So:

```text
101 decimal = e
```

Therefore:

```text
\x65\x65\x65 = eee
```

The required input is not `101101101`.
It is the character `e` repeated three times.

---

## Solving the Challenge

Instead of typing the bytes manually, I used Python to generate the correct string:

```bash
python3 -c 'print(chr(101)*3)' | nc candy-mountain.picoctf.net 64988
```

Here:

```text
chr(101) = e
chr(101) * 3 = eee
```

![Solving the challenge](assets/solve.png)

The server accepted the input and printed the flag.

---

## Full Command

```bash
python3 -c 'print(chr(101)*3)' | nc candy-mountain.picoctf.net 64988
```

---

## Investigation Summary

```text
1. Read the source code.
2. Found that the program expects "\x65\x65\x65".
3. Converted hexadecimal 65 to decimal 101.
4. Converted ASCII decimal 101 to the character e.
5. Concluded that the expected input is eee.
6. Generatedprint(chr(101)*3)' | nc candy-mountain.picoctf.net 64988
```

---

## Investigation Summary

```text
1. Read the source code.
2. Found that the program expects "\x65\x65\x65".
3. Converted hexadecimal 65 to decimal 101.
4. eee with Python.
7. Sent it to the remote service using netcat.
8. Recovered the flag.
```

---

## Tools Used

```text
cat
Hexadecimal Calculator
CyberChef
Python
netcat
```

---

## Key Takeaways

* `\x65` is hexadecimal byte notation.
* Hexadecimal `65` equals decimal `101`.
* ASCII decimal `101` represents the character `e`.
* The expected input was `eee`, not `101101101`.
* Python is useful for generating exact byte strings.

---

## Final Flag

```text
picoCTF{...REDACTED...}
```
