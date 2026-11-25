"""PS2 폰트 아틀라스의 '한자 칸'을 한글로 다시 그린다.

설계 판단
  - inside.txt 를 **늘리지 않는다**. 게임이 쓰는 2,783자 중 한자 2,503칸을 한글로 전용한다.
    목록 길이도 글리프 캐시 용량도 그대로라 엔진을 손댈 이유가 없다.
  - 배정 = KS X 1001 완성형 2,350자를 유니코드 순으로, 한자 캐리어를 SJIS 순으로 짝지음.
    결정적(deterministic)이라 언제 다시 만들어도 같은 표가 나온다.

아틀라스 좌표
  SJIS 2바이트 -> JIS 구/점 -> 페이지 `<구:02d>.tm2` 의 (점-1) 번째 칸, 16열 x 6행, 칸 32x34
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont
from tim2png import unswizzle_clut

FONT_DIR = r"P:\AI\demonbane-ps2-kr\work\font"
OUT_DIR = r"P:\AI\demonbane-ps2-kr\work\font_ko"
TTF = os.environ.get("KO_TTF", r"C:\Windows\Fonts\malgun.ttf")
MAP_OUT = r"P:\AI\demonbane-ps2-kr\work\ref\ps2_carrier_map.json"
CELL_W, CELL_H = 32, 34
COLS, ROWS = 16, 6
SIZE = int(os.environ.get("GLYPH_PX", 24))


def sjis_to_jis(lead, trail):
    r = (lead - 0x81) * 2 if lead <= 0x9F else (lead - 0xC1) * 2
    if trail >= 0x9F:
        return r + 2, trail - 0x9E
    return r + 1, (trail - 0x3F if trail < 0x7F else trail - 0x40)


# --- 1. 캐리어 배정 -------------------------------------------------------
glyphs = open(os.path.join(FONT_DIR, "inside.txt"), "rb").read().decode("cp932")
kanji = [c for c in glyphs if 0x4E00 <= ord(c) <= 0x9FFF]          # inside.txt 순 = SJIS 순
KS = []                                                             # KS X 1001 완성형 2,350자
for c in (chr(x) for x in range(0xAC00, 0xD7A4)):
    try:
        b = c.encode("cp949")
    except UnicodeEncodeError:
        continue
    if len(b) == 2 and 0xB0 <= b[0] <= 0xC8 and 0xA1 <= b[1] <= 0xFE:
        KS.append(c)
# KS X 1001 밖이지만 번역문이 실제로 쓰는 음절 (capacity_probe 로 실측). 남는 한자 슬롯에 얹는다.
EXTRA = [c for c in "큿쯉퓩츗얬햣늗겍웟쁽쥭" if c not in KS]   # 09-05 판정본 실측으로 6자 추가
KS = KS + EXTRA
print(f"한자 캐리어 {len(kanji)}칸 / 한글 {len(KS)}자 (KS X 1001 {len(KS) - len(EXTRA)} + 추가 {len(EXTRA)}: {''.join(EXTRA)})")
assert len(KS) <= len(kanji), "칸이 모자란다"

# ★ 실측 보정: 엔진은 코드포인트 C 를 만나면 inside.txt 에서 **C 의 다음 항목** 글리프를 그린다.
#   (화면 실측 — 캐리어 断#1633 을 넣었더니 暖#1634 자리의 그림이 나왔다. 5개 이상에서 일관)
#   따라서 한글 H 의 캐리어는 kanji[i] 로 두되, 그림은 kanji[i+SHIFT] 자리에 그린다.
SHIFT = int(os.environ.get("GLYPH_SHIFT", 1))

mapping = {}                                                        # 한글 -> 캐리어 한자 (스크립트에 넣을 것)
paint_at = {}                                                       # 한글 -> 그림을 그릴 한자 칸
for i, h in enumerate(KS):
    mapping[h] = kanji[i]
    paint_at[h] = kanji[i + SHIFT]

os.makedirs(os.path.dirname(MAP_OUT), exist_ok=True)
json.dump({h: k for h, k in mapping.items()}, open(MAP_OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
print(f"배정표 -> {MAP_OUT}")

# --- 2. 페이지별로 다시 그리기 --------------------------------------------
todo = {}
for h, k in paint_at.items():
    b = k.encode("cp932")
    row, cell = sjis_to_jis(b[0], b[1])
    todo.setdefault(row, []).append((cell, h))

os.makedirs(OUT_DIR, exist_ok=True)
fnt = ImageFont.truetype(TTF, SIZE)
painted = 0
for name in sorted(os.listdir(FONT_DIR)):
    src = os.path.join(FONT_DIR, name)
    dst = os.path.join(OUT_DIR, name)
    d = bytearray(open(src, "rb").read())
    if not name.endswith(".tm2"):
        open(dst, "wb").write(d)
        continue
    row = int(name[:-4]) if name[:-4].isdigit() else None
    if row not in todo:
        open(dst, "wb").write(d)
        continue

    off = 0x10
    total, clut_size, image_size, hdr_size, clut_colors = struct.unpack_from("<IIIHH", d, off)
    w, h = struct.unpack_from("<HH", d, off + 20)
    img_off = off + hdr_size
    clut = unswizzle_clut(bytes(d[img_off + image_size: img_off + image_size + clut_size]))
    # 알파 -> 팔레트 인덱스 (무채색 램프이므로 알파만 보면 된다)
    alpha_of = [clut[i * 4 + 3] for i in range(256)]
    lut = [min(range(256), key=lambda i: abs(alpha_of[i] - a)) for a in range(256)]

    for cell, ch in todo[row]:
        cx = (cell - 1) % COLS * CELL_W
        cy = (cell - 1) // COLS * CELL_H
        tile = Image.new("L", (CELL_W, CELL_H), 0)
        dr = ImageDraw.Draw(tile)
        bb = dr.textbbox((0, 0), ch, font=fnt)
        dr.text(((CELL_W - (bb[2] - bb[0])) // 2 - bb[0],
                 (CELL_H - (bb[3] - bb[1])) // 2 - bb[1]), ch, font=fnt, fill=255)
        px = tile.load()
        for y in range(CELL_H):
            base = img_off + (cy + y) * w + cx
            for x in range(CELL_W):
                d[base + x] = lut[px[x, y]]
        painted += 1
    open(dst, "wb").write(d)

print(f"한글 {painted}자를 아틀라스에 그림 -> {OUT_DIR}")

