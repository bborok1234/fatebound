"""엔진 단위 테스트 — 결정론(같은 시드=같은 결과)·공식·불변식(20 §5)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fatebound import content
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine.formula import evaluate
from fatebound.engine import balance


def _battle(build, zone="bamboo_grove", seed=1, boss=True):
    bag = Bag.auto(content.items_for_build(build))
    lo = Loadout.compile(bag)
    player = lo.make_player("t", balance.ZONE_LEVEL[zone])
    mobs = content.monsters_for_zone(zone)
    enemy = next((m for m in mobs if m.get("is_boss") == boss), mobs[0])
    return BattleM1(bag.cells, player, enemy, balance.ZONE_TIER[zone], Rng(seed)).run()


def test_formula_safe_and_correct():
    assert evaluate("0.6 * atk", {"atk": 100}) == 60
    assert evaluate("1.0 * atk + 5", {"atk": 10}) == 15
    assert evaluate("12") == 12
    assert evaluate("0.3 * atk 피해", {"atk": 40}) == 12   # 뒤꼬리 설명 제거
    assert evaluate("__import__('os')") == 0               # 코드 실행 차단


def test_determinism():
    a = _battle("poison", seed=42)
    b = _battle("poison", seed=42)
    assert a.outcome == b.outcome and a.rounds == b.rounds
    assert len(a.events) == len(b.events)


def test_all_builds_run_without_error():
    for build in ("poison", "crit", "guard", "dice"):
        r = _battle(build, boss=False)
        assert r.outcome in ("win", "loss", "timeout")
        assert r.rounds >= 1
        # 일반 몹은 대체로 승리(70%+ 목표) — 단일 시드라 약하게 검증
        assert r.player_hp_pct >= 0.0


def test_no_dead_build_vs_boss():
    """critic C1 회귀 가드: 어떤 빌드도 보스에 '구조적으로 0%(딜 창구 없음)'이면 안 됨.
    딜 창구 존재 증명 = 입문 보스(가장 쉬운)에서 12판 중 ≥1승. (존별 균형은 P1 스윕의 몫, 14)"""
    for build in ("poison", "crit", "guard", "dice"):
        wins = sum(1 for s in range(12) if _battle(build, "bamboo_grove", seed=s).outcome == "win")
        assert wins >= 1, f"{build}: 입문 보스 12판 전패 — 딜 창구 없음(C1 회귀)"


def test_combat_terminates():
    r = _battle("guard", "frost_spring_valley", seed=3)
    assert r.rounds <= balance.MAX_ROUNDS


def test_session_roundtrip():
    from fatebound.engine.session import GameSession
    s = GameSession.new_game("천기노조", "crit")
    s.gold, s.level, s.insight, s.reincarnations = 123, 9, 40, 2
    s.move(0, 4)
    d = s.to_dict()
    s2 = GameSession.from_dict(d)
    assert (s2.gold, s2.level, s2.insight, s2.reincarnations, s2.build) == (123, 9, 40, 2, "crit")
    assert [(c["item_id"] if c else None) for c in s2.bag.cells] == d["bag"]
    # 복원된 구궁이 다시 컴파일되는지(천명괘 산출)
    assert len(s2.loadout().faces) == 6
