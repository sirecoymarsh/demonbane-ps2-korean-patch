"""캐리어 글꼴 다시 그리기(11-01) — 한글을 **자기 캐리어 한자의 칸**에 그린다.

8월 tools/repaint_font.py 의 오차 두 개:
  1) 칸 위치를 (점-1) 로 셈. 실제 쪽 그림은 0번 칸이 비어 있고 칸 번호 = JIS 점(69쪽 전부 확인).
     엔진(dbInitFontSystem)도 쪽 시작 코드를 하나 앞(…3F/…9E)에서 잡아 칸 = 점 으로 읽는다.
  2) 그 오차를 화면에서 「다음 글자가 나온다」로 보고, 그림을 inside.txt 의 다음 한자 칸에 그림(GLYPH_SHIFT=1).
  두 오차는 다음 한자가 JIS 바로 옆일 때만 상쇄돼서, 사이에 안 쓰는 한자가 끼면 한글이 엉뚱한 칸에 그려지고
  캐리어 칸엔 한자가 그대로 남았다(2,361음절 중 732음절, 예: 젠→任). 화면 증거: 사용자 캡처 「任장……어디냐!?」.

캐리어 표(work/ref/ps2_carrier_map.json)는 그대로 쓴다 — 대본은 안 바뀌고 FONT.PCK 만 바뀐다.
그리는 방식(맑은 고딕 24px, 칸 가운데, 알파→팔레트 근사)은 8월 도구와 같다.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFont
from tim2png import unswizzle_clut

FONT_DIR = os.path.join(ROOT, r"work\font")
OUT_DIR = os.path.join(ROOT, r"work\font_ko_v3")
MAP = os.path.join(ROOT, r"work\ref\ps2_carrier_map.json")
TTF = r"C:\Windows\Fonts\malgun.ttf"
CELL_W, CELL_H, COLS, SIZE = 32, 34, 16, 24


def kuten(ch):
    b = ch.encode("cp932")
    lead, trail = b[0], b[1]
    r = (lead - 0x81) * 2 if lead <= 0x9F else (lead - 0xC1) * 2
    if trail >= 0x9F:
        return r + 2, trail - 0x9E
    return r + 1, (trail - 0x3F if trail < 0x7F else trail - 0x40)


mapping = json.load(open(MAP, encoding="utf-8"))          # 한글 -> 캐리어 한자
todo = {}
for h, k in mapping.items():
    ku, ten = kuten(k)
    todo.setdefault(ku, []).append((ten, h))

os.makedirs(OUT_DIR, exist_ok=True)
fnt = ImageFont.truetype(TTF, SIZE)
painted = 0
for name in sorted(os.listdir(FONT_DIR)):
    d = bytearray(open(os.path.join(FONT_DIR, name), "rb").read())
    ku = int(name[:-4]) if name.endswith(".tm2") and name[:-4].isdigit() else None
    if ku in todo:
        off = 0x10
        total, clut_size, image_size, hdr_size, clut_colors = struct.unpack_from("<IIIHH", d, off)
        w, h = struct.unpack_from("<HH", d, off + 20)
        img_off = off + hdr_size
        clut = unswizzle_clut(bytes(d[img_off + image_size: img_off + image_size + clut_size]))
        alpha_of = [clut[i * 4 + 3] for i in range(256)]
        lut = [min(range(256), key=lambda i: abs(alpha_of[i] - a)) for a in range(256)]
        for ten, ch in todo[ku]:
            assert 1 <= ten <= 94
            cx = ten % COLS * CELL_W                      # 칸 = 점 (0번 칸은 비어 있다)
            cy = ten // COLS * CELL_H
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
    open(os.path.join(OUT_DIR, name), "wb").write(d)
print(f"한글 {painted}자를 자기 캐리어 칸에 그림 -> {OUT_DIR}")
