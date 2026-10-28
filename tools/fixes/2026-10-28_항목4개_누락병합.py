"""표준품셈 JSON 4개 항목 정정 (원문: 2026 건설공사 표준품셈 PDF).

  - 토목 6-8-3, 9-5-5, 기계설비 13-8-7: 앞 항목(6-8-2, 9-5-4, 13-8-6)에 합쳐져 있던 것을 분리
    → 앞 항목 안에 문단으로 들어가 있던 '항목 제목' 위치에서 나누고, 그 뒤 블록은 그대로 옮긴다(내용 변경 없음).
  - 토목 3-3-1: JSON에 없던 항목을 원문 342쪽에서 옮겨 적어 추가.

사용:  python fix4.py <입력 json> <출력 json>
"""
import json
import sys


def mk_tx(bl):
    out = []
    for b in bl:
        if b["type"] == "p":
            out.append(b["text"])
        else:
            for r in b["rows"]:
                s = " ".join(c for c in r if c.strip())
                if s:
                    out.append(s)
    return "\n".join(out)


def find(J, div, ic):
    hits = [i for i, e in enumerate(J) if e["b"] == div and e["ic"] == ic]
    assert len(hits) == 1, (div, ic, hits)
    return hits[0]


def split(J, div, prev_ic, new_ic, new_title, new_pg, marker):
    """prev_ic 항목 안의 제목 문단(marker 포함)에서 나눠 new_ic 항목을 만든다."""
    i = find(J, div, prev_ic)
    e = J[i]
    ks = [k for k, b in enumerate(e["bl"]) if b["type"] == "p" and new_ic in b["text"] and marker in b["text"]]
    assert len(ks) == 1, (prev_ic, ks)
    k = ks[0]
    head, tail = e["bl"][:k], e["bl"][k + 1:]
    assert head and tail
    e["bl"] = head
    e["tx"] = mk_tx(head)
    new = {"b": e["b"], "cn": e["cn"], "ct": e["ct"], "sc": e["sc"], "st": e["st"],
           "ic": new_ic, "it": new_title, "pg": new_pg, "bl": tail, "tx": mk_tx(tail)}
    J.insert(i + 1, new)
    return new


def main(src, dst):
    J = json.load(open(src, encoding="utf-8"))
    n0 = len(J)

    split(J, "토목부문", "6-8-2", "6-8-3", "주철제･강관제 버터플라이 제수밸브 부설 및 접합('23년 보완)", 381, "버터플라이")
    split(J, "토목부문", "9-5-4", "9-5-5", "건물 및 지상물체 항공사진 ｢판독작업｣", 512, "항공사진")
    split(J, "기계설비부문", "13-8-6", "13-8-7", "활성탄･반응조제 및 소석회 공급설비 설치('04년 신설, '05년 보완)", 842,
          "활성탄")

    # 토목 3-3-1 (원문 342쪽)
    bl = [
        {"type": "p", "text": "(회당)"},
        {"type": "table", "rows": [
            ["구 분", "단 위", "수 량"],
            ["형 틀 목 공", "인", "6"],
            ["콘 크 리 트 공", "〃", "2"],
            ["특 별 인 부", "〃", "1"],
            ["보 통 인 부", "〃", "2"],
            ["콘 크 리 트 펌 프 ( 차 )", "대", "1"],
            ["소 요 일 수 (설치/콘크리트타설/해체/이동)", "일", "1"],
        ]},
        {"type": "p", "text": "[주] ① 본 품은 현장 조립이 완료된 상태의 철제거푸집 1span(2차로급 도로 또는 복선급 철도)을 "
                              "방수면에 설치, 콘크리트 타설 및 양생, 해체, 이동하는 기준이다."},
        {"type": "p", "text": "② 본 품은 레일설치, 마감면 합판거푸집 설치, 콘크리트 타설(펌프차) 작업을 포함하며, "
                              "거푸집 표면처리(샌딩) 작업은 제외되어 있다."},
        {"type": "p", "text": "③ 콘크리트 펌프차 규격은 타설능력 및 현장조건을 고려하여 적용한다."},
        {"type": "p", "text": "④ 철제레일, 침목, 박리재 등 소요자재는 제외되어 있다."},
    ]
    i = find(J, "토목부문", "3-2-5")
    ref = J[i]
    assert J[i + 1]["ic"] == "3-4-1"
    J.insert(i + 1, {"b": "토목부문", "cn": "3", "ct": ref["ct"], "sc": "3-3", "st": "현장 타설 콘크리트 라이닝",
                     "ic": "3-3-1", "it": "터널 철재거푸집 설치･해체･이동('07, '13, '20년 보완)", "pg": 342,
                     "bl": bl, "tx": mk_tx(bl)})

    assert len(J) == n0 + 4
    # 원본과 같은 형식(한 줄, ensure_ascii=False)으로 저장
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(json.dumps(J, ensure_ascii=False))
    print(f"{n0} → {len(J)} 항목")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
