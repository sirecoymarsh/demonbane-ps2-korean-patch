import sys
sys.path.insert(0, r"P:\AI\python\libs")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from fontTools.ttLib import TTFont

f = TTFont(r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf")
order = f.getGlyphOrder()
cmap = f.getBestCmap()
gid = {n: i for i, n in enumerate(order)}

for ch in "嵯之ルア郎椅":
    cp = ord(ch)
    n = cmap.get(cp)
    if not n:
        print(f"U+{cp:04X} {ch}: 폰트에 없음")
        continue
    i = gid[n]
    print(f"U+{cp:04X} {ch} -> glyph #{i} ({n})")
    print("   이웃:", " ".join(order[j] for j in range(max(0, i - 4), min(len(order), i + 5))))
