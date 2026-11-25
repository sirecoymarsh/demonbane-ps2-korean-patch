"""각 스크립트 줄의 화자를 <VOICE NAME="..."> 태그에서 뽑는다.

출력 work/ref/speakers.json : {"D0310_ps2.txt:36": "九郎", ...}
VOICE 태그는 바로 뒤의 대사 줄(들)에 붙는다. 빈 줄이나 다음 태그가 나오면 끝난다.
정렬 단위가 여러 물리 줄을 덮으면(lines 열) 그 줄들의 화자를 " / " 로 모두 잇는다.
"""
import csv, json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"P:\AI\demonbane-ps2-kr"
SD = os.path.join(ROOT, "work", "script_dec")
V = re.compile(r'<VOICE\s+NAME="([^"]*)"', re.I)
TAG = re.compile(r'^\s*<')
line_speaker = {}
for f in os.listdir(SD):
    t = open(os.path.join(SD, f), "rb").read().decode("cp932", "replace")
    cur = None
    for no, ln in enumerate(t.split("\n"), 1):
        s = ln.rstrip("\r")
        m = V.search(s)
        if m:
            cur = m.group(1); continue
        if TAG.match(s):          # 다른 태그(BOX, face, se...)는 화자를 끊지 않는다 — 실측: face 뒤에 VOICE 가 온다
            if s.lower().startswith(("<box", "<clear", "<a ", "<select", "<bgm", "<wipe")) and cur and "<voice" not in s.lower():
                pass
            continue
        if not s.strip():
            continue
        if cur:
            line_speaker[f"{f}:{no}"] = cur
            # 한 VOICE 가 여러 물리 줄을 덮는다(줄 이어짐). 빈 줄이 나오면 다음 VOICE 까지 화자 없음
        # 대사 줄이 끝나고 빈 줄 -> 아래에서 처리
    # 두 번째 패스: 빈 줄에서 화자 리셋
    cur = None
    out = {}
    for no, ln in enumerate(t.split("\n"), 1):
        s = ln.rstrip("\r")
        m = V.search(s)
        if m:
            cur = m.group(1); continue
        if not s.strip():
            cur = None; continue
        if TAG.match(s):
            continue
        if cur:
            out[f"{f}:{no}"] = cur
    for k, v in out.items():
        line_speaker[k] = v
    for k in [k for k in line_speaker if k.startswith(f + ":") and k not in out]:
        del line_speaker[k]

rows = [r for r in list(csv.reader(open(os.path.join(ROOT, "work", "ref", "aligned.tsv"), encoding="utf-8"),
                                    delimiter="\t", quoting=csv.QUOTE_NONE))[1:] if len(r) >= 6]
unit = {}
hit = 0
say = 0
for r in rows:
    keys = r[6].split(",") if len(r) >= 7 and r[6] else [f"{r[1]}:{r[2]}"]
    names = []
    for k in keys:
        n = line_speaker.get(k)
        if n and (not names or names[-1] != n):
            names.append(n)
    if names:
        unit[keys[0]] = " / ".join(names); hit += 1
    if r[3].startswith("「"):
        say += 1
json.dump(unit, open(os.path.join(ROOT, "work", "ref", "speakers.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"화자 붙은 단위 {hit:,} / 대사 단위(「로 시작) {say:,} / 전체 {len(rows):,}")
miss = [r for r in rows if r[3].startswith("「") and (r[6].split(",")[0] if len(r) >= 7 and r[6] else f"{r[1]}:{r[2]}") not in unit]
print("대사인데 화자 없음", len(miss))
for r in miss[:5]: print("  ", r[1], r[2], r[3][:50])
