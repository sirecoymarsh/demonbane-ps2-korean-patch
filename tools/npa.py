"""Nitroplus NPA 아카이브 리더 ("NPA\\x01\\x00\\x00\\x00NAGATO!!").

헤더 (0x29 바이트)
    0x00  "NPA\\x01\\x00\\x00\\x00"
    0x07  key1 u32 ("NAGA")
    0x0B  key2 u32 ("TO!!")
    0x0F  compress u8
    0x10  encrypt  u8
    0x11  total_count u32
    0x15  folder_count u32
    0x19  file_count u32
    0x1D  unk[8]
    0x25  table_size u32
    0x29  엔트리 시작

엔트리
    u32 name_len / name[name_len] (난독화) / u8 type(1=dir,2=file)
    u32 id / u32 offset / u32 comp_size / u32 orig_size

파일명 난독화 (known-plaintext 로 복원. nss.npa 581/581 엔트리가 ".nss" 로 끝나는 것으로 검증):
    plain[i] = (cipher[i] + 0x72 - index - (index >> 8) - 4*i) & 0xFF
    (index>>8 항 = 256개마다 1씩 더 밀림. 원본이 u8 카운터를 쓴 흔적)
"""
import struct
import sys
import zlib

HDR = 0x29


def deobfuscate(cipher, index):
    base = 0x72 - index - (index >> 8)
    return bytes((c + base - 4 * i) & 0xFF for i, c in enumerate(cipher))


def parse(path):
    blob = open(path, "rb").read()
    assert blob[:7] == b"NPA\x01\x00\x00\x00", blob[:7]
    compress = blob[0x0F]
    encrypt = blob[0x10]
    total, folders, files = struct.unpack_from("<III", blob, 0x11)
    table_size = struct.unpack_from("<I", blob, 0x25)[0]
    data_base = HDR + table_size
    off = HDR
    entries = []
    for idx in range(total):
        (nlen,) = struct.unpack_from("<I", blob, off)
        off += 4
        raw = blob[off:off + nlen]
        off += nlen
        typ = blob[off]
        off += 1
        fid, foff, csize, osize = struct.unpack_from("<IIII", blob, off)
        off += 16
        entries.append(dict(index=idx, name=deobfuscate(raw, idx), type=typ,
                            id=fid, offset=foff, comp=csize, orig=osize))
    return blob, entries, data_base, compress, encrypt


def read(blob, e, data_base, compress):
    raw = blob[data_base + e["offset"]: data_base + e["offset"] + e["comp"]]
    if compress and e["comp"] != e["orig"]:
        return zlib.decompress(raw)
    return raw


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cmd, path = sys.argv[1], sys.argv[2]
    blob, entries, base, comp, enc = parse(path)
    if cmd == "list":
        print(f"{path}: {len(entries)} entries  compress={comp} encrypt={enc} data_base=0x{base:X}")
        bad = [e for e in entries if not all(0x20 <= c < 0x7F or c >= 0x81 for c in e["name"])]
        print(f"이름 복호 실패 의심: {len(bad)}")
        for e in entries[:40]:
            print(f"  {e['index']:>4} {e['name'].decode('cp932', 'replace'):<40} "
                  f"type={e['type']} off=0x{e['offset']:08X} {e['comp']}->{e['orig']}")
    elif cmd == "extract":
        import os
        out = sys.argv[3]
        for e in entries:
            if e["type"] != 2:
                continue
            name = e["name"].decode("cp932", "replace").replace("\\", "/")
            dst = os.path.join(out, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(read(blob, e, base, comp))
        print(f"extracted {sum(1 for e in entries if e['type'] == 2)} files -> {out}")
