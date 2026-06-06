"""M1 전투 엔진 — 매 합 전체 발동 + 천명괘 줄(行/列) 강조 (doc 23).

M0 combat.py와 *별도*(점진 이행: 검증 후 교체). 순수 로직·시드 결정론.
- 공격 출력 = 놓인 무공의 m1.base × 레벨 스케일 × (1+인접 증폭) × 순독줄 × 중앙(천명 자리).
- 천명괘 = 매 합 6줄(3행+3열) 중 하나 ×N_SPOT(증폭기). 전 무공은 매 합 발동.
- 방어 = def/(def+K). 조건 무공(반격·약화·회복·취약)은 1차 최소 구현.
출력은 events 스트림(렌더러가 소비). 수치는 balance_sim으로 확정(시드값).
"""
from __future__ import annotations
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

    def _e(self, kind, **d):
        self.events.append(ev(kind, **d))

    def _mit(self, raw, dfn):
        return max(1, round(raw * (1 - dfn / (dfn + self.K))))

    def run(self, max_rounds=None):
        max_rounds = max_rounds or balance.MAX_ROUNDS
        self._e("battle_start", enemy=self.e_name, enemy_hp=self.e_max,
                faces=[it["name_ko"] for it in self.cells if it])
        rnd = 0
        e_atk = self.e_atk
        while self.player.hp > 0 and self.e_hp > 0 and rnd < max_rounds:
            rnd += 1
            self._e("round_start", n=rnd)
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
            total = self._mit(out, self.e_def)
            self.e_hp -= total
            for i in range(9):
                if effs[i] > 0:
                    it = self.cells[i]
                    self._e("m1_fire", name=it["name_ko"], amount=round(effs[i]),
                            spotlit=(i in line), by_player=True)
            self._e("damage", src=self.player.name, tgt=self.e_name, amount=total, crit=crit,
                    label=f"천명 {LINE_KO[li]}", by_player=True,
                    tgt_hp=max(0, self.e_hp), tgt_max=self.e_max)
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
                dealt = self._mit(dealt_sum, self.e_def)
                self.e_hp -= dealt
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
            # 적 공격(약화 조건 반영). guard block은 경감을 높이고, 막은 피해는 기(氣)로 적립.
            eff_atk = e_atk * (0.8 if self.has_weaken else 1.0)
            raw = eff_atk * 0.9
            dmg = self._mit(raw, self.player.defense + self.block)
            self.player.hp -= dmg
            self._e("damage", src=self.e_name, tgt=self.player.name, amount=dmg, crit=False,
                    label="", by_player=False, tgt_hp=max(0, round(self.player.hp)),
                    tgt_max=self.player.max_hp)
            if self.block > 0:
                blocked = max(0.0, raw - dmg)
                self.ki = min(self.ki_cap, self.ki + blocked * KI_GAIN)
            # 조건: 반격·회복(1차 최소)
            if self.has_counter and dmg > 0:
                ref = self._mit(dmg * 0.4, self.e_def)
                self.e_hp -= ref
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
