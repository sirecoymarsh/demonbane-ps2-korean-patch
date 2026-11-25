import csv
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TSV = r"P:\AI\demonbane-ps2-kr\work\ref\aligned.tsv"
scene = sys.argv[1]
RUN = 4

rows = [r for r in list(csv.reader(open(TSV, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:] if len(r) >= 6]
rs = [r for r in rows if r[0] == scene]

s = None
regions = []
for i, r in enumerate(rs + [["", "", "", "", "", "OK"]]):
    if r[5] in ("MISSING", "CHECK"):
        if s is None:
            s = i
    else:
        if s is not None and i - s >= RUN:
            regions.append((s, i))
        s = None

print(f"{scene}: {len(rs)}행 중 개작 의심 구간 {len(regions)}곳")
for a, b in regions[:3]:
    print(f"\n--- {a}~{b} ({b - a}줄) ---")
    for r in rs[max(0, a - 2):min(len(rs), b + 2)]:
        mark = "  " if r[5] == "OK" else "**"
        print(f"{mark}[{r[5]:<7}] JP {r[3][:88]}")
        print(f"            KO {r[4][:88]}")
