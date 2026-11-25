"""Render an 8bpp-indexed TIM2 to PNG (PS2 CLUT de-swizzle included)."""
import struct
import sys
from PIL import Image


def unswizzle_clut(clut):
    """PS2 CSM1 256-colour palette: swap the middle two 8-entry groups of every 32."""
    out = bytearray(len(clut))
    for i in range(0, 256, 32):
        for j in range(8):
            for k, src in enumerate((i + j, i + j + 8, i + j + 16, i + j + 24)):
                dstmap = (i + j, i + j + 16, i + j + 8, i + j + 24)
                d = dstmap[k]
                out[d * 4:d * 4 + 4] = clut[src * 4:src * 4 + 4]
    return bytes(out)


def load(path):
    d = open(path, "rb").read()
    assert d[:4] == b"TIM2"
    off = 0x10
    total, clut_size, image_size, hdr_size, clut_colors = struct.unpack_from("<IIIHH", d, off)
    img_type = d[off + 19]
    w, h = struct.unpack_from("<HH", d, off + 20)
    assert img_type == 5, img_type
    img = d[off + hdr_size: off + hdr_size + image_size]
    clut = d[off + hdr_size + image_size: off + hdr_size + image_size + clut_size]
    clut = unswizzle_clut(clut)
    pal = []
    alpha = []
    for i in range(256):
        r, g, b, a = clut[i * 4:i * 4 + 4]
        pal += [r, g, b]
        alpha.append(min(255, a * 2))
    im = Image.frombytes("P", (w, h), img)
    im.putpalette(pal)
    return im, alpha, w, h


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    im, alpha, w, h = load(src)
    rgb = im.convert("RGB")
    a = Image.frombytes("L", (w, h), bytes(alpha[p] for p in im.tobytes()))
    out = Image.new("RGB", (w, h), (255, 0, 255))
    out.paste(rgb, (0, 0), a)
    out.save(dst)
    print(f"{src} -> {dst} {w}x{h}")
