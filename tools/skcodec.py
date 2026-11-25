"""sk_decode / sk_encode — the SCRIPT.PCK byte cipher (from SLPM_654.91 @ 0x001BF4B0).

key[j] built with the MSVC rand() LCG seeded with 0x7573616F:
    seed = seed * 214013 + 2531011
    v    = ((seed >> 16) & 0x7FFF) >> 8      # 0..127
    if v == 0: v = 0x55
plain[i] = (cipher[i] - key[i % 32]) & 0xFF
"""

SEED = 0x7573616F


def make_key():
    seed = SEED
    key = []
    for _ in range(32):
        seed = (seed * 214013 + 2531011) & 0xFFFFFFFF
        v = ((seed >> 16) & 0x7FFF) >> 8
        if v == 0:
            v = 0x55
        key.append(v)
    return bytes(key)


KEY = make_key()


def decode(data):
    return bytes((b - KEY[i % 32]) & 0xFF for i, b in enumerate(data))


def encode(data):
    return bytes((b + KEY[i % 32]) & 0xFF for i, b in enumerate(data))


if __name__ == "__main__":
    import sys
    print("key:", KEY.hex(" "))
    if len(sys.argv) > 1:
        raw = open(sys.argv[1], "rb").read()
        out = decode(raw)
        if len(sys.argv) > 2:
            open(sys.argv[2], "wb").write(out)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(out[:1500].decode("cp932", "replace"))
