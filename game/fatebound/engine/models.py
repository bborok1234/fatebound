"""전투 런타임 엔티티 — Combatant, Summon. 콘텐츠(아이템/몬스터)는 dict 그대로 사용."""
from __future__ import annotations
from dataclasses import dataclass, field

STAT_KEYS = ("hp", "atk", "def", "spd", "crit", "crit_dmg", "luk")
BASE_FACES = ("검격", "방어", "집중", "회복", "특수", "빈칸")


@dataclass
class Combatant:
    name: str
    hp: float
    max_hp: float
    atk: float
    defense: float           # 데이터/수식 canonical 키는 'def'; 파이썬 키워드라 필드는 defense, ctx()에서 매핑
    spd: int
    crit: float              # %
    crit_dmg: float = 1.5
    luk: int = 0
    is_player: bool = False
    statuses: dict = field(default_factory=dict)   # poison/burn/weak/vulnerable/shield/stun 등
    counter_pct: float = 0.0
    poison_amp: float = 0.0  # amplify_poison_pct 누적(%)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def hp_pct(self) -> float:
        return max(0.0, self.hp) / self.max_hp if self.max_hp else 0.0

    def ctx(self) -> dict:
        """수식 평가 컨텍스트(데이터의 'def' 키 포함 — 단일 매핑 지점, 20 §2)."""
        return {"atk": self.atk, "hp": self.hp, "max_hp": self.max_hp,
                "def": self.defense, "defense": self.defense, "spd": self.spd,
                "crit": self.crit, "crit_dmg": self.crit_dmg, "luk": self.luk}


@dataclass
class Summon:
    """소환 빌드의 임시 아군(18 §4). 매 라운드 플레이어 뒤 자동 행동."""
    name: str
    atk: float
    hp: float
    duration: int            # 남은 라운드(0이면 피격 사망까지)
    kind: str = "beast"      # beast|clone|formation

    @property
    def alive(self) -> bool:
        return self.hp > 0
