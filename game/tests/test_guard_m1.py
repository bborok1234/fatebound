"""guard 받아넘김(유능제강) 메커니즘 단위 테스트 (doc27 P5).

검증 대상은 *메커니즘 정확성*(block 경감·기 적립·전환기 반격·전환기 배치 깊이)이지
밸런스/viability가 아니다 — 실제 guard 아이템 스탯·승률 밴드는 다양성 게이트가 별도 검증.
합성 무공으로 엔진 로직만 락인(실제 아이템 도입 후에도 메커니즘 회귀 차단).
"""
from fatebound import content
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine import balance
from fatebound.engine.models import Combatant


def _p():
    return Combatant(name="x", max_hp=400, hp=400, atk=60, defense=20, spd=10, crit=0.0)


def _gi(name, **m):
    return {"item_id": name, "name_ko": name, "m1": m}


def _enemy():
    return [m for m in content.monsters_for_zone("frost_spring_valley") if not m.get("is_boss")][0]


BLOCK = _gi("벽", role="guard", base=0, amp=0.0, block=6.0)
CONV = _gi("전환기", role="converter", base=0, amp=0.0, fx="convert_ki", conv=0.45)
AMP = _gi("증폭", role="amplifier", base=0, amp=0.4, fx="amp_convert", block=0)


def _run(cells, seed=3):
    return BattleM1(cells, _p(), _enemy(), balance.ZONE_TIER["frost_spring_valley"], Rng(seed)).run()


def _first_enemy_hit(cells):
    r = _run(cells)
    return next(e.amount for e in r.events if e.kind == "damage" and not e.by_player)


def _total_reversal(cells):
    return sum(e.amount for e in _run(cells).events if e.kind == "ki_reversal")


def test_block_reduces_damage_taken():
    """guard block은 받는 피해를 줄인다(경감↑ = 저분산 생존, 라이트 친화)."""
    no_block = [_gi("무", role="conditional", base=0, amp=0.0)] * 9
    assert _first_enemy_hit([BLOCK] * 9) < _first_enemy_hit(no_block), "block이 피해를 안 줄임"


def test_ki_reversal_fires():
    """전환기 + block → 막은 피해가 기(氣)로 적립되어 반격 발생(받아넘김 작동)."""
    cells = [BLOCK] * 4 + [CONV] + [BLOCK] * 4
    assert _total_reversal(cells) > 0, "기 전환 반격이 발생 안 함"


def test_no_block_no_ki():
    """block 없으면 기 적립 0 → 전환기 있어도 반격 0(비-guard 빌드 무영향)."""
    cells = [CONV] + [_gi("무", role="conditional", base=0, amp=0.0)] * 8
    assert _total_reversal(cells) == 0, "block 없이 기가 쌓임(no-op 위반)"


def test_converter_placement_depth():
    """전환기 칸 위치가 총 반격을 바꾼다(중앙 지렛대 > 코너) = guard 배치 깊이."""
    center = [BLOCK] * 4 + [CONV] + [BLOCK] * 4          # 전환기 중앙(idx4, ×1.5)
    corner = [CONV] + [BLOCK] * 8                          # 전환기 코너(idx0, ×1.0)
    assert _total_reversal(center) > _total_reversal(corner) * 1.1, "전환기 배치가 거의 무의미"


def test_converter_adjacent_amp_boosts():
    """전환기에 증폭(amp)을 인접시키면 전환이 커진다(클러스터 보상 = 배치 결정)."""
    plain = [BLOCK] * 4 + [CONV] + [BLOCK] * 4
    amped = [BLOCK, AMP, BLOCK, BLOCK, CONV, BLOCK, BLOCK, BLOCK, BLOCK]  # 증폭(1)이 전환기(4)에 인접
    assert _total_reversal(amped) > _total_reversal(plain), "전환기 인접 증폭이 무의미"
