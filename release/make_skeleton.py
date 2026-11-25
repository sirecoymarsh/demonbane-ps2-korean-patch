"""추가 시나리오 파일의 번역 대상 조각을 모두 뽑는다 -> work/added/skeleton.tsv (key, speaker, jp)."""
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from segs import split_runs, run_text
ROOT = r"P:\AI\demonbane-ps2-kr"
FILES = ["D0751.txt", "D0752.txt", "D0753.txt", "D0754.txt", "D0755.txt", "D0756.txt", "ep_ruri02a.txt"]
VOICE = re.compile(r'<VOICE\s+NAME="([^"]*)"', re.I)
out = ["key\tspeaker\tjp"]
for fn in FILES:
    lines = open(os.path.join(ROOT, "work", "script_dec", fn), "rb").read().decode("cp932").split("\n")
    pending = ""
    for no, raw in enumerate(lines, 1):
        line = raw.rstrip("\r")
        pieces, runs, tail = split_runs(line)
        for p in pieces:
            m = VOICE.match(p) if p.startswith("<") else None
            if m:
                pending = m.group(1)
        for k, (a, b) in enumerate(runs):
            jp = run_text(pieces, a, b, ruby=True)
            # 화자: 직전 VOICE 가 있으면 그 사람. 「 로 끝나지 않은 대사가 다음 줄로 이어지면 그대로 유지.
            out.append(f"{fn}:{no}:{k}\t{pending}\t{jp}")
            body = jp.strip(" 　")
            if pending and (body.endswith("」") or body.endswith("』")) :
                pending = ""
            elif not pending:
                pass
open(os.path.join(ROOT, "work", "added", "skeleton.tsv"), "w", encoding="utf-8").write("\n".join(out) + "\n")
import collections
c = collections.Counter(l.split(":")[0] for l in out[1:])
print(c, sum(c.values()))
