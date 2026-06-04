"""
게임 세션 오케스트레이터 (순수 로직) — TUI/CLI가 구동. 엔진=권위(15).
P1 수직 슬라이스 범위: 빌드 선택·구궁 배치·전투(이벤트 스트림)·기본 진행·죽음→회귀.
회귀 메타/경제/노드맵 전량은 후속(18/16). 상태는 직렬화 가능(20 §2, persistence).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from . import balance
from .bag import Bag, Loadout
from .combat import Battle, BattleResult
from .rng import Rng
from .. import content

BUILD_LABEL = {"poison": "독", "crit": "치명", "guard": "방어·반격", "dice": "주사위 조작"}


@dataclass
class GameSession:
    name: str = "천기노조"
    build: str = "poison"
    zone: str = "bamboo_grove"
    level: int = 6
    xp: int = 0
    gold: int = 50
    shards: int = 0
    cleared: list = field(default_factory=list)
    owned: list = field(default_factory=list)        # 보유 item_id
    reincarnations: int = 0
    insight: int = 0                                  # 깨달음(메타, 능동 런만)
    bag: Bag = field(default_factory=Bag)
    _seed: int = 0

    # ── 생성/배치 ──
    @classmethod
    def new_game(cls, name: str, build: str) -> "GameSession":
        s = cls(name=name, build=build)
        s.level = balance.ZONE_LEVEL["bamboo_grove"]
        s.owned = [it["item_id"] for it in content.items_for_build(build)]
        s.bag = Bag.auto([it for it in content.items() if it["item_id"] in s.owned])
        return s

    def loadout(self) -> Loadout:
        return Loadout.compile(self.bag)

    def player_preview(self):
        return self.loadout().make_player(self.name, self.level)

    def move(self, src_idx: int, dst_idx: int):
        self.bag.cells[src_idx], self.bag.cells[dst_idx] = self.bag.cells[dst_idx], self.bag.cells[src_idx]

    # ── 전투 ──
    def _enemy(self, boss: bool):
        mobs = content.monsters_for_zone(self.zone)
        if boss:
            return next((m for m in mobs if m.get("is_boss")), mobs[0])
        normals = [m for m in mobs if not m.get("is_boss")]
        cands = [m for m in normals if m["level"] <= self.level + 1] or normals
        self._seed += 1
        return Rng(self._seed * 7919).choice(cands) if cands else mobs[0]

    def fight(self, boss: bool = False) -> tuple[BattleResult, dict]:
        """전투 1회. (결과, 적dict) 반환. 이벤트 스트림은 result.events."""
        enemy = self._enemy(boss)
        lo = self.loadout()
        player = lo.make_player(self.name, self.level)
        self._seed += 1
        res = Battle(lo, player, enemy, balance.ZONE_TIER[self.zone], Rng(self._seed)).run(self.build)
        return res, enemy

    def apply_result(self, res: BattleResult, enemy: dict, boss: bool) -> dict:
        """보상/진행/죽음 처리. 반환: {leveled, drop, reincarnated, gains}."""
        out = {"leveled": [], "drop": None, "reincarnated": False, "gains": {}}
        if res.outcome == "win":
            lv = enemy["level"]
            xp, gold, sh = lv * (40 if boss else 18), lv * (30 if boss else 8), lv * (5 if boss else 1)
            self.xp += xp; self.gold += gold; self.shards += sh
            out["gains"] = {"xp": xp, "gold": gold, "shards": sh}
            while self.xp >= balance.xp_to_next(self.level):
                self.xp -= balance.xp_to_next(self.level); self.level += 1
                out["leveled"].append(self.level)
            if boss and self.zone not in self.cleared:
                self.cleared.append(self.zone)
            # 드랍: 미보유 빌드 아이템
            pool = [it for it in content.items_for_build(self.build) if it["item_id"] not in self.owned]
            if pool and (boss or self._seed % 4 == 0):
                self._seed += 1
                drop = Rng(self._seed * 104729).choice(pool)
                self.owned.append(drop["item_id"]); out["drop"] = drop
        else:
            out["reincarnated"] = True
            out["gain"] = self.reincarnate(reason="전사")
        return out

    # ── 직렬화(persistence, 20 §2·§3) ──
    def to_dict(self) -> dict:
        return {
            "v": 1, "name": self.name, "build": self.build, "zone": self.zone,
            "level": self.level, "xp": self.xp, "gold": self.gold, "shards": self.shards,
            "cleared": list(self.cleared), "owned": list(self.owned),
            "reincarnations": self.reincarnations, "insight": self.insight,
            "bag": [(c["item_id"] if c else None) for c in self.bag.cells], "seed": self._seed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameSession":
        s = cls(name=d["name"], build=d["build"], zone=d.get("zone", "bamboo_grove"),
                level=d.get("level", 6), xp=d.get("xp", 0), gold=d.get("gold", 50),
                shards=d.get("shards", 0), cleared=list(d.get("cleared", [])),
                owned=list(d.get("owned", [])), reincarnations=d.get("reincarnations", 0),
                insight=d.get("insight", 0), _seed=d.get("seed", 0))
        s.bag = Bag()
        for i, iid in enumerate(d.get("bag", [])):
            s.bag.cells[i] = content.item_by_id(iid) if iid else None
        return s

    def reincarnate(self, reason: str = "운기조식"):
        gain = balance.insight_gain(balance.ZONE_TIER[self.zone], len(self.cleared), 0, self.reincarnations, False)
        self.insight += gain
        self.reincarnations += 1
        # 영구 성장(간이): 짝수 회귀마다 시작 경지+1(캡), 무공 각인은 후속
        self.level = balance.ZONE_LEVEL["bamboo_grove"] + min(balance.MASTERY_LEVEL_CAP, self.reincarnations // 2)
        self.xp = 0; self.zone = "bamboo_grove"; self.cleared = []
        return gain
