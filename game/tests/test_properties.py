"""속성 기반 테스트(Hypothesis) — 불변식을 무작위 입력으로 깨보기.

OOPSLA'25: PBT가 단위테스트 대비 ~50배 더 많은 변이를 잡음. 고ROI 안전망(doc 25).
"""
from hypothesis import given, strategies as st, settings, HealthCheck
import pytest
from fatebound import content
from fatebound.engine.formula import evaluate
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1, cell_eff
from fatebound.engine.rng import Rng
from fatebound.engine import balance

_I = {it["item_id"]: it for it in content.items_for_build("poison")}
_GOOD = ["mandok_geom", "cheondok_ji", "azure_bamboo_venom_dagger", "doga_jeoldokchim",
         "heavenly_venom_blood_demon_sword", "chilbo_talhonsan", "myriad_venom_gu",
         "dokjeong_ju", "heungrin_gap"]
_CELLS = [_I[i] for i in _GOOD]
_ENEMY = next(m for m in content.monsters_for_zone("frost_spring_valley") if m.get("is_boss"))


# ── 보안 핵심: 수식 평가기는 어떤 입력에도 코드 실행/예외 없이 float ──
@given(st.text())
@settings(max_examples=300)
def test_formula_never_raises_or_executes(s):
    r = evaluate(s, {"atk": 50})
    assert isinstance(r, (int, float))           # 항상 숫자(파싱 실패=0), 예외 전파 없음


@given(st.sampled_from(["__import__('os')", "open('/etc/passwd')",
                        "().__class__", "atk.__class__", "os.system('x')"]))
def test_formula_blocks_adversarial(payload):
    # 코드 실행/속성접근 시도(추출가능 리터럴 없음)는 화이트리스트가 0으로 차단
    assert evaluate(payload, {"atk": 10}) == 0


@given(st.floats(min_value=0, max_value=10, allow_nan=False, allow_infinity=False),
       st.integers(min_value=1, max_value=9999))
def test_formula_linear_correct(c, atk):
    assert evaluate(f"{c} * atk", {"atk": atk}) == pytest.approx(c * atk, rel=1e-6, abs=1e-6)


# ── 전투 불변식: 어떤 시드에도 HP 범위·종료·유효 결과 ──
@given(st.integers(min_value=0, max_value=10**6))
@settings(max_examples=120, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_combat_invariants(seed):
    p = Loadout.compile(Bag(cells=_CELLS)).make_player("x", balance.ZONE_LEVEL["frost_spring_valley"])
    r = BattleM1(_CELLS, p, _ENEMY, balance.ZONE_TIER["frost_spring_valley"], Rng(seed)).run()
    assert r.outcome in ("win", "loss", "timeout")
    assert 0.0 <= r.player_hp_pct <= 1.0
    assert 1 <= r.rounds <= balance.MAX_ROUNDS    # 항상 종료


@given(st.permutations(list(range(9))))
@settings(max_examples=80)
def test_build_output_nonnegative_any_arrangement(perm):
    cells = [_CELLS[i] for i in perm]
    out = sum(cell_eff(cells, i, 2.0) for i in range(9))
    assert out >= 0.0                             # 어떤 배치도 음수 출력 불가


@given(st.integers(0, 10**6))
@settings(max_examples=40)
def test_determinism(seed):
    tier = balance.ZONE_TIER["frost_spring_valley"]

    def run():
        p = Loadout.compile(Bag(cells=_CELLS)).make_player("x", 20)
        return BattleM1(_CELLS, p, _ENEMY, tier, Rng(seed)).run()
    a, b = run(), run()
    assert a.outcome == b.outcome and a.rounds == b.rounds and len(a.events) == len(b.events)
