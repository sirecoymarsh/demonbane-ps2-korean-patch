import re
import sys

path = r"P:\AI\demonbane-ps2-kr\extract\SLPM_654.91"
data = open(path, "rb").read()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# runs of Shift-JIS double-byte characters
pat = re.compile(rb"(?:(?:[\x81-\x9F\xE0-\xEF][\x40-\x7E\x80-\xFC])|[\x20-\x7E]){4,}")
found = []
for m in pat.finditer(data):
    raw = m.group()
    try:
        s = raw.decode("cp932")
    except UnicodeDecodeError:
        continue
    if not any(ord(c) > 0x7F for c in s):
        continue
    found.append((m.start(), s))

print(f"{len(found)} Japanese string candidates in the ELF")
for off, s in found[:80]:
    print(f"  {off:08X}  {s}")
