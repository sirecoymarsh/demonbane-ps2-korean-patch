"""릴리스 빌드 — 코덱스 교정 정렬표(09-05 staged) + 추가 시나리오(클로드 직접 번역, 11-01)를 대본에 넣는다.

    python build_release.py --check                       # 대본 팩만 만들어 전수 검사(ISO 안 건드림)
    python build_release.py <원본 iso> <출력 iso>          # 원본을 출력으로 복사한 뒤 사본에 심는다

예전 build_full.py 와 다른 점(코덱스 09-05 build_audit 지적 + 11-01 확인):
 1) 한 줄에 단위가 여럿(<K> 로 갈림)이면 단위마다 제 조각에 넣는다. 예전엔 줄 번호 사전이 앞 단위를 덮어썼다.
 2) 여러 줄에 걸친 단위는 첫 조각에 전문을 넣고 나머지 조각은 비운다. 글자만 있던 줄은 지운다.
    예전엔 뒤 줄의 일본어가 그대로 남아 캐리어 글꼴로 깨져 보였다.
 3) 반각 기호: 게임이 전각으로 바꿔 그리는 것(공백 ! ? ' . _ + 영숫자, s_dbRunningScript·dbGetStringMultiByte)만
    남기고 나머지(, ~ - ( ) 등)는 전각으로 바꾼다. 글꼴 목록(inside.txt)에 없는 글자는 보고한다.
 4) 넣은 뒤 대본을 다시 풀어 모든 단위·조각이 제자리에 한국어로 들어갔는지, 일본어가 남은 조각이 어디인지 전수 대조한다.
 5) 추가 시나리오 7개 파일은 조각 단위 번역(work/added/ko/*.tsv)을 쓴다 — 원작의 클릭 대기·줄바꿈 자리가 그대로 남는다.
"""
import collections
import csv
import json
import os
import re
import shutil
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from digpck import parse, pack
from skcodec import decode, encode
from segs import split_runs, run_text, replace_run, JP

TABLE = r"P:\AI\Codex\projects\demonbane-ps2-kr-audit\handoff-fable\sessions\20260905-codex-repair\staged\work\ref\aligned_final.tsv"
ADDED = os.path.join(ROOT, r"work\added\ko")
LIMIT = 81920
OUT_DIR = os.path.join(HERE, "out")

CARRIER = json.load(open(os.path.join(ROOT, r"work\ref\ps2_carrier_map.json"), encoding="utf-8"))
UNCARRIER = {v: k for k, v in CARRIER.items()}
# 글꼴: 11-01 칸 계산을 고쳐 다시 그린 판(release/repaint_font_v3.py). 옛 work/font_ko 는 732음절이 한자로 깨졌다.
FONT_KO = os.path.join(ROOT, r"work\font_ko_v3")
INSIDE = set(open(os.path.join(FONT_KO, "inside.txt"), "rb").read().decode("cp932"))
ENGINE_ASCII = set(" !?'._+") | set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
TO_FULL = {",": "，", "-": "－", "~": "～", "(": "（", ")": "）", ":": "：", ";": "；", "%": "％", "&": "＆",
           "*": "＊", "=": "＝", "/": "／", "@": "＠", "[": "［", "]": "］", '"': "”", "$": "＄",
           "\uff61": "。", "\uff64": "、", "\u301c": "～", "\u2014": "―", "\u2013": "－", "\u00b7": "・",
           "\u2018": "’", "\u2025": "…", "\u2026": "…"}
JAMO_WORD = {"ㄱ": "기역"}
RUBY_PC = re.compile(r'<RUBY\s+text="([^"]*)"\s*>(.*?)</RUBY\s*>', re.I | re.S)
TAGSPLIT = re.compile(r"(<[^>\n]*>)")
KANA_KANJI = re.compile(r"[\u3041-\u3096\u30a1-\u30fa\u30fc\u3400-\u9fff]")

stats = collections.Counter()
charlog = collections.Counter()
missing_carrier = collections.Counter()
not_in_font = collections.Counter()


