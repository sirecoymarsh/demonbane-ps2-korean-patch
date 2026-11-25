"""전량 이식했을 때 실제로 들어가는지 재는 계측 도구 (ISO 를 만들지는 않는다).

묻는 것 4가지
  1) SCRIPT.PCK 가 원본 6,590,711B 안에 들어가는가 (아니면 ISO 재빌드 필요)
  2) 파일당 스크립트 버퍼 81,920B 를 넘는 파일이 있는가
  3) KS X 1001 밖이라 캐리어가 없는 음절이 있는가
  4) 버려지는 PC 태그(<RUBY> 등)가 얼마나 되는가

주의: 정렬 결과를 그대로 밀어넣는 계측이다. 의미 검수 전이라 **릴리스 후보가 아니다.**
"""
import collections
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from digpck import parse, pack
from skcodec import decode, encode

ROOT = r"P:\AI\demonbane-ps2-kr"
LIMIT = 81920
CARRIER = json.load(open(os.path.join(ROOT, r"work\ref\ps2_carrier_map.json"), encoding="utf-8"))
TAG = re.compile(r"(<[^>\n]*>)")
KOTAG = re.compile(r"<[^>\n]*>")

miss_ch = collections.Counter()
dropped_tags = collections.Counter()


def to_carrier(s):
    for m in KOTAG.finditer(s):
        dropped_tags[m.group()[:24]] += 1
    s = KOTAG.sub("", s).strip()
    out = []
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3:
            c = CARRIER.get(ch)
            if c is None:
                miss_ch[ch] += 1
                c = "?"
            out.append(c)
        elif ch == "\uff61":      # ｡
            out.append("。")
        elif ch == "\uff64":      # ､
            out.append("、")
        else:
            out.append(ch)
    return "".join(out)


ko_by = collections.defaultdict(dict)
for r in list(csv.reader(open(os.path.join(ROOT, r"work\ref\aligned.tsv"), encoding="utf-8"),
                         delimiter="\t", quoting=csv.QUOTE_NONE))[1:]:
    if len(r) < 6 or not r[4] or not r[2]:
        continue
    ko_by[os.path.splitext(r[1])[0].upper()][int(r[2])] = r[4]

blob, entries, base = parse(os.path.join(ROOT, r"extract\SCRIPT\SCRIPT.PCK"))
newdata = []
sizes = []
changed = 0
for e in entries:
    raw = blob[base + e["offset"]: base + e["offset"] + e["size"]]
    stem = os.path.splitext(e["name"])[0].upper()
    if stem not in ko_by:
        newdata.append((e["name"], raw))
        sizes.append((e["name"], e["size"], e["size"]))
        continue
    txt = decode(raw).decode("cp932", "replace")
    lines = txt.split("\n")
    for no, ko in ko_by[stem].items():
        if no - 1 >= len(lines):
            continue
        parts = TAG.split(lines[no - 1].rstrip("\r"))
        body = "".join(p for p in parts if not p.startswith("<"))
        if not body.strip():
            continue
        conv = to_carrier(ko)
        rebuilt, placed = [], False
        for p in parts:
            if p.startswith("<"):
                rebuilt.append(p)
            elif not placed and p.strip():
                rebuilt.append(("\u3000" if body.startswith("\u3000") else "") + conv)
                placed = True
        lines[no - 1] = "".join(rebuilt) + "\r"
    out = encode("\n".join(lines).encode("cp932", "replace"))
    newdata.append((e["name"], out))
    sizes.append((e["name"], e["size"], len(out)))
    changed += 1

newpck = pack(newdata, blob)
orig = len(blob)
print(f"한국어 적용 파일 {changed}개 / 전체 {len(entries)}개\n")
print(f"[1] SCRIPT.PCK  {orig:,} -> {len(newpck):,}  ({len(newpck) - orig:+,}B, {len(newpck) / orig - 1:+.1%})")
print(f"    {'원본 안에 들어감 - ISO 재빌드 불필요' if len(newpck) <= orig else 'ISO 재빌드 필요'}")

over = [(n, a, b) for n, a, b in sizes if b > LIMIT]
tight = sorted([(n, a, b) for n, a, b in sizes if b > LIMIT * 0.9], key=lambda x: -x[2])
print(f"\n[2] 파일당 상한 {LIMIT:,}B 초과: {len(over)}개")
for n, a, b in sorted(over, key=lambda x: -x[2]):
    print(f"      {n:<16} {a:,} -> {b:,}  (초과 {b - LIMIT:,})")
print(f"    90% 이상 차지: {len(tight)}개")
for n, a, b in tight[:6]:
    print(f"      {n:<16} {a:,} -> {b:,}  (여유 {LIMIT - b:,})")

print(f"\n[3] 캐리어 없는 음절: {len(miss_ch)}종 / {sum(miss_ch.values()):,}회")
if miss_ch:
    print("      " + " ".join(f"{c}({n})" for c, n in miss_ch.most_common(30)))

print(f"\n[4] 버려진 PC 태그: {sum(dropped_tags.values()):,}개")
for k, v in dropped_tags.most_common(8):
    print(f"      {k!r:<28} {v}")
