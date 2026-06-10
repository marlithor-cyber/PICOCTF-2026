# Hidden Cipher 1

**Category:** Reverse Engineering
**Difficulty:** Medium
**Author:** Yahaya Meddy

---

## Challenge Description

The challenge gives us a binary called `hiddencipher` and a local `flag.txt`.

The goal is to understand how the binary encrypts the flag, recover the key, and then use that knowledge to decrypt the real encrypted flag from the remote service.

Remote service:

```bash
nc candy-mountain.picoctf.net 50326
```

![Challenge](assets/challenge.png)

---

## Initial Recon

I started by checking the provided files:

```bash
ls
file hiddencipher flag.txt
strings hiddencipher | grep -iE "upx|flag|secret|encrypted|failed|%02x"
```

The binary is a 64-bit ELF:

```text
hiddencipher: ELF 64-bit LSB pie executable, x86-64, statically linked, no section header
```

The important part is:

```text
no section header
```

This makes static analysis harder because the binary does not expose normal section information.

The `strings` output also shows several useful clues:

```text
UPX!
flag.txt
%02x
$Info: This file is packed with the UPX executable packer
```

![Initial recon](assets/recon.png)

So the binary is packed with UPX, and it also references `flag.txt` and `%02x`, which suggests that it reads the flag and prints encrypted bytes as hexadecimal.

---

## Unpacking the Binary

Since the binary is packed with UPX, I unpacked it using:

```bash
upx -d hiddencipher -o hiddencipher_unpacked
```

UPX successfully unpacked the file:

```text
24275 <- 7196   29.64%   linux/amd64   hiddencipher_unpacked
Unpacked 1 file.
```

![UPX unpack](assets/unpack.png)

After unpacking, the binary becomes much easier to analyze.

---

## Recon After Unpacking

I checked the unpacked binary:

```bash
file hiddencipher_unpacked
strings hiddencipher_unpacked | grep -iE "flag|secret|encrypted|failed|%02x"
nm -C hiddencipher_unpacked | grep -iE "main|secret"
```

The unpacked file is now a normal dynamically linked ELF:

```text
ELF 64-bit LSB pie executable, x86-64, dynamically linked, not stripped
```

The useful strings are now clearer:

```text
flag.txt
[!] Failed to open flag.txt
Here your encrypted flag:
%02x
get_secret
```

The symbols reveal two important functions:

```text
00000000000012a9 T get_secret
00000000000012eb T main
```

![Unpacked recon](assets/unpacked_recon.png)

At this point, the reversing path is clear:

* `get_secret` probably builds or returns the encryption key.
* `main` probably reads `flag.txt`, encrypts it, and prints the encrypted output.

---

## Analyzing `get_secret`

I disassembled `get_secret`:

```bash
objdump -d -Mintel hiddencipher_unpacked | grep -A70 '<get_secret>'
```

The function writes several hardcoded bytes into memory:

```asm
12b1: mov BYTE PTR [rip+0x2d59],0x53
12b8: mov BYTE PTR [rip+0x2d53],0x33
12bf: mov BYTE PTR [rip+0x2d4d],0x43
12c6: mov BYTE PTR [rip+0x2d47],0x72
12cd: mov BYTE PTR [rip+0x2d41],0x33
12d4: mov BYTE PTR [rip+0x2d3b],0x74
12db: mov BYTE PTR [rip+0x2d35],0x0
```

![get\_secret objdump](assets/odjump_get_secret.png)

These bytes are:

```text
53 33 43 72 33 74
```

Converting them from hex to ASCII gives:

```text
S3Cr3t
```

I confirmed this using CyberChef with the `From Hex` operation.

![Key in CyberChef](assets/key_cyberchef.png)

So the secret key is:

```text
S3Cr3t
```

---

## Ghidra Confirmation: `get_secret`

I also opened the unpacked binary in Ghidra.

The decompiled `get_secret()` function confirms the same result:

```c
s.0._0_1_ = 0x53;
s.0._1_1_ = 0x33;
s.0._2_1_ = 0x43;
s.0._3_1_ = 0x72;
s.0._4_1_ = 0x33;
s.0._5_1_ = 0x74;
s.0._6_1_ = 0;
return &s.0;
```

![Ghidra get\_secret](assets/ghidra_get_secret.png)

So `get_secret()` builds the key byte by byte and returns it.

The key is:

```text
S3Cr3t
```

---

## Analyzing `main`

Next, I inspected the `main` function.

The program opens `flag.txt`:

```asm
130b: call fopen@plt
```

Then it reads the file content:

```asm
13ba: call fread@plt
13c6: call fclose@plt
```

After reading the flag, it calls `get_secret`:

```asm
13d9: call 12a9 <get_secret>
13de: mov QWORD PTR [rbp-0x8],rax
```

