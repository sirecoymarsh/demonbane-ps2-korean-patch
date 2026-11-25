"""PS2 대본 한 줄을 '글 조각(run)'으로 나눈다 — 번역 단위와 빌드 단위를 같은 규칙으로 맞추려고 둔다.

조각 = 태그로 갈리지 않는 글 덩어리. 루비 태그 <R TEXT=..>밑말</R> 는 조각을 가르지 않는다(밑말이 글에 포함).
// 뒤 주석은 조각이 아니다(태그 밖의 // 부터). 일본어 글자가 없는 조각(기호뿐)은 번역 대상이 아니다.
"""
import re

TAG = re.compile(r"(<[^>\n]*>)")
JP = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uff10-\uff5a]")
RUBY_OPEN = re.compile(r"<R\s", re.I)


def is_ruby_tag(t):
    return bool(RUBY_OPEN.match(t)) or t.lower().startswith("</r")


def comment_at(line):
    depth = 0
    for i, ch in enumerate(line):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif ch == "/" and depth == 0 and line.startswith("//", i):
            return i
    return len(line)


def split_runs(line, all_runs=False):
    """line(끝의 \r 없이) -> (pieces, runs, tail)
    pieces: 태그와 글 조각 목록. runs: [(첫 piece 번호, 끝 piece 번호+1)].
    all_runs=False 면 일본어 글자가 든 조각만(번역 뼈대 번호), True 면 공백 아닌 글 조각 전부(정렬표 단위 맞춤용).
    tail: 주석 꼬리(그대로 붙인다)."""
    cut = comment_at(line)
    body, tail = line[:cut], line[cut:]
    pieces = [p for p in TAG.split(body) if p != ""]
    runs, start = [], None
    for i, p in enumerate(pieces + ["<END>"]):
        boundary = p.startswith("<") and not is_ruby_tag(p)
        if boundary:
            if start is not None:
                runs.append((start, i))
                start = None
        elif start is None:
            start = i
    keep = (lambda t: t.strip(" 　	")) if all_runs else JP.search
    runs = [(a, b) for a, b in runs if keep("".join(x for x in pieces[a:b] if not x.startswith("<")))]
    return pieces, runs, tail


def run_text(pieces, a, b, ruby=False):
    """조각의 원문. ruby=True 면 밑말(루비) 꼴로 보여 준다(읽기용)."""
    out, rt = [], None
    for p in pieces[a:b]:
        if p.startswith("<"):
            if RUBY_OPEN.match(p):
                m = re.search(r'TEXT="([^"]*)"', p, re.I)
                rt = m.group(1) if m else ""
            elif p.lower().startswith("</r"):
                if ruby and rt is not None:
                    out.append(f"({rt})")
                rt = None
            continue
        out.append(p)
    return "".join(out)


def replace_run(pieces, a, b, ko):
    """조각 a..b 를 한국어 한 덩어리로 바꾼다. 원문 앞머리 공백(전각 들여쓰기)은 지킨다."""
    orig = run_text(pieces, a, b)
    lead = orig[: len(orig) - len(orig.lstrip(" 　"))]
    if ko and not ko.startswith(lead):
        ko = lead + ko
    return pieces[:a] + [ko] + pieces[b:]
