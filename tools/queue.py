"""판정 대기열. 판정 파일이 없거나 게이트를 못 넘는 패킷을 인덱스 순서로 N개씩 묶어 낸다.

    python queue.py [--per 6] [--chunks 16]
"""
import json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"P:\AI\demonbane-ps2-kr"
PK = os.path.join(ROOT, "work", "packets"); VD = os.path.join(ROOT, "work", "verdicts")
a = sys.argv[1:]
per = int(a[a.index("--per") + 1]) if "--per" in a else 6
chunks = int(a[a.index("--chunks") + 1]) if "--chunks" in a else 16
idx = json.load(open(os.path.join(PK, "_index.json"), encoding="utf-8"))
done = {f[:-5] for f in os.listdir(VD) if f.endswith(".json")}
skip_f = os.path.join(VD, "_skip.tsv")            # 보류 패킷(사용자 결정 대기)은 대기열에서 뺀다
skip = {ln.split("	")[0].strip() for ln in open(skip_f, encoding="utf-8") if ln.strip()} if os.path.exists(skip_f) else set()
# 이미 있는 판정 중 게이트 실패한 것은 다시 대기열에
bad = set()
if done:
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_verdicts.py")] + sorted(done),
                       capture_output=True, text=True, encoding="utf-8")
    for ln in r.stdout.splitlines():
        if ln.startswith("[FAIL]"):
            bad.add(ln.split()[1].rstrip(":"))
pending = [i["packet"] for i in idx if (i["packet"] not in done or i["packet"] in bad) and i["packet"] not in skip]
print(f"전체 {len(idx)} / 완료 {len(done) - len(bad)} / 게이트실패 {len(bad)} / 보류 {len(skip)} / 남음 {len(pending)}")
out = [pending[i:i + per] for i in range(0, len(pending), per)][:chunks]
for c in out:
    print(" ".join(c))
