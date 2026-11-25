import os
import re
import collections
from skcodec import decode, encode

src = r"P:\AI\demonbane-ps2-kr\work\script"
names = sorted(os.listdir(src))

# 1) round-trip
bad = 0
for fn in names:
    raw = open(os.path.join(src, fn), "rb").read()
    if encode(decode(raw)) != raw:
        bad += 1
        print("  roundtrip FAIL", fn)
print(f"round-trip: {len(names) - bad}/{len(names)} files byte-identical")

# 2) volume of actual displayed text (strip tags and comments)
tag = re.compile(r"<[^>\n]*>")
chars = 0
lines = 0
used = collections.Counter()
scenario = 0
for fn in names:
    if fn == "vssver.scc":
        continue
    txt = decode(open(os.path.join(src, fn), "rb").read()).decode("cp932", "replace")
    scenario += 1
    for line in txt.split("\n"):
        s = line.strip("\r")
        if s.startswith("//") or s.startswith(";"):
            continue
        s = tag.sub("", s).strip()
        if not s:
            continue
        lines += 1
        chars += len(s)
        used.update(c for c in s if ord(c) > 0x7F)

print(f"script files: {scenario}")
print(f"displayed text lines : {lines:,}")
print(f"displayed characters : {chars:,}")
print(f"distinct non-ascii characters actually displayed: {len(used):,}")

# 3) what does the font ship?
fontlist = open(r"P:\AI\demonbane-ps2-kr\work\font\inside.txt", "rb").read()
glyphs = fontlist.decode("cp932")
print(f"inside.txt: {len(fontlist)} bytes -> {len(glyphs)} glyph slots (sorted={list(glyphs) == sorted(glyphs)})")
missing = [c for c in used if c not in set(glyphs)]
print(f"displayed chars not in font list: {len(missing)} {''.join(missing[:40])}")
