"""치환 커버리지 — 화면에 나올 줄 중 몇 줄이 한국어로 바뀌는가.

캐리어 방식이라 **안 바뀐 일본어는 한글 글리프로 렌더되어 깨져 보인다.**
따라서 품질 이전에 '전부 덮였는가'가 먼저다.
"""
import collections
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from skcodec import decode

ROOT = r"P:\AI\demonbane-ps2-kr"
PS2 = os.path.join(ROOT, "work", "script")
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


covered = collections.defaultdict(set)
for r in list(csv.reader(open(os.path.join(ROOT, "work", "ref", "aligned.tsv"), encoding="utf-8"),
                         delimiter="\t", quoting=csv.QUOTE_NONE))[1:]:
    if len(r) >= 7 and r[6]:
        for cell in r[6].split(","):      # lines 열: "파일:줄,파일:줄,..."
            fn, no = cell.rsplit(":", 1)
            covered[fn].add(int(no))
    elif len(r) >= 6 and r[2]:
        covered[r[1]].add(int(r[2]))

tot = hit = 0
worst = []
for fn in sorted(os.listdir(PS2)):
    if fn == "vssver.scc":
        continue
    txt = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    n = h = 0
    for no, raw in enumerate(txt.split("\n"), 1):
        body = TAG.sub("", strip_comment(raw.rstrip("\r"))).strip()
        if not body:
            continue
        n += 1
        if no in covered.get(fn, ()):
            h += 1
    tot += n
    hit += h
    if n and h / n < 0.9:
        worst.append((fn, n, h))

print(f"화면에 나올 줄 {tot:,} 중 치환되는 줄 {hit:,} ({hit / tot:.1%})")
print(f"남는 일본어 줄 {tot - hit:,}  ← 캐리어 폰트에선 전부 깨져 보인다")
print(f"\n커버리지 90% 미만 파일 {len(worst)}개 (상위 12):")
for fn, n, h in sorted(worst, key=lambda x: (x[2] / x[1]))[:12]:
    print(f"  {fn:<18} {h:>5}/{n:<5} ({h / n:>4.0%})")
