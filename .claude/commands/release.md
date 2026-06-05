---
description: 새 버전 릴리스 — 버전 범프·CHANGELOG·태그·푸시로 GitHub Release(바이너리/휠) 빌드까지
argument-hint: "[patch | minor | major | X.Y.Z]"
allowed-tools: Bash, Read, Edit, Write, Skill
---

# /release — Fatebound 릴리스 프로세스

사용자가 릴리스를 지시했다. `$ARGUMENTS` 에 따라 아래를 **순서대로** 수행한다. 각 단계 결과를 한두 줄로 보고하고, 어느 단계든 실패하면 **멈추고** 사용자에게 알린다(되돌리기 어려운 단계는 4단계의 태그 푸시부터다 — 그 전에 다 점검할 것).

배경: `release.yml` 은 `v*` 태그 푸시에서만 돈다(3-OS 바이너리 + 휠/sdist → GitHub Release 첨부). 즉 **태그를 미는 것이 릴리스를 만드는 행위**다. 수동 절차는 `RELEASING.md` 참고.

## 0. 사전 점검 (하나라도 실패하면 중단)
- 브랜치가 `main` 인가 (`git rev-parse --abbrev-ref HEAD`). 아니면 사용자 확인.
- `git fetch origin` 후 origin/main 과 동기인가. 뒤처졌으면 `git pull --ff-only`.
- 작업 트리 클린인가 (`git status --short`). 미커밋 변경이 있으면 무엇인지 보고하고 어떻게 할지 확인(보통 릴리스 전에 정리/머지돼 있어야 함).
- 최신 main CI 가 그린인가 (`gh run list --workflow=ci.yml --branch=main --limit 1 --json conclusion`). 빨강이면 중단.
- 로컬 검증: `cd game && uv run pytest -q && uv run fatebound --selftest`.

## 1. 버전 결정
- 현재 버전 읽기: `game/pyproject.toml` 의 `version`, `game/fatebound/__init__.py` 의 `__version__` (둘이 같아야 정상).
- `$ARGUMENTS` 해석:
  - `patch` / `minor` / `major` → SemVer 규칙으로 범프.
  - `X.Y.Z` → 그 값으로 명시.
  - 비어 있으면 → 사용자에게 무엇을 올릴지 물어본다(추측 금지).
- 새 버전을 `NEW` 라 한다. `git tag -l vNEW` 로 **이미 있으면 중단**.

## 2. 버전 범프 (두 곳 + 잠금)
- `game/pyproject.toml` 의 `version = "..."` → `NEW`.
- `game/fatebound/__init__.py` 의 `__version__ = "..."` → `NEW`. (반드시 둘 다 — 어긋나면 안 됨)
- `cd game && uv lock` (uv.lock 의 자기 패키지 버전 갱신).

## 3. CHANGELOG 갱신  ⚠️ 표면 문구 = humanize 가드레일 적용
- 직전 릴리스 이후 변경 수집: `git log --oneline <직전태그>..HEAD` (태그가 없으면 전체 + PR 제목). 무엇이 사용자에게 바뀌었는지 파악.
- `CHANGELOG.md` 의 `## [Unreleased]` 내용 + 위 변경을 합쳐 **사용자 관점**으로 정리(Keep a Changelog: Added/Changed/Fixed).
- **표면 문구 규칙**(`surface-copy-convention`): 보통 말로, 한자 조어·내부 용어·em대시 금지. 초안 작성 후 **`humanize-korean` 스킬로 윤문**해서 반영.
- `## [Unreleased]` 블록 내용을 `## [NEW] - YYYY-MM-DD`(오늘 날짜 = `date +%F`) 섹션으로 옮기고, 맨 위에 비어 있는 새 `## [Unreleased]` 를 둔다.

## 4. 커밋 · 태그 · 푸시  ← 여기서부터 외부 공개(되돌리기 어려움)
- `git add -A`
- 🔒 누출 가드: `git diff --cached --name-only | grep -iE 'design/|_workspace|\.save\.json'` 가 비어야 함. 걸리면 중단.
- `git commit -m "release: vNEW"` (Co-Authored-By 트레일러 포함).
- `git tag -a vNEW -m "Fatebound vNEW"`.
- `git push origin main && git push origin vNEW`  → 태그 푸시가 `release.yml` 을 트리거.

## 5. 릴리스 빌드 감시
- 잠시 뒤 `gh run list --workflow=release.yml --limit 1` 로 run id 확보 → `gh run watch <id> --exit-status` 로 완료까지(3-OS 바이너리 + 휠). 시간이 걸리므로 인내.
- 실패하면 `gh run view <id> --log-failed` 요약 + 중단(태그/릴리스 롤백은 사용자와 상의).

## 6. 릴리스 노트 반영
- `release.yml` 이 자동 생성한 Release `vNEW` 에, 3단계에서 정리한 CHANGELOG 섹션을 노트로 보강:
  `gh release view vNEW` 로 현재 노트 확인 후, 필요하면 `gh release edit vNEW --notes-file <임시파일>` 로 사람 친화 노트로 교체(역시 humanize 적용).

## 7. 보고
- Release URL, 첨부 자산(`fatebound-linux-x86_64`·`-macos-arm64`·`-windows-x86_64.exe`·`*.whl`·`*.tar.gz`) 목록.
- 설치 안내: `uvx fatebound` / 바이너리 다운로드.
- 저장소 변수 `PUBLISH_PYPI != true` 면 PyPI 게시 잡은 스킵됨을 알린다(원하면 `RELEASING.md` §2 로 Trusted Publisher 설정).

---
인자 예: `/release patch` · `/release minor` · `/release 0.2.0`
