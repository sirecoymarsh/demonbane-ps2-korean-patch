import re
import sys

path = sys.argv[1]
minlen = int(sys.argv[2]) if len(sys.argv) > 2 else 5
pat = sys.argv[3] if len(sys.argv) > 3 else None

data = open(path, "rb").read()
rx = re.compile(rb"[\x20-\x7E]{%d,}" % minlen)
for m in rx.finditer(data):
    s = m.group().decode("ascii")
    if pat and pat.lower() not in s.lower():
        continue
    print(f"{m.start():08X}  {s}")
