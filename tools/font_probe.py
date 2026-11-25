"""폰트 아틀라스에 한글을 그려 넣기 전에, 기존 글리프가 어떤 인덱스/팔레트를 쓰는지 확인한다."""
import collections
import struct
import sys

sys.path.insert(0, r"P:\AI\demonbane-ps2-kr\tools")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from tim2png import unswizzle_clut

d = open(r"P:\AI\demonbane-ps2-kr\work\font\16.tm2", "rb").read()
off = 0x10
total, clut_size, image_size, hdr_size, clut_colors = struct.unpack_from("<IIIHH", d, off)
w, h = struct.unpack_from("<HH", d, off + 20)
img = d[off + hdr_size: off + hdr_size + image_size]
clut_raw = d[off + hdr_size + image_size: off + hdr_size + image_size + clut_size]
clut = unswizzle_clut(clut_raw)

print(f"{w}x{h} image={image_size} clut={clut_size} colors={clut_colors}")
c = collections.Counter(img)
print(f"쓰이는 인덱스 {len(c)}종, 상위 12: {c.most_common(12)}")
print("\n팔레트 (쓰이는 인덱스만):")
for idx, n in sorted(c.items())[:20]:
    r, g, b, a = clut[idx * 4: idx * 4 + 4]
    print(f"  idx {idx:>3}: RGBA({r:>3},{g:>3},{b:>3},{a:>3})  {n:>7}px")

# 팔레트가 단조 램프인지 (그렇다면 안티에일리어싱 값을 그대로 인덱스로 쓰면 된다)
mono = all(clut[i * 4] == clut[i * 4 + 1] == clut[i * 4 + 2] for i in range(256))
print(f"\n무채색 램프인가: {mono}")
print("전체 팔레트 앞 16:", [tuple(clut[i * 4:i * 4 + 4]) for i in range(16)])
print("전체 팔레트 뒤 8 :", [tuple(clut[i * 4:i * 4 + 4]) for i in range(248, 256)])

# 한 글자 셀의 픽셀 값 분포
cw, ch = w // 16, h // 6
cell = [img[(y) * w + x] for y in range(ch) for x in range(cw)]
print(f"\n첫 셀({cw}x{ch}) 값 분포: {sorted(collections.Counter(cell).items())[:12]}")
