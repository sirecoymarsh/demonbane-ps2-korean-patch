"""애셋 이름(SE·BGM·배경)을 동기점으로 삼아 개작 구간을 찾아낸다.

효과음 이름은 번역 대상이 아니라 판본이 달라도 그대로다(실측 92% 공통).
두 판본의 앵커 열에서 LCS 를 구하면 '여기까지는 같은 장면'이라는 확실한 동기점이 나오고,
동기점 사이 구간에서 한쪽에만 본문이 있으면 그게 개작·신규분이다.

길이 추정이 아니라 **문자열 완전 일치**에 기대므로 앞서 실패한 방법들과 성격이 다르다.
"""
import collections
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skcodec import decode

PS2 = r"P:\AI\demonbane-ps2-kr\work\script"
NSS = r"P:\AI\demonbane-ps2-kr\work\patch\nss"
MAPJ = r"P:\AI\demonbane-ps2-kr\work\patch\carrier_map.json"
TAG = re.compile(r"<[^>\n]*>")
PRE = re.compile(r"<PRE\b[^>]*>(.*?)</PRE>", re.S | re.I)

import json
CMAP = {chr(int(k, 16)): chr(int(v, 16)) for k, v in json.load(open(MAPJ, encoding="utf-8")).items()}


def scene_of(n):
    m = re.match(r"[Dd](\d{4})", os.path.splitext(n)[0])
    return m.group(1) if m else None


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


def ps2_stream(fn):
    """[(kind, payload)] — kind 'A'=앵커, 'T'=본문"""
    out = []
    t = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    for raw in t.split("\n"):
        line = strip_comment(raw.rstrip("\r"))
        # 앵커는 SE·BGM 만. 배경은 이식하며 이름을 갈아치워 이름 공통이 12% 뿐이라 오히려 방해된다.
        for m in re.finditer(r'<(se|bgm)\b[^>]*?\bsrc="([^"]*)"', line, re.I):
            v = m.group(2)
            if v and not v.startswith("#"):
                out.append(("A", (m.group(1).lower(), v)))
        body = TAG.sub("", line).strip()
        if body:
            out.append(("T", body))
    return out


def pc_stream(fn):
    out = []
    t = open(os.path.join(NSS, fn), "rb").read().decode("cp932", "replace")
    pos = 0
    events = []
    for m in re.finditer(r'SE_PLAY\s*\(\s*\d+\s*,\s*"([^"]+)"', t):
        events.append((m.start(), "A", ("se", m.group(1))))
    for m in re.finditer(r'(?:BGM_VOL|CreateBGM|BGM_NEXT)\s*\(\s*"([^"]+)"', t):
        events.append((m.start(), "A", ("bgm", m.group(1))))
    for m in PRE.finditer(t):
        off = m.start(1)
        for ln in m.group(1).split("\n"):
            s = ln.strip()
            if s and not s.startswith(("[", "{", "//", "<")):
                events.append((off, "T", "".join(CMAP.get(c, c) for c in s)))
            off += len(ln) + 1
    events.sort(key=lambda e: e[0])
    return [(k, v) for _, k, v in events]


def lcs_anchors(a, b):
    """앵커만 뽑아 LCS. 반환: 매칭된 (a_idx, b_idx) 쌍"""
    ia = [i for i, (k, _) in enumerate(a) if k == "A"]
    ib = [i for i, (k, _) in enumerate(b) if k == "A"]
    A = [a[i][1] for i in ia]
    B = [b[i][1] for i in ib]
    n, m = len(A), len(B)
    if not n or not m:
        return []
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if A[i] == B[j] else max(dp[i + 1][j], dp[i][j + 1])
    out = []
    i = j = 0
    while i < n and j < m:
        if A[i] == B[j]:
            out.append((ia[i], ib[j]))
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


ps2_files = collections.defaultdict(list)
for fn in sorted(os.listdir(PS2)):
    s = scene_of(fn)
    if s:
        ps2_files[s].append(fn)
pc_files = collections.defaultdict(list)
for fn in sorted(os.listdir(NSS)):
    s = scene_of(fn)
    if s:
        pc_files[s].append(fn)

