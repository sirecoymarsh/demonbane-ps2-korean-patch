"""Minimal ISO9660 reader for the Demonbane PS2 disc (read-only, no mounting)."""
import struct
import sys
import os

SECTOR = 2048


class Iso:
    def __init__(self, path):
        self.f = open(path, "rb")

    def sector(self, lba, count=1):
        self.f.seek(lba * SECTOR)
        return self.f.read(count * SECTOR)

    def read(self, lba, length):
        self.f.seek(lba * SECTOR)
        return self.f.read(length)

    def pvd(self):
        return self.sector(16)

    def root_record(self):
        return self.pvd()[156:190]

    def walk(self, lba, length, path=""):
        data = self.read(lba, length)
        off = 0
        entries = []
        while off < len(data):
            rl = data[off]
            if rl == 0:
                # move to next sector boundary
                off = (off // SECTOR + 1) * SECTOR
                if off >= len(data):
                    break
                continue
            e_lba = struct.unpack_from("<I", data, off + 2)[0]
            e_len = struct.unpack_from("<I", data, off + 10)[0]
            flags = data[off + 25]
            nl = data[off + 32]
            name = data[off + 33:off + 33 + nl].decode("ascii", "replace")
            off += rl
            if name in ("\x00", "\x01"):
                continue
            name = name.split(";")[0]
            full = path + "/" + name
            entries.append((full, e_lba, e_len, flags))
            if flags & 0x02:
                entries.extend(self.walk(e_lba, e_len, full))
        return entries

    def tree(self):
        r = self.root_record()
        lba = struct.unpack_from("<I", r, 2)[0]
        length = struct.unpack_from("<I", r, 10)[0]
        return self.walk(lba, length)

    def extract(self, lba, length, out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        self.f.seek(lba * SECTOR)
        remaining = length
        with open(out, "wb") as g:
            while remaining > 0:
                chunk = self.f.read(min(1 << 20, remaining))
                if not chunk:
                    break
                g.write(chunk)
                remaining -= len(chunk)


if __name__ == "__main__":
    iso = Iso(sys.argv[1])
    for full, lba, length, flags in iso.tree():
        kind = "D" if flags & 0x02 else "F"
        print(f"{kind} {length:>12} {lba:>9} {full}")
