import struct
import sys

BPP = {0: "none", 1: "16bit", 2: "24bit", 3: "32bit", 4: "4bpp-idx", 5: "8bpp-idx"}

for path in sys.argv[1:]:
    d = open(path, "rb").read()
    magic, ver, fmt, pics = d[:4], d[4], d[5], struct.unpack_from("<H", d, 6)[0]
    print(f"{path}: magic={magic!r} ver={ver} fmt={fmt} pictures={pics} filesize={len(d)}")
    off = 0x10
    for i in range(pics):
        (total, clut_size, image_size, hdr_size, clut_colors) = struct.unpack_from("<IIIHH", d, off)
        pic_fmt = d[off + 16]
        mipmaps = d[off + 17]
        clut_type = d[off + 18]
        img_type = d[off + 19]
        w, h = struct.unpack_from("<HH", d, off + 20)
        print(f"  pic{i}: total={total} clut={clut_size} image={image_size} hdr={hdr_size} "
              f"colors={clut_colors} fmt={pic_fmt} mip={mipmaps} clutType=0x{clut_type:02X} "
              f"imgType={img_type}({BPP.get(img_type)}) {w}x{h}")
        print(f"        GsTex0=0x{struct.unpack_from('<Q', d, off + 24)[0]:016X} "
              f"GsTex1=0x{struct.unpack_from('<Q', d, off + 32)[0]:016X}")
        off += total
