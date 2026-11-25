"""패치 .nss 에서 PS2 스크립트와 이어붙일 수 있는 '열쇠'(보이스 ID·화자·CG 이름)를 찾는다."""
import collections
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
NSS = r"P:\AI\demonbane-ps2-kr\work\patch\nss"

cmds = collections.Counter()
for fn in os.listdir(NSS):
    t = open(os.path.join(NSS, fn), "rb").read().decode("cp932", "replace")
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", t):
        cmds[m.group(1)] += 1
print("함수 호출 상위 45:")
for k, v in cmds.most_common(45):
    print(f"  {k:<22} {v:>7}")

t = open(os.path.join(NSS, "d0101.nss"), "rb").read().decode("cp932", "replace")
i = t.find("<PRE")
i = t.find("<PRE", i + 400)
print("\n---- 대사 부분 원문 그대로 ----")
print(t[i - 900:i + 500])
