# 릴리스 · 배포 가이드 (uv + GitHub Actions)

Fatebound(`game/`)을 자동으로 빌드·배포하는 흐름. 패키지 관리는 **uv**, CI/CD는 **GitHub Actions**(`.github/workflows/`).

## 한눈에
- **푸시/PR** → `ci.yml`: OS(리눅스·맥·윈도우) × Python(3.11~3.13) 매트릭스로 `uv sync --locked` + `pytest` + `--selftest`.
- **태그 `vX.Y.Z` 푸시** → `release.yml`: 3-OS **스탠드얼론 바이너리**(PyInstaller `--onefile`) + **휠/sdist**(`uv build`) 빌드 → **GitHub Release에 자동 첨부**. (선택) PyPI 게시.

## 0. 최초 1회 — GitHub에 올리기
```bash
# 레포 루트에서 (이미 git init·main 브랜치 됨)
git add -A && git commit -m "Fatebound: 기획 + P1 빌드 + uv/CI"
gh repo create fatebound --public --source=. --push     # 또는 GitHub에서 레포 생성 후 git remote add + push
```
푸시되면 `ci.yml`이 자동 실행된다(녹색 확인).

## 1. 릴리스 (바이너리 + 휠 배포)
```bash
# 1) 버전 올리기 — 두 곳을 같은 값으로
#    game/pyproject.toml  [project] version = "0.2.0"
#    game/fatebound/__init__.py  __version__ = "0.2.0"
# 2) 잠금 갱신(필요 시) + 커밋
cd game && uv lock && cd ..
git add -A && git commit -m "release: v0.2.0"
# 3) 태그 푸시 → release.yml 트리거
git tag v0.2.0 && git push origin main --tags
```
→ Actions가 끝나면 **Releases** 탭에 다음이 첨부된다:
- `fatebound-linux-x86_64` · `fatebound-macos-arm64` · `fatebound-windows-x86_64.exe` (파이썬 불필요)
- `fatebound-0.2.0-py3-none-any.whl` · `fatebound-0.2.0.tar.gz`

## 2. (선택) PyPI 자동 게시 — Trusted Publishing(토큰리스)
1. [PyPI](https://pypi.org) 계정 → **Publishing** → *Add a trusted publisher*:
   - Owner: `<github-user>` · Repo: `fatebound` · Workflow: `release.yml` · Environment: `pypi`
2. GitHub 레포 → Settings → **Variables** → `PUBLISH_PYPI = true` (이 변수가 없으면 publish-pypi 잡은 스킵).
3. 이후 태그 릴리스 시 `uv publish`가 OIDC로 토큰 없이 게시 → 유저는 `uvx fatebound` / `pipx install fatebound` 가능.
   (먼저 TestPyPI로 시험하려면 trusted publisher를 test.pypi.org에 등록하고 `uv publish --publish-url https://test.pypi.org/legacy/`.)

## 3. 유저 설치 경로
| 대상 | 방법 |
| --- | --- |
| 파이썬 사용자 | `uvx fatebound`(즉시 실행) · `uv tool install fatebound` · `pipx install fatebound` |
| 파이썬 없음 | GitHub Release에서 OS 바이너리 다운로드 → 실행 (`chmod +x` 후 `./fatebound-*`) |
| Claude Code/Codex | (예정) Agent Skill 배포 — 별도 채널 |

## 4. 로컬에서 릴리스 산출물 미리 만들기
```bash
cd game
uv build                                          # dist/*.whl, *.tar.gz
uv run pyinstaller --onefile --name fatebound \
  --collect-all textual --collect-data fatebound --noconfirm _entry.py
./dist/fatebound --selftest                        # frozen 검증
```

## 메모
- **버전 단일화 주의:** `pyproject.toml`과 `__init__.py.__version__` 두 곳을 항상 같이 올린다(향후 `hatch-vcs`로 태그 기반 단일화 가능 — 개선 후보).
- 바이너리는 **빌드한 OS/arch에서만** 동작(matrix가 OS별 생성). macOS는 `macos-latest`=arm64. x86_64 맥/리눅스 arm이 필요하면 matrix에 러너 추가.
- `setup-uv` 액션 버전은 주기적으로 최신(현재 v7, v8 존재) 확인 후 bump.
