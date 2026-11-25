"""검증된 번역에서 **용어 대응표**를 뽑는다.

전수 재번역으로 가더라도 고유명사 표기는 기존 번역을 따라야 한다(데몬베인은 크툴루 신화 고유명사가 많다).
정렬표에서 일본어 가타카나 용어 ↔ 한글 표기를 통계로 대응시킨다.

방법: 용어 T 를 포함한 JP 줄에 대응하는 KO 줄들을 모으고, 그 안에서 배경 빈도 대비
과대출현하는 한글 n-gram 을 고른다. 정렬이 조금 틀려도 통계라 견딘다.
"""
import collections
import csv
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skcodec import decode

TSV = r"P:\AI\demonbane-ps2-kr\work\ref\aligned.tsv"
PS2 = r"P:\AI\demonbane-ps2-kr\work\script"
OUT = r"P:\AI\demonbane-ps2-kr\work\ref\glossary.tsv"

KATA = re.compile(r"[ァ-ヴー]{2,}")
HAN = re.compile(r"[가-힣]+")

rows = [r for r in list(csv.reader(open(TSV, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:]
        if len(r) >= 6 and r[3] and r[4]]
print(f"정렬쌍 {len(rows):,}")

# 배경: 전체 KO 에서의 n-gram 빈도
bg = collections.Counter()
bg_lines = 0
for r in rows:
    bg_lines += 1
    seen = set()
    for w in HAN.findall(r[4]):
        for n in range(2, min(9, len(w) + 1)):
            for i in range(len(w) - n + 1):
                seen.add(w[i:i + n])
    bg.update(seen)

# 용어별
byterm = collections.defaultdict(list)
for r in rows:
    for t in set(KATA.findall(r[3])):
        byterm[t].append(r[4])

results = []
for t, kos in byterm.items():
    if len(kos) < 4:
        continue
    c = collections.Counter()
    for k in kos:
        seen = set()
        for w in HAN.findall(k):
            for n in range(2, min(9, len(w) + 1)):
                for i in range(len(w) - n + 1):
                    seen.add(w[i:i + n])
        c.update(seen)
    best = None
    for g, n in c.items():
        if n < max(3, len(kos) * 0.5):
            continue
        # 배경 대비 과대출현 + 길이 보너스
        score = (n / len(kos)) * (n / max(bg[g], 1)) * (1 + 0.15 * len(g))
        if best is None or score > best[1]:
            best = (g, score, n)
    if best and best[1] > 0.25:
        results.append((t, best[0], len(kos), best[2] / len(kos)))

results.sort(key=lambda x: -x[2])
with open(OUT, "w", encoding="utf-8", newline="") as g:
    g.write("일본어\t한국어\t등장\t일치율\n")
    for t, k, n, conf in results:
        g.write(f"{t}\t{k}\t{n}\t{conf:.2f}\n")

print(f"용어 {len(results):,}개 -> {OUT}\n")
print("상위 40:")
for t, k, n, conf in results[:40]:
    print(f"  {t:<18} → {k:<14} ({n:>5}회, 신뢰 {conf:.0%})")

# 화자 이름은 PS2 <VOICE NAME> 에 이미 정본이 있다
sp = collections.Counter()
for fn in os.listdir(PS2):
    t = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    for m in re.finditer(r'<VOICE\s+NAME="([^"]*)"', t, re.I):
        if m.group(1):
            sp[m.group(1)] += 1
gl = {t: k for t, k, _, _ in results}
print(f"\nPS2 화자 {len(sp)}명 중 대응표에 잡힌 것:")
miss = []
for name, n in sp.most_common(30):
    if name in gl:
        print(f"  {name:<16} → {gl[name]:<12} ({n}회)")
    else:
        miss.append(f"{name}({n})")
print("  미검출:", " ".join(miss[:20]))
