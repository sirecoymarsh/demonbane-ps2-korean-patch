"""Parse the index of a DIGPCK straight out of the ISO without extracting the payload."""
import struct
import sys
sys.path.insert(0, r"P:\AI\demonbane-ps2-kr\tools")
from iso9660 import Iso

ISO = r"F:\DOWN\Kishin Houkou Demonbane (Japan)\Kishin Houkou Demonbane (Japan).iso"
target = sys.argv[1] if len(sys.argv) > 1 else "/IMAGE/IMAGE.PCK"

iso = Iso(ISO)
ent = next(e for e in iso.tree() if e[0] == target)
_, lba, length, _ = ent
head = iso.read(lba, min(length, 1 << 20))
count = struct.unpack_from("<I", head, 0x14)[0]
off = 0x2C
names = []
for _ in range(count):
    nul = head.index(b"\0", off)
    nm = head[off:nul].decode("cp932", "replace")
    off = nul + 1
    typ, unk, o, s = struct.unpack_from("<BIII", head, off)
    off += 13
    names.append((nm, s))
print(f"{target}: {count} entries, index ends at 0x{off:X}")
for nm, s in names:
    print(f"  {nm:<28} {s}")
