"""PS2 일본어 줄 <-> PC 한국어 줄 자동 정렬 (Gale-Church 변형 + 앵커).

두 판본은 같은 시나리오라 줄 순서가 보존된다. 길이비와 줄 종류(대사/지문)를 비용으로 삼아
DP 로 1-1 / 1-0 / 0-1 / 1-2 / 2-1 을 고른다. 결과를 aligned.tsv 로 낸다.
"""
import os
import re
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skcodec import decode

PS2 = r"P:\AI\demonbane-ps2-kr\work\script"
KO = r"P:\AI\demonbane-ps2-kr\work\patch\ko"
OUT = r"P:\AI\demonbane-ps2-kr\work\ref\aligned.tsv"
TAG = re.compile(r"<[^>\n]*>")
OPEN = "「『（"


def strip_comment(line):
    depth = 0
    for i, ch in enumerate(line):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif ch == "/" and depth == 0 and line.startswith("//", i):
            return line[:i]
    return line


def kind(s):
    return "say" if s[:1] in OPEN else "narr"


CLICK = re.compile(r"<\s*[Kk]\s*>")
QSPLIT = re.compile(r"(?<=[」』）])[ 　]+(?=[「『（])")


def units(s):
    """양쪽 판본의 줄 나눔이 다르므로 '클릭 단위 / 대사 단위'로 쪼개 눈금을 맞춘다."""
    out = []
    for part in CLICK.split(s):
        for q in QSPLIT.split(part):
            q = q.strip()
            if q:
                out.append(q)
    return out


MAX_MERGE = int(os.environ.get("MAX_MERGE", 6))


def merge_quotes(items, get):
    """따옴표 하나가 여러 줄에 걸친 경우를 한 덩어리로 묶는다.
    PS2·PC 양쪽 다 「…」 안에서 줄을 나누므로 이걸 안 맞추면 정렬이 통째로 밀린다.

    ★ 상한 필수: 스크립트에는 닫히지 않는 「 가 있고(연출용), 상한이 없으면
      그 지점부터 파일 끝까지 한 덩어리가 된다. 실제로 13,121자짜리 행이 생겼고
      그 여파로 씬 전체가 미치환으로 남았다."""
    out = []
    buf = []
    depth = 0
    for it in items:
        t = get(it)
        depth += t.count("「") + t.count("『") - t.count("」") - t.count("』")
        buf.append(it)
        if depth <= 0 or len(buf) >= MAX_MERGE:
            out.append(buf)
            buf = []
            depth = 0
    if buf:
        out.append(buf)
    return out


def load_ps2(fn):
    out = []
    txt = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    for no, raw in enumerate(txt.split("\n"), 1):
        line = strip_comment(raw.rstrip("\r"))
        line = CLICK.sub("\x00", line)
        b = TAG.sub("", line)
        for u in units(b.replace("\x00", "<k>")):
            out.append((no, u))
    return out


def scene_of(name):
    """씬 키. D#### 외에 엔딩 스크립트도 짝지어야 한다 — PS2 `ep_al01.txt` 는
    PC 에서 `ep_al01_01.nss` / `ep_al01_02endroll.nss` 로 쪼개져 있다."""
    b = os.path.splitext(name)[0]
    m = re.match(r"[Dd](\d{4})", b)
    if m:
        return m.group(1)
    m = re.match(r"(ep_[A-Za-z]+\d+[a-z]?)", b, re.I)
    if m:
        return m.group(1).lower()
    if b.lower() == "endcomp":
        return "endcomp"
    return None


ko_raw = collections.defaultdict(list)
for fn in sorted(os.listdir(KO)):
    s = scene_of(fn)
    if s:
        for ln in open(os.path.join(KO, fn), encoding="utf-8"):
            for u in units(ln.strip()):
                ko_raw[s].append((fn, u))

ps2_raw = collections.defaultdict(list)
for fn in sorted(os.listdir(PS2)):
    s = scene_of(fn)
    if s:
        ps2_raw[s].extend((fn, no, t) for no, t in load_ps2(fn))

# 여러 줄에 걸친 따옴표를 한 덩어리로
ko_by_scene = {s: [(g[0][0], " ".join(x[1] for x in g)) for g in merge_quotes(v, lambda x: x[1])]
               for s, v in ko_raw.items()}
# 한 단위가 물리적으로 여러 줄에 걸치므로, 덮는 줄을 전부 기록해야 나중에 다 치환할 수 있다.
ps2_by_scene = {s: [(g[0][0], g[0][1], " ".join(x[2] for x in g),
                     sorted({(x[0], x[1]) for x in g})) for g in merge_quotes(v, lambda x: x[2])]
                for s, v in ps2_raw.items()}

# 전역 길이비 (한글이 일본어보다 몇 배)
tj = sum(len(t) for v in ps2_by_scene.values() for _, _, t, _ in v)
tk = sum(len(t) for v in ko_by_scene.values() for _, t in v)
RATIO = tk / tj
print(f"PS2 일본어 {tj:,}자 / PC 한국어 {tk:,}자   길이비 {RATIO:.3f}")

BIG = 1e9
SKIP = float(os.environ.get("ALIGN_SKIP", 1.6))     # 줄 버리기 비용 (낮을수록 잘 끊는다)
KIND = float(os.environ.get("ALIGN_KIND", 2.2))     # 대사/지문 종류 불일치 벌점
MERGEP = float(os.environ.get("ALIGN_MERGE", 0.3))  # 1-2 / 2-1 병합 벌점


