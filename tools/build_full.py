"""전량 빌드 — 정렬표의 한국어를 모든 스크립트에 적용하고 ISO 에 심는다.

    python build_full.py <iso> [--jump d0101]

SCRIPT.PCK 는 6.5% 커져 원래 익스텐트에 안 들어가므로 iso_patch 가 디스크 끝으로 이전한다.
FONT.PCK 는 크기가 같아 제자리.

주의: 의미 검수 전 정렬 결과를 그대로 밀어넣는다. **줄바꿈·박스 넘침 판정용이지 릴리스가 아니다.**
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
from iso_patch import IsoPatcher

ROOT = r"P:\AI\demonbane-ps2-kr"
LIMIT = 81920
TAG = re.compile(r"(<[^>\n]*>)")
KOTAG = re.compile(r"<[^>\n]*>")
RUBY = re.compile(r'<RUBY\s+text="([^"]*)"\s*>(.*?)</RUBY\s*>', re.I | re.S)

args = sys.argv[1:]
JUMP = None
if "--jump" in args:
    i = args.index("--jump")
    JUMP = args[i + 1].lower()
    del args[i:i + 2]
ISO = args[0]

CARRIER = json.load(open(os.path.join(ROOT, r"work\ref\ps2_carrier_map.json"), encoding="utf-8"))
miss = collections.Counter()


def to_carrier(s):
    # PC 루비 -> PS2 루비. PS2 는 <r text="..."> 를 2,402회 쓰고 있어 형식이 이미 존재한다.
    s = RUBY.sub(lambda m: f'<r text="{m.group(1)}">{m.group(2)}</r>', s)
    s = s.replace("<br>", "").replace("<BR>", "")
    parts = TAG.split(s)
    out = []
    for p in parts:
        if p.startswith("<"):
            out.append(p if p.lower().startswith(("<r ", "</r")) else "")
            continue
        buf = []
        for ch in p:
            o = ord(ch)
            if 0xAC00 <= o <= 0xD7A3:
                c = CARRIER.get(ch)
                if c is None:
                    miss[ch] += 1
                    c = "?"
                buf.append(c)
            elif ch == "\uff61":
                buf.append("。")
            elif ch == "\uff64":
                buf.append("、")
            else:
                buf.append(ch)
        out.append("".join(buf))
    return "".join(out).strip()


ko_by = collections.defaultdict(dict)
_af = os.path.join(ROOT, "work", "ref", "aligned_final.tsv")
# 판정본이 있으면 그걸 쓴다. 없으면 기계 정렬 결과.
ALIGNED = _af if os.path.exists(_af) else os.path.join(ROOT, "work", "ref", "aligned.tsv")

for r in list(csv.reader(open(ALIGNED, encoding="utf-8"),
                         delimiter="\t", quoting=csv.QUOTE_NONE))[1:]:
    if len(r) < 6 or not r[4] or not r[2]:
        continue
    ko_by[os.path.splitext(r[1])[0].upper()][int(r[2])] = r[4]

blob, entries, base = parse(os.path.join(ROOT, r"extract\SCRIPT\SCRIPT.PCK"))
newdata = []
changed = lines_done = 0
over = []
for e in entries:
    raw = blob[base + e["offset"]: base + e["offset"] + e["size"]]
    name = e["name"]
    stem = os.path.splitext(name)[0].upper()
    if JUMP and name.lower() == "d0100.txt":
        stub = ('<CALC WORKNAME="メニュー" OPERATOR="true" mode="global">\r\n'
                f'<A HREF="{JUMP}.txt" OPERATOR="">\r\n')
        newdata.append((name, encode(stub.encode("cp932"))))
        continue
    if stem not in ko_by:
        newdata.append((name, raw))
        continue
    lines = decode(raw).decode("cp932", "replace").split("\n")
    for no, ko in ko_by[stem].items():
        if no - 1 >= len(lines):
            continue
        raw_line = lines[no - 1].rstrip("\r")
        parts = TAG.split(raw_line)
        body = "".join(p for p in parts if not p.startswith("<"))
        if not body.strip():
            continue
        if not re.search(r"[぀-ヿ㐀-鿿０-ｚ]", body):
            continue            # 태그 잔여물(예: 깨진 BACKGROUND 줄의 ")//")은 건드리지 않는다
        # 원문 루비 <R TEXT="ほこり">埃</R> 를 남기면 한국어 전문이 루비 밑말이 되어
        # 일본어 읽기가 위에 얹힌다(2,400줄). 원문 R 태그는 버리고 텍스트 조각을 다시 잇는다.
        parts = [p for p in parts if not p.lower().startswith(("<r ", "</r"))]
        merged = []
        for p in parts:
            if merged and not p.startswith("<") and not merged[-1].startswith("<"):
                merged[-1] += p
            else:
                merged.append(p)
        parts = merged
        texts = [i for i, p in enumerate(parts) if not p.startswith("<") and p.strip()]
        kos = ko if isinstance(ko, list) else [ko]
        if len(kos) == len(texts):
            fill = [to_carrier(k) for k in kos]            # <K> 로 갈린 조각마다 제 단위의 한국어
        else:
            fill = [to_carrier(" ".join(kos))] + [""] * (len(texts) - 1)
        rebuilt = list(parts)
        for n, idx in enumerate(texts):
            rebuilt[idx] = ("　" if n == 0 and body.startswith("　") else "") + fill[n]
        lines[no - 1] = "".join(rebuilt) + "\r"
        lines_done += 1
    out = encode("\n".join(lines).encode("cp932", "replace"))
    if len(out) > LIMIT:
        over.append((name, len(out)))
    newdata.append((name, out))
    changed += 1

newpck = pack(newdata, blob)
print(f"한국어 적용: {changed}파일 / {lines_done:,}줄")
print(f"캐리어 없는 음절: {len(miss)}종 {sum(miss.values())}회  " +
      (" ".join(f"{c}({n})" for c, n in miss.most_common(8)) if miss else ""))
if over:
    print(f"!! 파일당 상한 초과 {len(over)}개: {over}")

fblob, fentries, fbase = parse(os.path.join(ROOT, r"extract\FONT\FONT.PCK"))
fdir = os.path.join(ROOT, r"work\font_ko")
newfont = pack([(e["name"], open(os.path.join(fdir, e["name"]), "rb").read()) for e in fentries], fblob)

p = IsoPatcher(ISO)
for path, payload in (("/SCRIPT/SCRIPT.PCK", newpck), ("/FONT/FONT.PCK", newfont)):
    how, lba, size, pad = p.replace(path, payload)
    print(f"  {path:<20} {how}  lba={lba} size={size:,} pad={pad}")
print(f"volumeSpace -> {p.vol_sectors} sectors ({p.vol_sectors * 2048:,}B)")
p.close()
print(f"\n완료 -> {ISO}  ({os.path.getsize(ISO):,}B)")
