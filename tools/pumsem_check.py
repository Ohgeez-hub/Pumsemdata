"""표준품셈 JSON 형식 검사와 manifest 관리 (파이썬 표준 라이브러리만 사용).

    python tools/pumsem_check.py                 # data/ 자료와 manifest.json 이 맞는지 검사
    python tools/pumsem_check.py --update        # 자료에 맞게 manifest.json 을 다시 씀(판 번호는 그대로)
    python tools/pumsem_check.py --update --version 2027.1 --edition 2027
    python tools/pumsem_check.py --diff 이전.json  # 항목 단위 변경 내역
    python tools/pumsem_check.py --auto          # 자료갱신.bat 이 쓰는 방식: 검사 → 판 번호 자동 → CHANGELOG 기록

검사 내용
  - JSON 목록이고 항목마다 b, cn, ct, sc, st, ic, it, pg, bl, tx 가 알맞은 형식인지
  - bl 블록이 문단(p) 또는 표(table, 행 = 문자열 목록)인지
  - 항목 수가 너무 적지 않은지(잘린 파일 방지), 같은 (부문, 항목 번호) 중복
  - manifest.json 의 SHA-256·크기·항목 수가 실제 파일과 같은지
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "pyojunpumsem.json"
MANIFEST = ROOT / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
# GitHub 에 올라가 있는(= 지난 판) 자료. 변경 내역 비교에 쓴다.
PUBLISHED_DATA_URL = "https://raw.githubusercontent.com/Ohgeez-hub/Pumsemdata/main/data/pyojunpumsem.json"
KST = timezone(timedelta(hours=9))

FIELDS = {"b": str, "cn": str, "ct": str, "sc": str, "st": str, "ic": str, "it": str, "pg": int, "bl": list,
          "tx": str}
KNOWN_DIVISIONS = {"공통부문", "토목부문", "건축부문", "기계설비부문", "유지관리부문"}
MIN_ENTRIES = 500          # 이보다 적으면 잘린 파일로 본다


class CheckError(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_entries(entries) -> list[str]:
    """형식 오류가 있으면 CheckError, 경고는 목록으로 돌려준다."""
    if not isinstance(entries, list):
        raise CheckError("최상위가 목록([...])이 아닙니다.")
    if len(entries) < MIN_ENTRIES:
        raise CheckError(f"항목이 {len(entries)}개뿐입니다(최소 {MIN_ENTRIES}). 파일이 잘렸을 수 있습니다.")
    errors, warnings = [], []
    seen = {}
    for i, e in enumerate(entries):
        where = f"{i}번 항목"
        if not isinstance(e, dict):
            errors.append(f"{where}: 객체가 아닙니다.")
            continue
        where = f"{i}번 항목({e.get('b', '?')} {e.get('ic', '?')})"
        for k, t in FIELDS.items():
            if k not in e:
                errors.append(f"{where}: '{k}' 없음")
            elif not isinstance(e[k], t) or (t is int and isinstance(e[k], bool)):
                errors.append(f"{where}: '{k}' 형식이 {t.__name__} 가 아님")
        for j, b in enumerate(e.get("bl") or []):
            if not isinstance(b, dict) or b.get("type") not in ("p", "table"):
                errors.append(f"{where}: 블록 {j} 의 type 이 p/table 이 아님")
            elif b["type"] == "p" and not isinstance(b.get("text"), str):
                errors.append(f"{where}: 문단 블록 {j} 에 text 없음")
            elif b["type"] == "table":
                rows = b.get("rows")
                if not isinstance(rows, list) or not all(isinstance(r, list) and all(isinstance(c, str) for c in r)
                                                         for r in rows):
                    errors.append(f"{where}: 표 블록 {j} 의 rows 가 문자열 목록의 목록이 아님")
        if e.get("b") not in KNOWN_DIVISIONS:
            warnings.append(f"{where}: 처음 보는 부문 '{e.get('b')}'")
        key = (e.get("b"), e.get("ic"))
        if key in seen:
            warnings.append(f"{where}: 같은 부문·항목 번호가 {seen[key]}번 항목에도 있음")
        else:
            seen[key] = i
        if len(errors) > 30:
            break
    if errors:
        raise CheckError("형식 오류 " + str(len(errors)) + "건:\n  " + "\n  ".join(errors[:30]))
    return warnings


def load(path: Path) -> tuple[bytes, list]:
    raw = path.read_bytes()
    try:
        return raw, json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CheckError(f"{path.name}: JSON 으로 읽을 수 없습니다 ({e})") from e


def summary(entries) -> dict:
    div = {}
    tables = 0
    for e in entries:
        div[e["b"]] = div.get(e["b"], 0) + 1
        tables += sum(1 for b in e["bl"] if b["type"] == "table")
    return {"entries": len(entries), "tables": tables, "divisions": div}


def build_manifest(raw: bytes, entries, old: dict | None = None, version=None, edition=None,
                   source_commit=None) -> dict:
    old = old or {}
    src = dict(old.get("source") or {})
    if source_commit:
        src["commit"] = source_commit
    s = summary(entries)
    return {
        "format": "jeoksan-pumsem-manifest",
        "schema": 1,
        "name": old.get("name", "건설공사 표준품셈"),
        "edition": edition or old.get("edition", ""),
        "version": version or old.get("version", ""),
        "updated": date.today().isoformat(),
        "source": src,
        "files": [{
            "path": "data/pyojunpumsem.json",
            "sha256": sha256(raw),
            "bytes": len(raw),
            "entries": s["entries"],
            "tables": s["tables"],
            "divisions": s["divisions"],
        }],
    }


def check_manifest(raw: bytes, entries, man: dict):
    if man.get("format") != "jeoksan-pumsem-manifest":
        raise CheckError("manifest.json 의 format 이 다릅니다.")
    f = man["files"][0]
    if f["sha256"] != sha256(raw):
        raise CheckError("manifest.json 의 sha256 이 실제 파일과 다릅니다. "
                         "자료를 바꿨다면 'python tools/pumsem_check.py --update' 로 manifest 를 갱신하세요.")
    if f["bytes"] != len(raw) or f["entries"] != len(entries):
        raise CheckError("manifest.json 의 크기·항목 수가 실제 파일과 다릅니다.")
    if not man.get("version"):
        raise CheckError("manifest.json 에 version(판 번호)이 없습니다.")


def diff(old_entries, new_entries) -> dict:
    """(부문, 항목 번호) 기준 추가·삭제·변경."""
    def index(es):
        out = {}
        for e in es:
            out.setdefault((e["b"], e["ic"]), e)
        return out
    a, b = index(old_entries), index(new_entries)
    added = [k for k in b if k not in a]
    removed = [k for k in a if k not in b]
    changed = [k for k in b if k in a and (a[k]["bl"] != b[k]["bl"] or a[k]["it"] != b[k]["it"])]
    label = lambda k, src: f"{k[0]} {k[1]} {src[k]['it']}"
    return {"added": [label(k, b) for k in added], "removed": [label(k, a) for k in removed],
            "changed": [label(k, b) for k in changed]}


def diff_text(d: dict, limit=60) -> str:
    lines = [f"- 추가 {len(d['added'])}건, 삭제 {len(d['removed'])}건, 내용 변경 {len(d['changed'])}건"]
    for name, title in (("added", "추가"), ("removed", "삭제"), ("changed", "변경")):
        if d[name]:
            lines.append(f"\n### {title}")
            lines += [f"- {x}" for x in d[name][:limit]]
            if len(d[name]) > limit:
                lines.append(f"- … 외 {len(d[name]) - limit}건")
    return "\n".join(lines)


def guess_edition(entries) -> str:
    """제목의 "('26년 보완)" 중 가장 최근 연도 → '2026'."""
    years = [int(y) for e in entries for y in re.findall(r"[’'‘](\d\d)년", e.get("it", ""))]
    recent = [y for y in years if y < 90]
    return f"20{max(recent):02d}" if recent else ""


def next_version(old: str, today: str) -> str:
    """오늘 날짜 판 번호. 같은 날 두 번째면 2026.10.28.2 처럼 붙인다."""
    old = old or ""
    if not old.startswith(today):
        return today
    tail = old[len(today):].lstrip(".")
    return f"{today}.{int(tail) + 1 if tail.isdigit() else 2}"


def fetch_published(url=PUBLISHED_DATA_URL, timeout=60):
    """GitHub 에 올라가 있는 지난 판 자료(없거나 인터넷이 안 되면 None)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Pumsemdata-check"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8-sig"))
    except Exception:
        return None


