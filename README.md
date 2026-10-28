# Pumsemdata — 건설공사 표준품셈 데이터

건설공사 표준품셈을 JSON으로 정리한 자료를 보관하고, **적산도우미** 프로그램이 이 저장소에서 최신 자료를 받아 쓰도록 하는 저장소입니다.

## 출처와 라이선스

- 원본: <https://gitlab.aigov.go.kr/archimin/pumsem> (`pyojunpumsem.json`)
- 이 저장소의 `data/pyojunpumsem.json` 은 원본 파일을 **바꾸지 않고 그대로** 옮긴 것입니다.
- 원본 라이선스: <!-- TODO: GitLab 원본 페이지의 라이선스 문구를 여기에 그대로 붙여 넣으세요 -->
- 표준품셈의 내용은 국토교통부 고시 「건설공사 표준품셈」에 따릅니다. 실제 적산에는 원본 고시와 대조해 사용하세요.
  자료는 PDF에서 추출된 것이어서 표 머리글(병합 셀)이 깨진 곳이 있습니다.

## 자료 현황

| 항목 | 값 |
|---|---|
| 품셈 연도 | 2026 (항목 제목의 '26년 보완 145건) |
| 항목 | 1,092개 (공통 321 · 토목 233 · 건축 162 · 기계설비 241 · 유지관리 135) |
| 표 | 2,328개 |
| 판 번호·검사값 | `manifest.json` |

## 프로그램에서 쓰는 주소

적산도우미는 먼저 작은 `manifest.json` 을 읽어 판 번호(`version`)와 검사값(`sha256`)이 바뀌었을 때만 자료를 받습니다.

```
https://raw.githubusercontent.com/Ohgeez-hub/Pumsemdata/main/manifest.json
https://raw.githubusercontent.com/Ohgeez-hub/Pumsemdata/main/data/pyojunpumsem.json
```

받은 자료는 `sha256`·항목 수가 manifest 와 같을 때만 사용합니다.

## 폴더 구성

```
data/pyojunpumsem.json           표준품셈 자료 (원본 그대로)
manifest.json                    판 번호, 날짜, 원본 정보, 파일 검사값(SHA-256)·항목 수
tools/pumsem_check.py            형식 검사, manifest 갱신, 이전 자료와 비교
tools/sync_from_gitlab.py        원본(GitLab)에서 받아 비교·갱신
.github/workflows/validate.yml   올릴 때마다 자동 형식 검사
.github/workflows/sync.yml       매주 원본 확인 → 바뀌면 '검토용 Pull Request' 생성
```

## 자료 갱신 방법

### 자동 (원본 GitLab이 바뀐 경우)

1. 매주 월요일 10:17(한국 시간)에 `원본(GitLab) 동기화` 작업이 원본을 확인합니다.
   Actions 탭 → `원본(GitLab) 동기화` → **Run workflow** 로 바로 실행할 수도 있습니다.
2. 바뀌었으면 **Pull Request** 가 만들어집니다. 설명에 추가·삭제·변경된 품셈 항목 목록이 있습니다.
3. 내용을 확인하고 **Merge** 하면 main 에 반영되고, 적산도우미가 다음 확인 때 새 자료를 받습니다.
   Merge 하지 않으면 아무것도 바뀌지 않습니다.

처음 한 번 저장소 설정이 필요합니다:
**Settings → Actions → General → Workflow permissions** 에서
"Read and write permissions" 선택, "Allow GitHub Actions to create and approve pull requests" 체크.

> GitHub 서버에서 `gitlab.aigov.go.kr` 에 접속할 수 없으면 동기화 작업이 실패(빨간 X)합니다.
> 그때는 아래 '직접' 방법으로 갱신하세요. 원본이 비공개로 바뀌면 GitLab 읽기 토큰을
> Settings → Secrets and variables → Actions 에 `PUMSEM_SOURCE_TOKEN` 으로 등록하면 됩니다.

### 직접 (PC에서)

1. 새 `pyojunpumsem.json` 을 `data/` 에 덮어씁니다.
2. 명령 창에서 이 폴더로 이동해 실행합니다 (Python 필요):
   ```
   python tools/pumsem_check.py --update --version 2027.01.15 --edition 2027
   ```
   형식 검사를 통과해야 `manifest.json` 이 갱신됩니다. 이전 자료와 비교하려면 `--diff 이전파일.json` 을 붙입니다.
3. GitHub Desktop 에서 바뀐 파일을 확인하고 **Commit to main → Push origin**.

`manifest.json` 을 갱신하지 않고 자료만 바꾸면 자동 검사가 실패해서 알려 줍니다.

## 주의

- 이 폴더는 Synology Drive 동기화 폴더 안에 있습니다. 같은 저장소를 **여러 PC에서 동시에** 고치면 `.git` 폴더가
  동기화 충돌로 꼬일 수 있으니, 다른 PC에서는 Synology 사본 대신 GitHub Desktop 으로 따로 Clone 해서 쓰세요.
