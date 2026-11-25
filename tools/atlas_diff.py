"""원본 vs 리페인트 아틀라스를 칸 단위로 비교해 '어디에 그려졌는지'를 실측한다."""
import struct
import sys

sys.path.insert(0, r"P:\AI\demonbane-ps2-kr\tools")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PAGE = sys.argv[1] if len(sys.argv) > 1 else "16"
W, H, CW, CH, COLS = 512, 204, 32, 34, 16


def cells(path):
    d = open(path, "rb").read()
    off = 0x10
    total, clut_size, image_size, hdr_size, clut_colors = struct.unpack_from("<IIIHH", d, off)
    img = d[off + hdr_size: off + hdr_size + image_size]
    out = []
    for i in range(96):
        cx, cy = i % COLS * CW, i // COLS * CH
        out.append(b"".join(img[(cy + y) * W + cx: (cy + y) * W + cx + CW] for y in range(CH)))
    return out


a = cells(rf"P:\AI\demonbane-ps2-kr\work\font\{PAGE}.tm2")
b = cells(rf"P:\AI\demonbane-ps2-kr\work\font_ko\{PAGE}.tm2")
changed = [i for i in range(96) if a[i] != b[i]]
print(f"page {PAGE}: 96칸 중 {len(changed)}칸 변경")
print("변경된 그리드 인덱스(0기준):", changed[:24])
print("→ JIS 점(1기준)으로 환산   :", [i + 1 for i in changed[:24]])

# 이 페이지에서 캐리어로 배정된 문자들의 목표 점
import json
CAR = json.load(open(r"P:\AI\demonbane-ps2-kr\work\ref\ps2_carrier_map.json", encoding="utf-8"))


def sjis_to_jis(lead, trail):
    r = (lead - 0x81) * 2 if lead <= 0x9F else (lead - 0xC1) * 2
    if trail >= 0x9F:
        return r + 2, trail - 0x9E
    return r + 1, (trail - 0x3F if trail < 0x7F else trail - 0x40)


want = []
for h, k in CAR.items():
    bs = k.encode("cp932")
    row, cell = sjis_to_jis(bs[0], bs[1])
    if row == int(PAGE):
        want.append((cell, h, k))
want.sort()
print(f"\n이 페이지 목표 {len(want)}칸")
print("목표 JIS 점:", [c for c, _, _ in want][:24])
print("목표 (점, 한글, 캐리어):", [(c, h, k) for c, h, k in want[:10]])
