"""불일치를 두 종류로 가른다.

 (A) 버려도 되는 것  : KO 쪽에만 길게 이어지는 구간 = PC 18금 본문. PS2 에 대응이 없다.
 (B) 새로 써야 하는 것: PS2 쪽에 확실한 대응이 없는 줄이 길게 이어지는 구간 = 콘솔판 개작분.

흩어진 한두 줄은 줄 나눔 차이일 뿐이므로 RUN 이상 이어질 때만 '구간'으로 센다.
"""
import csv
import os
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TSV = r"P:\AI\demonbane-ps2-kr\work\ref\aligned.tsv"
RUN = int(os.environ.get("RUN", 4))

rows = [r for r in list(csv.reader(open(TSV, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:] if len(r) >= 6]

by_scene = collections.defaultdict(list)
for r in rows:
    by_scene[r[0]].append(r)


def runs(seq, pred):
    out = []
    s = None
    for i, x in enumerate(seq):
        if pred(x):
            if s is None:
                s = i
        else:
            if s is not None and i - s >= RUN:
                out.append((s, i))
            s = None
    if s is not None and len(seq) - s >= RUN:
        out.append((s, len(seq)))
    return out


def jp_lines(r):
    return 0 if r[5] == "EXTRA" else max(1, r[3].count("\n") + 1) if r[3] else 0


rewrite_scenes = []
tot_new_lines = tot_new_chars = 0
tot_drop = 0
scatter = 0
for s, rs in sorted(by_scene.items()):
    # (A) KO 전용 구간
    for a, b in runs(rs, lambda r: r[5] == "EXTRA"):
        tot_drop += sum(len(r[4]) for r in rs[a:b])
    # (B) PS2 쪽에 확실한 대응이 없는 구간
    bad = runs(rs, lambda r: r[5] in ("MISSING", "CHECK"))
    n_lines = sum(1 for a, b in bad for r in rs[a:b] if r[5] != "EXTRA")
    n_chars = sum(len(r[3]) for a, b in bad for r in rs[a:b] if r[5] != "EXTRA")
    if n_lines:
        rewrite_scenes.append((s, n_lines, n_chars, len(rs)))
        tot_new_lines += n_lines
        tot_new_chars += n_chars
    # 흩어진 단발 CHECK = 줄 나눔 차이로 간주
    inrun = {i for a, b in bad for i in range(a, b)}
    scatter += sum(1 for i, r in enumerate(rs) if r[5] == "CHECK" and i not in inrun)

print(f"(A) 버리는 PC 18금 본문 : {tot_drop:,}자")
print(f"(B) 새로 써야 하는 구간   : {tot_new_lines:,}줄 / 일본어 {tot_new_chars:,}자")
print(f"    (흩어진 단발 불일치 {scatter:,}줄 은 줄 나눔 차이로 보고 제외)")

print(f"\n작업이 몰린 씬 (연속 {RUN}줄 이상 기준), 상위 25:")
for s, n, c, tot in sorted(rewrite_scenes, key=lambda x: -x[1])[:25]:
    print(f"  {s}: 새로 {n:>4}줄 / {c:>6}자   (씬 전체 {tot}행 중 {n / tot:.0%})")
print(f"\n손볼 씬 총 {len(rewrite_scenes)}개")
