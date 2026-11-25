"""볼륨 디스크립터를 훑어 Joliet(보조) 유무와 볼륨 크기 필드 위치를 확인한다."""
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ISO = r"F:\DOWN\Kishin Houkou Demonbane (Japan)\Kishin Houkou Demonbane (Japan).iso"
f = open(ISO, "rb")
for i in range(16, 24):
    f.seek(i * 2048)
    d = f.read(2048)
    if d[1:6] != b"CD001":
        print(f"sector {i}: (CD001 아님)")
        continue
    t = d[0]
    name = {0: "Boot", 1: "Primary", 2: "Supplementary(Joliet?)", 3: "Partition", 255: "Terminator"}.get(t, f"type{t}")
    print(f"sector {i}: type={t} {name}")
    if t in (1, 2):
        vol_le, vol_be = struct.unpack_from("<I>I".replace(">", ""), d, 80)[0], struct.unpack_from(">I", d, 84)[0]
        root = d[156:190]
        rlba = struct.unpack_from("<I", root, 2)[0]
        rlen = struct.unpack_from("<I", root, 10)[0]
        esc = d[88:120].rstrip(b"\0")
        print(f"    volumeSpace LE={vol_le} BE={vol_be}  root LBA={rlba} len={rlen}")
        print(f"    escape={esc!r}  volId={d[40:72].decode('ascii','replace').strip()!r}")
        pt_l = struct.unpack_from("<I", d, 140)[0]
        pt_m = struct.unpack_from(">I", d, 148)[0]
        pt_size = struct.unpack_from("<I", d, 132)[0]
        print(f"    pathTable size={pt_size} L={pt_l} M={pt_m}")
f.close()
