"""수직 슬라이스 빌드 — 지정한 씬만 한국어로 바꿔 ISO 에 심는다.

    python build_test.py D0101 D0102 ...

1. 정렬표에서 그 파일의 (줄번호 -> 한국어) 를 가져와 PS2 스크립트 본문만 치환 (태그는 그대로)
2. 한글 -> 캐리어 한자 (ps2_carrier_map.json) -> cp932 -> sk_encode
3. SCRIPT.PCK / FONT.PCK 재조립. 원본 크기 이하면 0 패딩해서 **같은 LBA 에 그대로 덮어쓴다**
   (DIGPCK 의 data_base = 0x2C + 인덱스크기 라 뒤 패딩은 무해. ISO 재빌드 불필요 = 반복이 빠르다)
"""
import csv
import collections
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from digpck import parse, pack
from skcodec import decode, encode
from iso9660 import Iso

ROOT = r"P:\AI\demonbane-ps2-kr"
ISO = os.path.join(ROOT, r"build\Demonbane_KR.iso")
CARRIER = json.load(open(os.path.join(ROOT, r"work\ref\ps2_carrier_map.json"), encoding="utf-8"))
TAG = re.compile(r"(<[^>\n]*>)")
args = sys.argv[1:]
JUMP = None
if "--jump" in args:
    i = args.index("--jump")
    JUMP = args[i + 1].lower()
    del args[i:i + 2]
targets = [a.upper() for a in args] or ["D0101"]


KOTAG = re.compile(r"<[^>\n]*>")


def to_carrier(s):
    # PC판 태그(<voice ...>, <k> 등)가 한국어 칸에 섞여 있다. PS2 태그는 원본 줄에서 그대로
    # 가져오므로, 한국어에서 넘어온 태그는 전부 버려야 한다. (안 그러면 PC 형식 태그가 심긴다)
    s = KOTAG.sub("", s).strip()
    out = []
    miss = []
    for ch in s:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            c = CARRIER.get(ch)
            if c is None:
                miss.append(ch)
                c = "?"
            out.append(c)
        elif ch == "｡":
            out.append("。")
        elif ch == "､":
            out.append("、")
        else:
            out.append(ch)
    return "".join(out), miss


# --- 1. 정렬표에서 한국어 가져오기 ---------------------------------------
ko_by = collections.defaultdict(dict)
_af = os.path.join(ROOT, "work", "ref", "aligned_final.tsv")
# 판정본이 있으면 그걸 쓴다. 없으면 기계 정렬 결과.
ALIGNED = _af if os.path.exists(_af) else os.path.join(ROOT, "work", "ref", "aligned.tsv")

