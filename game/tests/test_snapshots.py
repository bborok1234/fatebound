"""CLI 비주얼 QA — Textual SVG 스냅샷 회귀(#28, 워크플로 6단계 중 QA). 비주얼 변경 시 골든 SVG와 비교.
baseline 갱신: `uv run pytest tests/test_snapshots.py --snapshot-update`. 의도된 변경이면 갱신 후 SVG 커밋.
SVG는 폰트 메트릭이 OS별로 미세하게 달라 baseline OS(darwin)에서만 비교 — CI macos 잡에서 게이트, 그 외 skip."""
import sys
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin",
                                reason="SVG 스냅샷은 baseline OS(darwin)에서만 비교(크로스OS 폰트 메트릭 회피)")

TERM = (120, 40)


def test_snapshot_buildselect(snap_compare):
    """계열 선택 화면(빌드 카드 + 프리뷰)."""
    from fatebound.tui.app import FateboundApp
    from fatebound.tui.screens.buildselect import BuildSelectScreen

    async def run_before(pilot):
        await pilot.app.push_screen(BuildSelectScreen())
        await pilot.pause()

    assert snap_compare(FateboundApp(), run_before=run_before, terminal_size=TERM)


def test_snapshot_dice_select(snap_compare):
    """천명괘(주사위) 선택 단계 — 계열 확정 후 2단계(#6 키스톤). 전환 애니메이션 없이 die 단계 직접(결정론)."""
    from fatebound.tui.app import FateboundApp
    from fatebound.tui.screens.buildselect import BuildSelectScreen, BUILD_ORDER

    async def run_before(pilot):
        scr = BuildSelectScreen()
        await pilot.app.push_screen(scr)
        await pilot.pause()
        scr.picked_build = BUILD_ORDER[0]
        scr.sel = 0
        scr.phase = "die"               # press 전환 대신 die 단계 직접 — 타이밍 의존 제거
        await pilot.pause()
        await pilot.pause()

    assert snap_compare(FateboundApp(), run_before=run_before, terminal_size=TERM)
