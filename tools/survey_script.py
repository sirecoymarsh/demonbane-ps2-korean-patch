import os
import sys
import math
import collections

d = r"P:\AI\demonbane-ps2-kr\work\script"
names = sorted(os.listdir(d))


def ent(b):
    c = collections.Counter(b)
    n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


print(f"{len(names)} files")
print("--- head bytes of a sample ---")
for n in ["D1105le.txt", "D1105ru.txt", "start.txt", "chara.h", "include.h",
          "bgm.txt", "menu.nps", "test.nps", "CGmode.txt", "vssver.scc"]:
    p = os.path.join(d, n)
    if not os.path.exists(p):
        continue
    b = open(p, "rb").read()
    print(f"{n:<16} size={len(b):>7} entropy={ent(b):.2f}  head={b[:24].hex(' ')}")

print("--- files whose bytes look like plain cp932 text ---")
plain = []
for n in names:
    b = open(os.path.join(d, n), "rb").read()
    if not b:
        continue
    printable = sum(1 for x in b[:2000] if 0x20 <= x < 0x7F or x in (9, 10, 13))
    if printable / min(len(b), 2000) > 0.6:
        plain.append((n, len(b), ent(b)))
for n, s, e in plain:
    print(f"  PLAIN {n:<16} {s:>7} entropy={e:.2f}")
print(f"plain count = {len(plain)} / {len(names)}")
