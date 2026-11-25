"""ISO9660 파일 교체기.

이 디스크는 PVD 하나뿐이고(Joliet 없음) 파일이 12개라, 전체 재빌드 대신
**해당 파일만 교체**하는 게 안전하고 빠르다.

  - 새 데이터가 원래 익스텐트(섹터 단위)에 들어가면 → 제자리 덮어쓰기, 크기 필드만 갱신
  - 넘치면 → 디스크 끝으로 **이전**하고 디렉터리 레코드의 LBA·크기와 PVD 볼륨크기를 갱신

건드리는 필드는 셋뿐:
  디렉터리 레코드 +2/+6  extent (LE/BE)
  디렉터리 레코드 +10/+14 size   (LE/BE)
  PVD            +80/+84 volumeSpaceSize (LE/BE)

ISO9660 은 모든 수치를 **양쪽 엔디안으로 두 번** 적는다. 한쪽만 고치면
읽는 쪽 구현에 따라 조용히 옛값을 쓴다.
"""
import os
import struct
import sys

SECTOR = 2048


def _sectors(n):
    return (n + SECTOR - 1) // SECTOR


class IsoPatcher:
    def __init__(self, path):
        self.f = open(path, "r+b")
        self.path = path
        self.f.seek(16 * SECTOR)
        pvd = self.f.read(SECTOR)
        assert pvd[1:6] == b"CD001" and pvd[0] == 1, "PVD 아님"
        self.vol_sectors = struct.unpack_from("<I", pvd, 80)[0]
        self.root_lba = struct.unpack_from("<I", pvd, 156 + 2)[0]
        self.root_len = struct.unpack_from("<I", pvd, 156 + 10)[0]

    # --- 디렉터리 순회 -------------------------------------------------
    def _walk(self, lba, length, prefix=""):
        self.f.seek(lba * SECTOR)
        data = self.f.read(length)
        off = 0
        while off < len(data):
            rl = data[off]
            if rl == 0:
                off = (off // SECTOR + 1) * SECTOR
                if off >= len(data):
                    break
                continue
            e_lba = struct.unpack_from("<I", data, off + 2)[0]
            e_len = struct.unpack_from("<I", data, off + 10)[0]
            flags = data[off + 25]
            nl = data[off + 32]
            name = data[off + 33:off + 33 + nl].decode("ascii", "replace")
            rec_file_off = lba * SECTOR + off
            off += rl
            if name in ("\x00", "\x01"):
                continue
            full = prefix + "/" + name.split(";")[0]
            yield full, rec_file_off, e_lba, e_len, flags
            if flags & 0x02:
                yield from self._walk(e_lba, e_len, full)

    def find(self, path):
        for full, rec, lba, ln, fl in self._walk(self.root_lba, self.root_len):
            if full.upper() == path.upper():
                return rec, lba, ln, fl
        raise KeyError(path)

    def list(self):
        return list(self._walk(self.root_lba, self.root_len))

    # --- 교체 -----------------------------------------------------------
    def _set_record(self, rec_off, lba, size):
        self.f.seek(rec_off + 2)
        self.f.write(struct.pack("<I", lba) + struct.pack(">I", lba))
        self.f.seek(rec_off + 10)
        self.f.write(struct.pack("<I", size) + struct.pack(">I", size))

    def _set_volume_sectors(self, n):
        self.f.seek(16 * SECTOR + 80)
        self.f.write(struct.pack("<I", n) + struct.pack(">I", n))
        self.vol_sectors = n

    def end_lba(self):
        """마지막 데이터가 끝나는 지점(섹터). 파일 실제 크기와 볼륨 크기 중 큰 쪽."""
        end = self.vol_sectors
        for full, rec, lba, ln, fl in self._walk(self.root_lba, self.root_len):
            if not fl & 0x02:
                end = max(end, lba + _sectors(ln))
        return max(end, _sectors(os.path.getsize(self.path)))

    def replace(self, path, data):
        rec, lba, old_len, fl = self.find(path)
        assert not fl & 0x02, "디렉터리는 교체 못 함"
        old_cap = _sectors(old_len) * SECTOR
        if len(data) <= old_cap:
            self.f.seek(lba * SECTOR)
            self.f.write(data + b"\0" * (old_cap - len(data)))
            self._set_record(rec, lba, len(data))
            return ("제자리", lba, len(data), old_cap - len(data))
        new_lba = self.end_lba()
        self.f.seek(new_lba * SECTOR)
        pad = _sectors(len(data)) * SECTOR - len(data)
        self.f.write(data + b"\0" * pad)
        self._set_record(rec, new_lba, len(data))
        self._set_volume_sectors(new_lba + _sectors(len(data)))
        return ("이전", new_lba, len(data), pad)

    def close(self):
        self.f.flush()
        self.f.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = IsoPatcher(sys.argv[1])
    print(f"volumeSpace={p.vol_sectors} sectors ({p.vol_sectors * SECTOR:,}B)  "
          f"endLBA={p.end_lba()}  파일크기={os.path.getsize(sys.argv[1]):,}")
    for full, rec, lba, ln, fl in p.list():
        if not fl & 0x02:
            print(f"  {full:<24} lba={lba:<9} size={ln:,}  rec@0x{rec:X}")
    p.close()
