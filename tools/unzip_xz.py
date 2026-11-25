"""이 zip 은 압축 방식 95(XZ) 라 파이썬 zipfile 이 못 연다. 로컬 헤더에서 직접 뜯어 lzma 로 푼다."""
import lzma
import os
import struct
import sys
import zipfile

zpath = sys.argv[1]
out = sys.argv[2]
wanted = set(sys.argv[3:])
os.makedirs(out, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

z = zipfile.ZipFile(zpath)
f = open(zpath, "rb")
for i in z.infolist():
    name = i.filename if (i.flag_bits & 0x800) else i.filename.encode("cp437", "replace").decode("cp949", "replace")
    base = name.rsplit("/", 1)[-1]
    if wanted and base not in wanted:
        continue
    f.seek(i.header_offset)
    sig, ver, flags, method, t, d, crc, csize, usize, nlen, elen = struct.unpack("<IHHHHHIIIHH", f.read(30))
    assert sig == 0x04034B50, hex(sig)
    f.seek(i.header_offset + 30 + nlen + elen)
    raw = f.read(i.compress_size)
    if method == 95:
        data = lzma.decompress(raw, format=lzma.FORMAT_XZ)
    elif method == 8:
        import zlib
        data = zlib.decompress(raw, -15)
    else:
        data = raw
    assert len(data) == i.file_size, (len(data), i.file_size)
    open(os.path.join(out, base), "wb").write(data)
    print(f"extracted {base}  {len(data):,}")
