"""빌드된 전량 ISO 를 처음부터 다시 읽어 구조와 내용을 확인한다."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from iso9660 import Iso
from digpck import parse
from skcodec import decode

ISO = sys.argv[1]
CAR = json.load(open(r"P:\AI\demonbane-ps2-kr\work\ref\ps2_carrier_map.json", encoding="utf-8"))
REV = {v: k for k, v in CAR.items()}
TAG = re.compile(r"<[^>\n]*>")

iso = Iso(ISO)
tree = iso.tree()
files = [(p, l, s) for p, l, s, f in tree if not f & 0x02]
print(f"[구조] 디렉터리·파일 {len(tree)}개 정상 순회, 파일 {len(files)}개")
end = max(l + (s + 2047) // 2048 for _, l, s in files)
print(f"[레이아웃] 마지막 데이터 끝 LBA={end}  파일크기={os.path.getsize(ISO):,}B  "
      f"DVD5 여유={(4700372992 - os.path.getsize(ISO)) / 1024 / 1024:.0f}MB")

lba, ln = next((l, s) for p, l, s in files if p == "/SCRIPT/SCRIPT.PCK")
tmp = ISO + ".chk"
iso.extract(lba, ln, tmp)
blob, entries, base = parse(tmp)
print(f"[SCRIPT.PCK] lba={lba} size={ln:,}  엔트리 {len(entries)}개  "
      f"data_base=0x{base:X}  끝={base + entries[-1]['offset'] + entries[-1]['size']:,}")

ok = bad = 0
for e in entries:
    d = blob[base + e["offset"]: base + e["offset"] + e["size"]]
    if len(d) == e["size"]:
        ok += 1
    else:
        bad += 1
print(f"[엔트리] 크기 일치 {ok} / 불일치 {bad}")

for name in ("D0101.txt", "D1105le.txt", "d0100.txt"):
    e = next((x for x in entries if x["name"].lower() == name.lower()), None)
    if not e:
        continue
    t = decode(blob[base + e["offset"]: base + e["offset"] + e["size"]]).decode("cp932", "replace")
    body = [TAG.sub("", l).strip() for l in t.split("\n")]
    body = [b for b in body if b and not b.startswith("//")]
    print(f"\n--- {name} ({e['size']:,}B) ---")
    for l in body[:3]:
        print("   ", "".join(REV.get(c, c) for c in l)[:96])
os.remove(tmp)