def to_carrier(s):
    """한국어 한 덩어리 -> 게임에 넣을 글. 루비는 PS2 꼴로, 한글은 캐리어 한자로, 기호는 그릴 수 있는 꼴로."""
    s = RUBY_PC.sub(lambda m: f'<r text="{m.group(1)}">{m.group(2)}</r>', s)
    s = s.replace("<br>", "").replace("<BR>", "")
    out = []
    for p in TAGSPLIT.split(s):
        if p.startswith("<"):
            out.append(p if p.lower().startswith(("<r ", "</r")) else "")
            continue
        for ch in p:
            o = ord(ch)
            if 0xAC00 <= o <= 0xD7A3:
                c = CARRIER.get(ch)
                if c is None:
                    missing_carrier[ch] += 1
                    c = "？"
                out.append(c)
            elif ch in ENGINE_ASCII:
                out.append(ch)
            elif ch in TO_FULL:
                charlog[f"{ch!r}->{TO_FULL[ch]}"] += 1
                out.append(TO_FULL[ch])
            elif ch in INSIDE:
                out.append(ch)
            elif ch in JAMO_WORD:
                # 낱자(ㄱ)는 cp932 에 없고 글꼴에도 없다 — 이름으로 풀어 쓴다(D1409ru:275 「ㄱ」자)
                charlog[f"{ch!r}->{JAMO_WORD[ch]}"] += 1
                out.append("".join(CARRIER[c] for c in JAMO_WORD[ch]))
            else:
                not_in_font[ch] += 1
                try:
                    ch.encode("cp932")
                    out.append(ch)
                except UnicodeEncodeError:
                    out.append("？")
    return "".join(out).strip()


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"\s+", "", s)


CONTENT = re.compile(r"[ぁ-ゖァ-ヺー㐀-鿿A-Za-z0-9]")


def content(s):
    """정렬표 원문과 대본 조각을 맞출 때 쓰는 꼴: 가나·한자·영숫자만(기호·괄호·공백은 판본마다 흔들린다)."""
    return "".join(CONTENT.findall(unicodedata.normalize("NFKC", s)))


# 정렬 도구가 앞 파일의 끝 줄과 다음 파일의 첫 줄(루트 갈래)을 한 단위로 묶은 10곳.
# 한국어는 고치지 않고 나누기만 한다(각 조각이 원래 한국어의 일부인지 load_table 이 확인).
# 기호뿐인 쪽(「…………」·＊＊＊)은 원문 그대로 둔다.
SPLIT = {
    23938: [("D1105ru.txt", [7], "千年の悠久を、嵐の様に駈け抜けて来た。", "천년의 유구함을､ 폭풍처럼 달려왔다｡")],
    25373: [("D1109le.txt", [428], "（メタトロンを捕らえよ的会話必要）", "（메타트론을 붙잡아라 식의 대화 필요）"),
            ("D1109ru.txt", [5], "――デモンベイン出撃より１２分前。格納庫。", "――데몬베인 출격 12분 전｡ 격납고｡")],
    27532: [("D1205al.txt", [200], "「……おのれ！」", "「……이 자식!」"),
            ("D1205le.txt", [7], "作戦司令室。", "작전사령실｡")],
    29672: [("D1211le.txt", [378], "魔を断つ剣は、決して折らせはしないと。", "마를 베는 검은 결코 부러뜨리게 하지 않겠다고｡"),
            ("D1211ru.txt", [11], "「…………ッ」", "「…………읏」")],
    31596: [("D1303le.txt", [355], "（……九郎ちゃん！）", "（……쿠로 군!）"),
            ("D1303ru.txt", [7], "圧し掛かる闇に耐え切れなくなったかのように、九郎は蹲った。",
             "짓누르는 어둠을 견디다 못한 듯､ 쿠로는 쪼그려 앉았다｡")],
    37186: [("D1404le.txt", [528], "「約束するよ」", "「약속할게」"),
            ("D1404ru.txt", [7], "アンチクロスの襲撃と、クトゥルーによる破壊とで、満身創痍の覇道基地だったが、"
             "それでも全職員、全施設をフル稼働させ、来たるべき決戦の準備を急いでいた。",
             "안티크로스의 습격과 크툴루에 의한 파괴로 만신창이가 된 하도 기지였지만､ "
             "그래도 전 직원과 전 시설을 풀가동해 다가올 결전의 준비를 서두르고 있었다｡")],
    8635: [("D0704+.txt", [1128], "熱くとろけた視線を止めれ。", "뜨겁게 녹아내린 시선을 거두어라｡"),
           ("D0704.txt", [26], "「――仰る通りです。彼らはリゾート計画に反対する、インスマウスの住人達です」",
            "「――말씀하신 대로입니다｡ 저들은 리조트 계획에 반대하는､ 인스머스 주민들입니다」")],
    19401: [("D0907al.txt", [464], "「ぐあああああああああっ！」", "「구아아아아아아아아앗!」"),
            ("D0907le.txt", [12], "「ティマイオス！　クリティアス！　開放！」", "「티마이오스! 크리티아스! 개방!」")],
    9621: [("D0710le.txt", [1108, 1109], "「きゃああああ！？ 九郎ちゃんっ！」", "「꺄아아아아!? 쿠로 군!」")],
    11131: [("D0715le.txt", [322], "――今はまだ。", "――지금은 아직｡")],
}


