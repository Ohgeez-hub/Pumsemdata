"""원본(GitLab archimin/pumsem)의 pyojunpumsem.json 을 받아 이 저장소 자료와 비교한다.

    python tools/sync_from_gitlab.py              # 바뀌었으면 data/ 와 manifest.json 을 갱신
    python tools/sync_from_gitlab.py --check      # 확인만(파일은 그대로)

바뀐 경우에만 파일을 쓰고, 변경 내역을 sync_report.md 에 남긴다.
GitHub Actions(sync.yml)는 이 결과로 '검토용 Pull Request'를 만든다 — main 에 바로 넣지 않는다.
받은 자료가 형식 검사를 통과하지 못하면 아무것도 바꾸지 않고 실패(종료 코드 1)한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pumsem_check as pc  # noqa: E402

SOURCE_BASE = os.environ.get("PUMSEM_SOURCE_BASE", "https://gitlab.aigov.go.kr")
SOURCE_PROJECT = os.environ.get("PUMSEM_SOURCE_PROJECT", "archimin/pumsem")
SOURCE_BRANCH = os.environ.get("PUMSEM_SOURCE_BRANCH", "main")
SOURCE_FILE = os.environ.get("PUMSEM_SOURCE_FILE", "pyojunpumsem.json")
MAX_BYTES = 50 * 1024 * 1024
REPORT = pc.ROOT / "sync_report.md"
KST = timezone(timedelta(hours=9))


def raw_url() -> str:
    return f"{SOURCE_BASE}/{SOURCE_PROJECT}/-/raw/{SOURCE_BRANCH}/{SOURCE_FILE}"


def fetch(url: str, timeout=60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Pumsemdata-sync"})
    token = os.environ.get("PUMSEM_SOURCE_TOKEN")          # 원본이 비공개로 바뀐 경우에만
    if token:
        req.add_header("PRIVATE-TOKEN", token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise pc.CheckError("받은 파일이 50MB 를 넘습니다.")
    if data[:1] not in (b"[", b"\xef"):                     # 로그인 화면(HTML) 등을 걸러냄
        raise pc.CheckError("받은 내용이 JSON 이 아닙니다(로그인 화면이나 오류 페이지일 수 있음).")
    return data


def source_commit() -> str:
    """원본 파일의 마지막 커밋 번호(알 수 없으면 빈 문자열)."""
    pid = urllib.parse.quote(SOURCE_PROJECT, safe="")
    url = (f"{SOURCE_BASE}/api/v4/projects/{pid}/repository/commits"
           f"?ref_name={SOURCE_BRANCH}&path={urllib.parse.quote(SOURCE_FILE)}&per_page=1")
    try:
        items = json.loads(fetch_json(url))
        return items[0]["id"] if items else ""
    except Exception:
        return ""


def fetch_json(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Pumsemdata-sync"})
    if os.environ.get("PUMSEM_SOURCE_TOKEN"):
        req.add_header("PRIVATE-TOKEN", os.environ["PUMSEM_SOURCE_TOKEN"])
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(1_000_000)


def guess_edition(entries) -> str:
    """제목의 "('26년 보완)" 중 가장 최근 연도 → '2026'."""
    years = [int(y) for e in entries for y in re.findall(r"[’'‘](\d\d)년", e.get("it", ""))]
    recent = [y for y in years if y < 90]
    return f"20{max(recent):02d}" if recent else ""


def set_output(**kw):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            for k, v in kw.items():
                f.write(f"{k}={v}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="원본 GitLab 에서 표준품셈 자료 동기화")
    ap.add_argument("--check", action="store_true", help="비교만 하고 파일은 바꾸지 않음")
    ap.add_argument("--url", help="원본 파일 주소(기본: GitLab raw 주소)")
    a = ap.parse_args(argv)
    url = a.url or raw_url()
    print("원본:", url)
    try:
        new_raw = fetch(url)
        new_entries = json.loads(new_raw.decode("utf-8-sig"))
        warnings = pc.check_entries(new_entries)
    except pc.CheckError as e:
        print("원본 자료 검사 실패 — 아무것도 바꾸지 않았습니다:", e, file=sys.stderr)
        set_output(changed="false")
        return 1
    except Exception as e:
        print(f"원본에 접속하지 못했습니다: {e}", file=sys.stderr)
        set_output(changed="false")
        return 1

    old_raw, old_entries = pc.load(pc.DATA) if pc.DATA.exists() else (b"", [])
    if pc.sha256(new_raw) == pc.sha256(old_raw):
        print("변경 없음 — 이 저장소 자료가 원본과 같습니다.")
        set_output(changed="false")
        return 0

    d = pc.diff(old_entries, new_entries)
    now = datetime.now(KST)
    version = now.strftime("%Y.%m.%d")
    edition = guess_edition(new_entries)
    commit = source_commit()
    report = (f"## 표준품셈 자료 갱신 제안 ({version})\n\n"
              f"원본: {url}\n" + (f"원본 커밋: `{commit}`\n" if commit else "") +
              f"\n항목 {len(old_entries):,} → {len(new_entries):,}개\n\n" + pc.diff_text(d) +
              ("\n\n### 경고\n" + "\n".join(f"- {w}" for w in warnings[:30]) if warnings else "") +
              "\n\n---\n검토 후 문제가 없으면 이 Pull Request 를 Merge 하세요. "
              "적산도우미는 main 의 manifest.json 판 번호가 바뀌면 새 자료를 받습니다.\n")
    print(report)
    if a.check:
        set_output(changed="true", version=version)
        return 0

    pc.DATA.parent.mkdir(parents=True, exist_ok=True)
    pc.DATA.write_bytes(new_raw)
    old_man = json.loads(pc.MANIFEST.read_text(encoding="utf-8")) if pc.MANIFEST.exists() else None
    # 같은 날 두 번 바뀌면 판 번호가 겹치지 않게 2026.10.27.2 처럼 붙인다
    if old_man and str(old_man.get("version", "")).startswith(version):
        tail = str(old_man["version"])[len(version):].lstrip(".")
        version = f"{version}.{int(tail) + 1 if tail.isdigit() else 2}"
        report = report.replace(f"갱신 제안 ({now:%Y.%m.%d})", f"갱신 제안 ({version})")
    man = pc.build_manifest(new_raw, new_entries, old_man, version=version, edition=edition or None,
                            source_commit=commit or None)
    man["source"].update({"url": f"{SOURCE_BASE}/{SOURCE_PROJECT}", "file": SOURCE_FILE,
                          "branch": SOURCE_BRANCH, "fetched": now.isoformat(timespec="seconds")})
    pc.MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(report, encoding="utf-8")
    set_output(changed="true", version=version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
