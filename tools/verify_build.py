"""빌드된 ISO 를 다시 읽어 실제로 뭐가 들어갔는지 확인한다 (원본과 태그·개행 대조)."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from iso9660 import Iso
from digpck import parse
from skcodec import decode

ROOT = r"P:\AI\demonbane-ps2-kr"
scene = (sys.argv[1] if len(sys.argv) > 1 else "D0101") + ".txt"
CARRIER = json.load(open(os.path.join(ROOT, r"work\ref\ps2_carrier_map.json"), encoding="utf-8"))
REV = {v: k for k, v in CARRIER.items()}

iso = Iso(os.path.join(ROOT, r"build\Demonbane_KR.iso"))
lba, ln = next((l, s) for p, l, s, f in iso.tree() if p == "/SCRIPT/SCRIPT.PCK")
tmp = os.path.join(ROOT, r"build\_check.pck")
iso.extract(lba, ln, tmp)

new_blob, new_e, new_base = parse(tmp)
old_blob, old_e, old_base = parse(os.path.join(ROOT, r"extract\SCRIPT\SCRIPT.PCK"))
print(f"엔트리 수 원본 {len(old_e)} / 빌드 {len(new_e)}  "
      f"이름 순서 동일: {[x['name'] for x in old_e] == [x['name'] for x in new_e]}")


def get(blob, ents, base, name):
    e = next(x for x in ents if x["name"] == name)
    return decode(blob[base + e["offset"]: base + e["offset"] + e["size"]])


o = get(old_blob, old_e, old_base, scene)
n = get(new_blob, new_e, new_base, scene)
print(f"\n{scene}: 원본 {len(o):,}B / 빌드 {len(n):,}B")
CR, LF, CRLF = b"\r", b"\n", b"\r\n"
for label, b in (("원본", o), ("빌드", n)):
    crlf = b.count(CRLF)
    print(f"  {label}: CRLF {crlf}  bare CR {b.count(CR) - crlf}  "
          f"bare LF {b.count(LF) - crlf}  줄 {crlf + 1}")

ot = o.decode("cp932", "replace")
nt = n.decode("cp932", "replace")
TAG = re.compile(r"<[^>\n]*>")
ta, tb = TAG.findall(ot), TAG.findall(nt)
print(f"\n태그 개수 원본 {len(ta)} / 빌드 {len(tb)}   완전 동일: {ta == tb}")
if ta != tb:
    for i, (a, b) in enumerate(zip(ta, tb)):
        if a != b:
            print(f"  첫 불일치 #{i}: {a!r} -> {b!r}")
            break

print("\n--- 빌드된 본문을 캐리어 역변환해서 읽기 ---")
shown = 0
for line in nt.split("\n"):
    body = TAG.sub("", line).strip()
    if not body:
        continue
    ko = "".join(REV.get(c, c) for c in body)
    print("   ", ko[:90])
    shown += 1
    if shown >= 10:
        break
os.remove(tmp)
