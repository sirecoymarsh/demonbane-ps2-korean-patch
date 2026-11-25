import sys
sys.path.insert(0, r"P:\AI\python\libs")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from fontTools.ttLib import TTFont

f = TTFont(r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf")
print("cmap subtables:")
for t in f["cmap"].tables:
    print(f"  platform={t.platformID} enc={t.platEncID} format={t.format} entries={len(t.cmap)}")

best = f.getBestCmap()
hang = [cp for cp in best if 0xAC00 <= cp <= 0xD7A3]
print(f"\nbest cmap: {len(best)} entries; Hangul syllables present: {len(hang)}")

# contiguous ranges
cps = sorted(best)
ranges = []
s = p = cps[0]
for cp in cps[1:]:
    if cp == p + 1:
        p = cp
        continue
    ranges.append((s, p))
    s = p = cp
ranges.append((s, p))
print(f"ranges: {len(ranges)}")
for a, b in ranges[:40]:
    print(f"  U+{a:04X}..U+{b:04X}  ({b - a + 1})")
