import sys
sys.path.insert(0, r"P:\AI\python\libs")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from fontTools.ttLib import TTFont

f = TTFont(r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf")
glyf = f["glyf"]
cmap = f.getBestCmap()
hmtx = f["hmtx"]

for cp in (0x62C5, 0x5321, 0x6055, 0xAC00, 0xB098, 0xB2E4):
    n = cmap.get(cp)
    if not n:
        print(f"U+{cp:04X} {chr(cp)}: no glyph")
        continue
    g = glyf[n]
    print(f"U+{cp:04X} {chr(cp)} glyph={n} contours={g.numberOfContours} "
          f"composite={g.isComposite()} adv={hmtx[n]}")
    if g.numberOfContours > 0 and g.isComposite():
        print("   comps:", [(c.glyphName, getattr(c, "x", 0), getattr(c, "y", 0)) for c in g.components])
    elif g.numberOfContours > 0:
        pts = list(g.coordinates)
        print(f"   pts={len(pts)} bbox=({g.xMin},{g.yMin},{g.xMax},{g.yMax}) first={pts[:5]}")
