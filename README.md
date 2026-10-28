# Pumsemdata — 건설공사 표준품셈 데이터

건설공사 표준품셈을 JSON으로 정리한 자료를 **이 저장소에서 직접 관리**하고,
**적산도우미** 프로그램이 여기서 최신 자료를 받아 쓰도록 하는 저장소입니다.

## 자료 현황

| 항목 | 값 |
|---|---|
| 품셈 연도 | 2026 (국토교통부 공고, 2026년 적용분) |
| 항목 | 1,092개 (공통 321 · 토목 233 · 건축 162 · 기계설비 241 · 유지관리 135) |
| 표 | 2,328개 |
| 판 번호·검사값 | `manifest.json` |
| 판별 변경 내역 | `CHANGELOG.md` |

- 표준품셈 본문은 국토교통부가 공고하는 「건설공사 표준품셈」입니다(저작권법 제7조 제2호, 국가의 고시·공고).
- 최초 자료는 <https://gitlab.aigov.go.kr/archimin/pumsem> 의 `pyojunpumsem.json` 을 그대로 옮겨 왔습니다(2026-10-27).
- PDF에서 추출된 자료라 표 머리글(병합 셀)이 깨진 곳이 있습니다. 실제 적산에는 원본 공고와 대조해 사용하세요.

## 프로그램에서 쓰는 주소

적산도우미는 먼저 작은 `manifest.json` 을 읽고, 판 번호(`version`)·검사값(`sha256`)이 바뀌었을 때만 자료를 받습니다.
받은 자료는 검사값·항목 수가 manifest 와 같을 때만 사용합니다.

```
https://raw.githubusercontent.com/Ohgeez-hub/Pumsemdata/main/manifest.json
https://raw.githubusercontent.com/Ohgeez-hub/Pumsemdata/main/data/pyojunpumsem.json
```

## 자료 갱신 방법 (새 연도 품셈 반영, 오류 정정 모두 같음)

1. `data\pyojunpumsem.json` 을 새 파일로 덮어쓰거나 직접 고칩니다.
   (바꾸기 전에 `pyojunpumsem.json.bak` 처럼 사본을 남겨 두면 안전합니다. `.bak` 파일은 GitHub에 올라가지 않습니다.)
2. 폴더의 **`자료갱신.bat`** 을 두 번 클릭합니다. (Python 필요 — 적산도우미 실행에 쓰는 것과 같음)
   - 형식 검사: 실패하면 아무것도 바꾸지 않고 이유를 보여 줍니다.
   - 판 번호: 오늘 날짜로 자동 부여 (같은 날 두 번째면 `2026.10.28.2`)
   - 변경 내역: GitHub에 올라가 있는 지난 판과 비교해 추가·삭제·변경 항목을 `CHANGELOG.md` 맨 위에 적습니다.
3. **GitHub Desktop** 에서 `CHANGELOG.md`·`manifest.json`·자료 변경을 확인하고
   Summary 에 내용(예: `2027년 품셈 반영`)을 적은 뒤 **Commit to main → Push origin**.

Push 하면 GitHub가 자동으로 형식·검사값을 다시 확인합니다(Actions 탭의 `품셈 자료 검사`).
`자료갱신.bat` 을 빼먹고 자료만 올리면 여기서 빨간 X 로 알려 주고, 적산도우미도 검사값이 맞지 않는 자료는 받지 않습니다.

## 폴더 구성

```
data/pyojunpumsem.json           표준품셈 자료
manifest.json                    판 번호, 날짜, 출처, 파일 검사값(SHA-256)·항목 수, 배포 주소
CHANGELOG.md                     판별 변경 내역 (자료갱신.bat 이 작성)
자료갱신.bat                     검사 + 판 번호 + 변경 내역을 한 번에
tools/pumsem_check.py            검사 도구 (명령: --auto / --update / --diff)
.github/workflows/validate.yml   Push 할 때마다 자동 형식 검사
```

## 주의

- 이 폴더는 Synology Drive 동기화 폴더 안에 있습니다. 같은 저장소를 **여러 PC에서 동시에** 고치면 `.git` 폴더가
  동기화 충돌로 꼬일 수 있으니, 다른 PC에서는 GitHub Desktop 으로 따로 Clone 해서 쓰세요.
