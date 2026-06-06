"""밸런스 회귀 게이트 (키스톤) — 시드배틀로 M1 밸런스를 밴드에 락인.

에이전트가 밸런스를 조정해도 '안 깼음'을 결정론적으로 증명하는 게이트.
밴드는 넓게(비-flaky) 잡되 큰 회귀(죽은 빌드·즉살·무한전투)는 잡는다. 정본 design/docs/25.
"""
import statistics as st
import pytest
from fatebound import content
from fatebound.engine.session import GameSession
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine import balance

N = 120


def _sim(cells, lvl, enemy, zone, die="baekok", n=N):
    lo = Loadout.compile(Bag(cells=cells))
    wins, rounds = 0, []
    for sd in range(n):
        p = lo.make_player("x", lvl)
        r = BattleM1(cells, p, enemy, balance.ZONE_TIER[zone], Rng(sd), die=die).run()
        wins += r.outcome == "win"
        rounds.append(r.rounds)
    return wins / n, st.median(rounds)


def _enemy(zone, boss=False):
    mobs = content.monsters_for_zone(zone)
    if boss:
        return next(m for m in mobs if m.get("is_boss"))
    return [m for m in mobs if not m.get("is_boss")][0]


GOOD = ["mandok_geom", "cheondok_ji", "azure_bamboo_venom_dagger", "doga_jeoldokchim",
        "heavenly_venom_blood_demon_sword", "chilbo_talhonsan", "myriad_venom_gu",
        "dokjeong_ju", "heungrin_gap"]


def _good_cells():
    I = {it["item_id"]: it for it in content.items_for_build("poison")}
    return [I[i] for i in GOOD]


def test_starter_poison_clears_early_normals():
    """신규 독 스타터가 입문 일반전을 진행 가능해야(라이트 잔존 가드). 죽은 스타터 금지."""
    s = GameSession.new_game("x", "poison")
    win, rounds = _sim(s.bag.cells, s.level, _enemy("bamboo_grove"), "bamboo_grove")
    assert win >= 0.85, f"스타터 독 입문 일반전 승률 과저 {win:.0%} — 죽은 스타터 회귀"
    assert 3 <= rounds <= 20, f"스타터 전투 합수 이상 {rounds}"


def test_good_build_endgame_challenging_but_winnable():
    """발전한 독 빌드가 한천 보스를 깨되 즉살은 아님(엔드 도전성)."""
    cells = _good_cells()
    win, rounds = _sim(cells, balance.ZONE_LEVEL["frost_spring_valley"],
                       _enemy("frost_spring_valley", boss=True), "frost_spring_valley")
    assert 0.6 <= win <= 1.0, f"GOOD@한천보스 승률 밴드 이탈 {win:.0%}"
    assert 5 <= rounds <= 16, f"GOOD@한천보스 합수 밴드 이탈 {rounds} (목표 8~16)"


def test_placement_matters():
    """배치가 출력을 바꾼다(M1 핵심): 전설 중앙 vs 코너 출력차 유의미."""
    from fatebound.engine.combat_m1 import cell_eff, OUTPUT_C
    cells = _good_cells()
    scale = (10 + 2.6 * 11) * OUTPUT_C
    out = lambda c: sum(cell_eff(c, i, scale) for i in range(9))
    base = out(cells)
    li = next(i for i, c in enumerate(cells) if c["item_id"] == "heavenly_venom_blood_demon_sword")
    corner = next(i for i in (0, 2, 6, 8) if i != li)
    c2 = list(cells)
    c2[li], c2[corner] = c2[corner], c2[li]       # 전설을 중앙(4)에서 코너로 빼면 출력 급감
    assert abs(out(c2) - base) / base >= 0.05, "배치가 출력을 거의 안 바꿈 — M1 묘미 회귀"


def test_placement_depth_healthy():
    """배치 깊이가 건강한 밴드(doc27 P7 다양성 게이트): 단순그리디 대비 의미있게 좋되(라이트 텔레그래프 가치)
    잔혹하진 않고, 영리한 휴리스틱 너머에도 진짜 깊이가 남아야(헤비 최적화·'1초 소트' 아님).
    후속 곱-버킷 리팩터가 배치를 평탄화/잔혹화하거나 그리디로 다 풀리게 만들면 여기서 잡힌다."""
    from fatebound.engine.m1_layout import placement_depth
    from fatebound.engine.combat_m1 import OUTPUT_C
    cells = _good_cells()
    scale = (10 + 2.6 * 11) * OUTPUT_C
    d = placement_depth(cells, scale, method="hill")
    assert 8 <= d["gap_vs_naive"] <= 50, f"배치 깊이(단순그리디 대비) {d['gap_vs_naive']:.1f}% — 평탄화/잔혹화 회귀"
    assert d["gap_vs_smart"] >= 2, f"영리 휴리스틱 너머 깊이 {d['gap_vs_smart']:.1f}% — 배치가 1초 소트로 전락"


def test_dice_materials_differentiated():
    """주사위 재질이 전투를 측정상 다르게 만든다(혈옥 최속 ≤ 백옥)."""
    cells = _good_cells()
    fz = "frost_spring_valley"
    enemy = _enemy(fz, boss=True)
    _, r_base = _sim(cells, balance.ZONE_LEVEL[fz], enemy, fz, die="baekok", n=60)
    _, r_hyeol = _sim(cells, balance.ZONE_LEVEL[fz], enemy, fz, die="hyeolok", n=60)
    assert r_hyeol <= r_base, f"혈옥(출력↑)이 백옥보다 안 빠름 {r_hyeol} vs {r_base}"


def test_battle_perf_budget():
    """엔진 속도 예산 — 1000 시드배틀이 충분히 빨라야(RSI 플레이루프 토대). 로컬 ~0.15s; CI 여유로 4s."""
    import time
    cells = _good_cells()
    lo = Loadout.compile(Bag(cells=cells))
    enemy = _enemy("frost_spring_valley", boss=True)
    tier = balance.ZONE_TIER["frost_spring_valley"]
    t0 = time.perf_counter()
    for sd in range(1000):
        p = lo.make_player("x", 20)
        BattleM1(cells, p, enemy, tier, Rng(sd)).run()
    elapsed = time.perf_counter() - t0
    assert elapsed < 4.0, f"1000 전투 {elapsed:.2f}s — 성능 회귀(예산 4s)"


def test_build_diversity_multiple_m1_families():
    """이중잔존(D1~D4)은 다수 viable 빌드 패밀리를 요구. poison+guard+crit 충족(2026-06).
    dice 추가 시 ≥4로 상향. 한 계열이라도 M1 스텁으로 회귀하면 잡는다."""
    from fatebound.engine.combat_m1 import _m1
    families = [b for b in ("poison", "crit", "guard", "dice")
                if sum(1 for it in content.items_for_build(b) if _m1(it)) >= 9]
    assert len(families) >= 3, f"M1 보유 빌드 패밀리 {families} — 다양 빌드 미충족(가설 미검증)"


@pytest.mark.parametrize("zone", ["bamboo_grove", "black_wind_forest", "frost_spring_valley"])
def test_combat_terminates(zone):
    """모든 존에서 전투가 MAX_ROUNDS 안에 종료(무한전투 금지)."""
    cells = _good_cells()
    lo = Loadout.compile(Bag(cells=cells))
    p = lo.make_player("x", balance.ZONE_LEVEL[zone])
    r = BattleM1(cells, p, _enemy(zone, boss=True), balance.ZONE_TIER[zone], Rng(1)).run()
    assert r.rounds <= balance.MAX_ROUNDS
