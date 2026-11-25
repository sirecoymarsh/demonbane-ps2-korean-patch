"""받아온 일본어 nss.npa 가 이 한국어 패치와 **같은 판본인지** 기계적으로 판정한다.

한국어 패치는 `.nss` 의 `<PRE>` 안 텍스트만 갈아치우고 나머지(함수 호출·주석·애셋 이름·
`[textNNNN]` 블록 ID·플래그)는 원본 그대로 두었다. 따라서 <PRE> 본문을 지운 '뼈대'를 비교하면
같은 판본인지 파일 단위로 확정된다.

    python verify_jp_nss.py <일본어 nss.npa 경로>

판정
    뼈대 해시 일치        = 같은 판본. 그 파일은 위치 대응으로 100% 정확히 이식 가능.
    블록 수·ID 만 일치    = 개정판. 블록 단위로는 안전, 줄 단위는 확인 필요.
    불일치                = 다른 판본. 그 파일만 앵커 방식으로 처리.
"""
import hashlib
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from npa import parse, read

KO_NSS = r"P:\AI\demonbane-ps2-kr\work\patch\nss"
PRE = re.compile(r"(<PRE\b[^>]*>)(.*?)(</PRE>)", re.S | re.I)
TEXTID = re.compile(r"\[text\d+\]")


def skeleton(text):
    """<PRE> 본문을 지운 뼈대. 블록 ID 는 남긴다."""
    def repl(m):
        ids = " ".join(TEXTID.findall(m.group(2)))
        return f"{m.group(1)}{ids}{m.group(3)}"
    s = PRE.sub(repl, text)
    return re.sub(r"[ \t]+", " ", s)


def blocks(text):
    return [TEXTID.findall(m.group(2)) for m in PRE.finditer(text)]


ko = {}
for fn in os.listdir(KO_NSS):
    t = open(os.path.join(KO_NSS, fn), "rb").read().decode("cp932", "replace")
    ko[fn] = (hashlib.sha1(skeleton(t).encode("utf-8", "replace")).hexdigest(), blocks(t))

blob, entries, base, comp, enc = parse(sys.argv[1])
jp = {}
for e in entries:
    if e["type"] != 2:
        continue
    name = e["name"].decode("cp932", "replace").replace("\\", "/").rsplit("/", 1)[-1]
    t = read(blob, e, base, comp).decode("cp932", "replace")
    jp[name] = (hashlib.sha1(skeleton(t).encode("utf-8", "replace")).hexdigest(), blocks(t))

both = sorted(set(ko) & set(jp))
same = [f for f in both if ko[f][0] == jp[f][0]]
blk = [f for f in both if f not in same and ko[f][1] == jp[f][1]]
diff = [f for f in both if f not in same and f not in blk]

print(f"한국어 패치 {len(ko)}파일 / 후보 일본어 {len(jp)}파일 / 이름 공통 {len(both)}")
print(f"  뼈대 완전 일치 (같은 판본)   : {len(same):>4}  ({len(same) / max(len(both), 1):.0%})")
print(f"  블록 구성만 일치 (개정판)    : {len(blk):>4}")
print(f"  불일치 (다른 판본)           : {len(diff):>4}")
print(f"  한국어에만 있음              : {len(set(ko) - set(jp)):>4}")
print(f"  일본어에만 있음              : {len(set(jp) - set(ko)):>4}")
if diff:
    print("\n불일치 파일 (최대 30):")
    for f in diff[:30]:
        print(f"  {f}: 한국어 블록 {len(ko[f][1])}개 / 일본어 블록 {len(jp[f][1])}개")
verdict = ("같은 판본으로 판정 — 위치 대응으로 그대로 써도 된다."
           if len(same) / max(len(both), 1) >= 0.9 else
           "부분 일치 — 일치하는 파일만 위치 대응, 나머지는 앵커 방식 병행.")
print(f"\n판정: {verdict}")
