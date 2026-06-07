"""M1 전투 엔진 — 매 합 전체 발동 + 천명괘 줄(行/列) 강조 (doc 23).

M0 combat.py와 *별도*(점진 이행: 검증 후 교체). 순수 로직·시드 결정론.
- 공격 출력 = 놓인 무공의 m1.base × 레벨 스케일 × (1+인접 증폭) × 순독줄 × 중앙(천명 자리).
- 천명괘 = 매 합 6줄(3행+3열) 중 하나 ×N_SPOT(증폭기). 전 무공은 매 합 발동.
- 방어 = def/(def+K). 조건 무공(반격·약화·회복·취약)은 1차 최소 구현.
출력은 events 스트림(렌더러가 소비). 수치는 balance_sim으로 확정(시드값).
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from .events import ev
from . import balance

GRID = 3
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8)]  # 3행 + 3열 = 천명괘 6면
LINE_KO = ["1행", "2행", "3행", "1열", "2열", "3열"]
ORTH = {0: [1, 3], 1: [0, 2, 4], 2: [1, 5], 3: [0, 4, 6], 4: [1, 3, 5, 7],
        5: [2, 4, 8], 6: [3, 7], 7: [4, 6, 8], 8: [5, 7]}

# ── M1 레버(balance_sim 1차 확정 2026-06-05) ──
N_SPOT = 1.6            # 천명괘 줄 강조 배수
CENTER_MULT = 1.5      # 중앙 = 천명 자리
LINE_PURE_BONUS = 0.25  # 순독(純毒) 줄 보너스
VULN_BONUS = 0.15      # 취약(조건) 출력 보너스 — 적 독 스택>0일 때만(조건부, RSI #14)
OUTPUT_C = 0.040       # 출력 스케일 = player.atk × OUTPUT_C (③-bis: 스타터 일반전 클리어 + GOOD@한천 ~10합)

# ── 독 스택 DoT(RSI 평가 #14) ── M0(combat.py)의 독 시스템을 M1에 포팅. 독 정체성='깔고 쌓아 틱으로 죽임'.
#    독 무공(아래 fx)이 매 합 적에게 스택을 적립 → 스택 비례 DoT(방어 무시) → 후반일수록 틱이 커지는 페이싱.
#    비-poison 빌드엔 무영향(독 무공 0이면 e_poison 영원히 0, 전 로직 no-op — guard/crit 무회귀).
POISON_APPLY_FX = frozenset({"poison", "apply_poison", "on_hit_poison", "poison_slash", "poison_bigslash"})
POISON_AMP_FX = frozenset({"amp_poison", "poison_line_amp"})  # amp 합 = poison_amp(틱 증폭)

# ── guard 받아넘김(유능제강, doc27 P5) ── 막은 피해를 기(氣)로 적립 → 전환기가 기→반격 출력.
#    비-guard 빌드엔 무영향(block=0이면 전 로직 no-op). 수치는 balance_sim으로 확정.
KI_GAIN = 0.60         # 막은 피해 → 기 적립률
KI_CAP_MULT = 0.50     # 기 상한 = player.max_hp × 이값(폭주 방지)
CONV_BASE = 0.30       # 전환기 기본 전환율(칸 배수×인접 증폭이 곱해짐 = 배치 깊이)

# ── crit 예기(銳氣, doc27) ── 매 합 치명확률 누적 → 천명 강조 줄이 치명타로 폭발(고분산 고점).
#    비-crit 빌드엔 무영향(crit_now=0·crit_ramp=0이면 no-op).
CRIT_CAP = 75.0        # 예기 치명확률 상한(%) — 100%면 분산이 사라져 고점 정체성 소멸
# crit 입문 floor(#13, D-D 곡선) — crit 무공은 방어 스탯이 없어(글래스캐넌) 입문 보스1을 램프 전 전사로 떨굼.
# crit 계열(crit_ramp>0)에만, *입문존(tier1)에만* 적용되는 floor. 둘 다 비-crit엔 no-op, 엔드(tier3)엔 0.
CRIT_RAMP_BOOTSTRAP = 15.0   # 시작 치명확률 +(램프 전 첫 폭발 앞당김). 고분산 유지(여전히 확률).
CRIT_INTRO_GUARD = 10.0      # 입문 생존 쿠션(방어 가산). tier1 전액→tier3 0(엔드 viability·고분산 정체성 무영향).

# ── dice 천명 조작(#25) ── 천명괘 강조줄을 조작(추가 강조줄·최강 줄 통제). '넓은 스폿라이트'=단일줄 집중과 직교.
#    비-dice 빌드엔 무영향(spots=0·fate_pick False면 단일 무작위 줄, 기존과 동일).
FATE_SPOTS_CAP = 3           # 추가 강조줄 상한(1+3=최대 4줄 — 전 줄 강조로 무의미해지지 않게)

# ── 천명괘 주사위 = 아이템(재질). 비주얼 스킨 + RNG/출력 튜닝(코스메틱+스탯). [[dice-visual-and-itemization]]
#    spot_mult=줄 강조 배수, dmg_mult=출력 배수, reroll_weak=하위 줄 1회 재굴림(일관성).
# 키스톤 = 변수↔일관 메타축(#6). 런 시작에 계열×재질을 고르면 빌드 성격이 결정된다.
#   var=합당 출력 분산(±%, 결정론 rng). reroll_weak=약줄 1회 재굴림(분산↓). spot_mult=강조줄 비중.
DICE_MODS = {
    "baekok":  {"spot_mult": 1.00, "dmg_mult": 1.00},                              # 백옥(C) 기준점 — 무난
    "bichwi":  {"spot_mult": 0.92, "dmg_mult": 1.02, "reroll_weak": True},          # 비취(E) 일관(약줄 재굴림·저분산) — poison/guard 페어
    "heukyo":  {"spot_mult": 1.28, "dmg_mult": 0.94},                              # 흑요석(R) 조준(강조줄 몰빵 보상) — 줄빌드 페어
    "hyeolok": {"spot_mult": 1.06, "dmg_mult": 1.14, "var": 0.35},                 # 혈옥(L) 고분산 고점(±35% 스윙) — crit 페어 'd20'
    "baekgol": {"spot_mult": 1.06, "dmg_mult": 1.06, "var": 0.10},                 # 백골(R) 올라운드(소폭 출력·소분산)
}

# ── 적 몬스터 스킬(#44) ── monsters.json의 authored `skills`를 전투에 배선(죽은 데이터→다채로운 적·보스 차별화).
#   각 스킬 = 트리거(condition) + 효과(effect). 매 합 적 공격 페이즈에서 평가·적용(결정론).
#   트리거: every_N_turns(N합마다)·below_X_hp(적 HP<X% 발악)·on_crit(적 평타 치명 시). 효과는 정규 enum(아래).
#   효과 강도 글로벌 다이얼(밸런스: 적 스킬=적 강화라 승률↓ → 4빌드 ≥60%·5~20합 밴드 보존용 미세조정 레버).
ENEMY_SKILL_POWER = 0.62   # 적 스킬 효과 글로벌 배수(추가딜·버프·흡혈·실드를 일괄 감쇠 — 밴드 튜닝 단일 레버)
# 입문(tier1)은 라이트 글래스캐넌(crit)이 사는 D-D 곡선 출발점 → 스킬을 약화(생존 쿠션).
#   엔드(tier3)는 전액(도전성). CRIT_INTRO_GUARD와 같은 zone_factor 패턴(t1 약→t3 전액).
ENEMY_SKILL_TIER1 = 0.35   # tier1 스킬 배수(입문 라이트 생존 — 광폭 난도질 등 발악류 완화, crit 글래스캐넌 ≥40% 게이트 마진)
ENEMY_SKILL_TIER3 = 1.00   # tier3 스킬 배수(엔드 도전 전액)
ENEMY_POISON_PER_STACK = 1.6   # 적이 플레이어에 건 독 1스택당 틱(플레이어 max_hp 비례 성분과 합산)
ENEMY_POISON_HP_PCT = 0.010    # 적 독 틱 플레이어 max_hp 비례 성분(고HP에도 의미)


def _m1(it):
    return it.get("m1") if it else None


def cell_eff(cells, idx, scale, vuln=False):
    """무공 i의 이번 합 출력(스폿라이트 전). 증폭/조건은 자체 출력 0."""
    it = cells[idx]
    m = _m1(it)
    if not m or m.get("base", 0) <= 0:
        return 0.0
    adj = 0.0
    for n in ORTH[idx]:
        nb = _m1(cells[n])
        if nb:
            adj += nb.get("amp", 0.0)
    r, c = divmod(idx, GRID)
    row = [cells[r * GRID + j] for j in range(GRID)]
    col = [cells[j * GRID + c] for j in range(GRID)]
    line_bonus = 0.0
    for line in (row, col):
        if all(_m1(x) and _m1(x).get("role") == "payload" for x in line):
            line_bonus = LINE_PURE_BONUS
    center = CENTER_MULT if idx == 4 else 1.0
    out = m["base"] * scale * (1 + adj) * (1 + line_bonus) * center
    if vuln:
        out *= 1 + VULN_BONUS
    return out


@dataclass
class BattleM1Result:
    outcome: str
    rounds: int
    player_hp_pct: float
    events: list = field(default_factory=list)


@dataclass
class EnemySkill:
    """파싱된 적 스킬(monsters.json 정규 스키마 → 런타임). 트리거+효과+쿨다운."""
    name: str
    effect: str                 # 정규 enum: extra_damage·buff_atk·buff_def·buff_spd·lifesteal·gain_shield·heal·apply_poison·amplify_poison_pct·apply_stun
    value: float
    trig_kind: str              # every_n · below_pct · on_crit · passive
    trig_n: int = 0             # every_n: N합 / below_pct: HP% 임계
    cooldown: int = 0
    crit: bool = False          # extra_damage 치명 확정
    hits: int = 1               # extra_damage 연격 수
    atk_mult: float = 0.0       # lifesteal 동반 피해(atk×)
    hp_pct: bool = False        # gain_shield 값이 max_hp 비례인지(아니면 atk×)
    fired: bool = False         # below_pct/on_crit 1회성 발악 발동 여부
    _cd: int = 0                # 남은 쿨다운


def _parse_skill(s: dict) -> EnemySkill | None:
    """monsters.json 정규 스킬 dict → EnemySkill. 미지원 effect/condition은 None(안전 무시)."""
    eff = s.get("effect")
    cond = s.get("condition", "")
    if eff is None:
        return None
    tk, tn = "passive", 0
    if cond.startswith("every_"):
        try:
            tk, tn = "every_n", int(cond.split("_")[1])
        except (IndexError, ValueError):
            return None
    elif cond.startswith("below_"):
        try:
            tk, tn = "below_pct", int(cond.split("_")[1])
        except (IndexError, ValueError):
            return None
    elif cond == "on_crit":
        tk = "on_crit"
    return EnemySkill(
        name=s.get("name_ko", "스킬"), effect=eff, value=float(s.get("value", 0)),
        trig_kind=tk, trig_n=tn, cooldown=int(s.get("cooldown", 0)),
        crit=bool(s.get("crit", False)), hits=int(s.get("hits", 1)),
        atk_mult=float(s.get("atk_mult", 0.0)), hp_pct=bool(s.get("hp_pct", False)),
    )


class BattleM1:
    def __init__(self, cells, player, enemy_dict, zone_tier, rng, scale=None, die=None):
        self.cells = list(cells)
        self.player = player                 # Combatant — HP/def/spd(방어·생존)
        self.rng = rng
        self.K = balance.k_zone(zone_tier)
        m = enemy_dict
        ehp = round(m["hp"] * (balance.BOSS_HP_SCALE if m.get("is_boss") else balance.NORMAL_HP_SCALE))
        self.e_name = m.get("name_ko") or m.get("name", "적")
        self.e_hp = self.e_max = ehp
        self.e_atk = m["atk"]
        self.e_def = m.get("def", 0)
        self.e_atk_crit = float(m.get("crit", 0))    # 적 평타 치명 확률(%) — on_crit 스킬 트리거용
        # 출력 스케일: 레벨 비례(공격 스탯 기반). balance_sim으로 확정.
        self.scale = scale if scale is not None else max(1.0, player.atk * OUTPUT_C)
        # 천명괘 주사위(재질) 모디파이어 — 코스메틱+스탯
        d = DICE_MODS.get(die, {}) if isinstance(die, str) else (die or {})
        self.spot = N_SPOT * d.get("spot_mult", 1.0)
        self.scale *= d.get("dmg_mult", 1.0)
        self.reroll_weak = d.get("reroll_weak", False)
        self.die_var = d.get("var", 0.0)          # 합당 출력 분산(±%) — 혈옥 고분산, 비취 0(일관)
        self.events: list = []
        # 조건 무공 보유 여부(1차 최소)
        fxs = [(_m1(it) or {}).get("fx") for it in self.cells]
        self.has_weaken = "weaken" in fxs
        self.has_vuln = "vulnerable_if_poisoned" in fxs
        self.has_counter = any(f in ("counter", "counter_poison") for f in fxs)
        self.has_heal = "heal_low" in fxs
        # guard 받아넘김: 총 방어 가산(경감↑), 기 적립, 전환기 칸. block=0이면 전부 no-op.
        self.block = sum((_m1(it) or {}).get("block", 0.0) for it in self.cells)
        self.ki = 0.0
        self.ki_cap = self.player.max_hp * KI_CAP_MULT
        self.converters = [i for i in range(9) if (_m1(self.cells[i]) or {}).get("fx") == "convert_ki"]
        # crit 예기: 치명확률(player.crit %) + 합마다 누적(crit_ramp 보유 무공). 비-crit이면 0 → no-op.
        self.crit_now = max(0.0, self.player.crit)
        self.crit_dmg = max(1.0, self.player.crit_dmg)
        self.crit_ramp = sum((_m1(it) or {}).get("crit_ramp", 0.0) for it in self.cells)
        # crit 입문 floor: 예기 무공 보유(crit_ramp>0) + 입문존(tier1)에서만. zone_factor=1.0@tier1→0.0@tier3.
        if self.crit_ramp > 0:
            zone_factor = max(0.0, (100 - self.K) / 50.0)   # K=50(t1)→1.0, 75(t2)→0.5, 100(t3)→0.0
            self.crit_now = min(CRIT_CAP, self.crit_now + CRIT_RAMP_BOOTSTRAP * zone_factor)
            self.block += CRIT_INTRO_GUARD * zone_factor      # 입문 생존 쿠션(엔드선 0 → viability 불변)
        # 독 스택 DoT: 독 적용 무공 수 = 합당 적립 스택, 독 증폭 amp 합 = 틱 증폭, every3=3합마다 추가 1.
        #   독 무공 0이면 poison_apply=0 → e_poison 영원히 0 → 전 독 로직 no-op(비-poison 무회귀 보장).
        self.poison_apply = sum(1 for f in fxs if f in POISON_APPLY_FX)
        self.poison_amp = sum((_m1(it) or {}).get("amp", 0.0)
                              for it in self.cells if (_m1(it) or {}).get("fx") in POISON_AMP_FX)
        self.has_every3 = "every3_poison" in fxs
        self.e_poison = 0      # 적 독 스택
        self._e_pdt = 0        # 감쇠 카운터(POISON_DECAY_TURNS마다 1스택 감쇠)
        # dice 천명 조작(#25): 추가 강조줄(spots) + 천명 통제(fate_pick=최강 줄 선택). 비-dice엔 no-op(spots=0).
        self.fate_spots = min(FATE_SPOTS_CAP, sum((_m1(it) or {}).get("spots", 0) for it in self.cells))
        self.fate_pick = any((_m1(it) or {}).get("fx") == "fate_pick" for it in self.cells)
        # 비장(秘藏)의 수(헌법 D2): 빌드는 cells의 'build' 필드 다수결로 도출(명시 파라미터 없음).
        #   매 합 충전(+1) → BIJANG_CHARGE 도달 시 빌드별 결정타 발동(유틸 빌드 보스 딜 창구 + 유일 에이전시).
        bld = [it.get("build") for it in self.cells if it and it.get("build")]
        self.build = Counter(bld).most_common(1)[0][0] if bld else "poison"
        self.bijang_charge = 0
        # 적 몬스터 스킬(#44): authored skills를 파싱해 전투에 배선(보스 차별화 + 다채로움).
        #   스킬 없으면(빈 리스트) 전부 no-op → 평타만(기존 동작 동일, 무회귀).
        self.e_skills = [sk for sk in (_parse_skill(s) for s in (m.get("skills") or [])) if sk]
        self.e_has_oncrit = any(sk.trig_kind == "on_crit" for sk in self.e_skills)
        # 적 스킬 글로벌 배수 — zone 비례(입문 약→엔드 전액). zone_factor: K=50(t1)→1.0, 100(t3)→0.0.
        zf_sk = max(0.0, min(1.0, (100 - self.K) / 50.0))
        self.e_skill_power = ENEMY_SKILL_POWER * (ENEMY_SKILL_TIER3 + (ENEMY_SKILL_TIER1 - ENEMY_SKILL_TIER3) * zf_sk)
        self.e_atk_buff = 0.0      # buff_atk 누적(분율, eff_atk에 곱)
        self.e_def_buff = 0.0      # buff_def 누적(분율, e_def에 곱) — 플레이어 피해 경감↑
        self.e_shield = 0.0        # gain_shield 흡수 풀(플레이어 피해를 먼저 깎음)
        self.e_pamp = 0.0          # amplify_poison_pct(적이 건 플레이어 독 틱 증폭, 분율)
        self.p_stun = 0            # 플레이어 기절 남은 합(>0이면 공격 출력 스킵)
        self.p_poison = 0          # 플레이어가 적 스킬로 받은 독 스택(플레이어 DoT)

    def _e(self, kind, **d):
        self.events.append(ev(kind, **d))

    def _mit(self, raw, dfn):
        return max(1, round(raw * (1 - dfn / (dfn + self.K))))

    def _e_def_eff(self):
        """적 실효 방어 — buff_def 분율 반영(플레이어 피해 경감↑)."""
        return self.e_def * (1 + self.e_def_buff)

    def _hit_enemy(self, amount):
        """플레이어가 적에게 가하는 피해 — gain_shield를 먼저 흡수(흡수분 반환은 안 함).
        DoT(독)는 침투라 shield 무시(이 함수 경유 금지). 결정론: 정수 라운드."""
        if amount <= 0:
            return 0
        if self.e_shield > 0:
            absorbed = min(self.e_shield, amount)
            self.e_shield -= absorbed
            amount -= absorbed
        amount = round(amount)
        self.e_hp -= amount
        return amount

    def _eval_enemy_skills(self, rnd, e_crit):
        """적 공격 페이즈 — 트리거 충족 스킬을 평가·적용(결정론). 효과는 ENEMY_SKILL_POWER로 일괄 감쇠.
        반환: (this_turn_extra_damage_to_player, lifesteal_heal). 버프/실드/독/기절은 자체 상태에 반영."""
        bonus_dmg = 0.0       # extra_damage·lifesteal 동반딜(이번 합 플레이어 추가 피해)
        heal = 0.0
        P = self.e_skill_power
        for sk in self.e_skills:
            if sk._cd > 0:
                sk._cd -= 1
                continue
            # 트리거 평가
            if sk.trig_kind == "every_n":
                fire = sk.trig_n > 0 and rnd % sk.trig_n == 0
            elif sk.trig_kind == "below_pct":
                fire = (self.e_hp / self.e_max * 100.0) < sk.trig_n and not sk.fired
            elif sk.trig_kind == "on_crit":
                fire = e_crit
            else:                                  # passive — 매 합
                fire = True
            if not fire:
                continue
            if sk.trig_kind == "below_pct":
                sk.fired = True                    # 발악류는 1회성(쿨다운과 별개)
            if sk.cooldown:
                sk._cd = sk.cooldown
            self._apply_enemy_skill(sk, P)
            d, h = self._skill_yield(sk, P)
            bonus_dmg += d
            heal += h
        return bonus_dmg, heal

    def _skill_yield(self, sk, P):
        """딜/흡혈 산출(상태 변화 없는 순수 수치). _apply_enemy_skill과 분리(가독).
        딜에도 P(글로벌 배수)를 곱한다 — 추가딜이 밴드 튜닝/zone 스케일을 따르게(가장 치명적 성분)."""
        atk = self.e_atk * (1 + self.e_atk_buff)
        if sk.effect == "extra_damage":
            raw = atk * sk.value * max(1, sk.hits) * P
            dmg = self._mit(raw, self.player.defense + self.block)
            if sk.crit:
                dmg = round(dmg * 1.5)             # 치명 확정 스킬: 고정 1.5배(플레이어 crit_dmg와 비결합)
            return dmg, 0.0
        if sk.effect == "lifesteal":
            raw = atk * (sk.atk_mult or 1.0) * P
            dmg = self._mit(raw, self.player.defense + self.block)
            return dmg, dmg * sk.value             # 가한 피해의 value 분율 회복
        return 0.0, 0.0

    def _apply_enemy_skill(self, sk, P):
        """버프/실드/독/기절 등 상태성 효과 적용 + 이벤트 emit. 딜은 _skill_yield가 담당."""
        eff = sk.effect
        if eff == "buff_atk":
            self.e_atk_buff += sk.value * P
            self._e("enemy_action", name=f"{self.e_name}의 {sk.name}", tag="buff_atk")
        elif eff == "buff_def":
            self.e_def_buff += sk.value * P
            self._e("enemy_action", name=f"{self.e_name}의 {sk.name}", tag="buff_def")
        elif eff == "buff_spd":
            # spd는 M1 전투 수식에 미사용 → 소폭 공격 가산으로 의미 부여(민첩=치고빠지기 압박)
            self.e_atk_buff += sk.value * P * 0.5
            self._e("enemy_action", name=f"{self.e_name}의 {sk.name}", tag="buff_spd")
        elif eff == "gain_shield":
            atk = self.e_atk * (1 + self.e_atk_buff)
            amt = round((self.e_max * sk.value if sk.hp_pct else atk * sk.value) * P)
            self.e_shield += amt
            self._e("shield", tgt=self.e_name, amount=amt, by_player=False)
        elif eff == "heal":
            amt = round(self.e_max * sk.value * P)
            self.e_hp = min(self.e_max, self.e_hp + amt)
            self._e("heal", tgt=self.e_name, amount=amt, tgt_hp=round(self.e_hp), by_player=False)
        elif eff == "apply_poison":
            self.p_poison += max(1, round(sk.value * P))
            self._e("status", tgt=self.player.name, status="poison", stacks=self.p_poison, by_player=False)
        elif eff == "amplify_poison_pct":
            self.e_pamp += sk.value / 100.0
            self._e("enemy_action", name=f"{self.e_name}의 {sk.name}", tag="amp_poison")
        elif eff == "apply_stun":
            self.p_stun = max(self.p_stun, int(sk.value))
            self._e("status", tgt=self.player.name, status="stun", by_player=False)
        elif eff in ("extra_damage", "lifesteal"):
            self._e("enemy_action", name=f"{self.e_name}의 {sk.name}", tag=eff)

    def _fire_bijang(self, out):
        """비장의 수 발동 — 빌드별 결정타(유틸 빌드 보스 딜 창구 + 유일 에이전시, 헌법 D2).
        out = 이번 합 base+spot(crit/dice burst 기반). 발동 후 e_hp 차감 + bijang 이벤트 emit."""
        cfg = balance.BIJANG.get(self.build, {})
        typ = cfg.get("type")
        if typ == "detonate":                              # poison: 쌓인 독을 왈칵(방어 무시)
            stacks = max(self.e_poison, cfg.get("floor", 0))
            raw_dealt = cfg.get("k", 0) * stacks
            self.e_poison = self.e_poison // 2             # 폭발로 절반 소진(DoT 누적 페이싱은 보존)
        elif typ == "counter_burst":                       # guard: 적립 기·방어를 한 방
            raw = (self.ki * cfg.get("accum", 1.0)
                   + self.player.atk * cfg.get("atk", 1.0)
                   + (self.player.defense + self.block) * (cfg.get("def", 1.0) - 1.0))
            raw_dealt = self._mit(raw, self._e_def_eff())
            self.ki = 0.0                                  # 적립 기 소비
        else:                                              # burst: crit/dice — 이번 합 출력 ×배수
            mult = cfg.get("mult", 1.0)
            if cfg.get("luk_scale"):                       # dice: 운(運) 비례 결정타
                luk_factor = max(0.0, self.player.luk) / 100.0
                mult *= 1 + cfg.get("luk_scale", 0.0) * luk_factor
            raw_dealt = self._mit(out * mult, self._e_def_eff())
        dealt = self._hit_enemy(raw_dealt)                 # gain_shield 흡수 경유
        self._e("bijang", build=self.build, amount=round(dealt), tgt=self.e_name,
                tgt_hp=max(0, self.e_hp), tgt_max=self.e_max, by_player=True)

    def run(self, max_rounds=None):
        max_rounds = max_rounds or balance.MAX_ROUNDS
        self._e("battle_start", enemy=self.e_name, enemy_hp=self.e_max,
                faces=[it["name_ko"] for it in self.cells if it])
        rnd = 0
        e_atk = self.e_atk
        while self.player.hp > 0 and self.e_hp > 0 and rnd < max_rounds:
            rnd += 1
            # 적 기절(apply_stun): 이번 합 플레이어 무공 발동 스킵(출력 0, 결정론). 비장 충전도 멈춤(턴 상실).
            stunned = self.p_stun > 0
            if stunned:
                self.p_stun -= 1
            else:
                self.bijang_charge += 1                   # 비장 충전: 매 합 +1(게이지 fill) — 기절 시 정지
            self._e("round_start", n=rnd, bijang=self.bijang_charge)
            if stunned:
                self._e("status", tgt=self.player.name, status="stun", by_player=False)
            # 전 무공 발동(출력 합) — 빌드 고정. 취약(vulnerable_if_poisoned)은 *적 독 스택>0일 때만* 발동(조건부, RSI #14).
            vuln = self.has_vuln and self.e_poison > 0
            effs = {i: cell_eff(self.cells, i, self.scale, vuln) for i in range(9)}
            # 천명괘: 강조줄 선택. dice 조작 — 추가 강조줄(fate_spots) + 천명 통제(fate_pick=최강 줄).
            if self.fate_pick:                          # 천명 통제: 출력 최강 줄들을 직접 고른다(조작)
                order = sorted(range(6), key=lambda x: sum(effs[i] for i in LINES[x]), reverse=True)
                spot_li = order[:1 + self.fate_spots]
                li = spot_li[0]
            else:
                li = self.rng.roll(6)
                if self.reroll_weak:                    # 비취 키스톤: 약줄 1회 재굴림
                    li2 = self.rng.roll(6)
                    if sum(effs[i] for i in LINES[li2]) > sum(effs[i] for i in LINES[li]):
                        li = li2
                spot_li = [li]
                if self.fate_spots:                     # dice(통제 없이): 무작위 추가 강조줄
                    extra = [x for x in range(6) if x != li]
                    self.rng.shuffle(extra)
                    spot_li += extra[:self.fate_spots]
            line = LINES[li]
            self._e("m1_line", line=li, name=LINE_KO[li], extra=[x for x in spot_li if x != li])
            base = sum(effs.values())
            spot_cells = set()
            for x in spot_li:
                spot_cells.update(LINES[x])             # 겹치는 칸 중복 가산 방지
            spot = (self.spot - 1) * sum(effs[i] for i in spot_cells)
            # crit 예기: 합마다 치명확률 누적 → 적중 시 천명 강조 줄이 치명타로 폭발(고분산 고점)
            crit = False
            if self.crit_now > 0 or self.crit_ramp > 0:
                self.crit_now = min(CRIT_CAP, self.crit_now + self.crit_ramp)
                if self.rng.chance(self.crit_now):
                    spot += sum(effs[i] for i in line) * (self.crit_dmg - 1.0)
                    crit = True
            out = base + spot
            if self.die_var:                       # 주사위 재질 분산(혈옥 ±35% 스윙=고분산, 백골 ±10%)
                out *= 1 + self.rng.uniform(-self.die_var, self.die_var)
            if stunned:                            # 기절: 무공 발동 출력 0(턴 상실, 결정론)
                out = 0.0
            total = self._hit_enemy(self._mit(out, self._e_def_eff())) if out > 0 else 0
            for i in range(9):
                if effs[i] > 0 and not stunned:
                    it = self.cells[i]
                    self._e("m1_fire", name=it["name_ko"], amount=round(effs[i]),
                            spotlit=(i in line), by_player=True)
            if not stunned:
                self._e("damage", src=self.player.name, tgt=self.e_name, amount=total, crit=crit,
                        label=f"천명 {LINE_KO[li]}", by_player=True,
                        tgt_hp=max(0, self.e_hp), tgt_max=self.e_max)
            # 비장(秘藏)의 수: 충전 만료 시 빌드별 결정타(보스 딜 창구). out=이번 합 base+spot. 기절 시 미발동.
            if not stunned and self.bijang_charge >= balance.BIJANG_CHARGE and self.e_hp > 0:
                self._fire_bijang(out)
                self.bijang_charge = 0
                if self.e_hp <= 0:
                    break
            # 전환기: 적립된 기(氣)를 반격 출력으로. 유능제강 — 칸 위치(중앙×1.5)×인접 증폭이
            # 기→피해를 *증폭*(소비속도 아닌 지렛대) → 전환기 배치가 guard 총출력을 바꾼다(배치 깊이).
            if self.converters and self.ki > 0:
                dealt_sum = 0.0
                for ci in self.converters:
                    m = _m1(self.cells[ci])
                    consume = min(self.ki, self.ki * m.get("conv", CONV_BASE))
                    center = CENTER_MULT if ci == 4 else 1.0
                    adj = sum((_m1(self.cells[n]) or {}).get("amp", 0.0) for n in ORTH[ci])
                    self.ki -= consume
                    dealt_sum += consume * center * (1 + adj)        # 위치 지렛대로 증폭
                dealt = self._hit_enemy(self._mit(dealt_sum, self._e_def_eff()))
                self._e("ki_reversal", src=self.player.name, tgt=self.e_name, amount=round(dealt),
                        by_player=True, tgt_hp=max(0, self.e_hp), tgt_max=self.e_max)
            # 독 스택 DoT(RSI #14). 독 무공이 매 합 스택 적립 → 스택 비례 틱(방어 무시) → 후반일수록 큰 페이싱.
            #   poison_apply=0이면 이 블록 전체 no-op(비-poison 빌드 바이트 동일). M0 combat._tick 포팅.
            if self.poison_apply > 0:
                self.e_poison += self.poison_apply                    # 무공당 1스택/합
                if self.has_every3 and rnd % 3 == 0:
                    self.e_poison += 1                                # every3_poison: 3합마다 추가 1스택
                if self.e_poison > 0:
                    amt = max(1, round((balance.POISON_PER_STACK * self.e_poison
                                        + balance.POISON_HP_PCT * self.e_max) * (1 + self.poison_amp)))
                    self.e_hp -= amt                                  # DoT는 방어 무시(독은 침투)
                    # 감쇠: POISON_DECAY_TURNS마다 1스택(쌓여야 제맛 — M0와 동일 곡선)
                    self._e_pdt += 1
                    if self._e_pdt >= balance.POISON_DECAY_TURNS:
                        self.e_poison -= 1
                        self._e_pdt = 0
                    self._e("tick", status="poison", src="독", tgt=self.e_name, amount=amt,
                            stacks=self.e_poison, by_player=True,
                            tgt_hp=max(0, self.e_hp), tgt_max=self.e_max)
            if self.e_hp <= 0:
                break
            # 적 평타(약화 조건 + 적 buff_atk 반영). guard block은 경감을 높이고, 막은 피해는 기(氣)로 적립.
            eff_atk = e_atk * (1 + self.e_atk_buff) * (0.8 if self.has_weaken else 1.0)
            raw = eff_atk * 0.9
            # 적 평타 치명(on_crit 트리거용) — 적 crit 스탯(monsters.json) 확률. 평타 자체는 배율 미적용(밸런스 보수).
            #   on_crit 스킬 보유 적만 굴림(불필요 RNG 소모·결정론 스트림 churn 방지).
            e_crit = self.e_has_oncrit and self.rng.chance(self.e_atk_crit)
            dmg = self._mit(raw, self.player.defense + self.block)
            self.player.hp -= dmg
            self._e("damage", src=self.e_name, tgt=self.player.name, amount=dmg, crit=e_crit,
                    label="", by_player=False, tgt_hp=max(0, round(self.player.hp)),
                    tgt_max=self.player.max_hp)
            if self.block > 0:
                blocked = max(0.0, raw - dmg)
                self.ki = min(self.ki_cap, self.ki + blocked * KI_GAIN)
            # 적 몬스터 스킬(#44): 트리거 충족 스킬 평가·적용. extra_damage·lifesteal은 추가 피해(+흡혈 회복).
            #   버프/실드/독/기절은 _eval 내부에서 상태 반영. e_skills 비면 전부 no-op(평타만, 무회귀).
            if self.e_skills:
                bonus, leech = self._eval_enemy_skills(rnd, e_crit)
                if bonus > 0:
                    self.player.hp -= bonus
                    self._e("damage", src=self.e_name, tgt=self.player.name, amount=round(bonus),
                            crit=False, label="스킬", by_player=False,
                            tgt_hp=max(0, round(self.player.hp)), tgt_max=self.player.max_hp)
                    if self.block > 0:                    # 스킬 피해도 guard 기 적립(막은 분)
                        self.ki = min(self.ki_cap, self.ki + bonus * KI_GAIN * 0.3)
                if leech > 0:
                    self.e_hp = min(self.e_max, self.e_hp + round(leech))
                    self._e("heal", tgt=self.e_name, amount=round(leech),
                            tgt_hp=round(self.e_hp), by_player=False)
            # 적이 건 독(apply_poison) → 플레이어 DoT(방어 무시). p_poison=0이면 no-op(비-적독 무회귀).
            if self.p_poison > 0:
                pdmg = max(1, round((ENEMY_POISON_PER_STACK * self.p_poison
                                     + ENEMY_POISON_HP_PCT * self.player.max_hp) * (1 + self.e_pamp)))
                self.player.hp -= pdmg
                self._e("tick", status="poison", src="혈독", tgt=self.player.name, amount=pdmg,
                        stacks=self.p_poison, by_player=False,
                        tgt_hp=max(0, round(self.player.hp)), tgt_max=self.player.max_hp)
                if self.player.hp <= 0:
                    break
            # 조건: 반격·회복(1차 최소)
            if self.has_counter and dmg > 0:
                ref = self._hit_enemy(self._mit(dmg * 0.4, self._e_def_eff()))
                self._e("counter", src=self.player.name, tgt=self.e_name, amount=ref,
                        by_player=True, tgt_hp=max(0, self.e_hp))
            if self.has_heal and self.player.hp < self.player.max_hp * 0.5:
                heal = round(self.player.max_hp * 0.06)
                self.player.hp = min(self.player.max_hp, self.player.hp + heal)
                self._e("heal", tgt=self.player.name, amount=heal, tgt_hp=round(self.player.hp))
        outcome = "win" if self.e_hp <= 0 and self.player.hp > 0 else ("loss" if self.player.hp <= 0 else "timeout")
        self._e("end", outcome=outcome, rounds=rnd, player_hp=max(0, round(self.player.hp)),
                player_max=round(self.player.max_hp))
        return BattleM1Result(outcome, rnd, max(0.0, self.player.hp) / self.player.max_hp, self.events)