streams = {}
for s in sorted(set(ps2_files) & set(pc_files)):
    streams[s] = ([e for fn in ps2_files[s] for e in ps2_stream(fn)],
                  [e for fn in pc_files[s] for e in pc_stream(fn)])

RATIO = (sum(len(v) for A, B in streams.values() for k, v in B if k == "T") /
         sum(len(v) for A, B in streams.values() for k, v in A if k == "T"))

tot_jp = tot_empty = tot_short = 0
anchor_hit = anchor_tot = 0
rows = []
for s, (A, B) in streams.items():
    pairs = lcs_anchors(A, B)
    anchor_tot += sum(1 for k, _ in A if k == "A")
    anchor_hit += len(pairs)
    jp_chars = sum(len(v) for k, v in A if k == "T")
    tot_jp += jp_chars
    empty = short = 0
    pa = pb = -1
    for ai, bi in pairs + [(len(A), len(B))]:
        jt = sum(len(v) for k, v in A[pa + 1:ai] if k == "T")
        kt = sum(len(v) for k, v in B[pb + 1:bi] if k == "T")
        if jt:
            if kt == 0:
                empty += jt
            else:
                short += max(0, jt - kt / RATIO)
        pa, pb = ai, bi
    tot_empty += empty
    tot_short += short
    rows.append((s, jp_chars, empty, short, len(pairs), sum(1 for k, _ in A if k == "A")))

print(f"앵커(SE·BGM) 매칭: PS2 {anchor_tot:,}개 중 {anchor_hit:,}개가 순서까지 맞음 "
      f"({anchor_hit / max(anchor_tot, 1):.0%})   길이비 {RATIO:.3f}")
print(f"\n공통 씬 PS2 본문 {tot_jp:,}자 기준")
print(f"  ① 동기점 사이에 PC 본문이 **전혀 없음** : {tot_empty:>8,.0f}자 ({tot_empty / tot_jp:.1%})")
print(f"  ② 있긴 한데 분량이 모자람(구간 수지)      : {tot_short:>8,.0f}자 ({tot_short / tot_jp:.1%})")
print(f"  → 신규 번역 상한 추정 (①+②)              : {tot_empty + tot_short:>8,.0f}자 "
      f"({(tot_empty + tot_short) / tot_jp:.1%})")

# ② 는 구간마다 음수 편차를 0 으로 깎아 합치므로 구조적으로 과대추정이다.
# 문자열 완전 일치에만 기대는 지표 = 씬별 앵커 일치율.
print("\n[문자열 일치만으로 판정] 앵커 일치율이 낮은 씬 = 개작된 씬")
for th in (0.25, 0.5, 0.75):
    sc = [r for r in rows if r[5] >= 4 and r[4] / r[5] < th]
    print(f"  일치율 {th:.0%} 미만: 씬 {len(sc):>3}개 / PS2 본문 {sum(r[1] for r in sc):>7,}자 "
          f"({sum(r[1] for r in sc) / tot_jp:>5.1%})")

print("\n개작이 몰린 씬 상위 20 (①+② 기준):")
for s, tot, e, sh, hit, at in sorted(rows, key=lambda r: -(r[2] + r[3]))[:20]:
    print(f"  {s}: 씬 {tot:>7,}자 / 부족 {e + sh:>6,.0f}자 ({(e + sh) / max(tot, 1):>3.0%})  "
          f"앵커 {hit}/{at}")

# 씬별 앵커 일치율을 파일로 낸다 — 정렬 신뢰도의 유일한 '문자열 완전 일치' 기반 지표.
# 이게 낮은 씬은 개작된 씬이고, 그런 씬에서는 OK 등급도 믿으면 안 된다(0310 실증).
import json as _json
_json.dump(
    {r[0]: {"hit": r[4], "total": r[5],
            "rate": (r[4] / r[5]) if r[5] else None, "jp_chars": r[1]} for r in rows},
    open(r"P:\AI\demonbane-ps2-kr\work\ref\scene_anchor.json", "w", encoding="utf-8"),
    ensure_ascii=False, indent=1)
print(r"-> work\ref\scene_anchor.json")
