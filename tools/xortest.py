import os
import collections

d = r"P:\AI\demonbane-ps2-kr\work\script"
a = open(os.path.join(d, "D1105le.txt"), "rb").read()
b = open(os.path.join(d, "D1105ru.txt"), "rb").read()
n = min(len(a), len(b))
x = bytes(p ^ q for p, q in zip(a[:n], b[:n]))
zeros = x.count(0)
print(f"XOR of two scripts: len={n} zerobytes={zeros} ({zeros / n:.3%})")
print("first 64:", x[:64].hex(" "))
c = collections.Counter(x)
print("top 12 byte values in XOR:", c.most_common(12))

# High bit statistics of raw ciphertext: SJIS text is >50% high-bit bytes.
for name in ["D1105le.txt", "start.txt", "chara.h"]:
    raw = open(os.path.join(d, name), "rb").read()
    hi = sum(1 for v in raw if v & 0x80)
    print(f"{name}: high-bit ratio {hi / len(raw):.3f}")

# Does a common prefix pattern exist across many files?
heads = collections.Counter()
for fn in os.listdir(d):
    raw = open(os.path.join(d, fn), "rb").read()
    heads[raw[:8]] += 1
print("most common 8-byte heads:")
for k, v in heads.most_common(8):
    print("  ", k.hex(" "), v)
