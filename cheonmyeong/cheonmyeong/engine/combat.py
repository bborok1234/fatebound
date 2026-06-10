"""전투 엔진 — rulebook_sim(검산 하니스) 이식: 같은 다이얼, 라운드 제너레이터.
'검증 하니스가 인게임 기능이 된다'(5권 02 §3.2) — 수치·로직 이원화 금지.
fight 분해 스키마 정합: {slots:{무공명:피해}, smyeong, dot, taken}."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..data import slice_pack as P


@dataclass
class Action:
    move: str            # 무공명
    chosik: str          # 초식명(풀 굴림 — 매 합 다른 한 줄)
    effect: str          # 효과 텍스트
    dmg: float = 0.0
    kind: str = "gen"    # gen|amp|burst|smyeong|enemy|dot


@dataclass
class RoundEvent:
    round: int
    actions: list[Action] = field(default_factory=list)
    enemy_hp: int = 0
    enemy_max: int = 0
    poison: float = 0.0
    charge: int = 0
    player_hp: int = 0
    burst: bool = False         # 만독발현 발동(중 연출)
    smyeong: bool = False       # 성명절기 발동(대 연출 — 컷인)
    smyeong_dmg: float = 0.0
    result: str | None = None   # win|loss 시 종료


def mit(dmg: float, dfn: float, k: float = 50.0) -> float:
    return dmg * (1 - dfn / (dfn + k))


def run_battle(enemy_key: str, seed: int = 0, chain: list[str] | None = None):
    """라운드 제너레이터 — 스테이지가 합당 0.22s로 재생. 마지막 이벤트에 result·분해."""
    rng = random.Random(seed)
    moves = [P.MOVES[k] for k in (chain or P.CHAIN)]
    e = dict(P.ENEMIES[enemy_key])
    p = dict(P.PLAYER)
    e_hp, e_max = e["hp"], e["hp"]
    poison = 0.0
    charge = 0
    pending_smyeong = False                     # 충전 완료 = 예약 — 발동은 다음 합 개시(01 §3.2 정본)
    bd = {"slots": {}, "smyeong": 0.0, "dot": 0.0, "taken": 0.0}
    first = "무명" if p["spd"] >= e["spd"] else e["kind"]

    for rnd in range(1, 31):
        ev = RoundEvent(round=rnd, enemy_max=e_max, player_hp=int(p["hp"]))
        # ── 예약된 성명절기 — 이 합의 첫 행동으로 발동 ──
        if pending_smyeong:
            dmg = max(poison, P.SMYEONG["floor"]) * P.SMYEONG["mult"] * (p["atk"] * P.OUTPUT_C)
            e_hp -= dmg
            bd["smyeong"] += dmg
            poison = 0.0
            charge = 0
            pending_smyeong = False
            ev.smyeong = True
            ev.smyeong_dmg = dmg
            ev.actions.append(Action(P.SMYEONG["name"], P.SMYEONG["name"],
                                     f"☠ {dmg:.0f}", dmg=dmg, kind="smyeong"))
        # 증폭: 계열별 배수(인접 같은 계열만 — rulebook_sim 모델 정합)
        amp = {}
        for i, w in enumerate(moves):
            if w["role"] == "amp":
                adj = [moves[j] for j in (i - 1, i + 1) if 0 <= j < len(moves)]
                if any(a["series"] == w["series"] for a in adj):
                    amp[w["series"]] = amp.get(w["series"], 1.0) + w["amp"]
        for w in moves:
            cho = rng.choice(w["chosik"])
            if w["role"] == "gen":
                gain = w["gen"] * amp.get(w["series"], 1.0) * P.SIMBEOP["mult"]
                poison += gain
                ev.actions.append(Action(w["name"], cho, f"중독 +{gain:.0f}", kind="gen"))
            elif w["role"] == "amp":
                ev.actions.append(Action(w["name"], cho, f"인접 독 +{int(w['amp']*100)}%", kind="amp"))
            elif w["role"] == "burst" and poison >= w["thr"]:
                dmg = poison * w["mult"] * (p["atk"] * P.OUTPUT_C)   # 방어무시
                e_hp -= dmg
                bd["slots"][w["name"]] = bd["slots"].get(w["name"], 0.0) + dmg
                poison = 0.0
                ev.actions.append(Action(w["name"], cho, f"{dmg:.0f} 방어 무시", dmg=dmg, kind="burst"))
                ev.burst = True
        # 충전: 6 도달 = 충전 완료(예약·充 점멸) — 발동은 다음 합 개시
        if charge < 6:
            charge += 1
        if charge >= 6 and not pending_smyeong and e_hp > 0:
            charge = 6
            pending_smyeong = True
        # (정종 독: 중독은 만독발현이 소비하는 자원 — standing DoT 아님, rulebook_sim 정합)
        ev.poison = poison
        ev.charge = charge
        ev.enemy_hp = max(0, int(e_hp))
        if e_hp <= 0:
            ev.result = "win"
            ev.breakdown = bd          # type: ignore[attr-defined]
            yield ev
            return
        taken = mit(e["atk"] * 0.9, p["dfn"])
        p["hp"] -= taken
        bd["taken"] += taken
        ev.actions.append(Action(e["kind"].split(" ")[0], "반격", f"−{taken:.0f}", dmg=taken, kind="enemy"))
        ev.player_hp = max(0, int(p["hp"]))
        if p["hp"] <= 0:
            ev.result = "loss"
            ev.breakdown = bd          # type: ignore[attr-defined]
            yield ev
            return
        yield ev
    ev.result = "timeout"
    ev.breakdown = bd                  # type: ignore[attr-defined]
    yield ev
