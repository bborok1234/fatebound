"""dice 빌드(천명 조작) 게이트 (#25, 4번째 아키타입) — viability + '넓은 강조' 정체성 + 비-dice no-op.
결정론. dice 정체성=여러 줄을 동시 강조(단일줄 집중과 직교). 비-dice 빌드는 단일 무작위 줄(무회귀)."""
import statistics as st
from fatebound import content
from fatebound.engine.bag import Bag, Loadout
from fatebound.engine.combat_m1 import BattleM1
from fatebound.engine.rng import Rng
from fatebound.engine import balance

FZ = "frost_spring_valley"
DICE = ["artifact_heaven_compass_seal", "artifact_defying_heaven_blade_charm", "armor_returning_heaven_robe",
        "cheonun_boju", "cheongeop_seom", "cheongi_dungap", "pungnoe_bobeop", "geongon_jaejo_ban", "cheongi_soban"]
POISON = ["mandok_geom", "cheondok_ji", "azure_bamboo_venom_dagger", "doga_jeoldokchim",
          "heavenly_venom_blood_demon_sword", "chilbo_talhonsan", "myriad_venom_gu", "dokjeong_ju", "heungrin_gap"]


def _cells(build, ids):
    I = {it["item_id"]: it for it in content.items_for_build(build)}
    return [I[i] for i in ids]


def _boss():
    return next(m for m in content.monsters_for_zone(FZ) if m.get("is_boss"))


def _spot_lines(cells, seed=3):
    r = BattleM1(cells, Loadout.compile(Bag(cells=cells)).make_player("x", balance.ZONE_LEVEL[FZ]),
                 _boss(), balance.ZONE_TIER[FZ], Rng(seed)).run()
    return [1 + len(e.data.get("extra", [])) for e in r.events if e.kind == "m1_line"]


def test_dice_build_viable():
    """dice 빌드가 한천 보스를 깨되 즉살 아님(viable·밴드 내)."""
    cells = _cells("dice", DICE)
    lo = Loadout.compile(Bag(cells=cells))
    wins, rounds = 0, []
    for sd in range(80):
        r = BattleM1(cells, lo.make_player("x", balance.ZONE_LEVEL[FZ]), _boss(), balance.ZONE_TIER[FZ], Rng(sd)).run()
        wins += r.outcome == "win"; rounds.append(r.rounds)
    assert 0.6 <= wins / 80 <= 1.0, f"dice@한천 승률 밴드 이탈 {wins / 80:.0%}"
    assert 5 <= st.median(rounds) <= 18, f"dice@한천 합수 밴드 이탈 {st.median(rounds)}"


def test_dice_widens_spotlight():
    """dice 정체성: 매 합 여러 줄을 동시 강조(천명 조작). 단일줄 집중과 직교."""
    assert st.mean(_spot_lines(_cells("dice", DICE))) > 1.5, "dice 빌드가 단일줄만 강조 — 천명 조작 정체성 부재"


def test_nondice_single_line():
    """비-dice 빌드는 단일 강조줄(무회귀) — spots/fate_pick no-op."""
    assert st.mean(_spot_lines(_cells("poison", POISON))) == 1.0, "비-dice 빌드가 여러 줄 강조 — no-op 위반"
