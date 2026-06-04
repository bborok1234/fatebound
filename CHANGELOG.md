# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다. 형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따르며, 버전은 [유의적 버전(SemVer)](https://semver.org/lang/ko/)을 지향합니다.

## [Unreleased]

### Added — 첫 공개 빌드 (P1)

- **회귀 로그라이트 메타루프** — 죽음이 곧 영구 성장이 되는 회귀(回歸) 구조.
- **주사위 × 구궁(九宮)** — 6면 주사위(천명괘)의 면에 무공을 묶고 3×3 격자에 배치, 방향성 인접 시너지.
- **세팅 후 자동 전투 + 비장(秘藏)의 수** — 자동 전투 + 한 번의 수동 결정타.
- **4종 무공 기틀** — 독 · 치명 · 방어반격 · 주사위.
- **비주얼 TUI** — 수묵 테마, 구궁 위젯, HP/내공/비장 게이지, 애니메이션 전투 재생([Textual](https://textual.textualize.io/)).
- **세이브 / 이어하기** — 전투·배치·회귀 자동 저장(원자적 쓰기).
- **배포** — `uvx fatebound` / `uv tool install` / `pipx`, OS별 스탠드얼론 바이너리(Linux·macOS·Windows), `--version`·`--selftest` CLI.
- **CI/CD** — GitHub Actions: OS × Python 3.11~3.13 매트릭스 테스트, 태그(`v*`) → 바이너리/휠 자동 릴리스.

---

> 첫 공개 릴리스부터 `## [0.1.0] - YYYY-MM-DD` 형식의 버전 섹션을 추가해 운영합니다.
