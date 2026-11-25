"""Extract selected files out of the Demonbane PS2 ISO (read-only)."""
import sys
import os
from iso9660 import Iso

iso_path = sys.argv[1]
out_dir = sys.argv[2]
wanted = [w.upper() for w in sys.argv[3:]]

iso = Iso(iso_path)
for full, lba, length, flags in iso.tree():
    if flags & 0x02:
        continue
    if wanted and not any(w in full.upper() for w in wanted):
        continue
    out = os.path.join(out_dir, full.lstrip("/").replace("/", os.sep))
    iso.extract(lba, length, out)
    print(f"extracted {full} -> {out} ({length} bytes)")
