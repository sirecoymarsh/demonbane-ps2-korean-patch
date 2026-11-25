import sys
sys.path.insert(0, r"P:\AI\python\libs")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from fontTools.ttLib import TTFont

f = TTFont(r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf")
order = f.getGlyphOrder()
cmap = f.getBestCmap()
gid = {n: i for i, n in enumerate(order)}

# 폰트에서 사라진 한글 음절 = 캐리어로 옮겨간 것
missing = [cp for cp in range(0xAC00, 0xD7A4) if cp not in cmap]
print(f"한글 음절 11172 중 폰트에 없는 것: {len(missing)}")

for cp in (0x62C5, 0x5321, 0x6055):
    n = cmap[cp]
    i = gid[n]
    print(f"\nU+{cp:04X} {chr(cp)} -> glyph #{i} ({n})")
    print("  이웃:", " ".join(f"{order[j]}" for j in range(max(0, i - 4), min(len(order), i + 5))))
