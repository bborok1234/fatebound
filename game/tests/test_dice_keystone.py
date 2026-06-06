"""천명괘 재질 키스톤(#6) 게이트 — 변수↔일관 메타축이 실재하고, 어떤 재질도 빌드를 깨거나 지배하지 않는다.
결정론 시드배틀. 재질 선택이 '의미있는' 선택임을 락인(혈옥 고분산 > 백옥 > 비취 일관)."""
import statistics as st
from fatebound import content
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1, DICE_MODS
from fatebound.engine.rng import Rng
from fatebound.engine import balance

GOOD = ["mandok_geom", "cheondok_ji", "azure_bamboo_venom_dagger", "doga_jeoldokchim",
        "heavenly_venom_blood_demon_sword", "chilbo_talhonsan", "myriad_venom_gu",
        "dokjeong_ju", "heungrin_gap"]


def _cells():
    I = {it["item_id"]: it for it in content.items_for_build("poison")}
    return [I[i] for i in GOOD]


def _enemy():
    return next(m for m in content.monsters_for_zone("frost_spring_valley") if m.get("is_boss"))


def _run(die, n=80):
    cells, enemy = _cells(), _enemy()
    lo = Loadout.compile(Bag(cells=cells))
    tier, lvl = balance.ZONE_TIER["frost_spring_valley"], balance.ZONE_LEVEL["frost_spring_valley"]
    wins, hits = 0, []
    for sd in range(n):
        r = BattleM1(cells, lo.make_player("x", lvl), enemy, tier, Rng(sd), die=die).run()
        wins += r.outcome == "win"
        hits += [e.amount for e in r.events if e.kind == "damage" and e.by_player]
    return wins / n, st.pstdev(hits) / st.mean(hits)   # (win-rate, 합당 피해 cv)


def test_each_die_viable():
    """5재질 모두로 발전한 빌드가 한천 보스를 깬다 — 어떤 재질도 빌드를 깨지 않음."""
    for die in DICE_MODS:
        wr, _ = _run(die, n=60)
        assert wr >= 0.6, f"{die} 재질로 GOOD@한천 승률 {wr:.0%} — 재질이 빌드를 깸"


def test_variance_consistency_axis():
    """변수↔일관 축이 실재: 혈옥(고분산) > 백옥(기준) > 비취(일관). 재질 선택이 출력 성격을 바꾼다."""
    cv_hyeol = _run("hyeolok")[1]
    cv_base = _run("baekok")[1]
    cv_bichwi = _run("bichwi")[1]
    assert cv_hyeol > cv_base, f"혈옥 cv {cv_hyeol:.3f}가 백옥 {cv_base:.3f}보다 안 큼 — 고분산 정체성 소멸"
    assert cv_bichwi < cv_base, f"비취 cv {cv_bichwi:.3f}가 백옥 {cv_base:.3f}보다 안 작음 — 일관 정체성 소멸"


def test_die_skin_persists(tmp_path, monkeypatch):
    """선택한 재질이 세이브에 영속(키스톤은 런 내내 유지)."""
    monkeypatch.setenv("FATEBOUND_SAVE_DIR", str(tmp_path))
    import importlib
    from fatebound import persistence
    importlib.reload(persistence)
    from fatebound.engine.session import GameSession
    s = GameSession.new_game("x", "crit", die_skin="hyeolok")
    persistence.save(s)
    loaded = persistence.load()
    assert loaded is not None and loaded.die_skin == "hyeolok", "die_skin이 세이브 라운드트립에서 유실"
