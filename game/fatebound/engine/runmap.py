"""강호 지도 — 한 존의 여정을 노드 열(列)로 생성(17 §13.5). 순수·결정론.

존마다 5개의 갈림길 + 마지막 보스 관문. 각 갈림길에서 2~3개 노드 중 하나를 선택해 나아간다.
StS식 분기를 터미널에 맞춰 '열 단위 선택'으로 단순화.
"""
from __future__ import annotations
from .rng import Rng

NODE_LABEL = {
    "battle": "전투", "elite": "정예", "event": "사건",
    "inn": "객잔", "fortune": "기연", "boss": "보스",
}
NODE_GLYPH = {
    "battle": "⚔", "elite": "⚜", "event": "❖", "inn": "⌂", "fortune": "✦", "boss": "☷",
}
NODE_DESC = {
    "battle": "강호의 잡졸과 겨룬다. 경험치·골드.",
    "elite": "한 수 위의 강자. 위험하나 보상이 크다.",
    "event": "기연일까 함정일까 — 선택이 길을 가른다.",
    "inn": "객잔에서 숨을 고른다. 무공을 사거나 정비.",
    "fortune": "뜻밖의 기연. 무공 한 자루가 손에 들어올지도.",
    "boss": "이 땅의 주인. 쓰러뜨리면 다음 강호가 열린다.",
}

# 갈림길별 후보 풀(페이싱: 초반 전투, 중반 휴식/사건, 후반 정예/기연 → 보스)
STEP_POOLS = [
    ["battle", "event"],
    ["battle", "elite", "event"],
    ["event", "inn", "battle"],
    ["battle", "elite", "fortune"],
    ["inn", "event", "battle"],
]


def generate(seed: int) -> list[list[dict]]:
    """노드 열 리스트 반환. 각 열 = [{type}, ...] 선택지. 마지막 열 = [{boss}]."""
    rng = Rng(seed)
    steps: list[list[dict]] = []
    for pool in STEP_POOLS:
        p = list(pool)
        rng.shuffle(p)
        k = 3 if (len(p) >= 3 and rng.chance(45)) else 2
        steps.append([{"type": t} for t in p[:k]])
    steps.append([{"type": "boss"}])
    return steps
