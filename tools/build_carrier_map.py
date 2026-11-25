"""캐리어 한자 -> 한글 역매핑표 복원.

패치 폰트는 한글 글리프를 CP932 한자 코드포인트로 **옮겨** 놓았다(복사가 아니라 이동).
그래서 쓰인 음절은 U+AC00~D7A3 에서 사라졌고 윤곽 대조로는 못 찾는다.

그러나 **glyf 의 글리프 순서는 원본 그대로**다. 살아남은 한글 글리프를 앵커로 삼아
사이에 낀 캐리어 글리프의 원래 음절을 위치로 되짚는다.

    ... uniC540 uniC541 uniC542 uniC543 [uni62C5] [uni5664] uniC546 uniC547 ...
                                          ^C544      ^C545
"""
import json
import sys

sys.path.insert(0, r"P:\AI\python\libs")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from fontTools.ttLib import TTFont

FONT = r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf"
OUT = r"P:\AI\demonbane-ps2-kr\work\patch\carrier_map.json"

f = TTFont(FONT)
order = f.getGlyphOrder()
cmap = f.getBestCmap()
cp_of_glyph = {}
for cp, n in cmap.items():
    cp_of_glyph.setdefault(n, cp)

HAN = range(0xAC00, 0xD7A4)

# 1) 앵커: 아직 한글 코드포인트를 달고 있는 글리프
anchors = [(i, cp_of_glyph[n]) for i, n in enumerate(order)
           if n in cp_of_glyph and cp_of_glyph[n] in HAN]
anchors.sort()
print(f"살아남은 한글 앵커: {len(anchors)}")

# 2) 앵커 사이 구간에서 간격이 맞으면 선형 배정
carrier = {}
unresolved = []

# 2a) 첫 앵커 앞 / 마지막 앵커 뒤로도 연장 (가·각 처럼 블록 맨 앞이 여기 걸린다)
i0, c0 = anchors[0]
for k in range(1, min(i0, c0 - 0xAC00) + 1):
    g = order[i0 - k]
    cp = cp_of_glyph.get(g)
    if cp is None or cp in HAN:
        break
    carrier[cp] = c0 - k
i9, c9 = anchors[-1]
for k in range(1, min(len(order) - 1 - i9, 0xD7A3 - c9) + 1):
    g = order[i9 + k]
    cp = cp_of_glyph.get(g)
    if cp is None or cp in HAN:
        break
    carrier[cp] = c9 + k
for (i1, c1), (i2, c2) in zip(anchors, anchors[1:]):
    if i2 - i1 <= 1:
        continue
    if i2 - i1 != c2 - c1:
        unresolved.append((i1, c1, i2, c2))
        continue
    for k in range(1, i2 - i1):
        g = order[i1 + k]
        cp = cp_of_glyph.get(g)
        want = c1 + k
        if cp is None or cp in HAN:
            continue
        carrier[cp] = want

# 3) 글리프 이름이 uniXXXX(한글)인데 다른 코드포인트에 걸린 것 = 단순 리맵. 이름이 곧 정답.
direct = 0
for cp, n in cmap.items():
    if cp in HAN or not n.startswith("uni") or len(n) != 7:
        continue
    try:
        want = int(n[3:], 16)
    except ValueError:
        continue
    if want in HAN and carrier.get(cp) != want:
        carrier[cp] = want
        direct += 1
print(f"글리프 이름으로 직접 확정한 것: {direct}")

print(f"복원한 캐리어: {len(carrier)}")
print(f"간격 불일치로 보류한 구간: {len(unresolved)}")
for u in unresolved[:10]:
    print(f"  glyph #{u[0]}(U+{u[1]:04X}) .. #{u[2]}(U+{u[3]:04X})  "
          f"글리프 {u[2] - u[0]}칸 vs 음절 {u[3] - u[1]}칸")

json.dump({f"{k:04X}": f"{v:04X}" for k, v in sorted(carrier.items())},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"-> {OUT}")
print("샘플:", "  ".join(f"{chr(k)}→{chr(v)}" for k, v in list(sorted(carrier.items()))[:20]))
