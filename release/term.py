"""기존 번역(코덱스 교정 사본)에서 원문 낱말이 어떻게 옮겨졌는지 본다.  term.py 낱말... [--spk 화자] [-n 4]"""
import csv, sys, os, re, collections
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"P:\AI\demonbane-ps2-kr"
STAGED = r"P:\AI\Codex\projects\demonbane-ps2-kr-audit\handoff-fable\sessions\20260905-codex-repair\staged\work\ref\aligned_final.tsv"
args = sys.argv[1:]; n = 4; spk = None
if "-n" in args: i = args.index("-n"); n = int(args[i + 1]); del args[i:i + 2]
if "--spk" in args: i = args.index("--spk"); spk = args[i + 1]; del args[i:i + 2]
speakers = {}
for r in csv.reader(open(os.path.join(ROOT, r"work\ref\lines.tsv"), encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
    if len(r) >= 4 and r[3]: speakers[(r[0], r[1])] = r[3]
rows = list(csv.reader(open(STAGED, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:]
for t in args:
    hits = [r for r in rows if len(r) > 5 and t in r[3] and r[5] != "NEW" and (spk is None or spk in speakers.get((r[1], r[2]), ""))]
    print(f"== {t}  ({len(hits)})")
    for r in hits[:n]:
        print(f"  [{speakers.get((r[1], r[2]), '')}] {r[3][:70]}\n    → {r[4][:110]}")
