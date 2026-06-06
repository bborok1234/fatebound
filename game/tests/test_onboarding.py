"""온보딩 코치 회귀 가드(#16) — 클릭 경로 진행·Esc 비파괴·첫 전투 완주 완료.
헤드리스 Textual run_test를 asyncio.run으로 구동(pytest-asyncio 비의존, 스모크와 동일 패턴)."""
import asyncio
import os


def _scenario(coro):
    os.environ["FATEBOUND_REDUCED_MOTION"] = "1"
    import fatebound.persistence as P
    P.save = lambda *a, **k: None       # 세이브 부작용 차단
    return asyncio.run(coro())


def test_click_path_advances_coach():
    """클릭-only 유저도 코치가 진행해야(이전엔 coach=0 영구 정체). 집기 0→1, 놓기 1→2."""
    async def run():
        from fatebound.tui.app import FateboundApp
        from fatebound.tui.screens.game import GameScreen
        from fatebound.engine.session import GameSession
        msg = type("M", (), {"idx": 0})
        app = FateboundApp()
        async with app.run_test(size=(170, 50)) as pilot:
            scr = GameScreen(GameSession.new_game("x", "poison"), first_run=True)
            await app.push_screen(scr); await pilot.pause()
            c0 = scr.coach
            scr._on_cell_click(msg()); await pilot.pause()
            c1 = scr.coach
            scr._on_cell_click(msg()); await pilot.pause()
            return c0, c1, scr.coach
    c0, c1, c2 = _scenario(run)
    assert c0 == 0 and c1 == 1 and c2 == 2, f"클릭 코치 진행 실패 {c0}->{c1}->{c2}"


def test_esc_is_session_hide_not_permanent():
    """Esc는 이번 세션 숨김일 뿐 — tutorial_done을 영구 저장하지 않는다(오발 방지)."""
    async def run():
        from fatebound.tui.app import FateboundApp
        from fatebound.tui.screens.game import GameScreen
        from fatebound.engine.session import GameSession
        app = FateboundApp()
        s = GameSession.new_game("x", "poison")
        async with app.run_test(size=(170, 50)) as pilot:
            scr = GameScreen(s, first_run=True); await app.push_screen(scr); await pilot.pause()
            scr.coach = 1
            scr.action_dismiss_coach(); await pilot.pause()
            return scr.coach, s.tutorial_done
    coach, done = _scenario(run)
    assert coach is None and done is False, f"Esc가 영구 완료시킴 coach={coach} done={done}"


def test_build_intro_fires_once(monkeypatch):
    """빌드 고유 메커니즘 안내(#10)가 첫 전투에 1회만 발화(재전투 미발화). guard 받아넘김 예."""
    import asyncio
    import os
    os.environ["FATEBOUND_REDUCED_MOTION"] = "1"
    import fatebound.persistence as P
    P.save = lambda *a, **k: None

    async def run():
        from fatebound.tui.app import FateboundApp
        from fatebound.tui.screens.game import GameScreen
        from fatebound.engine.session import GameSession
        app = FateboundApp()
        s = GameSession.new_game("x", "guard")
        notes = []
        async with app.run_test(size=(170, 50)) as pilot:
            scr = GameScreen(s, first_run=True); await app.push_screen(scr); await pilot.pause()
            app.notify = lambda msg, **k: notes.append(k.get("title", ""))
            scr._play(boss=False)
            for _ in range(80):
                await asyncio.sleep(0.01); await pilot.pause()
            n1 = sum(t == "무공의 기틀" for t in notes)
            scr._play(boss=False)
            for _ in range(80):
                await asyncio.sleep(0.01); await pilot.pause()
            return ("intro_guard" in s.seen_events), n1, sum(t == "무공의 기틀" for t in notes)

    seen, n1, n2 = asyncio.run(run())
    assert seen and n1 == 1 and n2 == 1, f"빌드 인트로 발화 이상 seen={seen} 첫{n1} 누적{n2}"
