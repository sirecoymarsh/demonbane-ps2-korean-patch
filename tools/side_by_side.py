import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skcodec import decode

TAG = re.compile(r"<[^>\n]*>")
scene = sys.argv[1] if len(sys.argv) > 1 else "D0101"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 16


def strip_comment(line):
    depth = 0
    for i, ch in enumerate(line):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif ch == "/" and depth == 0 and line.startswith("//", i):
            return line[:i]
    return line


jp = []
p = rf"P:\AI\demonbane-ps2-kr\work\script\{scene}.txt"
for raw in decode(open(p, "rb").read()).decode("cp932", "replace").split("\n"):
    b = TAG.sub("", strip_comment(raw.rstrip("\r"))).strip()
    if b:
        jp.append(b)

ko = [l.strip() for l in open(rf"P:\AI\demonbane-ps2-kr\work\patch\ko\{scene.lower()}.nss.txt",
                              encoding="utf-8") if l.strip()]

print(f"{scene}:  PS2 일본어 {len(jp)}줄  /  PC 한국어 {len(ko)}줄\n")
for i in range(min(n, max(len(jp), len(ko)))):
    a = jp[i] if i < len(jp) else "—"
    b = ko[i] if i < len(ko) else "—"
    print(f"[{i + 1:>3}] JP  {a}")
    print(f"      KO  {b}")
