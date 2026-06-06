"""
구궁(九宮) + 주사위 발동 모델 컴파일 (D1, 02 §주사위 발동 모델).

Bag = 3×3 배치. Loadout.compile() = 배치로부터 천명괘 6면·면별 효과·상시·인접 시너지를 산출.
프로토타입 검증 로직 이식 + 실제 3×3 좌표 기반 방향성 인접(north/south/east/west) 구현.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import Combatant, BASE_FACES
from . import balance
from .formula import evaluate

GRID = 3
# 방향 → 이웃 오프셋(idx 기준). 행우선 0..8.
DIRS = {"north": -GRID, "south": GRID, "west": -1, "east": 1}


def norm_face(f: str) -> str:
    """면 이름 정규화: 'X(漢字)' 병기 무시(생성 데이터의 with/on_face 표기 차 흡수)."""
    return str(f).split("(", 1)[0].strip()


def _neighbors(idx: int):
    """(direction, neighbor_idx) — 격자 경계·행 넘어가는 좌우 제외."""
    r, c = divmod(idx, GRID)
    out = []
    for d, off in DIRS.items():
        n = idx + off
        if not (0 <= n < GRID * GRID):
            continue
        nr, nc = divmod(n, GRID)
        if d in ("east", "west") and nr != r:   # 좌우는 같은 행만
            continue
        out.append((d, n))
    return out


def synergy_cells(bag: "Bag"):
    """방향성 인접 상생이 발동하는 칸 집합과 쌍 목록 — TUI 시각화·디버그용."""
    cells, pairs = set(), []
    for idx, it in bag.occupied():
        for adj in it.get("adjacency", []):
            req = adj.get("required_tag", "")
            direction = adj.get("direction", "any")
            checks = _neighbors(idx) if direction == "any" else [(direction, idx + DIRS.get(direction, 0))]
            for _d, n in checks:
                if 0 <= n < GRID * GRID and bag.cells[n]:
                    nb = bag.cells[n]
                    if req in ("any", "none", "") or req in set(nb.get("tags", [])):
                        cells.add(idx); cells.add(n)
                        pairs.append((idx, n))
                        break
    return cells, pairs


@dataclass
class Bag:
    cells: list = field(default_factory=lambda: [None] * (GRID * GRID))  # 9칸, item dict 또는 None

    def place(self, idx: int, item: dict | None):
        self.cells[idx] = item

    def occupied(self):
        return [(i, it) for i, it in enumerate(self.cells) if it]

    @classmethod
    def auto(cls, items: list[dict]):
        """예산 상위 9개를 행우선 배치(자동 편성). TUI에서 수동 재배치."""
        pool = sorted(items, key=lambda it: it.get("power_budget", 0), reverse=True)[:9]
        b = cls()
        for i, it in enumerate(pool):
            b.cells[i] = it
        return b


@dataclass
class Loadout:
    """구궁 배치를 전투용으로 컴파일한 결과."""
    faces: list                       # 천명괘 6면
    face_effects: dict                # norm_face -> [(item, effect)]
    passives: list                    # (item, effect)
    oncrit: list                      # (item, effect)
    conditional: list                 # (item, effect) below_N_hp 등
    adj_bonus_atk: float
    adj_poison_amp: float
    grid_items: list                  # 배치된 item dict(상시 스탯 합산용)
    summon_defs: list                 # summon_ally 정의(소환 빌드)

    @classmethod
    def compile(cls, bag: Bag) -> "Loadout":
        faces = list(BASE_FACES)
        face_effects: dict = {}
        passives, oncrit, conditional, summon_defs = [], [], [], []
        items = [it for _, it in bag.occupied()]

        # 1) dice_mod 면 교체 — 좌상단(행우선) 우선, 충돌 시 첫 아이템만(02 §6)
        for _idx, it in bag.occupied():
            for mod in it.get("dice_mod", []):
                rep = mod.get("replace")
                if rep in faces:
                    faces[faces.index(rep)] = mod.get("with")

        # 2) 효과 바인딩
        for _idx, it in bag.occupied():
            for eff in it.get("effects", []):
                cond = eff.get("condition", "")
                if cond.startswith("on_face:"):
                    face_effects.setdefault(norm_face(cond.split(":", 1)[1]), []).append((it, eff))
                elif cond == "passive":
                    passives.append((it, eff))
                    if eff.get("effect") == "summon_ally":
                        summon_defs.append((it, eff))
                elif cond == "on_crit":
                    oncrit.append((it, eff))
                elif cond.startswith("below_"):
                    conditional.append((it, eff))

        # 3) 검격=기본 베기(02). 무기가 만든 면이 on_face 피해 없으면 기본 공격 내재
        def has_dmg(face):
            return any(e.get("effect") in ("deal_damage", "damage") for _, e in face_effects.get(face, []))
        for _idx, it in bag.occupied():
            if it.get("type") == "weapon":
                for mod in it.get("dice_mod", []):
                    f = norm_face(mod.get("with"))
                    if not has_dmg(f):
                        face_effects.setdefault(f, []).append(
                            (it, {"condition": f"on_face:{f}", "target": "enemy", "effect": "deal_damage", "value": "1.0 * atk", "duration": 0}))
        if "검격" in [norm_face(f) for f in faces] and not has_dmg("검격"):
            face_effects.setdefault("검격", []).append(
                (None, {"effect": "deal_damage", "target": "enemy", "value": "1.0 * atk", "duration": 0}))

        # 4) 방향성 인접 시너지 — 스탯·독증폭만 정적 합산(전투 중 발동형 시너지는 effect로)
        adj_atk = adj_amp = 0.0
        for idx, it in bag.occupied():
            for adj in it.get("adjacency", []):
                req = adj.get("required_tag", "")
                direction = adj.get("direction", "any")
                checks = _neighbors(idx) if direction == "any" else [(direction, idx + DIRS.get(direction, 0))]
                for _d, n in checks:
                    if not (0 <= n < GRID * GRID):
                        continue
                    nb = bag.cells[n]
                    if nb and (req == "any" or req == "none" or req in set(nb.get("tags", []))):
                        be = adj.get("bonus_effect", adj.get("bonus", {}).get("effect", "") if isinstance(adj.get("bonus"), dict) else "")
                        bv = adj.get("bonus_value", adj.get("bonus", {}).get("value", 0) if isinstance(adj.get("bonus"), dict) else 0)
                        if be == "increase_attack":
                            adj_atk += evaluate(bv)
                        elif be == "amplify_poison_pct":
                            adj_amp += evaluate(bv)
                        break

        return cls(faces, face_effects, passives, oncrit, conditional, adj_atk, adj_amp, items, summon_defs)

    def make_player(self, name: str, level: int, mastery_reroll: int = 0) -> Combatant:
        s = balance.base_player_stats(level)
        p = Combatant(name=name, hp=s["hp"], max_hp=s["hp"], atk=s["atk"], defense=s["def"],
                      spd=s["spd"], crit=s["crit"], crit_dmg=s["crit_dmg"], luk=s["luk"], is_player=True)
        for it in self.grid_items:
            st = it.get("stats", {})
            p.atk += st.get("atk", 0); p.max_hp += st.get("hp", 0); p.hp += st.get("hp", 0)
            p.defense += st.get("def", 0); p.spd += st.get("spd", 0)
            p.crit += st.get("crit", 0); p.crit_dmg += max(0.0, st.get("crit_dmg", 1.5) - 1.5)
            p.luk += st.get("luk", 0)
        for _it, eff in self.passives:
            e, v = eff.get("effect"), eff.get("value")
            if e == "increase_attack": p.atk += evaluate(v)
            elif e == "increase_defense": p.defense += evaluate(v)
            elif e == "increase_crit": p.crit += evaluate(v)
            elif e == "increase_crit_dmg": p.crit_dmg += evaluate(v)
            elif e == "increase_speed": p.spd += evaluate(v)
            elif e == "counter": p.counter_pct = max(p.counter_pct, evaluate(v) or balance.COUNTER_PCT_DEFAULT)
            elif e == "amplify_poison_pct": p.poison_amp += evaluate(v)
        p.atk += self.adj_bonus_atk
        p.poison_amp += self.adj_poison_amp
        # reroll tokens 등은 combat에서 luk+mastery로 계산
        p._mastery_reroll = mastery_reroll  # type: ignore[attr-defined]
        return p
