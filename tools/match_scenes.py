"""PS2(.txt) 와 PC 패치(.nss) 의 씬 이름을 대조해 구조가 얼마나 겹치는지 본다."""
import os
import re
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PS2 = r"P:\AI\demonbane-ps2-kr\work\script"
PC = r"P:\AI\demonbane-ps2-kr\work\patch\nss"


def key(name):
    """d0105_21かばう.nss / D0105ru.txt -> ('0105', 접미사)"""
    b = os.path.splitext(name)[0]
    m = re.match(r"[Dd](\d{4})(.*)$", b)
    if not m:
        return None, b
    return m.group(1), m.group(2)


ps2 = collections.defaultdict(list)
for f in os.listdir(PS2):
    k, s = key(f)
    if k:
        ps2[k].append(f)
pc = collections.defaultdict(list)
for f in os.listdir(PC):
    k, s = key(f)
    if k:
        pc[k].append(f)

both = sorted(set(ps2) & set(pc))
only2 = sorted(set(ps2) - set(pc))
onlyp = sorted(set(pc) - set(ps2))
print(f"PS2 씬번호 {len(ps2)} / PC 씬번호 {len(pc)}")
print(f"  양쪽 다 있음 : {len(both)}")
print(f"  PS2 에만     : {len(only2)}  {' '.join(only2[:30])}")
print(f"  PC 에만      : {len(onlyp)}  {' '.join(onlyp[:30])}")

print("\n겹치는 씬 샘플 (PS2 파일 | PC 파일):")
for k in both[:14]:
    print(f"  {k}: {sorted(ps2[k])}  |  {sorted(pc[k])}")

print("\nPS2 에만 있는 씬 (전연령판 대체·추가분 후보):")
for k in only2[:40]:
    print(f"  {k}: {sorted(ps2[k])}")