![Main analysis part 1](assets/odjump_main_1.png)

The important encryption logic is here:

```asm
1407: movzx esi,BYTE PTR [rax]
...
143b: movzx eax,BYTE PTR [rax]
143e: xor eax,esi
1440: mov BYTE PTR [rbp-0x25],al
...
145b: call printf@plt
1460: add DWORD PTR [rbp-0x24],0x1
1469: cmp QWORD PTR [rbp-0x18],rax
146d: jg 13fa <main+0x10f>
```

![Main analysis part 2](assets/odjump_main_2.png)

This means the program:

1. Takes one byte from the flag.
2. Takes one byte from the key.
3. XORs them together.
4. Prints the result as hexadecimal using `%02x`.
5. Repeats until the whole flag is processed.

---

## Ghidra Confirmation: `main`

Ghidra makes the logic much easier to read.

The program opens the flag file:

```c
__stream = fopen("flag.txt","rb");
```

Then it calls `get_secret()`:

```c
puVar2 = get_secret();
puts("Here your encrypted flag:");
```

The encryption loop is:

```c
for (local_2c = 0; (long)local_2c < (long)__n; local_2c = local_2c + 1) {
    printf("%02x",
        (uint)*(byte *)((long)puVar2 + (long)(local_2c % 6)) ^
        (uint)*(byte *)((long)__ptr + (long)local_2c));
}
```

![Ghidra main](assets/ghidra_main.png)

The key part is:

```c
local_2c % 6
```

This means the key is repeated every 6 bytes.

Since:

```text
len("S3Cr3t") = 6
```

The encryption is repeating-key XOR:

```text
cipher[i] = flag[i] XOR key[i % 6]
```

With:

```text
key = S3Cr3t
```

Because XOR is reversible, decryption is the same operation:

```text
flag[i] = cipher[i] XOR key[i % 6]
```

---

## Local Verification

Before attacking the remote service, I verified the logic locally.

Running the unpacked binary with the provided fake `flag.txt` gives:

```bash
./hiddencipher_unpacked
```

Output:

```text
Here your encrypted flag:
235a201d70201548251358110c552f135409
```

Then I decrypted the local ciphertext in CyberChef.

Recipe:

```text
From Hex
XOR
```

XOR key:

```text
S3Cr3t
```

Key format:

```text
UTF8
```

The output was:

```text
picoCTF{fake_flag}
```

![Local decrypt](assets/local_decrypt.png)

This confirms that the binary encrypts the flag using repeating-key XOR with the key `S3Cr3t`.

---

## Remote Exploitation

Now that the encryption logic is understood, I connected to the remote service:

```bash
nc candy-mountain.picoctf.net 50326
```

The remote service printed a real encrypted flag:

```text
Here your encrypted flag:
235a201d702015483b1d412b265d3313501f0c072d135f0d2002302d0a406a0a701756102e
```

I decrypted it using the same CyberChef recipe:

```text
From Hex
XOR
```

With the key:

```text
S3Cr3t
```

The decrypted output was:

```text
picoCTF{...redacted...}
```

![Remote decrypt](assets/remote_decrypt.png)

Challenge pwned.

---

## Flag

```text
picoCTF{xor_unpack_4nalys1s_94993eed}
```

---

## Why This Works

The binary does not print the flag directly.

Instead, it:

1. Reads `flag.txt`.
2. Builds the secret key using `get_secret()`.
3. XORs every flag byte with the repeating key.
4. Prints the result as hexadecimal.

The key is built from these bytes:

```text
53 33 43 72 33 74
```

Which decode to:

```text
S3Cr3t
```

The encryption is:

```text
cipher[i] = flag[i] XOR key[i % 6]
```

Since XOR is reversible, applying the same key again decrypts the ciphertext.

---

## Tools Used

* `file`
* `strings`
* `upx`
* `nm`
* `objdump`
* Ghidra
* CyberChef
* netcat

---

## Key Takeaways

* UPX-packed binaries should be unpacked before deeper analysis.
* `strings` can quickly reveal packers and useful clues.
* `nm` is useful when symbols are not stripped.
* `get_secret` revealed the XOR key.
* `%02x` showed that encrypted bytes are printed as hex.
* Repeating-key XOR can be reversed by applying the same key again.
* Verifying locally with the fake flag makes the remote solve straightforward.

---

## Final Thoughts

This was a clean reverse engineering challenge.

The main trick was not guessing the flag, but understanding how the binary transformed it.

After unpacking the binary, the `get_secret` function revealed the key `S3Cr3t`, and the `main` function showed that the flag was encrypted using repeating-key XOR.

Once the logic was verified locally with the fake flag, the same CyberChef recipe decrypted the remote output and revealed the real flag.

Pwned.
