import csv
import sys
import random

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TSV = r"P:\AI\demonbane-ps2-kr\work\ref\aligned.tsv"
rows = [r for r in list(csv.reader(open(TSV, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:] if len(r) >= 6]
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 7)

for tag, n in (("OK", 6), ("CHECK", 14)):
    sel = random.sample([r for r in rows if r[5] == tag], n)
    print(f"\n########## {tag} 표본 {n} ##########")
    for r in sel:
        print(f"[{r[0]} {r[1]}:{r[2]}]")
        print(f"  JP {r[3][:110]}")
        print(f"  KO {r[4][:110]}")
