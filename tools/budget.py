"""씬 단위 글자량 수지로 '한국어가 못 덮는 PS2 본문'을 보수적으로 추정한다.

줄 단위 정렬은 판본 간 줄 묶음이 달라 경계가 흔들리지만, 씬 단위 총량은 흔들리지 않는다.
    부족분(씬) = max(0, PS2_일본어자수 - KO_한글자수 / 길이비)
"""
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


def scene_of(n):
    m = re.match(r"[Dd](\d{4})", os.path.splitext(n)[0])
    return m.group(1) if m else None


jp = collections.Counter()
for fn in os.listdir(PS2):
    s = scene_of(fn)
    if not s:
        continue
    t = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    for raw in t.split("\n"):
        b = TAG.sub("", strip_comment(raw.rstrip("\r"))).strip()
        jp[s] += len(b)

ko = collections.Counter()
for fn in os.listdir(KO):
    s = scene_of(fn)
    if s:
        ko[s] += sum(len(l.strip()) for l in open(os.path.join(KO, fn), encoding="utf-8"))

RATIO = sum(ko.values()) / sum(jp.values())
short = []
for s in sorted(jp):
    need = jp[s]
    have = ko.get(s, 0) / RATIO
    if need - have > 0:
        short.append((s, need, have, need - have))

tot_jp = sum(jp.values())
tot_short = sum(x[3] for x in short)
print(f"PS2 본문 {tot_jp:,}자 / 한국어 환산 {sum(ko.values()) / RATIO:,.0f}자   길이비 {RATIO:.3f}")
print(f"한국어가 못 덮는 PS2 본문(씬 수지 기준): {tot_short:,.0f}자  = 전체의 {tot_short / tot_jp:.1%}")
print(f"부족한 씬 {len(short)}개 / 전체 {len(jp)}개\n")
for s, n, h, d in sorted(short, key=lambda x: -x[3])[:20]:
    tag = " ← PS2 전용" if h == 0 else ""
    print(f"  {s}: PS2 {n:>7,}자 / KO환산 {h:>8,.0f}자 / 부족 {d:>7,.0f}자{tag}")
