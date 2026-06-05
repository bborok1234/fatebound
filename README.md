<h1 align="center">Fatebound · 天命回歸 · 천명회귀</h1>

<p align="center">
  <b>터미널에서 돌아가는 무협 로그라이트 오토배틀러.</b><br>
  스킬을 주사위 면에 새겨 굴리고 죽으면 다시 시작하며 점점 강해진다.
</p>

<p align="center">
  <a href="https://github.com/bborok1234/fatebound/actions/workflows/ci.yml"><img src="https://github.com/bborok1234/fatebound/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-PolyForm%20Noncommercial-orange" alt="License: PolyForm Noncommercial">
  <img src="https://img.shields.io/badge/TUI-Textual-5a3fc0" alt="Textual TUI">
</p>

> **English TL;DR** — A wuxia "regression" (回歸) roguelite autobattler that runs entirely in your terminal. Forge martial arts onto a 6-faced fate die, arrange them on a 3×3 grid, set up your build, and let the battle auto-resolve with a single hand-played special move. Die, regress, grow stronger, endlessly. Built with [Textual](https://textual.textualize.io/). Source-available under a **noncommercial** license (see [License](#-라이선스)).

---

## 게임 소개

Fatebound는 터미널에서 즐기는 무협 로그라이트 오토배틀러입니다. 직접 조작하는 액션 게임이 아니라, 전투에 들어가기 전에 빌드를 짜두면 싸움은 자동으로 풀립니다. 한 판이 끝나면 처음으로 돌아가지만 그때마다 조금씩 강해지고, 그렇게 더 깊은 곳까지 나아갑니다.

- **빌드를 짜면 전투는 자동.** 스킬을 주사위 면에 새기고 격자에 배치해 서로 맞물리게 합니다. 판마다 한 번 직접 쓰는 필살기가 승부처입니다.
- **죽어도 손해는 없습니다.** 처음부터 다시 시작하지만 성장은 영구히 남습니다(로그라이트). 매번 더 멀리 갑니다.
- **갈림길에서 길을 고릅니다.** Slay the Spire처럼 전투, 상점, 랜덤 이벤트, 보스 중 하나를 골라 나아가는 분기 맵입니다.
- **네 가지 빌드.** 독을 쌓거나, 치명타로 한 방을 노리거나, 받아치며 버티거나, 주사위 확률 자체를 조작하거나.
- **터미널 안의 비주얼.** 격자, 게이지, 애니메이션 전투가 전부 텍스트로 살아 움직입니다([Textual](https://textual.textualize.io/) 기반).

배경은 무협입니다. 죽은 고수가 풋내기 몸으로 다시 태어나 한 번 잃었던 강호를 밑바닥부터 헤쳐 나갑니다.

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
| **방향키** | 격자 커서 이동 |
| **Enter** | 스킬 집기 / 놓기 |
| **Space** | 지도 (다음 갈림길) |
| **I** | 인벤토리 (모은 스킬 장착) |
| **F** | 전투 재생 배속 |
| **?** | 도움말 |
| **Q** | 종료 |

> 터미널은 24비트 트루컬러와 유니코드(한글 전각)를 지원하는 환경을 권장합니다. iTerm2, Windows Terminal, 최신 GNOME Terminal 정도면 충분합니다.

## 🛠 소스에서 빌드 / 개발

```bash
git clone https://github.com/bborok1234/fatebound.git
cd fatebound/game
uv sync                 # .venv + 잠금(uv.lock) 기반 의존성 설치 (+ dev)
uv run fatebound         # 게임 실행
uv run pytest -q        # 테스트
```

자세한 기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md), 릴리스 절차는 [RELEASING.md](RELEASING.md)를 참고하세요.

## 🧱 구조 (엔진이 권위, 표현층은 분리)

```
fatebound/
└── game/                      플레이 가능한 프로덕션 패키지
    └── fatebound/
        ├── engine/            순수 게임 로직(I/O 0). 권위 코어
        │                      models·rng·formula·events·balance·bag·combat·session·render_text
        ├── content/data/      번들 콘텐츠(아이템·몬스터·지역·사건 JSON)
        ├── tui/               Textual 앱. 화면·위젯·테마
        ├── persistence/       세이브(원자적 쓰기·자동저장)
        └── cli.py             진입점 (--version / --selftest)
```

- **전투는 이벤트 스트림이다.** `engine.combat`이 타입 이벤트(주사위 굴림·피해·상태이상·필살기…)를 흘려보내면, TUI는 그걸 애니메이션으로 재생하고 텍스트 렌더러는 무협풍 로그로 옮긴다. 숫자와 결과는 엔진이 확정하므로 표현층이 무엇이든 결과는 같다.
- 세계관·밸런스 수치·운영 로드맵 같은 상세 기획 문서는 비공개로 따로 관리한다. 공개 레포에는 **플레이 가능한 게임 코드와 런타임 데이터**가 들어 있다.

## 🤝 기여

버그 리포트, 기능 제안, PR 모두 환영합니다. 시작 전에 [CONTRIBUTING.md](CONTRIBUTING.md)와 [행동 강령](CODE_OF_CONDUCT.md)을 읽어 주세요. 보안 이슈는 [SECURITY.md](SECURITY.md)의 절차를 따라 주세요.

## 📜 라이선스

[**PolyForm Noncommercial License 1.0.0**](LICENSE). 학습, 수정, 재배포는 자유지만 **상업적 이용은 허용되지 않습니다**. 비상업 제한이 있으니 OSI 정의상 "오픈소스"가 아니라 source-available로 분류됩니다. 상업적 라이선스가 필요하면 아래로 문의하세요.

> Required Notice: Copyright 2026 Mir Lim (https://github.com/bborok1234/fatebound)

문의: [@bborok1234](https://github.com/bborok1234)
