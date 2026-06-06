"""아키타입 다양성 게이트 (#11, LUDUS '죽은 아키타입 0') — 4 빌드 계열 모두 엔드게임 viable.
이중잔존(D1~D4)의 핵심: 어느 계열도 죽지 않는다. 밸런스 변경이 한 계열을 무력화하면 여기서 잡힌다."""
import statistics as st
from fatebound import content
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine import balance

FZ = "frost_spring_valley"

# 계열별 대표(발전한) 빌드 — 각 계열 정체성을 대표.
ARCHETYPE_BUILDS = {
    "poison": ["mandok_geom", "cheondok_ji", "azure_bamboo_venom_dagger", "doga_jeoldokchim",
               "heavenly_venom_blood_demon_sword", "chilbo_talhonsan", "myriad_venom_gu", "dokjeong_ju", "heungrin_gap"],
    "guard": ["armor_guardian_qi_plate", "immovable_king_body", "soul_shattering_strike", "fist_avalanche_counter",
              "mirror_reverse_heart_guard", "heaven_returning_counter", "armor_breaking_hand", "four_ounce_thousand_catty",
              "rebound_heart_mirror"],
    "crit": ["cheongeom_hyeollak", "danhon_seomgeom", "hoegwang_geomgap", "swift_short_sword", "oncrit_pierce_ring",
             "tiger_fang_ring", "finisher_killing_intent", "chain_link_sword", "demon_heart_blade"],
    "dice": ["artifact_heaven_compass_seal", "artifact_defying_heaven_blade_charm", "armor_returning_heaven_robe",
             "cheonun_boju", "cheongeop_seom", "cheongi_dungap", "pungnoe_bobeop", "geongon_jaejo_ban", "cheongi_soban"],
}


def _winrate(build, ids, n=80):
    pool = {it["item_id"]: it for it in content.items_for_build(build)}
    cells = [pool[i] for i in ids]
    lo = Loadout.compile(Bag(cells=cells))
    enemy = next(m for m in content.monsters_for_zone(FZ) if m.get("is_boss"))
    tier, lvl = balance.ZONE_TIER[FZ], balance.ZONE_LEVEL[FZ]
    wins, rounds = 0, []
    for sd in range(n):
        r = BattleM1(cells, lo.make_player("x", lvl), enemy, tier, Rng(sd)).run()
        wins += r.outcome == "win"; rounds.append(r.rounds)
    return wins / n, st.median(rounds)


def test_all_four_archetypes_viable():
    """4 계열 모두 한천 보스를 깬다(≥60%·즉살 아님) — 죽은 아키타입 0(이중잔존 토대)."""
    for build, ids in ARCHETYPE_BUILDS.items():
        wr, rounds = _winrate(build, ids)
        assert wr >= 0.6, f"{build} 계열 엔드 승률 {wr:.0%} < 60% — 죽은 아키타입(다양성 붕괴)"
        assert 5 <= rounds <= 20, f"{build} 계열 합수 {rounds} 밴드 이탈(즉살/무한)"
