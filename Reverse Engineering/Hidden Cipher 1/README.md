# Hidden Cipher 1

**Category:** Reverse Engineering
**Difficulty:** Medium
**Author:** Yahaya Meddy

---

## Challenge Description

The challenge gives us a binary called `hiddencipher` and a local `flag.txt`.

The description says that the flag is slightly encrypted and that we need to figure out the cipher and the key.

We can also connect to the remote service using netcat:

```bash
nc candy-mountain.picoctf.net 50326
```

![Challenge](assets/challenge.png)

The local `flag.txt` only contains a fake flag, so I used it to understand and verify the encryption logic locally before attacking the remote service.

---

## Initial Recon

I started by checking the provided files:

```bash
ls
file hiddencipher flag.txt
strings hiddencipher | grep -iE "upx|flag|secret|encrypted|failed|%02x"
```

The binary was detected as a 64-bit ELF:

```text
hiddencipher: ELF 64-bit LSB pie executable, x86-64, statically linked, no section header
```

The interesting part is:

```text
no section header
```

This usually makes static analysis harder because normal sections and symbols are not easily available.

The strings output also showed several UPX indicators:

```text
UPX!
flag.txt
%02x
$Info: This file is packed with the UPX executable packer
```

![Recon](assets/recon.png)

So the first important discovery was that the binary is packed with UPX.

---

## Unpacking the Binary

Since the binary was packed with UPX, I unpacked it using:

```bash
upx -d hiddencipher -o hiddencipher_unpacked
```

UPX successfully unpacked the file:

```text
24275 <- 7196   29.64%   linux/amd64   hiddencipher_unpacked
Unpacked 1 file.
```

![Unpacking](assets/unpack.png)

After unpacking, the binary became much easier to analyze.

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

The strings became more useful:

```text
flag.txt
[!] Failed to open flag.txt
Here your encrypted flag:
%02x
get_secret
```

The symbols also revealed two important functions:

```text
00000000000012a9 T get_secret
00000000000012eb T main
```

![Unpacked recon](assets/unpacked_recon.png)

At this point, the reversing path is clear:

* `get_secret` probably creates or returns the key.
* `main` probably reads `flag.txt`, encrypts it, and prints the encrypted result.

---

## Analyzing `get_secret`

I disassembled the `get_secret` function:

```bash
objdump -d -Mintel hiddencipher_unpacked | grep -A70 '<get_secret>'
```

The function writes several bytes into memory:

```asm
12b1: mov BYTE PTR [rip+0x2d59],0x53
12b8: mov BYTE PTR [rip+0x2d53],0x33
12bf: mov BYTE PTR [rip+0x2d4d],0x43
12c6: mov BYTE PTR [rip+0x2d47],0x72
12cd: mov BYTE PTR [rip+0x2d41],0x33
12d4: mov BYTE PTR [rip+0x2d3b],0x74
12db: mov BYTE PTR [rip+0x2d35],0x0
```

![get\_secret objdump](assets/odjump.png)

These bytes are:

```text
53 33 43 72 33 74
```

Converting them from hex to ASCII gives:

```text
S3Cr3t
```

I also confirmed this in CyberChef using:

```text
From Hex
```

![CyberChef key conversion](assets/cyberchef.png)

So the secret key is:

```text
S3Cr3t
```

---

## Ghidra Confirmation: `get_secret`

To make the logic easier to read, I opened the unpacked binary in Ghidra.

The decompiled `get_secret()` function confirms the same thing:

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

![Ghidra get\_secret](assets/get_secret.png)

This confirms that the program builds the key byte by byte.

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
```

After that, it calls `get_secret`:

```asm
13d9: call 12a9 <get_secret>
13de: mov QWORD PTR [rbp-0x8],rax
```

![Main part 1](assets/odjump1.png)

The most important part is the encryption loop:

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

![Main XOR loop](assets/odjump2.png)

This tells us that the program:

1. Reads one byte from the flag.
2. Reads one byte from the secret key.
3. XORs them together.
4. Prints the encrypted byte using `%02x`.
5. Repeats this for the entire flag.

---

## Ghidra Confirmation: `main`

The Ghidra decompiler makes the logic much clearer.

The program first opens the local flag file:

```c
__stream = fopen("flag.txt","rb");
```

Then it reads the file and calls `get_secret()`:

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

![Ghidra main](assets/ghidra.png)

The `local_2c % 6` part means the key is reused every 6 bytes.

That makes sense because:

```text
len("S3Cr3t") = 6
```

So the encryption is repeating-key XOR:

```text
cipher[i] = flag[i] XOR key[i % 6]
```

Where:

```text
key = S3Cr3t
```

Since XOR is reversible, decryption is the same operation:

```text
flag[i] = cipher[i] XOR key[i % 6]
```

---

## Local Verification

Before attacking the remote service, I tested the logic locally.

Running the unpacked binary with the provided fake `flag.txt` gives:

```bash
./hiddencipher_unpacked
```

Output:

```text
Here your encrypted flag:
235a201d70201548251358110c552f135409
```

![Local encrypted output](assets/exploit_local.png)

To verify the reversing result, I decrypted that local ciphertext in CyberChef.

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

![Local CyberChef verification](assets/exploit_local.png)

This confirms that the binary encrypts the flag using repeating-key XOR with the key `S3Cr3t`.

---

## Remote Exploitation

Now that the encryption logic is understood, I connected to the remote service:

```bash
nc candy-mountain.picoctf.net 50326
```

The remote service printed an encrypted flag:

```text
Here your encrypted flag:
235a201d702015483b1d412b265d3313501f0c072d135f0d2002302d0a406a0a701756102e
```

![Remote output](assets/exploit.png)

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
picoCTF{xor_unpack_4nalys1s_94993eed}
```

![Remote decrypt](assets/exploit.png)

Challenge hacked.

---

## Flag

```text
picoCTF{xor_unpack_4nalys1s_94993eed}
```

---

## Why This Works

The binary does not directly print the flag.

Instead, it reads `flag.txt`, encrypts it with a repeating XOR key, and prints the encrypted bytes as hexadecimal.

The key is not hidden very strongly. After unpacking the binary, the `get_secret()` function clearly constructs it byte by byte:

```text
53 33 43 72 33 74
```

Which is:

```text
S3Cr3t
```

The encryption loop uses:

```text
flag_byte XOR key_byte
```

and prints the result with:

```c
printf("%02x", encrypted_byte);
```

Because XOR is reversible, applying the same key again decrypts the ciphertext.

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

* Packed binaries should be checked with `strings` and unpacked if possible.
* UPX-packed binaries can often be unpacked with `upx -d`.
* `nm` is very useful when symbols are not stripped.
* `get_secret` revealed the encryption key.
* The encryption was repeating-key XOR.
* `%02x` showed that the encrypted bytes were printed as hexadecimal.
* XOR encryption can be reversed by applying the same key again.

---

## Final Thoughts

This was a clean reverse engineering challenge.

The main trick was not guessing the flag, but understanding how the program transformed it.

Once the binary was unpacked, the logic became straightforward:

1. Read `flag.txt`.
2. Build the key `S3Cr3t`.
3. XOR each flag byte with the repeating key.
4. Print the result as hex.

After verifying the logic locally with the fake flag, the same CyberChef recipe was enough to decrypt the real remote output and recover the flag.

Pwned.