def load_table():
    units = collections.defaultdict(list)
    rows = list(csv.reader(open(TABLE, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))[1:]
    for idx, r in enumerate(rows):
        r = r + [""] * (7 - len(r))
        scene, fn, line, jp, ko, status, lines = r[:7]
        if not fn or not line or not ko:
            continue
        if idx in SPLIT:
            for sfn, slines, sjp, sko in SPLIT[idx]:
                assert sko in ko, (idx, sko)
                units[sfn.upper()].append(dict(id=idx, file=sfn, line=slines[0], jp=sjp, ko=sko,
                                               status=status + "+SPLIT", lines=slines))
            stats["units_split_across_files"] += 1
            continue
        lns = sorted({int(x.rsplit(":", 1)[1]) for x in lines.split(",")
                      if ":" in x and x.rsplit(":", 1)[0].upper() == fn.upper()}) or [int(line)]
        units[fn.upper()].append(dict(id=idx, file=fn, line=int(line), jp=jp, ko=ko, status=status, lines=lns))
    for fn in units:
        units[fn].sort(key=lambda u: (u["line"], u["id"]))
    return units


def load_added():
    seg = {}
    for fn in os.listdir(ADDED):
        if fn.startswith("_") or not fn.endswith(".tsv"):
            continue
        src = fn[:-4].upper()
        m = {}
        for l in open(os.path.join(ADDED, fn), encoding="utf-8").read().split("\n"):
            if not l.strip():
                continue
            pos, text = l.split("\t", 1)
            line, _, s = pos.partition(":")
            m[(int(line), int(s or 0))] = text
        seg[src] = m
    single = {}
    p = os.path.join(ADDED, "_singles.tsv")
    for l in open(p, encoding="utf-8").read().split("\n"):
        if l.strip():
            key, text = l.split("\t", 1)
            fn, line = key.rsplit(":", 1)
            single[(fn.upper(), int(line))] = text
    return seg, single


def load_choices():
    """선택지 글은 태그 속성(<CHOICE ... TEXT="…">)이라 조각 치환에 안 걸린다 — 따로 바꾼다(11-01 클로드 번역)."""
    out = collections.defaultdict(dict)
    for l in open(os.path.join(ADDED, "_choices.tsv"), encoding="utf-8").read().split("\n"):
        if l.strip():
            key, jp, ko = l.split("\t")
            fn, line = key.rsplit(":", 1)
            out[fn.upper()][int(line)] = (jp, ko)
    return out


CHOICE_TEXT = re.compile(r'(<CHOICE\b[^>]*?\bTEXT\s*=\s*")([^"]*)(")', re.I)


def apply_choices(name, text, table, report):
    lines = text.split("\n")
    for ln, (jp, ko) in table.items():
        line = lines[ln - 1]
        m = CHOICE_TEXT.search(line)
        if not m or m.group(2) != jp:
            report["choice_missing"].append(f"{name}:{ln}")
            continue
        lines[ln - 1] = line[:m.start(2)] + to_carrier(ko) + line[m.end(2):]
        stats["choices_done"] += 1
    return "\n".join(lines)


def add_check_menu(text):
    """점검용 판(--check-menu)만: 새 게임 첫머리(D0100)의 프롤로그 영상을 건너뛰고 점검 선택지를 띄운다.
    정식판 D0100 은 영상(prg) 뒤 15줄의 <A HREF="d0101.txt"> 로 바로 넘어가고, 뒤의 선택지 묶음(28~29줄)은 안 지나간다.
    루리 갈래는 실제 입구(ep_ruri01 1177줄 「いや……まだだ！」 → ep_ruri02a.txt#トゥルー)와 같은 곳으로 들어간다.
    메뉴=true 는 8월 점프 시험에서 목적지 장면이 타이틀로 되돌아가지 않게 하려고 세운 전역 플래그다."""
    movie = '<MOVIE SRC="prg">'
    jump = '<A HREF="d0101.txt" OPERATOR="">'
    assert text.count(movie) >= 1 and text.count(jump) >= 1
    items = [("d0751.txt", "【점검】 7장 추가 장면"),
             ("ep_ruri02a.txt#トゥルー", "【점검】 루리 진엔딩 갈래"),
             ("d0101.txt", "처음부터 시작")]
    block = ['<CALC WORKNAME="メニュー" OPERATOR="true" mode="global">'] + \
            [f'<CHOICE HREF="{h}" TEXT="{to_carrier(t)}" OPERATOR="">' for h, t in items]
    text = text.replace(movie, "", 1)
    # 원작 선택지 묶음은 늘 빈 줄로 끝난다(D0103 676~679, D0709 854~858) — 같은 꼴로
    return text.replace(jump, "\r\n".join(block) + "\r\n\r\n\r", 1)


def build_script(name, text, units, seg_map, report):
    """한 대본 파일. 돌려주는 값: 새 글, 기대값 목록 [(줄, 조각, 기대 글)]"""
    lines = text.split("\n")
    parsed = []
    for raw in lines:
        cr = raw.endswith("\r")
        body = raw[:-1] if cr else raw
        pieces, runs, tail = split_runs(body, all_runs=seg_map is None)
        parsed.append(dict(cr=cr, pieces=pieces, runs=runs, tail=tail, orig=body,
                           new={}, cleared=set()))
    expect = []

    if seg_map is not None:
        for no, P in enumerate(parsed, 1):
            for k in range(len(P["runs"])):
                if (no, k) not in seg_map:
                    report["seg_missing"].append(f"{name}:{no}:{k}")
                else:
                    P["new"][k] = to_carrier(seg_map[(no, k)])
                    expect.append((no, k, P["new"][k]))
        for (no, k) in seg_map:
            if no > len(parsed) or k >= len(parsed[no - 1]["runs"]):
                report["seg_extra"].append(f"{name}:{no}:{k}")
    else:
        ptr = collections.defaultdict(int)
        for u in units:
            # 비교는 두 겹: 내용 글자(가나·한자·영숫자)로 단위가 끝났는지 보고,
            # 기호뿐인 조각(「!?」·「…………」)은 단위 원문(공백 뺀 꼴)에 실제로 들어 있을 때만 이 단위에 묶는다.
            target = content(u["jp"])
            rem = norm(u["jp"])
            acc, chosen = "", []
            for ln in u["lines"]:
                if ln - 1 >= len(parsed):
                    break
                runs = parsed[ln - 1]["runs"]
                while ptr[ln] < len(runs):
                    a, b = runs[ptr[ln]]
                    raw_t = run_text(parsed[ln - 1]["pieces"], a, b)
                    t, tn = content(raw_t), norm(raw_t)
                    if t:
                        if acc == target or not target.startswith(acc + t):
                            break
                        acc += t
                    else:
                        pos = rem.find(tn)
                        if not tn or pos < 0:
                            break
                    pos = rem.find(tn)
                    if pos >= 0:
                        rem = rem[pos + len(tn):]
                    chosen.append((ln, ptr[ln]))
                    ptr[ln] += 1
                if acc == target and not rem:
                    break
            if not target:
                stats["units_symbol_only"] += 1      # 기호뿐인 단위: 묶인 조각은 원문 그대로 둔다
                continue
            if acc != target or not chosen:
                report["unit_unmatched"].append((u["id"], name, u["line"], u["jp"][:40], acc[:40]))
                for ln, k in chosen:                 # 못 맞춘 단위가 집어 든 조각은 되돌린다
                    ptr[ln] = min(ptr[ln], k)
                continue
            first = True
            for ln, k in chosen:
                if first:
                    parsed[ln - 1]["new"][k] = to_carrier(u["ko"])
                    expect.append((ln, k, parsed[ln - 1]["new"][k]))
                    first = False
                else:
                    parsed[ln - 1]["new"][k] = ""
                    parsed[ln - 1]["cleared"].add(k)
                    expect.append((ln, k, ""))
            stats["units_placed"] += 1
            if len(chosen) > 1:
                stats["units_multi_run"] += 1

    out_lines = []
    for no, P in enumerate(parsed, 1):
        if not P["new"]:
            out_lines.append(P["orig"] + ("\r" if P["cr"] else ""))
            continue
        pieces = list(P["pieces"])
        # 뒤 조각부터 바꿔야 앞 조각의 번호가 안 밀린다
        for k in sorted(P["new"], reverse=True):
            a, b = P["runs"][k]
            pieces = replace_run(pieces, a, b, P["new"][k])
        body = "".join(pieces)
        only_cleared = all(k in P["cleared"] for k in P["new"])
        has_tag = any(p.startswith("<") for p in pieces)
        if only_cleared and not has_tag and not body.strip(" 　") and not P["tail"].strip():
            stats["lines_dropped"] += 1
            expect = [e for e in expect if e[0] != no]
            continue
        if only_cleared and has_tag:
            stats["cleared_lines_kept_for_tags"] += 1
        out_lines.append(body + P["tail"] + ("\r" if P["cr"] else ""))
    return "\n".join(out_lines), expect


def verify_script(name, newtext, expect, report):
    """다시 풀어서 대조: 기대한 조각에 기대한 글이 있는가, 일본어가 남은 조각은 어디인가."""
    lines = newtext.split("\n")
    got = {}
    residual = []
    for no, raw in enumerate(lines, 1):
        pieces, runs, tail = split_runs(raw.rstrip("\r"), all_runs=True)
        for k, (a, b) in enumerate(runs):
            t = run_text(pieces, a, b)
            got[(no, k)] = t
            back = "".join(UNCARRIER.get(c, c) for c in t)
            if KANA_KANJI.search(back):
                residual.append((no, back[:50]))
    return got, residual


def main():
    args = sys.argv[1:]
    global OUT_DIR
    check_only = "--check" in args
    check_menu = "--check-menu" in args
    args = [a for a in args if a not in ("--check", "--check-menu")]
    if check_menu:
        OUT_DIR = os.path.join(HERE, "out_check")
    units_by_file = load_table()
    seg, single = load_added()
    choices = load_choices()
    for (fn, ln), text in single.items():
        hit = [u for u in units_by_file.get(fn, []) if u["line"] == ln]
        assert len(hit) == 1, (fn, ln, len(hit))
        hit[0]["ko"] = text
        hit[0]["status"] = "CLAUDE_1101"

    blob, entries, base = parse(os.path.join(ROOT, r"extract\SCRIPT\SCRIPT.PCK"))
    report = collections.defaultdict(list)
    newdata, residual_all, over = [], {}, []
    changed = 0
    for e in entries:
        raw = blob[base + e["offset"]: base + e["offset"] + e["size"]]
        name = e["name"]
        stem = name.upper()
        if not name.lower().endswith((".txt", ".nps")):
            newdata.append((name, raw))
            continue
        text = decode(raw).decode("cp932")
        if stem in choices:
            text = apply_choices(name, text, choices[stem], report)
        seg_map = seg.get(stem)
        units = units_by_file.get(stem, [])
        if seg_map is None and not units and stem in choices:
            newdata.append((name, encode(text.encode("cp932"))))
            changed += 1
            continue
        if seg_map is None and not units:
            newdata.append((name, raw))
            _, res = verify_script(name, text, [], report)
            if res:
                residual_all[name] = res
            continue
        newtext, expect = build_script(name, text, units, seg_map, report)
        if check_menu and stem == "D0100.TXT":
            newtext = add_check_menu(newtext)
        got, res = verify_script(name, newtext, expect, report)
        # 기대값 대조는 줄이 지워진 만큼 번호가 밀리므로, 지운 줄을 뺀 순서로 다시 맞춘다
        exp_texts = [re.sub(r"<[^>]*>", "", t).strip(" 　") for (_, _, t) in sorted(expect) if t.strip(" 　")]
        got_texts = [t.strip(" 　") for (_, t) in sorted(got.items()) if t.strip(" 　")]
        if collections.Counter(exp_texts) - collections.Counter(got_texts):
            report["roundtrip_missing"].append(name)
        if res:
            residual_all[name] = res
        enc = newtext.encode("cp932")
        out = encode(enc)
        if len(out) > LIMIT:
            over.append((name, len(out)))
        newdata.append((name, out))
        changed += 1

    newpck = pack(newdata, blob)
    print(f"대본 적용: {changed}파일 / 단위 {stats['units_placed']:,}개(여러 조각 {stats['units_multi_run']:,}) / "
          f"추가 시나리오 {len(seg)}파일 + 단일 {len(single)}줄")
    print(f"  글자만 있던 뒤 줄 지움 {stats['lines_dropped']:,} / 태그 때문에 남긴 빈 줄 {stats['cleared_lines_kept_for_tags']:,}")
    print(f"  못 맞춘 단위 {len(report['unit_unmatched'])} / 조각 누락 {len(report['seg_missing'])} / 조각 남음 {len(report['seg_extra'])} / "
          f"역추출 불일치 파일 {len(report['roundtrip_missing'])}")
    print(f"  선택지 {stats['choices_done']}개 바꿈 / 못 찾음 {len(report['choice_missing'])} {report['choice_missing'][:5]}")
    print(f"  캐리어 없는 음절 {sum(missing_carrier.values())}회 {dict(missing_carrier.most_common(10))}")
    print(f"  글꼴 밖 글자 {sum(not_in_font.values())}회 {dict(not_in_font.most_common(15))}")
    print(f"  기호 바꿈 {dict(charlog.most_common(20))}")
    print(f"  파일당 상한 초과 {over}")
    res_files = sorted(residual_all.items(), key=lambda kv: -len(kv[1]))
    print(f"  일본어가 남은 조각: {sum(len(v) for v in residual_all.values()):,}개 / {len(residual_all)}파일")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "report.txt"), "w", encoding="utf-8") as f:
        f.write("# 못 맞춘 단위 (id, 파일, 줄, 원문, 맞춘 데까지)\n")
        for x in report["unit_unmatched"]:
            f.write("\t".join(map(str, x)) + "\n")
        f.write("\n# 조각 누락/남음\n" + "\n".join(report["seg_missing"] + report["seg_extra"]) + "\n")
        f.write("\n# 역추출 불일치 파일\n" + "\n".join(report["roundtrip_missing"]) + "\n")
        f.write("\n# 일본어가 남은 조각 (파일별)\n")
        for name, items in res_files:
            f.write(f"## {name} {len(items)}\n")
            for no, t in items[:400]:
                f.write(f"{no}\t{t}\n")
    print(f"  보고서 -> {os.path.join(OUT_DIR, 'report.txt')}")
    for name, items in res_files[:25]:
        print(f"    {name:<18} {len(items)}")

    fblob, fentries, fbase = parse(os.path.join(ROOT, r"extract\FONT\FONT.PCK"))
    fdir = FONT_KO
    newfont = pack([(e["name"], open(os.path.join(fdir, e["name"]), "rb").read()) for e in fentries], fblob)
    open(os.path.join(OUT_DIR, "SCRIPT.PCK"), "wb").write(newpck)
    open(os.path.join(OUT_DIR, "FONT.PCK"), "wb").write(newfont)
    print(f"  SCRIPT.PCK {len(newpck):,}B / FONT.PCK {len(newfont):,}B -> {OUT_DIR}")
    if check_only:
        return
    src_iso, dst_iso = args[0], args[1]
    assert os.path.abspath(src_iso) != os.path.abspath(dst_iso), "원본 ISO 에 직접 쓰지 않는다"
    print(f"원본 복사: {src_iso} -> {dst_iso}")
    shutil.copyfile(src_iso, dst_iso)
    from iso_patch import IsoPatcher
    p = IsoPatcher(dst_iso)
    for path, payload in (("/SCRIPT/SCRIPT.PCK", newpck), ("/FONT/FONT.PCK", newfont)):
        how, lba, size, pad = p.replace(path, payload)
        print(f"  {path:<20} {how}  lba={lba} size={size:,}")
    print(f"  volumeSpace -> {p.vol_sectors} sectors ({p.vol_sectors * 2048:,}B)")
    p.close()
    print(f"완료 -> {dst_iso} ({os.path.getsize(dst_iso):,}B)")


if __name__ == "__main__":
    main()