def align(jp, ko):
    """jp: [(file,no,text)], ko: [(file,text)] -> [(j_idx or None, k_idx or None)]"""
    n, m = len(jp), len(ko)
    prev = [0.0] + [BIG] * m
    back = [[(0, 0)] * (m + 1) for _ in range(n + 1)]
    for k in range(1, m + 1):
        prev[k] = prev[k - 1] + SKIP
        back[0][k] = (0, 1)
    for j in range(1, n + 1):
        cur = [prev[0] + SKIP] + [BIG] * m
        back[j][0] = (1, 0)
        lj = len(jp[j - 1][2])
        kj = kind(jp[j - 1][2])
        for k in range(1, m + 1):
            lk = len(ko[k - 1][1])
            kk = kind(ko[k - 1][1])
            c11 = abs(lk - RATIO * lj) / max(8.0, RATIO * lj) + (KIND if kj != kk else 0.0)
            best = prev[k - 1] + c11
            bp = (1, 1)
            v = cur[k - 1] + SKIP                      # KO 줄 삽입
            if v < best:
                best, bp = v, (0, 1)
            v = prev[k] + SKIP                         # PS2 줄 미번역
            if v < best:
                best, bp = v, (1, 0)
            if k >= 2:
                lk2 = lk + len(ko[k - 2][1])
                v = prev[k - 2] + abs(lk2 - RATIO * lj) / max(8.0, RATIO * lj) + MERGEP
                if v < best:
                    best, bp = v, (1, 2)
            if j >= 2:
                lj2 = lj + len(jp[j - 2][2])
                v = prev2[k - 1] + abs(lk - RATIO * lj2) / max(8.0, RATIO * lj2) + MERGEP
                if v < best:
                    best, bp = v, (2, 1)
            cur[k] = best
            back[j][k] = bp
        prev2 = prev
        prev = cur
    # traceback
    pairs = []
    j, k = n, m
    while j > 0 or k > 0:
        dj, dk = back[j][k]
        if dj == 0 and dk == 0:
            break
        js = list(range(j - dj, j))
        ks = list(range(k - dk, k))
        pairs.append((js, ks))
        j -= dj
        k -= dk
    pairs.reverse()
    return pairs


rows = []
stat = collections.Counter()
per_scene = []
for s in sorted(set(ps2_by_scene) | set(ko_by_scene)):
    jp = ps2_by_scene.get(s, [])
    ko = ko_by_scene.get(s, [])
    if not jp:
        stat["PC 전용(버림)"] += len(ko)
        continue
    if not ko:
        stat["신규 번역"] += len(jp)
        for f, no, t, cov in jp:
            rows.append((s, f, no, t, "", "MISSING",
                         ",".join(f"{a}:{b}" for a, b in cov)))
        per_scene.append((s, len(jp), 0, 0))
        continue
    pairs = align(jp, ko)
    ok = 0
    for js, ks in pairs:
        jt = " ".join(jp[i][2] for i in js)
        kt = " ".join(ko[i][1] for i in ks)
        if js and ks:
            stat["대응"] += len(js)
            dev = abs(len(kt) - RATIO * len(jt)) / max(8.0, RATIO * len(jt))
            same_kind = kind(jt) == kind(kt)
            if len(js) == 1 and len(ks) == 1 and same_kind and dev <= 0.35:
                tagv = "OK"
                ok += 1
                stat["  └ 확실"] += 1
            else:
                tagv = "CHECK"
                stat["  └ 확인필요"] += len(js)
        elif js:
            stat["신규 번역"] += len(js)
            tagv = "MISSING"
        else:
            stat["KO 잉여"] += len(ks)
            tagv = "EXTRA"
        f = jp[js[0]][0] if js else ""
        no = jp[js[0]][1] if js else ""
        cov = sorted({c for i in js for c in jp[i][3]})
        rows.append((s, f, no, jt, kt, tagv, ",".join(f"{a}:{b}" for a, b in cov)))
    per_scene.append((s, len(jp), len(ko), ok))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="") as g:
    g.write("scene\tfile\tline\tjp\tko\tstatus\tlines\n")
    for r in rows:
        g.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")

total_jp = sum(len(v) for v in ps2_by_scene.values())
print("\n=== 정렬 결과 ===")
for k, v in stat.most_common():
    print(f"  {k:<14} {v:>7,}")
print(f"\nPS2 번역 대상 줄 {total_jp:,} 중 한국어가 붙은 줄 {stat['대응']:,} "
      f"({stat['대응'] / total_jp:.1%})")
print(f"새로 번역해야 하는 줄 {stat['신규 번역']:,} ({stat['신규 번역'] / total_jp:.1%})")

worst = sorted(per_scene, key=lambda x: (x[3] / x[1]) if x[1] else 0)[:22]
print("\n확신도가 낮은 씬 (전연령 개작 의심 구간):")
for s, a, b, ok in worst:
    print(f"  {s}: PS2 {a:>5}줄 / KO {b:>5}줄 / 확실 {ok:>5}  ({ok / a:.0%})")
good = sum(1 for s, a, b, ok in per_scene if a and ok / a >= 0.8)
mid = sum(1 for s, a, b, ok in per_scene if a and 0.4 <= ok / a < 0.8)
bad = sum(1 for s, a, b, ok in per_scene if a and ok / a < 0.4)
print(f"\n씬 확신도 분포: 80%↑ {good}개 / 40~80% {mid}개 / 40%↓ {bad}개")
print(f"\n-> {OUT}")

