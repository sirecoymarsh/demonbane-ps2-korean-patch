"""캐리어 문자열을 동봉 폰트로 렌더해서 실제로 무슨 한글인지 눈으로 확인한다."""
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = r"P:\AI\demonbane-ps2-kr\work\patch\MShangang.ttf"
text = sys.argv[1] if len(sys.argv) > 1 else ""
out = sys.argv[2] if len(sys.argv) > 2 else r"P:\AI\demonbane-ps2-kr\work\patch\render.png"

if not text:
    import re
    raw = open(r"P:\AI\demonbane-ps2-kr\work\patch\nss\d0101.nss", "rb").read().decode("cp932", "replace")
    blocks = re.findall(r"<PRE @box00>(.*?)</PRE>", raw, re.S)
    lines = [ln.strip() for b in blocks for ln in b.split("\n")
             if ln.strip() and not ln.strip().startswith(("[", "{", "//"))]
    text = "\n".join(lines[:6])

fnt = ImageFont.truetype(FONT, 34)
rows = text.split("\n")
img = Image.new("RGB", (1500, 46 * len(rows) + 24), (24, 24, 28))
d = ImageDraw.Draw(img)
for i, r in enumerate(rows):
    d.text((14, 12 + i * 46), r, font=fnt, fill=(235, 235, 235))
img.save(out)
print(out, f"({len(rows)} lines)")