def auto_update(raw: bytes, entries, old: dict | None, prev_entries=None, today: str | None = None) -> str:
    """자료가 바뀌었으면 manifest 와 CHANGELOG 를 갱신하고 결과 문장을 돌려준다."""
    if old and old.get("files") and old["files"][0].get("sha256") == sha256(raw):
        return f"변경 없음 — manifest(판 {old.get('version')})가 이미 이 자료와 맞습니다."
    today = today or datetime.now(KST).strftime("%Y.%m.%d")
    version = next_version((old or {}).get("version", ""), today)
    edition = guess_edition(entries) or (old or {}).get("edition", "")
    man = build_manifest(raw, entries, old, version, edition)
    MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if prev_entries is not None:
        changes = diff_text(diff(prev_entries, entries), limit=200)
    else:
        changes = "- (지난 판과 비교하지 못함: 인터넷 연결 또는 GitHub 접속 확인)"
    entry = (f"## {version}  ({len(entries):,}개 항목, 품셈 {edition or '?'}년)\n\n{changes}\n")
    # 맨 위 제목 줄 바로 아래에 새 판을 넣는다(최신이 위)
    old_log = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else "# 변경 내역\n"
    head, _, rest = old_log.partition("\n")
    rest = rest.strip("\n")
    CHANGELOG.write_text(head + "\n\n" + entry + ("\n" + rest + "\n" if rest else ""), encoding="utf-8")
    return f"manifest.json 갱신: 판 {version} (품셈 {edition}년)\n" + changes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="표준품셈 자료 검사")
    ap.add_argument("--update", action="store_true", help="manifest.json 을 자료에 맞게 다시 씀")
    ap.add_argument("--version", help="판 번호 (예: 2027.1)")
    ap.add_argument("--edition", help="품셈 연도 (예: 2027)")
    ap.add_argument("--diff", metavar="OLD_JSON", help="이전 자료와 항목 단위 비교")
    ap.add_argument("--auto", action="store_true",
                    help="검사 → (바뀌었으면) 오늘 날짜 판 번호로 manifest 갱신 → GitHub 의 지난 판과 비교해 CHANGELOG 기록")
    a = ap.parse_args(argv)
    try:
        raw, entries = load(DATA)
        warnings = check_entries(entries)
        s = summary(entries)
        print(f"형식 검사 통과: 항목 {s['entries']:,}개, 표 {s['tables']:,}개, "
              + ", ".join(f"{k} {v}" for k, v in s["divisions"].items()))
        for w in warnings[:20]:
            print("  경고:", w)
        old = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
        if a.auto:
            prev = None
            if not (old and old.get("files") and old["files"][0].get("sha256") == sha256(raw)):
                print("GitHub 에 올라가 있는 지난 판과 비교하는 중…")
                prev = fetch_published()
            print(auto_update(raw, entries, old, prev))
            return 0
        if a.update:
            man = build_manifest(raw, entries, old, a.version, a.edition)
            MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"manifest.json 갱신: 판 {man['version'] or '(없음)'}, sha256 {man['files'][0]['sha256'][:12]}…")
        elif old is None:
            raise CheckError("manifest.json 이 없습니다. '--update --version 판번호' 로 만드세요.")
        else:
            check_manifest(raw, entries, old)
            print(f"manifest 일치: 판 {old['version']}")
        if a.diff:
            _, prev = load(Path(a.diff))
            print(diff_text(diff(prev, entries)))
    except CheckError as e:
        print("검사 실패:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
