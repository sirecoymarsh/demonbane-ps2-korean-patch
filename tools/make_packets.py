"""의미 판정 작업 패킷 생성.

정렬표는 길이로 붙인 것이라 개작 구간에서 틀린다. 그래서 **일본어 원문을 기준으로**
한국어를 확정하는 단계가 필요하다. 후보(기존 패치)는 참고자료로 같이 준다.

설계 판단
  - 3지 판정(그대로/고침/신규)이 아니라 **모든 줄의 최종 한국어를 다시 내게 한다.**
    판본 간 줄 묶음이 달라 후보가 이웃 줄로 밀려 있는 경우가 많은데(CHECK 의 2/3),
    창 안에서 재배분하면 그 문제가 자연히 풀린다. 안 바뀌면 그게 KEEP 이다.
  - 창은 **연속된 줄 묶음**으로 준다. 앞뒤 문맥 없이는 대명사·경어를 못 고른다.
  - 용어는 창에 등장하는 것만 붙인다. 281개를 통째로 주면 희석된다.

    python make_packets.py [--size 40] [--only CHECK,MISSING] [--scene 0101]
"""
import collections
import csv
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"P:\AI\demonbane-ps2-kr"
OUT = os.path.join(ROOT, r"work\packets")
TSV = os.path.join(ROOT, r"work\ref\aligned.tsv")
GLOSS = os.path.join(ROOT, "work", "ref", "glossary_curated.tsv")   # 자동 추출본은 동시출현 잡음이 많아 정제본을 쓴다
SPK = os.path.join(ROOT, "work", "ref", "speakers.json")

args = sys.argv[1:]


def opt(name, default=None):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


SIZE = int(opt("--size", "40"))
ONLY = set((opt("--only", "") or "").split(",")) - {""}
SCENE = opt("--scene")

# 씬별 앵커 일치율(문자열 완전 일치 기반). 낮으면 개작 씬이고, 그런 씬은 OK 등급도 못 믿는다.
# 0310 이 실증: 앵커 0/62 인데 정렬표는 그 씬 줄들에 OK 를 붙여놨고 내용은 전부 딴 문장이었다.
ANCHOR = os.path.join(ROOT, "work", "ref", "scene_anchor.json")
anchor = json.load(open(ANCHOR, encoding="utf-8")) if os.path.exists(ANCHOR) else {}
TRUST = 0.75
# 용어 대조(audit_ok.py)로 걸러진 의심 줄 — 신뢰 씬의 OK 등급이라도 여기 들면 검수 대상.
_sp = os.path.join(ROOT, "work", "ref", "suspect_ids.json")
SUSPECT = set(json.load(open(_sp, encoding="utf-8"))) if os.path.exists(_sp) else set()


def scene_trusted(sc):
    a = anchor.get(sc)
    if not a or a.get("total", 0) < 4 or a.get("rate") is None:
        return False                      # 앵커가 너무 적으면 판정 불가 -> 믿지 않는다
    return a["rate"] >= TRUST



import re as _re
def term_in(jp, text):
    """가타카나 용어는 앞뒤가 가타카나가 아닐 때만 일치로 본다."""
    if not _re.fullmatch(r"[ァ-ヶー]+", jp):
        return jp in text
    return _re.search(r"(?<![ァ-ヶー])" + _re.escape(jp) + r"(?![ァ-ヶー])", text) is not None

gloss = {}
if os.path.exists(GLOSS):
    for r in list(csv.reader(open(GLOSS, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:]:
        if len(r) >= 2:
            gloss[r[0]] = r[1]

speakers = json.load(open(SPK, encoding="utf-8")) if os.path.exists(SPK) else {}
rows = [r for r in list(csv.reader(open(TSV, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:] if len(r) >= 6]
by_scene = collections.OrderedDict()
for i, r in enumerate(rows):
    by_scene.setdefault(r[0], []).append((i, r))

os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    os.remove(os.path.join(OUT, f))

OPEN = "「『（"
n_pk = n_item = n_work = 0
index = []
for scene, items in by_scene.items():
    if SCENE and scene != SCENE:
        continue
    items = [(i, r) for i, r in items if r[5] != "EXTRA"]        # KO 잉여는 버리는 것
    if not items:
        continue
    trusted = scene_trusted(scene)
    for s in range(0, len(items), SIZE):
        chunk = items[s:s + SIZE]
        need = [r for i, r in chunk if r[5] in ("CHECK", "MISSING") or not trusted or i in SUSPECT]
        if ONLY and not need:
            continue                                            # 손댈 게 없는 창은 건너뛴다
        terms = {}
        for _, r in chunk:
            hit = [jp for jp in gloss if term_in(jp, r[3])]
            for jp in hit:                                     # 최장일치: 더 긴 용어에 포함되는 짧은 용어는 뺀다
                if not any(jp != o and jp in o for o in hit):
                    terms[jp] = gloss[jp]
        a = anchor.get(scene, {})
        pk = {
            "packet": f"{scene}_{s // SIZE:02d}",
            "scene": scene,
            "anchor": {"hit": a.get("hit"), "total": a.get("total"),
                       "rate": round(a["rate"], 3) if a.get("rate") is not None else None},
            "trusted": trusted,
            "note": ("앵커 일치율이 높은 씬. status=OK 는 대체로 맞다."
                     if trusted else
                     "앵커 일치율이 낮거나 판정 불가인 씬 = 콘솔 개작 의심. "
                     "**status=OK 도 믿지 말고 전부 원문 기준으로 확정할 것.**"),
            "glossary": terms,
            "items": [{
                "id": i,
                "key": (r[6].split(",")[0] if len(r) >= 7 and r[6]
                        else f"{r[1]}:{r[2]}"),
                "file": r[1], "line": int(r[2]) if r[2] else None,
                "speaker": speakers.get(r[6].split(",")[0] if len(r) >= 7 and r[6] else f"{r[1]}:{r[2]}"),
                "kind": "say" if r[3][:1] in OPEN else "narr",
                "status": r[5],
                "work": (r[5] in ("CHECK", "MISSING")) or not trusted or i in SUSPECT,
                "jp": r[3],
                "ko_candidate": r[4],
            } for i, r in chunk],
        }
        with open(os.path.join(OUT, pk["packet"] + ".json"), "w", encoding="utf-8") as g:
            json.dump(pk, g, ensure_ascii=False, indent=1)
        n_pk += 1
        n_item += len(chunk)
        n_work += len(need)
        index.append({"packet": pk["packet"], "scene": scene, "items": len(chunk),
                      "work": len(need), "trusted": trusted})

json.dump(index, open(os.path.join(OUT, "_index.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"패킷 {n_pk}개 / 항목 {n_item:,}줄 (그중 손볼 것 {n_work:,}줄) -> {OUT}")
