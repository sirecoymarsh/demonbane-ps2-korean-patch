"""씬별로 PS2 일본어 줄 수 vs PC 한국어 줄 수를 대조해 이식 가능 범위를 잰다."""
import os
import re
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skcodec import decode

PS2 = r"P:\AI\demonbane-ps2-kr\work\script"
KO = r"P:\AI\demonbane-ps2-kr\work\patch\ko"
TAG = re.compile(r"<[^>\n]*>")


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


def scene(name):
    m = re.match(r"[Dd](\d{4})", os.path.splitext(name)[0])
    return m.group(1) if m else None


ps2 = collections.defaultdict(lambda: [0, 0])   # scene -> [lines, chars]
for fn in os.listdir(PS2):
    s = scene(fn)
    if not s:
        continue
    txt = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    for raw in txt.split("\n"):
        body = TAG.sub("", strip_comment(raw.rstrip("\r"))).strip()
        if body:
            ps2[s][0] += 1
            ps2[s][1] += len(body)

ko = collections.defaultdict(lambda: [0, 0])
for fn in os.listdir(KO):
    s = scene(fn)
    if not s:
        continue
    for ln in open(os.path.join(KO, fn), encoding="utf-8"):
        ln = ln.strip()
        if ln:
            ko[s][0] += 1
            ko[s][1] += len(ln)

allsc = sorted(set(ps2) | set(ko))
match = near = far = 0
missing_lines = missing_chars = 0
extra = []
rows = []
for s in allsc:
    a, ac = ps2.get(s, [0, 0])
    b, bc = ko.get(s, [0, 0])
    if a and not b:
        missing_lines += a
        missing_chars += ac
        rows.append((s, a, b, "PS2 전용(번역 없음)"))
        continue
    if b and not a:
        extra.append(s)
        rows.append((s, a, b, "PC 전용(PS2에 없음)"))
        continue
    d = abs(a - b) / max(a, b)
    if d <= 0.02:
        match += 1
        tagv = "일치"
    elif d <= 0.15:
        near += 1
        tagv = f"근사 {a}/{b}"
    else:
        far += 1
        tagv = f"차이 큼 {a}/{b}"
        missing_lines += max(0, a - b)
    rows.append((s, a, b, tagv))

print(f"씬 {len(allsc)}개")
print(f"  줄 수 ±2% 일치      : {match}")
print(f"  근사(±15%)          : {near}")
print(f"  차이 큼             : {far}")
print(f"  PS2 전용(신규 번역) : {sum(1 for r in rows if r[3].startswith('PS2 전용'))}")
print(f"  PC 전용(버림)       : {len(extra)}  {' '.join(extra)}")
print(f"\n신규 번역이 필요한 줄(추정): {missing_lines:,}  /  글자: {missing_chars:,}")

print("\n차이 큰 씬:")
for s, a, b, t in rows:
    if t.startswith("차이") or t.startswith("PS2 전용"):
        print(f"  {s}: PS2 {a:>5}줄 / KO {b:>5}줄   {t}")
