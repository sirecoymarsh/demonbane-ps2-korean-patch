"""한국어 패치(.nss)의 표시 텍스트를 캐리어 해제해서 진짜 한글로 뽑는다."""
import json
import os
import re
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NSS = r"P:\AI\demonbane-ps2-kr\work\patch\nss"
MAP = r"P:\AI\demonbane-ps2-kr\work\patch\carrier_map.json"
OUT = r"P:\AI\demonbane-ps2-kr\work\patch\ko"
os.makedirs(OUT, exist_ok=True)

cmap = {chr(int(k, 16)): chr(int(v, 16)) for k, v in json.load(open(MAP, encoding="utf-8")).items()}
PRE = re.compile(r"<PRE\b[^>]*>(.*?)</PRE>", re.S | re.I)


def unwrap(s):
    return "".join(cmap.get(c, c) for c in s)


files = sorted(os.listdir(NSS))
tot_lines = tot_chars = 0
hangul = other_cjk = 0
leftover = collections.Counter()
per_file = []
for fn in files:
    txt = open(os.path.join(NSS, fn), "rb").read().decode("cp932", "replace")
    blocks = PRE.findall(txt)
    lines = []
    for b in blocks:
        for ln in b.split("\n"):
            s = ln.strip()
            if not s or s.startswith(("[", "{", "//", "<")):
                continue
            lines.append(unwrap(s))
    per_file.append((fn, len(lines), sum(len(x) for x in lines)))
    tot_lines += len(lines)
    for ln in lines:
        tot_chars += len(ln)
        for c in ln:
            o = ord(c)
            if 0xAC00 <= o <= 0xD7A3:
                hangul += 1
            elif 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF:
                other_cjk += 1
                leftover[c] += 1
    if lines:
        with open(os.path.join(OUT, fn + ".txt"), "w", encoding="utf-8") as g:
            g.write("\n".join(lines))

print(f"패치 스크립트 {len(files)}개 / 텍스트가 있는 파일 {sum(1 for _, n, _ in per_file if n)}개")
print(f"표시 줄 {tot_lines:,}  문자 {tot_chars:,}")
print(f"  한글 {hangul:,} ({hangul / max(tot_chars, 1):.1%})")
print(f"  일본어(가나·한자) 잔존 {other_cjk:,} ({other_cjk / max(tot_chars, 1):.1%})")
print("잔존 상위:", " ".join(f"{c}({n})" for c, n in leftover.most_common(25)))

empty = [fn for fn, n, _ in per_file if n == 0]
print(f"\n표시 텍스트가 하나도 없는 스크립트: {len(empty)}")
print("  " + ", ".join(empty[:25]))
