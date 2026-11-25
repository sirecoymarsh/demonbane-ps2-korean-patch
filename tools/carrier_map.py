"""동봉 폰트(MShangang.ttf)의 글리프 윤곽을 대조해 '캐리어 한자 -> 한글' 역매핑표를 만든다.

패치는 한글을 CP932 한자 코드포인트에 실어 보내고, 폰트가 그 자리에 한글 글리프를 그려 넣는 방식이다.
글리프 이름은 uniXXXX 라 정보가 없으므로 **윤곽 좌표 해시**로 원래 한글을 찾는다.
"""
import hashlib
import json
import sys

sys.path.insert(0, r"P:\AI\python\libs")
from fontTools.ttLib import TTFont

FONT = r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf"
OUT = r"P:\AI\demonbane-ps2-kr\work\patch\carrier_map.json"

f = TTFont(FONT)
glyf = f["glyf"]
cmap = f.getBestCmap()
hmtx = f["hmtx"]


def sig(name):
    g = glyf[name]
    h = hashlib.sha1()
    h.update(str(hmtx[name]).encode())
    if g.numberOfContours == 0:
        return None
    if g.isComposite():
        for c in g.components:
            h.update(f"{c.glyphName}|{getattr(c, 'x', 0)}|{getattr(c, 'y', 0)}".encode())
    else:
        h.update(bytes(g.flags))
        h.update(",".join(f"{x},{y}" for x, y in zip(g.coordinates.array[0::2], g.coordinates.array[1::2])).encode()
                 if hasattr(g.coordinates, "array") else
                 ",".join(f"{p[0]},{p[1]}" for p in g.coordinates).encode())
        h.update(str(list(g.endPtsOfContours)).encode())
    return h.hexdigest()


# 한글 음절 -> 윤곽 해시
hangul = {}
collide = 0
for cp in range(0xAC00, 0xD7A4):
    n = cmap.get(cp)
    if not n:
        continue
    s = sig(n)
    if not s:
        continue
    if s in hangul:
        collide += 1
        continue
    hangul[s] = cp

print(f"한글 글리프 {len(hangul)}종 (윤곽 중복 {collide})")

# 나머지 코드포인트 중 한글 윤곽과 일치하는 것 = 캐리어
carrier = {}
for cp, n in cmap.items():
    if 0xAC00 <= cp <= 0xD7A3 or cp < 0x80:
        continue
    s = sig(n)
    if s and s in hangul:
        carrier[cp] = hangul[s]

print(f"캐리어로 판정된 코드포인트: {len(carrier)}")
json.dump({f"{k:04X}": f"{v:04X}" for k, v in sorted(carrier.items())},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"-> {OUT}")

sample = sorted(carrier.items())[:25]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("샘플:", "  ".join(f"{chr(k)}(U+{k:04X})->{chr(v)}" for k, v in sample))
