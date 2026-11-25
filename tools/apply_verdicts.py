"""판정 결과를 정렬표에 되먹인다.

원본 aligned.tsv 는 건드리지 않는다. 정렬은 기계 산출물이고 판정은 사람/모델 산출물이라
섞으면 나중에 어느 쪽이 틀렸는지 못 가른다. 결과는 aligned_final.tsv 로 따로 낸다.

    python apply_verdicts.py            # work/verdicts/*.json 전부 적용

판정 파일 형식
    {"packet": "0310_00", "items": [{"id": 3448, "ko": "..."}, ...]}
  - ko 가 후보와 같으면 KEEP, 다르면 FIXED, 후보가 없었으면 NEW 로 기록한다.
  - 창 안의 모든 줄을 다시 내게 하므로 '이웃 줄로 밀린 후보'가 자연히 재배분된다.
"""
import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"P:\AI\demonbane-ps2-kr"
TSV = os.path.join(ROOT, "work", "ref", "aligned.tsv")
VDIR = os.path.join(ROOT, "work", "verdicts")
OUT = os.path.join(ROOT, "work", "ref", "aligned_final.tsv")

rows = list(csv.reader(open(TSV, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))
head, body = rows[0], [r for r in rows[1:] if len(r) >= 6]

verdicts = {}
os.makedirs(VDIR, exist_ok=True)
files = sorted(f for f in os.listdir(VDIR) if f.endswith(".json"))
for f in files:
    d = json.load(open(os.path.join(VDIR, f), encoding="utf-8"))
    for it in d.get("items", []):
        # 행 인덱스는 재정렬하면 어긋난다. 파일:줄 키를 우선 쓴다.
        k = it.get("key") or f'ID{it["id"]}'
        verdicts.setdefault(k, []).append(it["ko"])   # <K> 로 갈린 단위는 key 가 같다 -> 순서대로

PUNCT = str.maketrans({"。": "｡", "、": "､", "！": "!", "？": "?"})

stat = {"KEEP": 0, "FIXED": 0, "NEW": 0, "미판정": 0}
for i, r in enumerate(body):
    key = (r[6].split(",")[0] if len(r) >= 7 and r[6] else f"{r[1]}:{r[2]}")
    lst = verdicts.get(key) or verdicts.get(f"ID{i}")
    hit = lst.pop(0) if lst else None
    if hit is not None:
        new = r[4] if hit.strip() == "=" else hit.translate(PUNCT).strip()   # "=" = 후보 그대로 채택
        if not r[4]:
            r[5] = "NEW"
            stat["NEW"] += 1
        elif new.strip() == r[4].strip():
            r[5] = "KEEP"
            stat["KEEP"] += 1
        else:
            r[5] = "FIXED"
            stat["FIXED"] += 1
        r[4] = new
    elif r[5] != "EXTRA":
        stat["미판정"] += 1

with open(OUT, "w", encoding="utf-8", newline="") as g:
    g.write("\t".join(head) + "\n")
    for r in body:
        g.write("\t".join(x.replace("\t", " ") for x in r) + "\n")

print(f"판정 파일 {len(files)}개 / 항목 {len(verdicts):,}줄 적용")
for k, v in stat.items():
    print(f"  {k:<6} {v:>7,}")
print(f"-> {OUT}")
