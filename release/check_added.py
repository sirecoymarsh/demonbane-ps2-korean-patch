"""추가 시나리오 번역 검사 — 빠진 조각·남는 조각·괄호 짝·일본어 잔존·글꼴 밖 글자."""
import json, os, re, sys, collections
sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"P:\AI\demonbane-ps2-kr"
skel = {}
for l in open(os.path.join(ROOT, r"work\added\skeleton.tsv"), encoding="utf-8").read().split("\n")[1:]:
    if l:
        k, spk, jp = l.split("\t")
        skel[k] = (spk, jp)
ko = {}
dup = []
for fn in sorted(os.listdir(os.path.join(ROOT, r"work\added\ko"))):
    if fn.startswith("_"):
        continue
    src = fn[:-4]
    for n, l in enumerate(open(os.path.join(ROOT, r"work\added\ko", fn), encoding="utf-8").read().split("\n"), 1):
        if not l.strip():
            continue
        pos, text = l.split("\t", 1)
        line, _, seg = pos.partition(":")
        key = f"{src}:{int(line)}:{int(seg or 0)}"
        if key in ko:
            dup.append(key)
        ko[key] = text
carrier = json.load(open(os.path.join(ROOT, r"work\ref\ps2_carrier_map.json"), encoding="utf-8"))
inside = set(open(os.path.join(ROOT, r"work\font_ko\inside.txt"), "rb").read().decode("cp932"))
ENGINE_ASCII = set(" !?'._+") | set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
HALF = {"\uff61": "。", "\uff64": "、"}
JPCHK = re.compile(r"[\u3040-\u309f\u30a0-\u30fa\u30fc-\u30ff\u3400-\u9fff]")
missing = [k for k in skel if k not in ko]
extra = [k for k in ko if k not in skel]
bad = collections.defaultdict(list)
for k, t in ko.items():
    if k not in skel:
        continue
    jp = skel[k][1]
    body = re.sub(r"<[^>]*>", "", t)
    for a in "「」『』":
        if jp.count(a) != body.count(a):
            bad["bracket"].append((k, jp, t)); break
    if JPCHK.search(body):
        bad["japanese"].append((k, t))
    for ch in body:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            if ch not in carrier:
                bad["no_carrier"].append((k, ch))
        elif ch in HALF:
            continue
        elif ord(ch) < 0x80:
            if ch not in ENGINE_ASCII:
                bad["ascii"].append((k, ch))
        elif ch not in inside:
            bad["not_in_font"].append((k, ch))
print(f"skeleton {len(skel)} / translated {len(ko)} / missing {len(missing)} / extra {len(extra)} / dup {len(dup)}")
for k in missing: print("  MISSING", k, skel[k])
for k in extra: print("  EXTRA", k, ko[k][:40])
for k in dup: print("  DUP", k)
for kind, items in bad.items():
    print(f"== {kind}: {len(items)}")
    for it in items[:30]: print("  ", it)

# 줄 번호가 하나 밀려 다른 줄 내용이 들어간 경우를 잡는다: 한↔일 글자 수 비율이 크게 벗어난 칸
def plain(s):
    return re.sub(r"<[^>]*>|[\s　「」『』…―！？!?､｡、。，．・（）()]", "", s)
odd = []
for k, t in ko.items():
    if k in skel:
        a, b = len(plain(skel[k][1])), len(plain(t))
        if a >= 3 and not (0.55 <= b / a <= 2.3):
            odd.append((round(b / a, 2), k, skel[k][1], t))
print(f"== length ratio outliers: {len(odd)}")
for o in sorted(odd): print("  ", o)

# 고유명사 짝(원문에 있으면 번역에도 있어야) + 문장 끝 부호 갈래 대조
NAMES = {"イタクァ": "이타콰", "クトゥグア": "크투가", "アル": "알", "九郎": "쿠로", "デモンベイン": "데몬베인",
         "瑠璃": "루리", "ウィンフィールド": "윈필드", "マスターテリオン": "마스터 테리온", "鋼造": "코조",
         "アーカム": "아컴", "ブラックロッジ": "블랙로지", "ネス": "네스", "ページモンスター": "페이지 몬스터",
         "ウェンディゴ": "웬디고", "ネクロノミコン": "네크로노미콘", "リベル・レギス": "리베르 레기스", "アリゾナ": "애리조나"}
def ending(s):
    s = re.sub(r"<[^>]*>", "", s).rstrip(" 　」』")
    if not s: return "?"
    c = s[-1]
    return {"？": "Q", "?": "Q", "！": "E", "!": "E", "。": "P", "｡": "P", "…": "D", "―": "H", "、": "C", "､": "C", "♪": "M"}.get(c, "T")
names_bad, end_bad = [], []
for k, t in ko.items():
    jp = skel[k][1]
    for j, kr in NAMES.items():
        if j in jp and kr not in t and not (j == "アル" and ("アルちゃん" in jp or "アル・アジフ" in jp)):
            names_bad.append((k, j, jp[:40], t[:40]))
    a, b = ending(jp), ending(t)
    if a != b and not (a in "PT" and b in "PT"):
        end_bad.append((k, a, b, jp[-25:], t[-25:]))
print(f"== name anchors missing: {len(names_bad)}")
for x in names_bad: print("  ", x)
print(f"== ending class differs: {len(end_bad)}")
for x in end_bad: print("  ", x)
