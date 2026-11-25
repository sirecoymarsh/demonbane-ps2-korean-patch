"""화면에 나온 글자로부터 엔진의 글리프 조회 규칙을 역산한다.

기대: 아무리 도시의 불빛이 밤을 밝혀도
실제: 악묵릭 독식蕩 붉빠透 밥읊 밝峙독
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INSIDE = open(r"P:\AI\demonbane-ps2-kr\work\font\inside.txt", "rb").read().decode("cp932")
CAR = json.load(open(r"P:\AI\demonbane-ps2-kr\work\ref\ps2_carrier_map.json", encoding="utf-8"))
REV = {v: k for k, v in CAR.items()}
idx = {c: i for i, c in enumerate(INSIDE)}

expect = "아무리 도시의 불빛이 밤을 밝혀도"
actual = "악묵릭 독식蕩 붉빠透 밥읊 밝峙독"

print(f"{'기대':<4} {'캐리어':<4} {'inside#':>7} | {'실제':<4} {'그 글자의 위치':>10}  판정")
for e, a in zip(expect, actual):
    if e == " ":
        continue
    c = CAR.get(e)
    if c is None:
        print(f"{e} : 캐리어 없음")
        continue
    ie = idx[c]
    # 실제로 보인 글자가 '한글' 이면 그 한글의 캐리어 위치, '한자' 면 그 한자 자체의 위치
    if 0xAC00 <= ord(a) <= 0xD7A3:
        ca = CAR.get(a)
        ia = idx.get(ca) if ca else None
        what = f"캐리어 {ca}"
    else:
        ia = idx.get(a)
        what = "한자 그대로"
    d = (ia - ie) if ia is not None else None
    print(f"{e}    {c}    {ie:>7} | {a}    {what:>10} #{ia}  차이 {d}")
