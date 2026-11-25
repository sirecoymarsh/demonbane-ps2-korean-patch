"""OK 등급의 오정렬률을 **객관적으로** 잰다.

고유명사는 번역돼도 대응이 1:1 이다. JP 에 용어가 있으면 KO 에 그 역어가 있어야 한다.
없으면 그 쌍은 어긋난 것이다. 눈짐작이 아니라 문자열 일치로 판정한다.

한계: 용어가 없는 줄은 못 잰다. 그래서 이 수치는 '용어를 포함한 줄'의 오류율이다.
"""
import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"P:\AI\demonbane-ps2-kr"
gloss = {}
for r in list(csv.reader(open(os.path.join(ROOT, "work", "ref", "glossary.tsv"), encoding="utf-8"),
                         delimiter="\t", quoting=csv.QUOTE_NONE))[1:]:
    if len(r) >= 4 and float(r[3]) >= 0.7 and len(r[0]) >= 3:   # 신뢰 높은 고유명사만
        gloss[r[0]] = r[1]
anchor = json.load(open(os.path.join(ROOT, "work", "ref", "scene_anchor.json"), encoding="utf-8"))
rows = [r for r in list(csv.reader(open(os.path.join(ROOT, "work", "ref", "aligned.tsv"),
                                        encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:] if len(r) >= 6]
idx_of = {id(r): i for i, r in enumerate(rows)}
print(f"검증용 고유명사 {len(gloss)}개")


def trusted(sc):
    a = anchor.get(sc)
    return bool(a and a.get("total", 0) >= 4 and a.get("rate") is not None and a["rate"] >= 0.75)


suspect = []
for label, pred in (("신뢰 씬 · OK", lambda r: r[5] == "OK" and trusted(r[0])),
                    ("신뢰 씬 · CHECK", lambda r: r[5] == "CHECK" and trusted(r[0])),
                    ("비신뢰 씬 · OK", lambda r: r[5] == "OK" and not trusted(r[0]))):
    hit = miss = 0
    samples = []
    for r in rows:
        if not pred(r) or not r[3] or not r[4]:
            continue
        terms = [(jp, ko) for jp, ko in gloss.items() if jp in r[3]]
        if not terms:
            continue
        if all(ko in r[4] for _, ko in terms):
            hit += 1
        else:
            miss += 1
            suspect.append(rows.index(r) if False else idx_of[id(r)])
            if len(samples) < 3:
                bad = [f"{jp}->{ko}" for jp, ko in terms if ko not in r[4]]
                samples.append((bad, r[3][:60], r[4][:60]))
    n = hit + miss
    print(f"\n{label}: 용어 포함 {n:,}행 중 역어 불일치 {miss:,} ({miss / max(n,1):.1%})")
    for bad, jp, ko in samples:
        print(f"    {bad}")
        print(f"      JP {jp}")
        print(f"      KO {ko}")


# 용어 대조로 걸러진 의심 줄 = LLM 없이 얻는 무료 필터. 패킷 생성이 이걸 읽어 work 로 승격한다.
json.dump(sorted(set(suspect)),
          open(os.path.join(ROOT, "work", "ref", "suspect_ids.json"), "w", encoding="utf-8"))
print(f"→ 의심 줄 {len(set(suspect)):,}개 -> work/ref/suspect_ids.json")
