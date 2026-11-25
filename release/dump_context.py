"""추가 시나리오(정렬표 NEW) 원문을 장면 문맥과 함께 뽑는다 — 번역 작업용 읽기 자료."""
import csv, os, re, sys
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"P:\AI\demonbane-ps2-kr"
TAG = re.compile(r"<[^>\n]*>")
RUBY = re.compile(r'<R\s+TEXT="([^"]*)">([^<]*)</R>', re.I)
ATTR = re.compile(r'(\w+)="([^"]*)"')

def strip_comment(line):
    depth = 0
    for i, ch in enumerate(line):
        if ch == "<": depth += 1
        elif ch == ">": depth = max(0, depth - 1)
        elif ch == "/" and depth == 0 and line.startswith("//", i): return line[:i]
    return line

rows = list(csv.reader(open(os.path.join(ROOT, r"work\ref\aligned_final.tsv"), encoding="utf-8"),
                       delimiter="\t", quoting=csv.QUOTE_NONE))[1:]
new = {}
for idx, r in enumerate(rows, 1):
    r += [""] * (7 - len(r))
    if r[5] == "NEW":
        new.setdefault(r[1], []).append((idx, int(r[2]), r[6]))

def condensed(fn, lo=1, hi=10**9):
    from skcodec import decode
    out = []
    txt = open(os.path.join(ROOT, "work", "script_dec", fn), "rb").read().decode("cp932", "replace").split("\n")
    starts = {ln: idx for idx, ln, _ in new.get(fn, [])}
    pending = ""
    for no, raw in enumerate(txt, 1):
        if not (lo <= no <= hi): continue
        line = strip_comment(raw.rstrip("\r"))
        notes = []
        for t in TAG.findall(line):
            name = t[1:].split()[0].rstrip(">").upper() if len(t) > 2 else ""
            a = dict((k.upper(), v) for k, v in ATTR.findall(t))
            if name == "VOICE": notes.append("VOICE:" + a.get("NAME", ""))
            elif name in ("BACKGROUND", "BGMOVIE", "MOVIE"): notes.append(name + ":" + a.get("SRC", ""))
            elif name in ("FACE", "BUSTUP"): notes.append(name + ":" + a.get("NAME", "") + "/" + a.get("FACE", a.get("SRC", "")))
            elif name in ("CHOICE", "SELECT", "A", "ENDING", "END"): notes.append(t)
            elif name == "K": notes.append("<K>")
        body = RUBY.sub(lambda m: f"{m.group(2)}({m.group(1)})", line)
        body = TAG.sub(lambda m: "<K>" if m.group(0).upper() == "<K>" else "", body).strip()
        mark = f"#{starts[no]} " if no in starts else ""
        v = [n for n in notes if n.startswith("VOICE:")]
        if v: pending = v[-1][6:]
        if body.replace("<K>", "").strip():
            spk = pending if body.lstrip("　 ")[:1] in "「『（" or v else ""
            out.append(f"{no}: {mark}{'['+spk+'] ' if spk else ''}{body}")
            if body.lstrip("　 ")[:1] in "「『（" or v: pending = ""
        else:
            keep = [n for n in notes if not n.startswith("VOICE:") and n != "<K>" and not n.startswith("FACE:")]
            if keep: out.append(f"{no}: ({' '.join(keep)})")
    return out

sys.path.insert(0, os.path.join(ROOT, "tools"))
for fn in ["D0751.txt", "D0752.txt", "D0753.txt", "D0754.txt", "D0755.txt", "D0756.txt", "ep_ruri02a.txt"]:
    with open(os.path.join(ROOT, "work", "added", "src_" + fn), "w", encoding="utf-8") as f:
        f.write("\n".join(condensed(fn)) + "\n")
with open(os.path.join(ROOT, "work", "added", "src_singles.txt"), "w", encoding="utf-8") as f:
    for fn in ["D0801al.txt", "D1202ru.txt", "D1303le.txt", "D1514al.txt"]:
        for idx, ln, lines in new[fn]:
            f.write(f"== {fn} #{idx} line {ln} ==\n" + "\n".join(condensed(fn, ln - 12, ln + 6)) + "\n")
for fn in sorted(os.listdir(os.path.join(ROOT, "work", "added"))):
    p = os.path.join(ROOT, "work", "added", fn); print(fn, os.path.getsize(p))
