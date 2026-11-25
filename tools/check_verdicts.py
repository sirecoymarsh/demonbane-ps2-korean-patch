"""판정 파일 게이트. 통과 못 하면 exit 1 과 사유.

    python check_verdicts.py 0310_00 0310_01 ...      (패킷 이름, 생략하면 verdicts 전부)

검사(하드): 항목 수·순서·key 일치 / ko 비어있음 / 일본어 문자 잔존 / 태그 / 줄바꿈 / 「」 개수 불일치
검사(소프트, 경고만): 대사 안 그·그녀 / 용어집 미준수 / 길이비 이상(원문 대비 2.2배 초과 또는 0.3배 미만) / 알 1인칭 '첩'
"""
import json, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"P:\AI\demonbane-ps2-kr"
PK = os.path.join(ROOT, "work", "packets"); VD = os.path.join(ROOT, "work", "verdicts")
JP = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

import re as _re
def term_in(jp, text):
    """가타카나 용어는 앞뒤가 가타카나가 아닐 때만 일치로 본다."""
    if not _re.fullmatch(r"[ァ-ヶー]+", jp):
        return jp in text
    return _re.search(r"(?<![ァ-ヶー])" + _re.escape(jp) + r"(?![ァ-ヶー])", text) is not None

names = sys.argv[1:] or [f[:-5] for f in sorted(os.listdir(VD)) if f.endswith(".json")]
bad = 0
for n in names:
    vp = os.path.join(VD, n + ".json")
    errs, warns = [], []
    try:
        v = json.load(open(vp, encoding="utf-8"))
    except Exception as e:
        print(f"[FAIL] {n}: JSON 오류 {e}"); bad += 1; continue
    p = json.load(open(os.path.join(PK, n + ".json"), encoding="utf-8"))
    pit = p["items"]; vit = v.get("items", [])
    if [i["key"] for i in vit] != [i["key"] for i in pit]:
        pk = {i["key"] for i in pit}; vk = {i["key"] for i in vit}
        errs.append(f"항목 불일치: 빠짐 {sorted(pk - vk)[:5]} 잉여 {sorted(vk - pk)[:5]} (순서/개수 {len(vit)}/{len(pit)})")
    gl = p.get("glossary", {})
    for it, src in zip(vit, pit):          # 같은 key 가 둘일 수 있어(<K> 분할) 순서로 짝짓는다
        if it["key"] != src["key"]: continue
        ko = it.get("ko", "")
        if ko.strip() == "=":
            ko = src["ko_candidate"]
            if not ko: errs.append(f"{it['key']}: 후보가 없는데 '='"); continue
        if not ko.strip() and src["jp"].strip():
            errs.append(f"{it['key']}: ko 비어 있음"); continue
        if JP.search(ko): errs.append(f"{it['key']}: 일본어 잔존 {JP.findall(ko)[:5]}")
        if "<" in ko or ">" in ko: errs.append(f"{it['key']}: 태그")
        if "\n" in ko or "\r" in ko: errs.append(f"{it['key']}: 줄바꿈")
        jq, kq = src["jp"].count("「"), ko.count("「")
        if jq != kq and src["jp"].count("「") == src["jp"].count("」"):
            errs.append(f"{it['key']}: 「 개수 {jq}->{kq}")
        if src.get("speaker") and re.search(r"그녀|(^|[^가-힣])그(가|는|를|의|에게)", ko):
            warns.append(f"{it['key']}: 대사 안 그/그녀")
        for jp, k in gl.items():
            if term_in(jp, src["jp"]) and k.split()[0] not in ko:
                warns.append(f"{it['key']}: 용어 {jp}->{k} 없음")
        L = len(src["jp"].replace("　", "").strip()); K = len(ko.strip())
        if L >= 8 and (K > 2.2 * L or K < 0.3 * L):
            warns.append(f"{it['key']}: 길이비 {K}/{L}")
        if src.get("speaker") and "アル" in src["speaker"] and re.search(r"(^|[^가-힣])첩(이|은|을|의|과|에게|도|한테)?([^가-힣]|$)", ko):
            warns.append(f"{it['key']}: 알 1인칭 '첩'")
    if errs:
        bad += 1; print(f"[FAIL] {n}: " + " | ".join(errs[:6]))
    else:
        print(f"[OK] {n}" + (f"  경고 {len(warns)}: " + " | ".join(warns[:4]) if warns else ""))
sys.exit(1 if bad else 0)