tsv = ALIGNED
for r in list(csv.reader(open(tsv, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:]:
    if len(r) < 6 or not r[4] or not r[2]:
        continue
    stem = os.path.splitext(r[1])[0].upper()
    cells = r[6].split(",") if len(r) >= 7 and r[6] else [f"{r[1]}:{r[2]}"]
    for n_, cell in enumerate(cells):
        fn_, no_ = cell.rsplit(":", 1)
        # 한 단위가 여러 물리 줄에 걸치면 첫 줄에 전문을 넣고 나머지는 비운다.
        # 안 그러면 나머지 줄의 일본어가 남아 캐리어 폰트에서 깨져 보인다.
        ko_by[os.path.splitext(fn_)[0].upper()][int(no_)] = r[4] if n_ == 0 else ""

# --- 2. 스크립트 치환 -----------------------------------------------------
blob, entries, base = parse(os.path.join(ROOT, r"extract\SCRIPT\SCRIPT.PCK"))
newdata = []
changed = allmiss = 0
for e in entries:
    raw = blob[base + e["offset"]: base + e["offset"] + e["size"]]
    stem = os.path.splitext(e["name"])[0].upper()
    # 팩 안의 이름은 대문자 D 로 들어있다 (`D0100.txt`). 대소문자 구분하면 조용히 안 먹는다.
    if JUMP and e["name"].lower() == "d0100.txt":
        # 프롤로그(영상 다수)를 통째로 건너뛴다. D0100 말미가 세우는 전역 플래그는 그대로 세워야
        # 목적지 씬이 타이틀로 되돌아가지 않는다 (점프 빌드 첫 시도가 여기서 실패했다).
        stub = ('<CALC WORKNAME="メニュー" OPERATOR="true" mode="global">\r\n'
                f'<A HREF="{JUMP}.txt" OPERATOR="">\r\n')
        newdata.append((e["name"], encode(stub.encode("cp932"))))
        print(f"  d0100.txt: 프롤로그 스텁 -> {JUMP}.txt ({e['size']} -> {len(newdata[-1][1])}바이트)")
        continue
    if JUMP and e["name"].lower() == "start.txt":
        # 점프 빌드: 부팅 대상을 바꿔 그 씬으로 바로 들어간다. 파일명 길이가 같아 크기 변동 0.
        newdata.append((e["name"], raw))   # start.txt 는 건드리지 않는다 (정상 흐름 유지)
        continue
    if stem not in targets or stem not in ko_by:
        newdata.append((e["name"], raw))
        continue
    txt = decode(raw).decode("cp932", "replace")
    lines = txt.split("\n")
    hit = 0
    for no, ko in ko_by[stem].items():
        if no - 1 >= len(lines):
            continue
        parts = TAG.split(lines[no - 1].rstrip("\r"))
        body = "".join(p for p in parts if not p.startswith("<"))
        if not body.strip():
            continue
        conv, miss = to_carrier(ko) if ko else ("", [])
        allmiss += len(miss)
        # 태그는 순서대로 두고 본문만 통째로 교체
        rebuilt, placed = [], False
        for p in parts:
            if p.startswith("<"):
                rebuilt.append(p)
            elif not placed and p.strip():
                rebuilt.append(("　" if body.startswith("　") else "") + conv)
                placed = True
        lines[no - 1] = "".join(rebuilt) + "\r"
        hit += 1
    # 이 스크립트의 개행 규격은 **CRLF**. split("\n") 한 줄들은 이미 끝에 \r 을 달고 있으므로
    # 그대로 "\n" 으로 다시 이어야 원본 규격이 보존된다. (\r 을 벗기면 756곳이 LF 로 바뀐다)
    out = "\n".join(lines)
    newdata.append((e["name"], encode(out.encode("cp932", "replace"))))
    changed += 1
    print(f"  {e['name']}: {hit}줄 치환, {e['size']} -> {len(newdata[-1][1])}바이트")

newpck = pack(newdata, blob)
if len(newpck) > len(blob):
    # 자리가 모자라면 `vssver.scc`(제작사가 실수로 넣은 Visual SourceSafe 잔재, 7,104B) 를 비운다.
    # 엔트리 자체는 남겨서 개수·이름은 그대로 둔다.
    newdata = [(n, b"" if n == "vssver.scc" else p) for n, p in newdata]
    newpck = pack(newdata, blob)
    print("  (자리 확보: vssver.scc 를 비움)")
print(f"\nSCRIPT.PCK {len(blob):,} -> {len(newpck):,}  (캐리어 없는 글자 {allmiss})")
assert len(newpck) <= len(blob), "원본보다 커졌다 — ISO 재빌드 필요"

# --- 3. FONT.PCK 재조립 ---------------------------------------------------
fblob, fentries, fbase = parse(os.path.join(ROOT, r"extract\FONT\FONT.PCK"))
fdir = os.path.join(ROOT, r"work\font_ko")
fdata = [(e["name"], open(os.path.join(fdir, e["name"]), "rb").read()) for e in fentries]
newfont = pack(fdata, fblob)
print(f"FONT.PCK   {len(fblob):,} -> {len(newfont):,}")
assert len(newfont) <= len(fblob)

# --- 4. ISO 제자리 패치 ---------------------------------------------------
iso = Iso(ISO)
loc = {p: (lba, ln) for p, lba, ln, fl in iso.tree() if not fl & 0x02}
with open(ISO, "r+b") as f:
    for path, payload in (("/SCRIPT/SCRIPT.PCK", newpck), ("/FONT/FONT.PCK", newfont)):
        lba, length = loc[path]
        f.seek(lba * 2048)
        f.write(payload + b"\0" * (length - len(payload)))
        print(f"  {path} @ LBA {lba} 에 {len(payload):,}바이트 기록 (패딩 {length - len(payload)})")
print(f"\n완료 -> {ISO}")
