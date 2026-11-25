import os
import sys
sys.path.insert(0, r"P:\AI\demonbane-ps2-kr\tools")
from digpck import parse
from skcodec import decode

src = r"P:\AI\demonbane-ps2-kr\work\script"
LIMIT = 81920

sizes = []
for fn in os.listdir(src):
    sizes.append((os.path.getsize(os.path.join(src, fn)), fn))
sizes.sort(reverse=True)
print(f"script buffer s_dbScirptInfo = 82152 bytes (text area presumably 0x14000 = {LIMIT})")
print("largest script files:")
for s, fn in sizes[:12]:
    print(f"  {s:>7}  {fn}   headroom={LIMIT - s:>7}")
over = [f for s, f in sizes if s > LIMIT]
print(f"files already over {LIMIT}: {len(over)}")
tight = [(s, f) for s, f in sizes if s > LIMIT * 0.9]
print(f"files above 90% of the ceiling: {len(tight)}")

# textbox / align INIs from PARTS.PCK
blob, entries, base = parse(r"P:\AI\demonbane-ps2-kr\extract\PARTS\PARTS.PCK")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for e in entries:
    if e["name"].lower().endswith(".ini"):
        d = blob[base + e["offset"]: base + e["offset"] + e["size"]]
        txt = d.decode("cp932", "replace")
        if sum(1 for c in txt[:200] if c.isprintable() or c in "\r\n") < 150:
            txt = decode(d).decode("cp932", "replace")
            note = "(sk_decoded)"
        else:
            note = "(plain)"
        print(f"\n===== {e['name']} {e['size']}B {note} =====")
        print(txt[:900])
