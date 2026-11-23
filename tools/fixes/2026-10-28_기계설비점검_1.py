"""기계설비부문 점검 1차 (사용자 점검 요청, 2026-10-28).

  1. 관 규격 칸의 ø 표기 통일: 표 첫 칸에만 붙은 'ø15' 같은 표기에서 ø 를 뺀다(기계설비 43곳).
     'ø15㎜', '6.5ø×305m/m' 처럼 다른 글자가 함께 있는 칸은 그대로 둔다.
  2. 1-1-2 용접배관 표를 원문(645쪽)처럼 두 묶음으로 정리하고 병합 셀(spans)을 기록한다.
       15~150㎜  : 배관공 3인 · 보통인부 1인
       200~400㎜ : 배관공 4인 · 보통인부 1인
     PDF 추출 때 직종 행이 규격 행 사이에 따로 끼어 있던 것(빈 규격 행 2개)을 없애고,
     묶음마다 직종·단위·수량을 병합 칸 하나에 줄바꿈으로 함께 적는다(두 직종이 모든 규격에 함께 투입).
     규격·시공량 값은 그대로.

표 블록의 병합 셀 형식(선택 항목):  "spans": [[행, 열, 행 수, 열 수], ...]   (0부터 셈)
한 칸 안의 줄바꿈(\\n)은 같은 행의 다른 여러 줄 칸과 줄끼리 짝이다(직종 k번째 줄 ↔ 수량 k번째 줄).
고친 항목의 tx 는 블록에서 다시 만든다(원래 tx 처럼 공백 또는 줄바꿈으로 이음).

사용:  python 2026-10-28_기계설비점검_1.py <입력 json> <출력 json>
"""
import json
import re
import sys

DIV = "기계설비부문"
PHI = re.compile(r"^[øφØΦ]\s*(\d+(?:\.\d+)?)$")

PIPE_112_BEFORE = [
    ["구 분", "단 위", "수 량", "관규격(㎜)", "시공량(m)"],
    ["", "", "", "15", "83"], ["", "", "", "20", "75"], ["배 관 공", "인", "3", "25", "60"],
    ["", "", "", "32", "50"], ["", "", "", "40", "45"], ["", "", "", "50", "37"], ["", "", "", "65", "30"],
    ["", "", "", "80", "25"], ["보 통 인 부", "인", "1", "", ""], ["", "", "", "100", "18"],
    ["", "", "", "125", "14"], ["", "", "", "150", "12"], ["", "", "", "200", "10"],
    ["배 관 공", "인", "4", "", ""], ["", "", "", "250", "8.0"], ["", "", "", "300", "6.0"],
    ["보 통 인 부", "인", "1", "350", "5.0"], ["", "", "", "400", "4.0"],
]
# (규격, 시공량) 순서 그대로
PIPE_112_SIZES = [("15", "83"), ("20", "75"), ("25", "60"), ("32", "50"), ("40", "45"), ("50", "37"), ("65", "30"),
                  ("80", "25"), ("100", "18"), ("125", "14"), ("150", "12"), ("200", "10"), ("250", "8.0"),
                  ("300", "6.0"), ("350", "5.0"), ("400", "4.0")]
# 묶음마다 직종 전체가 모든 규격에 함께 들어간다(예: 15㎜ 83m/일 = 배관공 3인 + 보통인부 1인).
# 그래서 직종·단위·수량을 묶음 전체 병합 칸 하나에 줄을 바꿔 함께 적는다: {첫 규격 순번: (직종, 단위, 수량, 규격 수)}
PIPE_112_CREW = {0: ("배 관 공\n보 통 인 부", "인\n인", "3\n1", 11),
                 11: ("배 관 공\n보 통 인 부", "인\n인", "4\n1", 5)}


def mk_tx(bl, sep="\n"):
    out = []
    for b in bl:
        if b["type"] == "p":
            out.append(b["text"])
        else:
            for r in b["rows"]:
                s = " ".join(c for c in r if c.strip())
                if s:
                    out.append(s)
    return sep.join(out)


def tx_sep(e):
    """원래 tx 가 줄바꿈으로 이었는지 공백으로 이었는지(자료에 두 방식이 섞여 있음). 같은 방식으로 다시 만든다."""
    for sep in ("\n", " "):
        if e["tx"] == mk_tx(e["bl"], sep):
            return sep
    raise AssertionError(("tx 형식을 알 수 없음", e["ic"]))


def find(J, ic):
    hits = [i for i, e in enumerate(J) if e["b"] == DIV and e["ic"] == ic]
    assert len(hits) == 1, (ic, hits)
    return J[hits[0]]


def remove_phi(J, touched):
    n = 0
    for e in J:
        if e["b"] != DIV:
            continue
        for b in e["bl"]:
            if b["type"] != "table":
                continue
            for r in b["rows"]:
                for k, c in enumerate(r):
                    m = PHI.match(c.strip())
                    if m:
                        if e["ic"] not in touched:
                            touched[e["ic"]] = (e, tx_sep(e))
                        r[k] = m.group(1)
                        n += 1
    assert n == 43, n
    return n


def rebuild_112(e):
    t = e["bl"][1]
    assert t["type"] == "table" and t["rows"] == PIPE_112_BEFORE and "spans" not in t
    rows, spans = [PIPE_112_BEFORE[0]], []
    for i, (size, amount) in enumerate(PIPE_112_SIZES):
        name, unit, qty, n = PIPE_112_CREW.get(i, ("", "", "", 0))
        rows.append([name, unit, qty, size, amount])
        if n:
            spans += [[i + 1, c, n, 1] for c in range(3)]
    assert sum(PIPE_112_CREW[k][3] for k in PIPE_112_CREW) == len(PIPE_112_SIZES)
    t["rows"], t["spans"] = rows, spans


def main(src, dst):
    J = json.load(open(src, encoding="utf-8"))
    n0 = len(J)
    touched = {}
    n = remove_phi(J, touched)
    e = find(J, "1-1-2")
    rebuild_112(e)
    for e, sep in touched.values():
        e["tx"] = mk_tx(e["bl"], sep)
    assert len(J) == n0
    # 원본과 같은 형식(한 줄, ensure_ascii=False)으로 저장
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(J, ensure_ascii=False))
    print(f"ø {n}곳 정리({len(touched)}개 항목), 1-1-2 표 묶음 정리")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
