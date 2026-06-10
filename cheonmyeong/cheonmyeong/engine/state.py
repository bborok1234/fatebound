"""게임 상태 — 전선(2권 14)·축적(2권 06)·돌파(2권 01 §3)·루팅(2권 08 §2.5).
슬라이스: 시간은 명령형(하루 보내기) — 실시간 방치는 본 구현(last_seen 타임스탬프).
다이얼은 frontier_sim·progression_sim 검산값 정합."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

TIER_CEIL = 50                    # 삼류 천장 (08 §2.5)
P_BLESSED = 0.012                 # 축복률
DONO_BASE, DONO_FAIL_BONUS = 0.45, 0.10   # 돈오 (01 §3)
WALL_NEED_DAYS = 3.0              # 이류 벽 축적(frontier_sim 정합)
IDLE_HUNTS = 8                    # 방치 바닥 (08 §2.5)

DROP_BASES = ["녹슨 비수", "죽력 표창", "대껍질 호심갑", "청죽 단봉", "들풀 영약"]
JOURNAL_MISHAPS = [
    "들개한테 또 물렸다. 세 번째다.",
    "산적 하나가 독 안 통하는 척하다가 picked 자세로 굳었다. 통한 거다.",
    "댓잎 차를 끓였는데 찻물이 초록인 게 영 미덥잖다.",
    "밤새 비가 왔다. 독무가 비에 씻겨 두 번 헛손질했다.",
]


@dataclass
class Drop:
    name: str
    quality: int
    blessed: bool

    @property
    def label(self) -> str:
        star = "★" if self.blessed else ""
        return f"{star}{self.name} (품질 {self.quality}/{TIER_CEIL})"


@dataclass
class GameState:
    seed: int = 11
    name: str = "천기노조"
    day: int = 1
    gyeongji: str = "삼류"
    star: int = 1                       # 소단계(10성)
    naegong: float = 0.3                # 갑자
    wall_progress: float = 0.0          # 이류 벽 축적(0~1)
    dono_fails: int = 0
    explored: list[str] = field(default_factory=lambda: ["죽림"])
    drops: list[Drop] = field(default_factory=list)
    clues: int = 0
    journal: list[dict] = field(default_factory=list)
    battles_won: int = 1                # 첫 전투
    chain: list[str] = field(default_factory=list)
    shelf: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        from ..data import slice_pack as P
        if not self.chain:
            self.chain = list(P.CHAIN)
        if not self.shelf:
            self.shelf = list(P.SHELF)

    # ── 검산 텔레그래프 (서재 — rulebook 엔진 그대로, 이원화 금지) ──
    def appraise(self, chain: list[str] | None = None, n: int = 24) -> dict:
        from . import combat
        rounds = []
        wins = 0
        for s in range(n):
            last = None
            for ev in combat.run_battle("죽림 산적", seed=s * 13 + 1, chain=chain or self.chain):
                last = ev
            if last and last.result == "win":
                wins += 1
                rounds.append(last.round)
        avg = sum(rounds) / len(rounds) if rounds else 0
        return dict(avg=avg, winrate=wins / n)

    # ── 벽 상태 (전선 바) ──
    @property
    def wall_ready(self) -> bool:
        return self.wall_progress >= 1.0

    @property
    def dono_chance(self) -> float:
        return min(0.95, DONO_BASE + DONO_FAIL_BONUS * self.dono_fails)

    # ── 방치 하루 (걸어두기 → 보고) ──
    def idle_day(self) -> dict:
        hunts = IDLE_HUNTS + self.rng.randint(-1, 2)
        day_drops: list[Drop] = []
        for _ in range(hunts):
            if self.rng.random() < 0.8:
                blessed = self.rng.random() < P_BLESSED * 4   # 슬라이스 체감 보정(데모 밀도)
                q = (self.rng.randint(int(TIER_CEIL * 0.9), TIER_CEIL) if blessed
                     else self.rng.randint(12, int(TIER_CEIL * 0.85)))
                day_drops.append(Drop(self.rng.choice(DROP_BASES), q, blessed))
        self.drops += day_drops
        self.naegong += 0.05
        self.battles_won += hunts
        gained = (1.0 / WALL_NEED_DAYS) * self.rng.uniform(0.9, 1.15)
        self.wall_progress = min(1.0, self.wall_progress + gained)
        self.star = min(10, self.star + 1)
        clue = self.rng.random() < 0.5 and self.clues < 1
        if clue:
            self.clues += 1
        entry = dict(
            day=self.day, hunts=hunts, drops=day_drops,
            best=max(day_drops, key=lambda d: d.quality) if day_drops else None,
            wall=self.wall_progress, clue=clue,
            mishap=self.rng.choice(JOURNAL_MISHAPS),
        )
        self.journal.append(entry)
        self.day += 1
        return entry

    # ── 돈오 돌파 (이류의 벽) ──
    def attempt_breakthrough(self) -> bool:
        ok = self.rng.random() < self.dono_chance
        if ok:
            self.gyeongji = "이류"
            self.star = 1
            self.wall_progress = 0.0
            # explored 추가는 디졸브 완료 시점(MapScreen._step) — 안개 걷힘이 보여야 한다
        else:
            self.dono_fails += 1            # 실패=진척 (01 §3)
        return ok
