import os
import sys
from skcodec import decode

src = r"P:\AI\demonbane-ps2-kr\work\script"
dst = r"P:\AI\demonbane-ps2-kr\work\script_dec"
os.makedirs(dst, exist_ok=True)

ok = bad = 0
total_chars = 0
total_jp = 0
report = []
for fn in sorted(os.listdir(src)):
    raw = open(os.path.join(src, fn), "rb").read()
    out = decode(raw)
    open(os.path.join(dst, fn), "wb").write(out)
    try:
        txt = out.decode("cp932")
        ok += 1
    except UnicodeDecodeError as e:
        txt = out.decode("cp932", "replace")
        bad += 1
        report.append((fn, str(e)[:90]))
    total_chars += len(txt)
    total_jp += sum(1 for c in txt if ord(c) > 0x7F)

print(f"decoded {ok + bad} files: clean cp932 = {ok}, with errors = {bad}")
for fn, e in report[:20]:
    print(f"  ! {fn}: {e}")
print(f"total characters = {total_chars:,}   non-ascii (JP) characters = {total_jp:,}")
