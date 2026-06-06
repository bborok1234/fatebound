"""
게임 세션 오케스트레이터 (순수 로직) — TUI/CLI가 구동. 엔진=권위(15).
P1 수직 슬라이스 범위: 빌드 선택·구궁 배치·전투(이벤트 스트림)·기본 진행·죽음→회귀.
회귀 메타/경제/노드맵 전량은 후속(18/16). 상태는 직렬화 가능(20 §2, persistence).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from . import balance, runmap
from .bag import Bag, Loadout
from .combat import Battle, BattleResult
from .combat_m1 import BattleM1
from .rng import Rng
from .. import content

BUILD_LABEL = {"poison": "독", "crit": "치명", "guard": "방어·반격", "dice": "주사위 조작"}
ZONE_ORDER = ["bamboo_grove", "black_wind_forest", "frost_spring_valley"]

# 계열별 '입문에 충분한' 6무공 스타터(#13, D-D 곡선). 제네릭 budget 정렬은 guard·crit을 절벽으로 떨굼:
#  - guard는 role=payload가 없어 sorted(pool)[:6]=약블록6벌 → 출력 0에 가까워 보스1 timeout.
#  - crit은 약페이로드 + 저밀도 crit → 램프 전 전사.
# 손으로 고른 6벌은 각 계열의 입문 출력/생존 floor를 보장(여전히 6벌 = 성장 여지 유지). 미정의 계열은 제네릭.
STARTER_SETS = {
    # guard: 블록2 + 강전환기1(四兩撥千斤 conv0.6) + 받아넘김 출력(증폭-페이로드 2) + 전환기1 → 기→반격 충분.
    "guard": ["protective_qi_shell", "iron_palm_gauntlet", "four_ounce_thousand_catty",
              "armor_breaking_hand", "soul_shattering_strike", "bedrock_heart_method"],
    # crit: 페이로드 출력(예기검 base7 + 마검 base5 + 쾌검 base4) + 예기 누적 엔진2 + crit 밀도. 고분산 유지.
    "crit": ["danhon_seomgeom", "demon_heart_blade", "keen_focus_band",
             "finisher_killing_intent", "swift_short_sword", "blood_claw_gauntlet"],
}


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
    karma: int = 0                                    # 명성/업(사건 선택 누적, 19)
    essence: int = 0                                  # 정수(사건 보상 화폐)
    tutorial_done: bool = False                       # 가이드 첫 런 완료(디제틱 온보딩, 17 §13)
    seen_events: list = field(default_factory=list)   # once_per_run 사건 소진 기록
    map_steps: list = field(default_factory=list)     # 강호 지도 노드 열(runmap, 17 §13.5)
    map_step: int = 0                                 # 현재 갈림길 인덱스
    bag: Bag = field(default_factory=Bag)
    _seed: int = 0

    # ── 생성/배치 ──
    @classmethod
    def new_game(cls, name: str, build: str) -> "GameSession":
        s = cls(name=name, build=build)
        s.level = balance.ZONE_LEVEL["bamboo_grove"]
        # 시작은 6종만 — 나머지는 여정(드랍·기연·객잔·사건)에서 획득(성장 여지).
        pool = content.items_for_build(build)
        bud = lambda it: it.get("power_budget", 0)
        if build in STARTER_SETS:
            by_id = {it["item_id"]: it for it in pool}
            starter = [by_id[i] for i in STARTER_SETS[build] if i in by_id]
        else:
            # M1 빌드(m1 역할 보유): 페이로드 없으면 "전체 발동"이 0이 되므로 페이로드 앵커(출력 3 + 서포트 3).
            payloads = sorted([it for it in pool if (it.get("m1") or {}).get("role") == "payload"], key=bud)
            if payloads:
                others = sorted([it for it in pool if it not in payloads], key=bud)
                starter = payloads[:3] + others[:3]
            else:
                starter = sorted(pool, key=bud)[:6]
        s.owned = [it["item_id"] for it in starter]
        s.bag = Bag.auto([it for it in content.items() if it["item_id"] in s.owned])
        s.ensure_map()
        return s

    # ── 강호 지도(여정, 17 §13.5) ──
    def _map_seed(self) -> int:
        zi = ZONE_ORDER.index(self.zone) if self.zone in ZONE_ORDER else 0
        return (zi * 1_000_003 + self.reincarnations * 7919 + (self._seed or 1) * 31) & 0x7fffffff

    def ensure_map(self):
        if not self.map_steps:
            self.map_steps = runmap.generate(self._map_seed())
            self.map_step = 0

    def node_choices(self) -> list:
        if 0 <= self.map_step < len(self.map_steps):
            return self.map_steps[self.map_step]
        return []

    def at_boss_step(self) -> bool:
        ch = self.node_choices()
        return len(ch) == 1 and ch[0]["type"] == "boss"

    def advance_node(self):
        self.map_step += 1

    # ── 사건(events.json) ──
    def pick_event(self) -> dict | None:
        pool = [e for e in content.events_for_zone(self.zone)
                if not (e.get("once_per_run") and e.get("event_id") in self.seen_events)]
        if not pool:
            pool = content.events_for_zone(self.zone)
        if not pool:
            return None
        self._seed += 1
        rng = Rng((self._seed * 2246822519) & 0x7fffffff)
        weighted = []
        for e in pool:
            weighted += [e] * max(1, int(e.get("weight", 1)))
        return rng.choice(weighted)

    def choice_available(self, choice: dict) -> bool:
        req = choice.get("require", "") or ""
        if not req:
            return True
        if req.startswith("build:"):
            return self.build == req.split(":", 1)[1]
        if req.startswith("karma>="):
            try:
                return self.karma >= int(req.split(">=", 1)[1])
            except ValueError:
                return True
        return True

    def resolve_event_choice(self, event: dict, choice: dict) -> dict:
        eff = choice.get("effects", {}) or {}
        self.gold = max(0, self.gold + int(eff.get("gold", 0)))
        self.shards = max(0, self.shards + int(eff.get("shards", 0)))
        self.essence += int(eff.get("essence", 0))
        self.karma += int(eff.get("karma", 0))
        granted = None
        gi = eff.get("grant_item", "") or ""
        if gi:
            it = content.item_by_id(gi)
            if it and gi not in self.owned:
                self.acquire(it); granted = it
        if event.get("once_per_run") and event.get("event_id") not in self.seen_events:
            self.seen_events.append(event["event_id"])
        return {"result_ko": choice.get("result_ko", ""), "granted": granted, "effects": eff}

    # ── 기연(무공 한 자루) ──
    def fortune_grant(self) -> dict | None:
        pool = [it for it in content.items_for_build(self.build) if it["item_id"] not in self.owned]
        if not pool:
            self.essence += 5
            return None
        self._seed += 1
        it = Rng((self._seed * 40503) & 0x7fffffff).choice(pool)
        self.acquire(it)
        return it

    # ── 객잔(정비·상점): 미보유 무공 1자루 구매가 ──
    def inn_offer(self) -> tuple[dict | None, int]:
        pool = [it for it in content.items_for_build(self.build) if it["item_id"] not in self.owned]
        if not pool:
            return None, 0
        self._seed += 1
        it = Rng((self._seed * 92821) & 0x7fffffff).choice(pool)
        price = balance.RARITY_BUDGET.get(it.get("rarity", "common"), 10) * 4
        return it, price

    def buy(self, item: dict, price: int) -> bool:
        if self.gold < price or item["item_id"] in self.owned:
            return False
        self.gold -= price
        self.acquire(item)
        return True

    # ── 무공 획득/보관(드랍·기연·객잔·사건 공용) ──
    def acquire(self, item: dict) -> str:
        """소유에 추가하고 빈 칸이 있으면 즉시 배치. 'placed' 또는 'reserve'."""
        iid = item["item_id"]
        if iid not in self.owned:
            self.owned.append(iid)
        for i, c in enumerate(self.bag.cells):
            if c is None:
                self.bag.cells[i] = item
                return "placed"
        return "reserve"

    def reserve(self) -> list:
        """보유했으나 구궁에 안 놓인 무공(보관함)."""
        placed = {c["item_id"] for c in self.bag.cells if c}
        return [content.item_by_id(i) for i in self.owned if i not in placed and content.item_by_id(i)]

    def place_from_reserve(self, item_id: str, idx: int):
        """보관함의 무공을 구궁 칸에 놓는다(기존 무공은 자동으로 보관함行)."""
        it = content.item_by_id(item_id)
        if it and 0 <= idx < len(self.bag.cells):
            self.bag.cells[idx] = it

    def loadout(self) -> Loadout:
        return Loadout.compile(self.bag)

    def player_preview(self):
        return self.loadout().make_player(self.name, self.level)

    def move(self, src_idx: int, dst_idx: int):
        self.bag.cells[src_idx], self.bag.cells[dst_idx] = self.bag.cells[dst_idx], self.bag.cells[src_idx]

    # ── 전투 ──
    def _enemy(self, boss: bool, elite: bool = False):
        mobs = content.monsters_for_zone(self.zone)
        if boss:
            return next((m for m in mobs if m.get("is_boss")), mobs[0])
        normals = [m for m in mobs if not m.get("is_boss")]
        if elite and normals:
            return max(normals, key=lambda m: m.get("level", 0))   # 가장 강한 잡졸
        cands = [m for m in normals if m["level"] <= self.level + 1] or normals
        self._seed += 1
        return Rng(self._seed * 7919).choice(cands) if cands else mobs[0]

    def fight(self, boss: bool = False, elite: bool = False) -> tuple[BattleResult, dict]:
        """전투 1회. (결과, 적dict) 반환. 이벤트 스트림은 result.events."""
        enemy = self._enemy(boss, elite)
        lo = self.loadout()
        player = lo.make_player(self.name, self.level)
        self._seed += 1
        res = Battle(lo, player, enemy, balance.ZONE_TIER[self.zone], Rng(self._seed)).run(self.build)
        return res, enemy

    def fight_m1(self, boss: bool = False, elite: bool = False):
        """M1 전투(파일럿) — 매 합 빌드 전체 발동 + 천명괘 줄 강조 + 주사위 재질.
        (BattleM1Result, 적dict). 결과는 apply_result와 호환(outcome만 읽음)."""
        enemy = self._enemy(boss, elite)
        player = self.loadout().make_player(self.name, self.level)
        self._seed += 1
        res = BattleM1(self.bag.cells, player, enemy, balance.ZONE_TIER[self.zone],
                       Rng(self._seed), die=getattr(self, "die_skin", "baekok")).run()
        return res, enemy

    def use_m1(self) -> bool:
        """M1 적용 여부 — m1 데이터 완비 계열. poison(독)·guard(받아넘김)·crit(예기). dice는 아직 스텁."""
        return self.build in ("poison", "guard", "crit")

    def apply_result(self, res: BattleResult, enemy: dict, boss: bool, elite: bool = False) -> dict:
        """보상/진행/죽음 처리. 반환: {leveled, drop, reincarnated, gains, zone_advanced, boss_cleared}."""
        out = {"leveled": [], "drop": None, "reincarnated": False, "gains": {}}
        if res.outcome == "win":
            lv = enemy["level"]
            xp = lv * (40 if boss else 25 if elite else 18)
            gold = lv * (30 if boss else 16 if elite else 8)
            sh = lv * (5 if boss else 3 if elite else 1)
            self.xp += xp; self.gold += gold; self.shards += sh
            out["gains"] = {"xp": xp, "gold": gold, "shards": sh}
            while self.xp >= balance.xp_to_next(self.level):
                self.xp -= balance.xp_to_next(self.level); self.level += 1
                out["leveled"].append(self.level)
            if boss:
                if self.zone not in self.cleared:
                    self.cleared.append(self.zone)
                zi = ZONE_ORDER.index(self.zone) if self.zone in ZONE_ORDER else -1
                if 0 <= zi and zi + 1 < len(ZONE_ORDER):
                    self.zone = ZONE_ORDER[zi + 1]
                    out["zone_advanced"] = self.zone
                else:
                    out["zone_advanced"] = None      # 마지막 존 — 같은 강호를 다시(끝없는)
                self.map_steps = []; self.ensure_map()
                out["boss_cleared"] = True
            # 드랍: 미보유 빌드 아이템
            pool = [it for it in content.items_for_build(self.build) if it["item_id"] not in self.owned]
            if pool and (boss or elite or self._seed % 4 == 0):
                self._seed += 1
                drop = Rng(self._seed * 104729).choice(pool)
                self.acquire(drop); out["drop"] = drop
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
            "karma": self.karma, "essence": self.essence,
            "tutorial_done": self.tutorial_done, "seen_events": list(self.seen_events),
            "map_steps": self.map_steps, "map_step": self.map_step,
            "bag": [(c["item_id"] if c else None) for c in self.bag.cells], "seed": self._seed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameSession":
        s = cls(name=d["name"], build=d["build"], zone=d.get("zone", "bamboo_grove"),
                level=d.get("level", 6), xp=d.get("xp", 0), gold=d.get("gold", 50),
                shards=d.get("shards", 0), cleared=list(d.get("cleared", [])),
                owned=list(d.get("owned", [])), reincarnations=d.get("reincarnations", 0),
                insight=d.get("insight", 0), karma=d.get("karma", 0), essence=d.get("essence", 0),
                tutorial_done=d.get("tutorial_done", False), seen_events=list(d.get("seen_events", [])),
                map_steps=d.get("map_steps", []), map_step=d.get("map_step", 0),
                _seed=d.get("seed", 0))
        s.ensure_map()
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
        self.seen_events = []                 # once_per_run 초기화(새 생)
        self.map_steps = []; self.ensure_map()  # 새 강호 지도
        return gain
