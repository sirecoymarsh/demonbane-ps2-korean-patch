"""DIGPCK container reader (Demonbane PS2, SCRIPT.PCK / FONT.PCK / IMAGE.PCK ...).

Observed layout:
  0x00  "DIGPCK"
  0x06  u32 version (=1)
  ...   header fields (44 bytes total, see dump_header)
  0x2C  index: repeated records of
            asciiz name
            u8   type
            u32  unknown (0)
            u32  offset  (relative to data base)
            u32  size
  data base = filesize - sum(sizes)  [verified: entries are contiguous from 0]
"""
import struct
import sys
import os

HDR = 0x2C


def parse(path):
    with open(path, "rb") as f:
        blob = f.read()
    assert blob[:6] == b"DIGPCK", blob[:6]
    count = struct.unpack_from("<I", blob, 0x14)[0]
    off = HDR
    entries = []
    while len(entries) < count:
        nul = blob.index(b"\0", off)
        name = blob[off:nul].decode("cp932")
        off = nul + 1
        typ, unk, data_off, size = struct.unpack_from("<BIII", blob, off)
        off += 13
        entries.append(dict(name=name, type=typ, unk=unk, offset=data_off, size=size))
    # data_base 는 자기기술적이다: 0x2C + 인덱스 크기(0x28).
    # (filesize - sum(size) 로도 맞지만, 뒤에 패딩을 붙이면 깨지므로 이쪽을 쓴다)
    base = HDR + struct.unpack_from("<I", blob, 0x28)[0]
    return blob, entries, base


def pack(entries_data, template):
    """entries_data: [(name, bytes)] (원본 순서 유지), template: 원본 blob (헤더 형식 복제)"""
    idx = bytearray()
    data = bytearray()
    for name, payload in entries_data:
        idx += name.encode("cp932") + b"\0"
        idx += struct.pack("<BIII", 2, 0, len(data), len(payload))
        data += payload
    out = bytearray(template[:HDR])
    struct.pack_into("<I", out, 0x14, len(entries_data))
    struct.pack_into("<I", out, 0x1C, len(entries_data))
    struct.pack_into("<I", out, 0x28, len(idx))
    return bytes(out + idx + data)


def dump_header(blob):
    print(f"magic={blob[:6]!r}")
    for o in range(6, HDR, 4):
        v = struct.unpack_from("<I", blob, o)[0]
        print(f"  0x{o:02X}: {v:>12} (0x{v:X})")


if __name__ == "__main__":
    cmd = sys.argv[1]
    path = sys.argv[2]
    blob, entries, base = parse(path)
    if cmd == "list":
        print(f"file={path} size={len(blob)} entries={len(entries)} data_base=0x{base:X} ({base})")
        dump_header(blob)
        contiguous = True
        cur = 0
        for e in entries:
            if e["offset"] != cur:
                contiguous = False
            cur = e["offset"] + e["size"]
        print(f"contiguous={contiguous}  end={cur} (base+end={base + cur} vs filesize={len(blob)})")
        for i, e in enumerate(entries):
            print(f"{i:>4} {e['name']:<20} type={e['type']} unk={e['unk']} off=0x{e['offset']:08X} size={e['size']}")
    elif cmd == "extract":
        out_dir = sys.argv[3]
        os.makedirs(out_dir, exist_ok=True)
        for e in entries:
            data = blob[base + e["offset"]: base + e["offset"] + e["size"]]
            with open(os.path.join(out_dir, e["name"]), "wb") as g:
                g.write(data)
        print(f"extracted {len(entries)} files to {out_dir}")
