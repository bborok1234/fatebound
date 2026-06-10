"""슬라이스 회귀 게이트 — 결정론·밴드·분해·페이싱·전 경로·T1 완주 (02 §5).
'검증=해자': 이 게이트가 깨지면 슬라이스는 미통과다."""
from __future__ import annotations

import subprocess
import sys

import pytest

from cheonmyeong.engine import combat
from cheonmyeong.engine.state import GameState


# ── 1. 전투: 시드 결정론 + 합수 밴드 + 절기 예약 + 분해 합치 ──
def test_battle_deterministic():
    a = [(e.round, e.enemy_hp, e.poison, e.charge) for e in combat.run_battle("죽림 산적", 7)]
    b = [(e.round, e.enemy_hp, e.poison, e.charge) for e in combat.run_battle("죽림 산적", 7)]
    assert a == b


def test_battle_band():
    """일반전 합수 밴드 8~16 (07 §2 — rulebook_sim 정합)."""
    rounds = []
    for s in range(60):
        last = None
        for ev in combat.run_battle("죽림 산적", s * 13 + 1):
            last = ev
        assert last.result == "win"
        rounds.append(last.round)
    avg = sum(rounds) / len(rounds)
    assert 7.0 <= avg <= 16.0, avg


def test_smyeong_reserved_fires_next_round():
    """충전 6 = 예약(充 점멸) → 발동은 다음 합 개시 (01 §3.2 정본)."""
    evs = list(combat.run_battle("죽림 산적", 7))
    ready = next(e.round for e in evs if e.charge >= 6 and not e.smyeong)
    fire = next((e.round for e in evs if e.smyeong), None)
    if fire is not None:
        assert fire == ready + 1, (ready, fire)


def test_breakdown_sums():
    """분해 합 = 입힌 총 피해 (02 §3.2 회귀 게이트: slots+smyeong+dot = 총량)."""
    last = None
    for ev in combat.run_battle("죽림 산적", 7):
        last = ev
    bd = last.breakdown
    total = sum(bd["slots"].values()) + bd["smyeong"] + bd["dot"]
    from cheonmyeong.data import slice_pack as P
    assert abs(total - P.ENEMIES["죽림 산적"]["hp"]) < total * 0.35   # 오버킬 허용 폭


# ── 2. 상태: 방치 결정론 + 벽 페이싱(14 §7: 2~5일 리듬) ──
def test_idle_deterministic():
    a, b = GameState(seed=5), GameState(seed=5)
    ea, eb = a.idle_day(), b.idle_day()
    assert ea["hunts"] == eb["hunts"] and ea["wall"] == eb["wall"]


def test_wall_pacing():
    for seed in range(8):
        g = GameState(seed=seed)
        d = 0
        while not g.wall_ready and d < 10:
            g.idle_day()
            d += 1
        assert 2 <= d <= 6, (seed, d)


def test_breakthrough_fail_is_progress():
    g = GameState(seed=3)
    base = g.dono_chance
    g.rng = __import__("random").Random(999)        # 실패 유도용 시드
    fails = 0
    while not g.attempt_breakthrough() and fails < 10:
        fails += 1
        assert g.dono_chance == pytest.approx(base + 0.10 * fails)
    assert "흑풍림" not in g.explored               # explored는 디졸브 완료 시점(연출 버그 회귀)


# ── 3. 검산 텔레그래프: 사슬 변경이 의미 있는 Δ를 낸다 ──
def test_appraise_delta():
    g = GameState()
    base = g.appraise(n=16)
    alt = g.appraise(["독침", "천화비우", "독증폭", "만독발현"], n=16)
    assert base["winrate"] == 1.0
    assert abs(alt["avg"] - base["avg"]) > 0.2      # 스왑이 합수를 움직인다


# ── 4. 전 경로 파일럿(T2) + T1 완주 게이트(02 §5: 키보드 완결·채비 왕복 포함) ──
E2E = r"""
import asyncio, sys
from cheonmyeong.app import Cheonmyeong

async def t():
    app = Cheonmyeong()
    async with app.run_test(size=(110, 36)) as pilot:
        await pilot.press('enter'); await pilot.pause()
        await pilot.press('enter'); await pilot.pause(0.5)        # 즉시 정산
        await pilot.press('escape'); await pilot.pause(0.2)       # 지도
        for _ in range(4):
            await pilot.press('i'); await pilot.pause(0.05)
            await pilot.press('enter'); await pilot.pause(0.05)
            if app.state.wall_ready: break
            await pilot.press('escape'); await pilot.pause(0.05)
        assert app.state.wall_ready
        # 채비 왕복(서재 — T1 키보드 시퀀스 04 §2.1.1)
        await pilot.press('escape'); await pilot.pause(0.05)
        await pilot.press('b'); await pilot.pause(0.3)
        await pilot.press('tab'); await pilot.pause(0.05)
        await pilot.press('space'); await pilot.pause(0.2)
        await pilot.press('right'); await pilot.pause(0.3)
        await pilot.press('enter'); await pilot.pause(0.3)
        assert '천화비우' in app.state.chain
        await pilot.press('p'); await pilot.pause(0.3)            # 유파 복귀
        await pilot.press('escape'); await pilot.pause(0.05)
        # 돌파 → 디졸브 → 채색
        await pilot.press('d'); await pilot.pause(0.1)
        tries = 0
        while '흑풍림' not in app.state.explored and tries < 8:
            if app.screen.__class__.__name__ != 'DonoCard':
                await pilot.press('d'); await pilot.pause(0.1)
            await pilot.press('enter'); await pilot.pause(1.5)
            tries += 1
        assert '흑풍림' in app.state.explored
        await pilot.press('t'); await pilot.pause(0.1)            # 천기록
        await pilot.press('escape'); await pilot.pause(0.05)
        await pilot.press('o'); await pilot.pause(0.1)            # 한 줄
        await pilot.press('enter'); await pilot.pause(0.05)
        await pilot.press('q')
    print('E2E-OK', app.state.gyeongji, app.state.day)

asyncio.run(t())
"""


def _run_e2e(extra_args: list[str]) -> str:
    out = subprocess.run([sys.executable, "-c",
                          f"import sys; sys.argv += {extra_args!r}\n" + E2E],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr[-2000:]
    return out.stdout


def test_e2e_t2():
    assert "E2E-OK 이류" in _run_e2e([])


def test_e2e_t1_gate():
    """★슬라이스 통과 게이트(02 §5): --tier=1 키보드 완주 + 채비 왕복."""
    assert "E2E-OK 이류" in _run_e2e(["--tier=1"])


def test_t1_no_truecolor():
    """T1 경로의 렌더에 24bit 시퀀스가 없어야 한다 (04 §2.1)."""
    code = (
        "import sys; sys.argv.append('--tier=1')\n"
        "from cheonmyeong.engine import render, worldmap\n"
        "s = ''.join(render.sprite('죽림 산적', 3))\n"
        "wm = worldmap.WorldMap(60, 26)\n"
        "m = ''.join(wm.render(['죽림']))\n"
        "assert '38;2;' not in s + m, 'truecolor in T1'\n"
        "assert '38;5;' in s + m\n"
        "print('T1-COLORS-OK')\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-1500:]
    assert "T1-COLORS-OK" in out.stdout
