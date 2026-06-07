"""TUI 전투 게이트(#40) — 4 빌드 모두 헤드리스 마운트+전투가 무크래시·위젯안정으로 완주.
private 스모크의 핵심을 CI 공개 게이트로(3OS). asyncio.run 패턴(pytest-asyncio 비의존)."""
import asyncio
import os

import pytest

BUILDS = ["poison", "guard", "crit", "dice"]


def _fight_build(build):
    os.environ["FATEBOUND_REDUCED_MOTION"] = "1"
    import fatebound.persistence as P
    P.save = lambda *a, **k: None
    P.load = lambda *a, **k: None          # 외부/오염 세이브 비의존(타이틀 _save_line 격리)

    async def run():
        from fatebound.tui.app import FateboundApp
        from fatebound.tui.screens.game import GameScreen
        from fatebound.engine.session import GameSession
        app = FateboundApp()
        async with app.run_test(size=(170, 50)) as pilot:
            scr = GameScreen(GameSession.new_game("x", build))
            await app.push_screen(scr)
            await pilot.pause()
            n_before = len(list(scr.walk_children()))
            scr.speed = 64
            scr._play(boss=False)
            ok = False
            for _ in range(400):
                if not scr.busy:
                    ok = True
                    break
                await asyncio.sleep(0.004)
                await pilot.pause()
            await pilot.pause()
            n_after = len(list(scr.walk_children()))
            return ok, n_before, n_after

    return asyncio.run(run())


@pytest.mark.parametrize("build", BUILDS)
def test_build_mounts_and_fights(build):
    """각 빌드: 마운트→전투 완주(busy 해제)·위젯 누수 없음(±5)."""
    ok, n_before, n_after = _fight_build(build)
    assert ok, f"{build}: 전투가 끝나지 않음(400틱)"
    assert n_after <= n_before + 5, f"{build}: 위젯 누수 {n_before}→{n_after}"
