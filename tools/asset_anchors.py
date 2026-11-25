"""두 판본이 공유하는 '애셋 이름'을 세어 본다.

배경·효과음·BGM 파일명은 번역 대상이 아니라 판본이 달라도 그대로 남는다.
이게 양쪽에 충분히 촘촘하면 **일본어 원본 없이도** 정렬 기준점으로 쓸 수 있다.
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


def scene_of(n):
    m = re.match(r"[Dd](\d{4})", os.path.splitext(n)[0])
    return m.group(1) if m else None


# --- PS2 쪽 ---
ps2_bg, ps2_se, ps2_bgm = collections.Counter(), collections.Counter(), collections.Counter()
ps2_per_scene = collections.defaultdict(list)
for fn in os.listdir(PS2):
    s = scene_of(fn)
    if not s:
        continue
    t = decode(open(os.path.join(PS2, fn), "rb").read()).decode("cp932", "replace")
    for m in re.finditer(r'<background\b[^>]*?\bsrc="([^"]*)"', t, re.I):
        if m.group(1) and not m.group(1).startswith("#"):
            ps2_bg[m.group(1)] += 1
            ps2_per_scene[s].append(("BG", m.group(1)))
    for m in re.finditer(r'<se\b[^>]*?\bsrc="([^"]*)"', t, re.I):
        if m.group(1):
            ps2_se[m.group(1)] += 1
            ps2_per_scene[s].append(("SE", m.group(1)))
    for m in re.finditer(r'<bgm\b[^>]*?\bsrc="([^"]*)"', t, re.I):
        if m.group(1):
            ps2_bgm[m.group(1)] += 1
            ps2_per_scene[s].append(("BGM", m.group(1)))

# --- PC 쪽 ---
pc_bg, pc_se, pc_bgm = collections.Counter(), collections.Counter(), collections.Counter()
pc_per_scene = collections.defaultdict(list)
for fn in os.listdir(NSS):
    s = scene_of(fn)
    if not s:
        continue
    t = open(os.path.join(NSS, fn), "rb").read().decode("cp932", "replace")
    for m in re.finditer(r'BG\s*\(\s*"([^"]+)"', t):
        n = os.path.splitext(os.path.basename(m.group(1)))[0]
        pc_bg[n] += 1
        pc_per_scene[s].append(("BG", n))
    for m in re.finditer(r'SE_PLAY\s*\(\s*\d+\s*,\s*"([^"]+)"', t):
        pc_se[m.group(1)] += 1
        pc_per_scene[s].append(("SE", m.group(1)))
    for m in re.finditer(r'(?:BGM_VOL|CreateBGM|BGM_NEXT)\s*\(\s*"([^"]+)"', t):
        pc_bgm[m.group(1)] += 1
        pc_per_scene[s].append(("BGM", m.group(1)))

for label, a, b in (("배경", ps2_bg, pc_bg), ("효과음", ps2_se, pc_se), ("BGM", ps2_bgm, pc_bgm)):
    inter = set(a) & set(b)
    print(f"{label}: PS2 {len(a)}종({sum(a.values())}회) / PC {len(b)}종({sum(b.values())}회) "
          f"→ 이름 공통 {len(inter)}종  (PS2 기준 {len(inter) / max(len(a), 1):.0%})")
    if label == "배경":
        print("   공통 예:", " ".join(sorted(inter)[:8]))
        print("   PS2 전용 예:", " ".join(sorted(set(a) - set(b))[:8]))

print("\n씬별 앵커 밀도 (양쪽 다 있는 씬):")
common = sorted(set(ps2_per_scene) & set(pc_per_scene))
tot_a = tot_b = tot_match = 0
rows = []
for s in common:
    A = ps2_per_scene[s]
    B = pc_per_scene[s]
    sa = collections.Counter(A)
    sb = collections.Counter(B)
    shared = sum((sa & sb).values())
    tot_a += len(A)
    tot_b += len(B)
    tot_match += shared
    rows.append((s, len(A), len(B), shared))
print(f"  PS2 앵커 {tot_a:,}개 / PC 앵커 {tot_b:,}개 / 공통 {tot_match:,}개 "
      f"({tot_match / max(tot_a, 1):.0%})")
worst = sorted(rows, key=lambda r: r[3] / max(r[1], 1))[:10]
print("  앵커가 안 맞는 씬:", " ".join(f"{s}({m}/{a})" for s, a, b, m in worst))
