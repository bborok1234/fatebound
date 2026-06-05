# Fatebound · 천명회귀 — game package

이 디렉터리는 플레이 가능한 **프로덕션 패키지**(`fatebound`)입니다. 게임 소개·설치·조작은 레포 루트 [`../README.md`](../README.md)를 참고하세요. 여기서는 패키지 구조와 개발/빌드만 다룹니다.

## 개발

```bash
uv sync                 # .venv + uv.lock 기반 의존성(textual·rich·wcwidth + dev)
uv run fatebound        # 게임 실행(TUI)
uv run pytest -q        # 테스트(6)
uv run fatebound --selftest   # 비대화 자가검증(데이터·엔진)
```

`requires-python >=3.11` (개발 기준 `.python-version`=3.13). 빌드 백엔드는 hatchling, 패키지/환경 관리는 [uv](https://docs.astral.sh/uv/)를 씁니다.

## 구조 (엔진 = 권위 / 표현층 분리)

```
fatebound/
  engine/        순수 로직(I/O 0) — 권위 코어
    models·rng·formula·events·balance·bag·combat·session·render_text
  content/data/  번들 콘텐츠(아이템·몬스터·지역·사건 JSON) + 로더
  tui/           Textual 앱 — app·app.tcss·screens(title·game·reincarnate)·widgets(gugung·statuspanel)
  persistence/   세이브 — 직렬화·원자적 쓰기·자동저장(이어하기)
  cli.py·__main__.py   진입점(--version / --selftest)
tests/           pytest(결정론·공식 안전성·빌드 보스 공략 가드·세션 라운드트립)
_entry.py        PyInstaller 진입 스크립트
```

- **전투 = 이벤트 스트림**: `engine.combat`이 타입 이벤트(주사위·피해·상태이상·비장…)를 emit하면 TUI는 애니메이션을 재생하고, `engine.render_text`는 이를 무협 로그로 변환합니다. 숫자와 결과는 엔진이 확정하므로 형태와 무관합니다.
- **격자 배치 → 주사위 컴파일**: `engine.bag`이 3×3 격자(인게임 명칭 "구궁") 배치에서 6면 주사위(인게임 "천명괘")의 면 구성·면별 효과·인접 시너지를 컴파일합니다.
- **밸런스 SSOT**: 모든 밸런스 상수는 `engine/balance.py` 한 곳에 둡니다.
- **결정론**: 무작위는 시드 가능한 `engine.rng.Rng`만 씁니다.

## 패키징 · 배포

- **휠/sdist:** `uv build` → `dist/*.whl`,`*.tar.gz` (콘텐츠·tcss 자동 포함).
- **스탠드얼론 바이너리:** `uv run pyinstaller --onefile --name fatebound --collect-all textual --collect-data fatebound _entry.py` → `dist/fatebound`.
- **CI/CD:** [`../.github/workflows/`](../.github/workflows/) — `ci.yml`(OS×py 매트릭스 테스트+selftest), `release.yml`(태그 `v*` → 3-OS 바이너리 + 휠 → GitHub Release). 릴리스 절차는 [`../RELEASING.md`](../RELEASING.md)를 보세요.

## 테스트

```bash
uv run pytest -q
```

결정론(시드 동일→결과 동일)·수식 안전성·빌드별 보스 공략 가능성(죽은 빌드 0) 가드·세션 라운드트립을 검증합니다. 동작을 바꾸면 회귀 테스트를 추가하세요([`../CONTRIBUTING.md`](../CONTRIBUTING.md)).
