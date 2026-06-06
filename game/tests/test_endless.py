"""끝없는 강호 스케일(#9) 게이트 — 마지막 존 재격이 깊이별로 가팔라지는 도전 곡선을 갖는다.
결정론. 깊이 0=정규(클리어), 깊이↑=점진 한계(DPS 레이스). 즉사 절벽 아닌 완만 온셋."""
from fatebound import content
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine import balance
from fatebound.engine.session import GameSession

GOOD = ["mandok_geom", "cheondok_ji", "azure_bamboo_venom_dagger", "doga_jeoldokchim",
        "heavenly_venom_blood_demon_sword", "chilbo_talhonsan", "myriad_venom_gu",
        "dokjeong_ju", "heungrin_gap"]
FZ = "frost_spring_valley"


def _cells():
    I = {it["item_id"]: it for it in content.items_for_build("poison")}
    return [I[i] for i in GOOD]


def _sess(depth):
    s = GameSession.new_game("x", "poison")
    s.zone = FZ
    s.endless_depth = depth
    return s


def _wr(depth, n=60):
    s, cells = _sess(depth), _cells()
    enemy = s._enemy(boss=True)          # 깊이 스케일 반영된 적
    lo = Loadout.compile(Bag(cells=cells))
    tier, lvl = balance.ZONE_TIER[FZ], balance.ZONE_LEVEL[FZ]
    return sum(BattleM1(cells, lo.make_player("x", lvl), enemy, tier, Rng(sd)).run().outcome == "win"
               for sd in range(n)) / n


def test_endless_scales_enemy():
    """깊이>0이면 적 HP·공격이 가산 스케일된다(같은 존 재격이 강해짐)."""
    base = _sess(0)._enemy(boss=True)
    deep = _sess(8)._enemy(boss=True)
    assert deep["hp"] > base["hp"] and deep["atk"] > base["atk"], "엔드리스 깊이가 적을 안 키움"


def test_endless_challenge_curve():
    """깊이 0=정규 클리어 → 깊이↑로 승률 감쇠(도전 실재), 단 초반 깊이는 완만(즉사 절벽 아님)."""
    wr0, wr2, wr_deep = _wr(0), _wr(2), _wr(14)
    assert wr0 >= 0.9, f"깊이0 정규 보스 승률 {wr0:.0%} — 엔드리스 출발점이 이미 과난"
    assert wr2 >= 0.5, f"깊이2 승률 {wr2:.0%} — 너무 이른 절벽(완만 온셋 위반)"
    assert wr_deep < wr0, f"깊은 곳 승률 {wr_deep:.0%}가 안 떨어짐 — 도전 곡선 부재"


def test_endless_depth_persists():
    """endless_depth가 세이브 라운드트립에 영속(런 내내 누적 유지)."""
    s = _sess(7)
    loaded = GameSession.from_dict(s.to_dict())
    assert loaded.endless_depth == 7, "endless_depth 라운드트립 유실"
