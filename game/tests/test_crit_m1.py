"""crit 예기(銳氣) 메커니즘 단위 테스트 (doc27). 천명 강조 줄 치명타·고분산·예기 누적·비-crit no-op.
메커니즘 정확성만 검증(밸런스/viability는 다양성 게이트가 별도). 합성 무공으로 락인."""
import statistics as st
from fatebound import content
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine import balance
from fatebound.engine.models import Combatant


def _gi(name, **m):
    return {"item_id": name, "name_ko": name, "m1": m}


def _enemy():
    return [m for m in content.monsters_for_zone("frost_spring_valley") if not m.get("is_boss")][0]


CELLS = [_gi("칼", role="payload", base=4, amp=0.0)] * 9


def _p(crit, crit_dmg=2.0):
    return Combatant(name="x", max_hp=600, hp=600, atk=60, defense=20, spd=10, crit=crit, crit_dmg=crit_dmg)


def _run(player, cells=None, seed=3):
    return BattleM1(cells or CELLS, player, _enemy(), balance.ZONE_TIER["frost_spring_valley"], Rng(seed)).run()


def _crit_hits(events):
    return [e for e in events if e.kind == "damage" and e.by_player and e.crit]


def test_noncrit_no_crit_events():
    """crit 0 빌드는 치명타 발생 안 함(no-op — poison/guard 무영향)."""
    assert len(_crit_hits(_run(_p(0.0)).events)) == 0


def test_crit_fires_on_spotlit_line():
    """crit 높은 빌드는 천명 강조 줄 치명타가 발생."""
    assert len(_crit_hits(_run(_p(60.0)).events)) > 0, "crit 60%인데 치명타 0"


def test_crit_increases_variance():
    """crit 빌드는 합당 피해 분산이 더 크다(고분산·고점 정체성)."""
    def hits(cr):
        return [e.amount for e in _run(_p(cr, 2.2)).events if e.kind == "damage" and e.by_player]
    assert st.pstdev(hits(50.0)) > st.pstdev(hits(0.0)), "crit이 분산을 안 키움"


def test_crit_ramp_accumulates():
    """예기(crit_ramp) 무공은 합이 지날수록 치명확률을 누적 → 비-ramp보다 치명 잦음."""
    ramp = [_gi("예기", role="engine", base=2, amp=0.0, crit_ramp=8.0)] + [_gi("칼", role="payload", base=4, amp=0.0)] * 8
    plain = [_gi("칼", role="payload", base=4, amp=0.0)] * 9
    p1 = Combatant(name="x", max_hp=1500, hp=1500, atk=55, defense=25, spd=10, crit=3.0, crit_dmg=2.0)
    p2 = Combatant(name="x", max_hp=1500, hp=1500, atk=55, defense=25, spd=10, crit=3.0, crit_dmg=2.0)
    ramp_crits = len(_crit_hits(_run(p1, ramp).events))
    plain_crits = len(_crit_hits(_run(p2, plain).events))
    assert ramp_crits >= plain_crits, f"예기 ramp가 치명을 안 늘림 {ramp_crits} vs {plain_crits}"
