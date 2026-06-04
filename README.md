<h1 align="center">Fatebound · 天命回歸 · 천명회귀</h1>

<p align="center">
  <b>터미널에서 즐기는 무협 회귀 로그라이트 오토배틀러.</b><br>
  주사위(천명괘)에 무공을 새기고, 구궁(九宮)에 배치하고, 죽으면 회귀하여 더 강해진다.
</p>

<p align="center">
  <a href="https://github.com/bborok1234/fatebound/actions/workflows/ci.yml"><img src="https://github.com/bborok1234/fatebound/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange" alt="License: PolyForm Noncommercial">
  <img src="https://img.shields.io/badge/TUI-Textual-5a3fc0" alt="Textual TUI">
</p>

> **English TL;DR** — A wuxia "regression" (回歸) roguelite autobattler that runs entirely in your terminal. Forge martial arts onto a 6-faced fate die, arrange them on a 3×3 grid, set up your build, and let the battle auto-resolve with a single hand-played special move. Die, regress, grow stronger — endlessly. Built with [Textual](https://textual.textualize.io/). Source-available under a **noncommercial** license (see [License](#-라이선스)).

---

## ✨ 무엇인가

- **회귀 = 로그라이트 메타루프** — 한 생(run)은 휘발되지만, 죽음은 곧 영구 성장이다. 다음 생은 더 강한 경지에서 시작한다.
- **주사위 × 구궁(九宮)** — 6면 주사위(천명괘)의 각 면에 무공을 묶고, 3×3 격자에 배치해 방향성 상생(인접 시너지)을 짠다.
- **세팅 후 자동 전투 + 비장(秘藏)의 수** — 전투는 자동으로 흐르되, 한 번의 결정적 수(秘藏)는 직접 친다. 빌드 설계가 전부.
- **비주얼 TUI** — 수묵(水墨) 테마, 구궁 위젯, HP/내공/비장 게이지, 애니메이션 전투 재생. 100% 터미널.
- **세이브 / 이어하기** — 전투·배치·회귀가 자동 저장된다.

4개의 무공 기틀(독 · 치명 · 방어반격 · 주사위)로 시작해, 강호를 누비며 끝없이 성장한다.

## 🚀 설치 & 실행

### 파이썬이 있다면 (권장)

```bash
uvx fatebound            # 설치 없이 즉시 실행 (uv)
uv tool install fatebound   # 전역 설치 → 이후 그냥 `fatebound`
pipx install fatebound      # pipx 사용자
```

> [uv](https://docs.astral.sh/uv/)가 없다면: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 파이썬이 없다면

[**Releases**](https://github.com/bborok1234/fatebound/releases)에서 OS별 단일 실행 바이너리를 받으세요 (파이썬 불필요).

| OS | 파일 |
| --- | --- |
| Linux x86_64 | `fatebound-linux-x86_64` |
| macOS (Apple Silicon) | `fatebound-macos-arm64` |
| Windows x86_64 | `fatebound-windows-x86_64.exe` |

```bash
chmod +x fatebound-*        # macOS/Linux
./fatebound-macos-arm64
```

## 🎮 조작

| 키 | 동작 |
| --- | --- |
| **방향키** | 구궁 커서 이동 |
| **Enter** | 무공 집기 / 놓기 |
| **Space** | 전투 시작 |
| **B** | 보스전 |
| **F** | 전투 재생 배속 |
| **Q** | 종료 |

> 터미널은 24비트 트루컬러 + 유니코드(한글 전각)를 지원하는 환경(예: iTerm2, Windows Terminal, 최신 GNOME Terminal)을 권장합니다.

## 🛠 소스에서 빌드 / 개발

```bash
git clone https://github.com/bborok1234/fatebound.git
cd fatebound/game
uv sync                 # .venv + 잠금(uv.lock) 기반 의존성 설치 (+ dev)
uv run fatebound         # 게임 실행
uv run pytest -q        # 테스트
```

자세한 기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md), 릴리스 절차는 [RELEASING.md](RELEASING.md)를 참고하세요.

## 🧱 구조 (엔진 = 권위 / 표현층 분리)

```
fatebound/
└── game/                      플레이 가능한 프로덕션 패키지
    └── fatebound/
        ├── engine/            순수 게임 로직(I/O 0) — 권위 코어
        │                      models·rng·formula·events·balance·bag·combat·session·render_text
        ├── content/data/      번들 콘텐츠(아이템·몬스터·지역·사건 JSON)
        ├── tui/               Textual 앱 — 화면·위젯·테마
        ├── persistence/       세이브(원자적 쓰기·자동저장)
        └── cli.py             진입점 (--version / --selftest)
```

- **전투 = 이벤트 스트림**: `engine.combat`이 타입 이벤트(주사위·피해·상태이상·비장…)를 emit → TUI는 애니메이션 재생, 텍스트 렌더러는 무협 로그로 변환. 숫자/결과는 엔진이 확정한다(형태 독립적).
- 게임 설계의 상세 기획 문서(세계관·밸런스 수치·운영 로드맵 등)는 별도로 비공개 관리됩니다. 공개 레포는 **플레이 가능한 게임 코드와 런타임 데이터**를 담습니다.

## 🤝 기여

버그 리포트·기능 제안·PR을 환영합니다. 시작 전에 [CONTRIBUTING.md](CONTRIBUTING.md)와 [행동 강령](CODE_OF_CONDUCT.md)을 읽어 주세요. 보안 이슈는 [SECURITY.md](SECURITY.md)의 절차를 따라 주세요.

## 📜 라이선스

[**PolyForm Noncommercial License 1.0.0**](LICENSE) — 학습·수정·재배포는 자유지만 **상업적 이용은 허용되지 않습니다**. (비상업 제한이 있으므로 OSI 정의상 "오픈소스"가 아닌 *source-available*로 분류됩니다.) 상업적 라이선스가 필요하면 아래로 문의하세요.

> Required Notice: Copyright 2026 Mir Lim (https://github.com/bborok1234/fatebound)

문의: [@bborok1234](https://github.com/bborok1234)
