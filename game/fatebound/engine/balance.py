"""
밸런스 상수·곡선 — 08(수치 백본)·14(시뮬 5차 튜닝)의 단일 출처.
재미 튜닝을 빠르게 하려고 모든 수치를 여기 모음. 시드값이며 sim 스윕으로 확정.
"""
from __future__ import annotations

BUILD_LABEL = {"poison": "독", "crit": "치명", "guard": "방어·반격", "dice": "주사위 조작"}

# ── 캐릭터 기본 스탯 곡선(08 §2.2, 14 5차: 초반 atk 하향으로 전투 길이↑) ──
def base_player_stats(level: int) -> dict:
    return {
        "hp": 100 + 30 * level,
        "atk": round(10 + 2.6 * level),
        "def": round(5 + 1.5 * level),
        "spd": 8, "crit": 5, "crit_dmg": 1.5, "luk": 0,
    }

def xp_to_next(level: int) -> int:           # 08 §2.1
    return round(100 * (1.15 ** (level - 1)))

# ── 전투(08 §4, 14) ──
def k_zone(tier: int) -> int:                # 방어 비율 경감 상수
    return 50 + 25 * (tier - 1)

BOSS_HP_SCALE = 0.6        # 보스 과탱 보정(데이터 ×6 → 실효 ×3.6)
NORMAL_HP_SCALE = 1.8      # 일반 몹 HP↑ — 전투 8~16합 목표(C2)
MAX_ROUNDS = 30            # 강제 종료
TARGET_ROUNDS = (8, 16)

# ── 상태이상(08 §7, 14) ──
POISON_PER_STACK = 2.0
POISON_HP_PCT = 0.014      # 독 틱 max_hp 비례 성분(고HP 보스 대응)
POISON_DECAY_TURNS = 2     # 독 감쇠 주기(2턴당 1중첩 — 램프 허용)
BURN_COEF = 0.12
WEAK_PCT = 0.20
VULNERABLE_PCT = 0.25
COUNTER_PCT_DEFAULT = 0.30
COUNTER_SCALE = 1.15       # 반격 글로벌 보정(14 5차)
STUN_CHANCE = 30.0
FOCUS_THRESHOLD = 3        # 응기 카운터 → 특수 보장

# ── 비장(秘藏)의 수(02, 14 4·5차) — 유틸 빌드 보스 딜 창구 + 에이전시 ──
BIJANG_CHARGE = 6
BIJANG = {
    "poison": {"type": "detonate", "k": 12},
    "crit":   {"type": "burst", "mult": 1.15, "crit": True},
    "guard":  {"type": "counter_burst", "atk": 0.8, "def": 1.2, "accum": 0.8},
    "dice":   {"type": "burst", "mult": 2.6, "crit": True},
}

# ── 시너지/예산(08 §6) ──
ADJ_DISCOUNT = 0.6
RARITY_BUDGET = {"common": 10, "rare": 20, "epic": 35, "legendary": 55}

# ── 회귀 메타(08 §11.2, 18 §2) ──
def insight_gain(zones_reached: int, bosses: int, elites: int, reincarnations: int, cleared: bool) -> int:
    g = zones_reached * 20 + bosses * 40 + elites * 8 + reincarnations * 3
    return round(g * (1.5 if cleared else 1.0))

def meta_node_cost(nth: int) -> int:
    return round(30 * (1.25 ** (nth - 1)))

MASTERY_LEVEL_CAP = 12
MASTERY_REROLL_CAP = 3

# ── 방치(08 §11.4, 16 C6) — 능동의 1/3~1/5, 깨달음은 능동만 ──
IDLE_CAP_HOURS = 8
def idle_per_hour(level: int) -> dict:
    return {"gold": level * 30, "xp": level * 20, "shards": level * 3}

# ── 지역 게이팅(08 §8.2) ──
ZONE_TIER = {"bamboo_grove": 1, "black_wind_forest": 2, "frost_spring_valley": 3}
ZONE_LEVEL = {"bamboo_grove": 6, "black_wind_forest": 13, "frost_spring_valley": 20}
