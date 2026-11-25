"""PS2 원문을 줄 단위로 정규화해 뽑는다 — 어떤 판본의 번역본이든 여기에 붙인다.

출력 1: lines.tsv   file / lineno / kind / speaker / voice / text
출력 2: index.json   정규화 키 -> [(file, lineno), ...]   (판본 간 매칭용)

kind:  say  = 「」로 시작하는 대사
       narr = 지문 (전각 공백 들여쓰기 포함)
       cmd  = 명령만 있는 줄 (번역 대상 아님)
"""
import os
import re
import json
import hashlib
import unicodedata
from skcodec import decode

SRC = r"P:\AI\demonbane-ps2-kr\work\script"
OUT = r"P:\AI\demonbane-ps2-kr\work\ref"
os.makedirs(OUT, exist_ok=True)

TAG = re.compile(r"<[^>\n]*>")
VOICE = re.compile(r'<VOICE\s+NAME="([^"]*)"\s+SRC="([^"]*)"', re.I)
RUBY = re.compile(r'<R\s+TEXT="[^"]*">([^<]*)</R>', re.I)

SKIP = {"vssver.scc"}


def strip_comment(line):
    """태그 밖의 // 부터는 주석. `<BACKGROUND ...>//` 처럼 뒤에 붙는 형태가 흔하다."""
    depth = 0
    for i, ch in enumerate(line):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif ch == "/" and depth == 0 and line.startswith("//", i):
            return line[:i]
    return line


def normalize(s):
    """판본 간 비교용 키. 루비/태그/공백/이체자 차이를 흡수한다."""
    s = RUBY.sub(r"\1", s)
    s = TAG.sub("", s)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\s　]+", "", s)
    return s


rows = []
index = {}
for fn in sorted(os.listdir(SRC)):
    if fn in SKIP:
        continue
    txt = decode(open(os.path.join(SRC, fn), "rb").read()).decode("cp932", "replace")
    speaker = voice = ""
    for no, raw in enumerate(txt.split("\n"), 1):
        line = strip_comment(raw.rstrip("\r"))
        mv = VOICE.search(line)
        if mv:
            speaker, voice = mv.group(1), mv.group(2)
        stripped = line.strip()
        body = TAG.sub("", line).strip()
        if not body:
            if stripped:
                rows.append((fn, no, "cmd", "", "", ""))
            continue
        kind = "say" if body[0] in "「『（" else "narr"
        rows.append((fn, no, kind, speaker if kind == "say" else "", voice if kind == "say" else "", body))
        key = normalize(line)
        if key:
            index.setdefault(hashlib.sha1(key.encode()).hexdigest()[:16], []).append([fn, no])
        if kind == "say":
            speaker = voice = ""

with open(os.path.join(OUT, "lines.tsv"), "w", encoding="utf-8", newline="") as f:
    f.write("file\tline\tkind\tspeaker\tvoice\ttext\n")
    for r in rows:
        f.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")

with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False)

trans = [r for r in rows if r[2] in ("say", "narr")]
say = [r for r in trans if r[2] == "say"]
dupe = sum(len(v) - 1 for v in index.values() if len(v) > 1)
print(f"files           : {len({r[0] for r in rows})}")
print(f"translatable    : {len(trans):,}  (say {len(say):,} / narr {len(trans) - len(say):,})")
print(f"characters      : {sum(len(r[5]) for r in trans):,}")
print(f"unique keys     : {len(index):,}   (중복 재사용 줄 {dupe:,})")
print(f"speakers        : {len({r[3] for r in say if r[3]})}")
print(f"-> {OUT}\\lines.tsv , index.json")
