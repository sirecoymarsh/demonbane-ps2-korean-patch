"""한글 캐리어를 어디에 배정할지 정한다.

핵심 판단: inside.txt 를 **늘리지 않는다**. 게임이 쓰는 2,783자 중 한자 자리를 한글로 갈아끼우면
글리프 캐시(g_dbFontInfo) 용량도, 목록 길이도 그대로라 엔진을 건드릴 이유가 없다.
(늘리려면 dbInitFontSystem 의 캐시 정원을 먼저 확인해야 하는데, 그럴 필요가 없다면 안 하는 게 낫다.)
"""
import collections
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skcodec import decode

INSIDE = r"P:\AI\demonbane-ps2-kr\work\font\inside.txt"
KO = r"P:\AI\demonbane-ps2-kr\work\patch\ko"
PS2 = r"P:\AI\demonbane-ps2-kr\work\script"

glyphs = open(INSIDE, "rb").read().decode("cp932")
print(f"inside.txt: {len(glyphs)}자")


def cls(c):
    o = ord(c)
    if 0x4E00 <= o <= 0x9FFF:
        return "한자"
    if 0x3040 <= o <= 0x309F:
        return "히라가나"
    if 0x30A0 <= o <= 0x30FF:
        return "가타카나"
    if 0xFF01 <= o <= 0xFF5E or 0xFF61 <= o <= 0xFF9F:
        return "전각영숫자/반각"
    if 0x0391 <= o <= 0x03C9 or 0x0401 <= o <= 0x044F:
        return "그리스/키릴"
    return "기호·기타"


c = collections.Counter(cls(x) for x in glyphs)
for k, v in c.most_common():
    print(f"  {k:<16} {v:>5}")

kanji = [x for x in glyphs if cls(x) == "한자"]
print(f"\n→ 한자 슬롯 {len(kanji)}개를 한글로 전용 가능")

# 한국어에 실제로 필요한 음절 수 (기존 번역 기준 = 재번역해도 비슷한 규모)
used = collections.Counter()
for fn in os.listdir(KO):
    for ln in open(os.path.join(KO, fn), encoding="utf-8"):
        used.update(ch for ch in ln if 0xAC00 <= ord(ch) <= 0xD7A3)
print(f"기존 번역이 쓴 한글 음절: {len(used)}종 (총 {sum(used.values()):,}자)")

need = len(used)
print(f"\n판정: 한자 슬롯 {len(kanji)} vs 필요 음절 {need}  →  "
      f"{'여유 ' + str(len(kanji) - need) + '칸' if len(kanji) >= need else '부족 ' + str(need - len(kanji)) + '칸'}")

# 그래도 남겨야 할 한자 (UI·시스템 문자열이 쓰는 것)
elf = open(r"P:\AI\demonbane-ps2-kr\extract\SLPM_654.91", "rb").read()
keep = set()
dbl = re.compile(rb"(?:[\x81-\x9F\xE0-\xEF][\x40-\x7E\x80-\xFC])+")
for m in dbl.finditer(elf):
    try:
        s = m.group().decode("cp932")
    except UnicodeDecodeError:
        continue
    keep.update(ch for ch in s if cls(ch) == "한자")
print(f"ELF UI 문자열이 쓰는 한자: {len(keep)}종 (이건 UI 를 번역하면 대부분 불필요)")

# 미사용 JIS 칸 (참고: 늘려야 할 때의 여유)
free = 79 * 94 - len(glyphs)
print(f"\n참고: 아틀라스 전체 {79 * 94}칸 중 게임이 안 쓰는 칸 {free}개 "
      f"(inside.txt 를 늘릴 경우의 여유)")

# 자주 쓰는 음절부터 낮은 SJIS 캐리어에 (디버깅 편의)
print("\n가장 많이 쓰이는 음절 20:", " ".join(ch for ch, _ in used.most_common(20)))
