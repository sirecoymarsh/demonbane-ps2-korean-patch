import re
import sys

path = r"P:\AI\demonbane-ps2-kr\extract\SLPM_654.91"
data = open(path, "rb").read()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# NUL-terminated C strings that contain >=3 consecutive Shift-JIS double-byte chars
dbl = rb"(?:[\x81-\x9F\xE0-\xEF][\x40-\x7E\x80-\xFC])"
pat = re.compile(rb"[\x20-\x7E\x81-\xEF]{0,40}?" + dbl + b"{3,}" + rb"[\x20-\x7E\x81-\xEF]{0,40}?\x00")
seen = set()
out = []
for m in pat.finditer(data):
    raw = m.group()[:-1]
    try:
        s = raw.decode("cp932")
    except UnicodeDecodeError:
        continue
    if s in seen:
        continue
    seen.add(s)
    out.append((m.start(), s))

print(f"{len(out)} distinct Japanese UI strings in the ELF")
for off, s in out:
    print(f"  {off:08X}  {s}")
