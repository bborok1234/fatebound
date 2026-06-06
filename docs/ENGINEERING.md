# 엔지니어링 워크플로 (SSOT)

> 이 프로젝트는 **1인(최종 결정자) + AI 에이전트**로 개발·운영한다. GitHub이 원천(SSOT) — 이슈·PR·CI가 진실이다.
> 모든 작업은 아래 6단계를 따른다. 한 이슈에 PR이 여럿일 수 있다(전략적으로 쪼갠다).

## 6단계

1. **이슈 생성** — 신규 기능 / 개선 / 유지보수 단위로 GitHub 이슈를 연다. 무엇을·왜·받아들임 기준을 적는다.
2. **플랜·전략** — 처리 방법을 세운다. 필요하면 리서치(웹·코드)와 자가 검수를 한다. 간단하거나 해결법이 명확하면 바로 3으로.
3. **PR 생성(전략적)** — 이슈를 풀기 위해 PR을 만든다. **이슈당 PR 다수 가능**. 독립적으로 진행 가능한 작업은 **에이전트 fan-out / 다이나믹 워크플로**를 적극 활용해 병렬로.
4. **작업** — 구현. 비공개 누출 금지(`design/`·`_workspace/`·`*.save.json`은 공개 레포에 절대 안 올림).
5. **QA** — 아래 게이트를 통과시킨다. **비주얼 변경이 있으면 CLI 비주얼 QA(스냅샷)** 추가.
6. **머지** — QA 통과 시 머지. main은 브랜치 보호(직접 push 금지, PR 필수). 검증 green 집중 PR은 에이전트가 머지하고 사람이 사후 감수.

## 브랜치·PR 규칙
- 작업은 `main`에서 분기한 브랜치(`feat/…`·`fix/…`·`chore/…`)에서. main 직접 커밋 금지(브랜치 보호).
- 한 이슈 → 1개 이상의 집중 PR. PR은 리뷰 가능한 단위로 쪼갠다(거대 PR 금지 — 그럴 거면 main 직접 커밋과 다를 바 없다).
- PR 본문에 `Closes #N`(완결) 또는 `Refs #N`(부분). 커밋 trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- 머지 후 다음 작업은 **갱신된 main에서 다시 분기**(충돌 회피). worktree 격리 에이전트는 main에서 분기하니 main이 최신이어야 한다.

## QA 게이트 (5단계)
`cd game` 기준:
- **단위·밸런스·속성**: `uv run pytest -q` (밸런스 회귀·다양성≥4·죽은아키타입0·정체성 불변량·곡선·엔드리스·온보딩·persistence·Hypothesis).
- **아키텍처**: `uv run lint-imports` (core ↛ tui).
- **린트**: `uv run ruff check fatebound tests`.
- **데이터/엔진 번들**: `uv run python _entry.py --selftest` (frozen 경로와 동일).
- **TUI 회귀(스모크)**: `uv run python ../design/dev-harnesses/tui_smoke.py --all` (4빌드 마운트+전투, dice-realtime).
- **공급망 보안**: `uvx zizmor --min-severity medium .github/workflows/` (cache-poisoning·credential 등).

## CLI 비주얼 QA (스냅샷) — 비주얼 변경 시 필수
Textual SVG 스냅샷으로 화면 출력 회귀를 잡는다(`tests/test_snapshots.py`, pytest-textual-snapshot).
- 비교 실행: `uv run pytest tests/test_snapshots.py -q` — 골든 SVG와 다르면 실패 + HTML diff 리포트.
- 의도된 비주얼 변경이면 baseline 갱신: `uv run pytest tests/test_snapshots.py --snapshot-update` 후 변경된 `tests/__snapshots__/**.svg`를 **커밋**(diff로 변화를 사람이 확인).
- 새 화면/위젯을 만들면 스냅샷 테스트를 추가한다.
- SVG는 폰트 메트릭이 OS별로 미세하게 달라 **baseline OS(darwin)에서만** 비교(`skipif`). CI는 macos 잡에서 게이트, 그 외 skip.
- 보조: `app.run_test()` + pilot로 상호작용 후 상태/스크린샷 확인(스모크 하니스가 이 패턴).

## 운영 메모
- RSI 튜닝(밸런스·메커니즘): 격리 worktree 에이전트 → diff 검토 → 비충돌 적용 → 독립 검증 → 머지. 상세는 스킬 `fatebound-rsi-tune`.
- 한국어 표면 콘텐츠(아이템 flavor 등)는 `humanize-korean`으로 윤문(gist는 기능 한 줄, flavor는 천기노조 보이스).
