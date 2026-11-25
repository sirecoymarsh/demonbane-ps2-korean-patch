import os
import re
import collections
from skcodec import decode

src = r"P:\AI\demonbane-ps2-kr\work\script"
tag = re.compile(r"<[^>\n]*>")

cmds = collections.Counter()
box_len = collections.defaultdict(list)
maxline = ("", 0, "")
scen = 0
for fn in sorted(os.listdir(src)):
    if fn == "vssver.scc":
        continue
    txt = decode(open(os.path.join(src, fn), "rb").read()).decode("cp932", "replace")
    scen += 1
    box = "0"
    for raw in txt.split("\n"):
        s = raw.rstrip("\r")
        for m in re.finditer(r"<\s*([A-Za-z_]+)", s):
            cmds[m.group(1).upper()] += 1
        mb = re.search(r'<BOX\s+type="(\d+)"', s, re.I)
        if mb:
            box = mb.group(1)
        if s.lstrip().startswith("//"):
            continue
        t = tag.sub("", s).strip()
        if not t:
            continue
        # display width: full-width chars count 2 half-widths
        w = sum(2 if ord(c) > 0x7F else 1 for c in t)
        box_len[box].append(w)
        if w > maxline[1]:
            maxline = (fn, w, t[:60])

print(f"scenario files: {scen}")
print("\ncommands used (top 40):")
for k, v in cmds.most_common(40):
    print(f"  {k:<14} {v:>7}")

print("\nline length (in half-width units) per BOX type:")
for b in sorted(box_len, key=lambda x: int(x) if x.isdigit() else 99):
    v = box_len[b]
    v.sort()
    print(f"  BOX {b:>2}: n={len(v):>6} max={v[-1]:>4} p99={v[int(len(v) * 0.99)]:>4} median={v[len(v) // 2]:>3}")
print(f"\nlongest line: {maxline[0]} width={maxline[1]}  {maxline[2]}")
