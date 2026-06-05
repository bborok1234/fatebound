"""
전투 엔진 (02 §전투 · 08 §4·§7 · 14 튜닝). 순수 로직 — I/O 없음, 시드 결정론.
산출: BattleResult(events: list[Event], outcome, rounds, player_hp_pct). 렌더러가 events를 소비.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import Combatant, Summon
from .bag import Loadout, norm_face
from .events import Event, ev
from .formula import evaluate
from . import balance


@dataclass
class BattleResult:
    outcome: str            # win | loss | timeout
    rounds: int
    player_hp_pct: float
    events: list = field(default_factory=list)


class Battle:
    def __init__(self, loadout: Loadout, player: Combatant, enemy_dict: dict,
                 zone_tier: int, rng, reroll_policy: str = "blank"):
        self.lo = loadout
        self.player = player
        self.rng = rng
        self.tier = zone_tier
        self.K = balance.k_zone(zone_tier)
        self.policy = reroll_policy
        m = enemy_dict
        scale = balance.BOSS_HP_SCALE if m.get("is_boss") else balance.NORMAL_HP_SCALE
        ehp = round(m["hp"] * scale)
        self.enemy = Combatant(name=m.get("name_ko") or m.get("name", "적"), hp=ehp, max_hp=ehp,
                               atk=m["atk"], defense=m["def"], spd=m.get("spd", 6),
                               crit=m.get("crit", 5))
        self.enemy_skills = m.get("skills", [])
        self.events: list[Event] = []
        # 자원
        reroll_items = sum(int(evaluate(e.get("value", 0))) for _, e in loadout.passives
                           if e.get("effect") == "reroll_token")
        self.reroll = 1 + player.luk // 25 + getattr(player, "_mastery_reroll", 0) + reroll_items
        self.focus = 0
        self.bijang = 0
        self.counter_accum = 0.0
        self.summons: list[Summon] = []
        self._spawn_initial_summons()

    def _e(self, kind, **d):
        self.events.append(ev(kind, **d))

    # ── 소환(18 §4) ──
    def _spawn_initial_summons(self):
        for it, eff in self.lo.summon_defs:
            v = eff.get("value", {})
            if isinstance(v, dict):
                self.summons.append(Summon(name=it.get("name_ko", "소환수"),
                                           atk=self.player.atk * v.get("atk_coeff", 0.4),
                                           hp=self.player.max_hp * v.get("hp_coeff", 0.3),
                                           duration=v.get("duration", 0), kind=v.get("type", "beast")))

    # ── 피해(08 §4.2) ──
    def _deal(self, attacker: Combatant, defender: Combatant, raw: float,
              ignore_def=False, can_crit=True, src_label="") -> tuple[int, bool]:
        dmg = raw
        crit = False
        if can_crit and self.rng.roll(100) < attacker.crit:
            dmg *= attacker.crit_dmg
            crit = True
        if not ignore_def:
            dmg *= 1 - defender.defense / (defender.defense + self.K)
        if "vulnerable" in defender.statuses:
            dmg *= 1 + balance.VULNERABLE_PCT
        if "weak" in attacker.statuses:
            dmg *= 1 - balance.WEAK_PCT
        final = max(1, round(dmg))
        if defender.statuses.get("shield", 0) > 0:
            sh = defender.statuses["shield"]
            absorbed = min(sh, final)
            defender.statuses["shield"] = sh - absorbed
            final -= absorbed
            if defender.statuses["shield"] <= 0:
                del defender.statuses["shield"]
        defender.hp -= final
        self._e("damage", src=attacker.name, tgt=defender.name, amount=final, crit=crit,
                label=src_label, by_player=attacker.is_player,
                tgt_hp=max(0, round(defender.hp)), tgt_max=defender.max_hp)
        # 반격
        if final > 0 and defender.counter_pct > 0 and defender.alive:
            ref = max(1, round(final * defender.counter_pct * balance.COUNTER_SCALE))
            if defender.is_player:
                self.counter_accum += ref
            attacker.hp -= ref
            self._e("counter", src=defender.name, tgt=attacker.name, amount=ref,
                    by_player=defender.is_player, tgt_hp=max(0, round(attacker.hp)))
        return final, crit

    def _apply(self, eff: dict, src: Combatant, tgt: Combatant, allow_oncrit=True):
        e, v = eff.get("effect"), eff.get("value")
        ctx = src.ctx()
        if e in ("deal_damage", "damage"):
            _, crit = self._deal(src, tgt, evaluate(v, ctx))
            if allow_oncrit and crit and src.is_player:
                for _, oc in self.lo.oncrit:
                    self._apply(oc, src, tgt, allow_oncrit=False)
        elif e == "apply_poison":
            n = int(evaluate(v, ctx) or 1)
            tgt.statuses["poison"] = tgt.statuses.get("poison", 0) + n
            self._e("status", status="poison", tgt=tgt.name, stacks=tgt.statuses["poison"], added=n)
        elif e == "apply_burn":
            tgt.statuses["burn"] = tgt.statuses.get("burn", 0) + int(evaluate(v, ctx) or 1)
            self._e("status", status="burn", tgt=tgt.name, stacks=tgt.statuses["burn"])
        elif e == "apply_weak":
            tgt.statuses["weak"] = int(eff.get("duration") or 2)
            self._e("status", status="weak", tgt=tgt.name)
        elif e == "apply_vulnerable":
            tgt.statuses["vulnerable"] = int(eff.get("duration") or 2)
            self._e("status", status="vulnerable", tgt=tgt.name)
        elif e == "apply_stun":
            if self.rng.roll(100) < balance.STUN_CHANCE and "stun_immune" not in tgt.statuses:
                tgt.statuses["stun"] = 1
                self._e("status", status="stun", tgt=tgt.name)
        elif e == "gain_shield":
            amt = round(evaluate(v, ctx))
            src.statuses["shield"] = src.statuses.get("shield", 0) + amt
            self._e("shield", tgt=src.name, amount=amt)
        elif e == "heal":
            amt = round(evaluate(v, ctx))
            src.hp = min(src.max_hp, src.hp + amt)
            self._e("heal", tgt=src.name, amount=amt, tgt_hp=round(src.hp))
        elif e == "lock_face":
            self._e("info", text="다음 합 빈칸 제거(면 고정)")
            self._lock_next = True

    # ── 비장(02, 14) ──
    def _fire_bijang(self):
        bj = balance.BIJANG.get(self.lo_build_key())
        if not bj:
            return
        p, en = self.player, self.enemy
        self._e("bijang", build=self.lo_build_key(), btype=bj["type"])
        if bj["type"] == "burst":
            base = p.atk * bj["mult"] * (p.crit_dmg if bj.get("crit") else 1)
            base *= 1 + p.luk * bj.get("luk_scale", 0) / 100.0   # 주사위: 운(運) 비례 결정타
            self._deal(p, en, base, ignore_def=True, can_crit=False, src_label="비장")
        elif bj["type"] == "detonate":
            stacks = en.statuses.get("poison", 0) + bj.get("floor", 0)   # 비장이 독을 왈칵 쏟아붓는다
            dmg = max(1, round(stacks * bj["k"] * (1 + p.poison_amp / 100.0)))
            en.hp -= dmg
            self._e("damage", src=p.name, tgt=en.name, amount=dmg, crit=False, label="만독발현",
                    by_player=True, tgt_hp=max(0, round(en.hp)), tgt_max=en.max_hp)
        elif bj["type"] == "counter_burst":
            base = p.atk * bj["atk"] + p.defense * bj["def"] + self.counter_accum * bj["accum"]
            self.counter_accum = 0
            self._deal(p, en, base, ignore_def=True, can_crit=False, src_label="반탄폭발")

    def lo_build_key(self):
        return getattr(self, "_build_key", None)

    # ── 턴 ──
    def player_turn(self, rnd: int):
        if self.player.statuses.pop("stun", 0):
            self._e("info", text=f"{self.player.name}이(가) 굳었다. 이번 합은 움직일 수 없다"); return
        self.bijang += 1
        if self.bijang >= balance.BIJANG_CHARGE:
            self.bijang = 0
            self._fire_bijang()
            if not self.enemy.alive:
                return
        face = self.rng.choice(self.lo.faces)
        rerolled = False
        if getattr(self, "_lock_next", False) and face == "빈칸":
            self._lock_next = False
            face = self.rng.choice([f for f in self.lo.faces if f != "빈칸"] or self.lo.faces)
        elif self.policy == "blank" and face == "빈칸" and self.reroll > 0:
            self.reroll -= 1
            face = self.rng.choice(self.lo.faces)
            rerolled = True
        self._e("dice", face=face, rerolled=rerolled, reroll_left=self.reroll)
        effs = self.lo.face_effects.get(norm_face(face), [])
        if face == "빈칸" or not effs:
            self.focus += 1
            self._e("focus", count=self.focus)
            if self.focus >= balance.FOCUS_THRESHOLD:
                self.focus = 0
                self._e("info", text="쌓인 응기가 터진다! 특수의 수가 보장된다")
                for _, eff in self.lo.face_effects.get("특수", []):
                    self._apply(eff, self.player, self.enemy)
            return
        for it, eff in effs:
            self._apply(eff, self.player, self.enemy)

    def summons_turn(self):
        for s in list(self.summons):
            if not s.alive or not self.enemy.alive:
                continue
            self._deal_summon(s)
            if s.duration > 0:
                s.duration -= 1
                if s.duration == 0:
                    self.summons.remove(s)

    def _deal_summon(self, s: Summon):
        dmg = max(1, round(s.atk * (1 - self.enemy.defense / (self.enemy.defense + self.K))))
        self.enemy.hp -= dmg
        self._e("summon_attack", name=s.name, amount=dmg, tgt_hp=max(0, round(self.enemy.hp)))

    def enemy_turn(self, rnd: int):
        if self.enemy.statuses.pop("stun", 0):
            self._e("info", text=f"{self.enemy.name} 기절"); return
        for sk in self.enemy_skills:
            cond = sk.get("condition", "")
            fire = False
            if cond.startswith("every_"):
                import re
                nums = re.findall(r"\d+", cond)
                fire = bool(nums) and rnd % int(nums[0]) == 0
            elif cond.startswith("below_"):
                import re
                nums = re.findall(r"\d+", cond)
                fire = bool(nums) and self.enemy.hp_pct * 100 <= int(nums[0])
            if fire:
                e = sk.get("effect", "deal_damage")
                self._e("enemy_action", name=sk.get("name_ko") or sk.get("name", "스킬"))
                if e in ("increase_attack", "atk_buff"):
                    self.enemy.atk *= 1 + evaluate(sk.get("value", 0)) / 100.0
                elif e in ("apply_poison", "apply_stun", "heal"):
                    self._apply({"effect": e, "value": sk.get("value", 1)}, self.enemy, self.player)
                else:
                    self._apply({"effect": "deal_damage", "value": sk.get("value", "1.0 * atk")}, self.enemy, self.player)
                return
        self._deal(self.enemy, self.player, self.enemy.atk * 0.9, src_label="평타")

    def _tick(self, c: Combatant):
        st = c.statuses
        if st.get("poison", 0) > 0:
            stacks = st["poison"]
            amp = 1 + (self.player.poison_amp / 100.0 if c is self.enemy else 0)
            dmg = max(1, round((balance.POISON_PER_STACK * stacks + balance.POISON_HP_PCT * c.max_hp) * amp))
            c.hp -= dmg
            # 램프: 2턴당 1중첩만 감쇠(독은 쌓여야 제맛 — 비장 만독발현·고HP 보스 대응). 14
            dt = st.get("_pdt", 0) + 1
            if dt >= balance.POISON_DECAY_TURNS:
                st["poison"] = stacks - 1
                dt = 0
            st["_pdt"] = dt
            self._e("tick", status="poison", tgt=c.name, amount=dmg, stacks=st["poison"], tgt_hp=max(0, round(c.hp)))
            if st["poison"] <= 0:
                del st["poison"]
                st.pop("_pdt", None)
        if st.get("burn", 0) > 0:
            stacks = st["burn"]
            atk = self.player.atk if c is self.enemy else self.enemy.atk
            dmg = max(1, round(balance.BURN_COEF * atk * stacks))
            c.hp -= dmg
            self._e("tick", status="burn", tgt=c.name, amount=dmg, tgt_hp=max(0, round(c.hp)))
        for k in ("weak", "vulnerable"):
            if k in st:
                st[k] -= 1
                if st[k] <= 0:
                    del st[k]

    def run(self, build_key: str, max_rounds: int | None = None) -> BattleResult:
        self._build_key = build_key
        max_rounds = max_rounds or balance.MAX_ROUNDS
        self._e("battle_start", enemy=self.enemy.name, enemy_hp=self.enemy.max_hp, faces=list(self.lo.faces))
        rnd = 0
        while self.player.alive and self.enemy.alive and rnd < max_rounds:
            rnd += 1
            self._e("round_start", n=rnd)
            order = [self.player, self.enemy] if self.player.spd >= self.enemy.spd else [self.enemy, self.player]
            for actor in order:
                if not (self.player.alive and self.enemy.alive):
                    break
                if actor.is_player:
                    self.player_turn(rnd)
                    if self.enemy.alive:
                        self.summons_turn()
                else:
                    self.enemy_turn(rnd)
            self._tick(self.enemy)
            if self.enemy.alive:
                self._tick(self.player)
        outcome = "win" if (self.enemy.hp <= 0 and self.player.hp > 0) else ("loss" if self.player.hp <= 0 else "timeout")
        self._e("end", outcome=outcome, rounds=rnd, player_hp=max(0, round(self.player.hp)),
                player_max=round(self.player.max_hp))
        return BattleResult(outcome, rnd, max(0.0, self.player.hp) / self.player.max_hp, self.events)
