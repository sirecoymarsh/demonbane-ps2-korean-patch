import struct
import sys

path = sys.argv[1]
blob = open(path, "rb").read()
off = 0x2C
entries = []
while True:
    nul = blob.find(b"\0", off)
    if nul < 0 or nul - off > 40:
        break
    raw = blob[off:nul]
    try:
        name = raw.decode("ascii")
    except UnicodeDecodeError:
        print(f"STOP at 0x{off:X}: non-ascii {raw[:16]!r}")
        break
    if not name or any(c < 0x20 for c in raw):
        print(f"STOP at 0x{off:X}: bad name {raw[:16]!r}")
        break
    off = nul + 1
    typ, unk, data_off, size = struct.unpack_from("<BIII", blob, off)
    off += 13
    entries.append((name, typ, unk, data_off, size))

print(f"parsed {len(entries)} entries, index ends at 0x{off:X}")
total = sum(e[4] for e in entries)
print(f"sum(size)={total}  filesize={len(blob)}  filesize-total={len(blob) - total} (0x{len(blob) - total:X})")
cur = 0
gaps = 0
for name, typ, unk, o, s in entries:
    if o != cur:
        gaps += 1
    cur = o + s
print(f"non-contiguous entries: {gaps}; end offset = {cur} (0x{cur:X})")
print("first 8:")
for e in entries[:8]:
    print("  ", e)
print("last 8:")
for e in entries[-8:]:
    print("  ", e)
print("header dwords:")
for o in range(0, 0x2C, 4):
    print(f"  0x{o:02X}: {struct.unpack_from('<I', blob, o)[0]}")
