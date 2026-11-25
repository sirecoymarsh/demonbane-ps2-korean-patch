"""빌드된 ISO 안의 스크립트를 꺼내 실제 내용을 확인한다."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from iso9660 import Iso
from digpck import parse
from skcodec import decode

ISO = r"P:\AI\demonbane-ps2-kr\build\Demonbane_KR.iso"
names = sys.argv[1:] or ["d0100.txt", "start.txt", "D0101.txt"]

iso = Iso(ISO)
lba, ln = next((l, s) for p, l, s, f in iso.tree() if p == "/SCRIPT/SCRIPT.PCK")
tmp = r"P:\AI\demonbane-ps2-kr\build\_c.pck"
iso.extract(lba, ln, tmp)
blob, entries, base = parse(tmp)

for name in names:
    x = next((y for y in entries if y["name"].lower() == name.lower()), None)
    if not x:
        print(f"{name}: NOT FOUND")
        continue
    d = decode(blob[base + x["offset"]: base + x["offset"] + x["size"]]).decode("cp932", "replace")
    size = x["size"]
    print(f"--- {name} ({size}B) ---")
    print(d[:260].replace("\r", ""))
    print()
os.remove(tmp)
