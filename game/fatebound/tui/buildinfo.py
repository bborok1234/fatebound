"""무공 기틀(빌드) 소개 카피 — 온보딩용 표현 콘텐츠(17 §13.2). UI 레이어.

엔진=권위(수치는 balance/data), 여기는 '무슨 빌드인지 이해시키는' 설명 텍스트만.
"""
from __future__ import annotations

# 표시 순서 = 학습 난이도(쉬움→까다로움): 독 → 치명 → 방어 → 주사위
BUILD_ORDER = ["poison", "crit", "guard", "dice"]

BUILD_GUIDE = {
    "poison": {
        "key": "poison",
        "name": "독(毒)",
        "glyph": "☠",
        "tagline": "시간을 내 편으로.",
        "how": "적에게 독을 차곡차곡 쌓는다. 독은 매 합 알아서 체력을 갉으니 오래 끌수록 내가 이긴다.",
        "bijang": "천독혈무(天毒血舞). 쌓아둔 독을 한 번에 터뜨려 폭발 피해로 바꾼다.",
        "sample": "독을 세 겹 묻혀두면 가만히 둬도 적이 무너진다.",
        "feel": "인내심 있는 운영가",
        "difficulty": "쉬움",
    },
    "crit": {
        "key": "crit",
        "name": "치명(致命)",
        "glyph": "✦",
        "tagline": "단 한 수에 모든 것을.",
        "how": "치명타 확률과 배수를 끌어올려 한 번의 굴림으로 전세를 뒤집는다.",
        "bijang": "필연(必然)의 일격. 확정 치명으로 결정타를 꽂는다.",
        "sample": "치명 한 방에 적 체력 절반이 날아간다.",
        "feel": "한 방의 로망",
        "difficulty": "쉬움",
    },
    "guard": {
        "key": "guard",
        "name": "방어·반격(防)",
        "glyph": "▣",
        "tagline": "맞을수록 강해진다.",
        "how": "방어로 버티며 적의 공격을 반격으로 되돌려준다. 쌓은 인내가 곧 화력이 된다.",
        "bijang": "반탄(反彈). 그동안 쌓은 방어를 한순간에 반격 폭발로 바꾼다.",
        "sample": "호신강기로 막아내고, 되돌려준 반격이 적을 가른다.",
        "feel": "침착한 수성가",
        "difficulty": "보통",
    },
    "dice": {
        "key": "dice",
        "name": "주사위 조작(占)",
        "glyph": "◍",
        "tagline": "운명을 조작한다.",
        "how": "천명괘의 면을 비틀고 다시 굴려, 원하는 수가 뜨도록 확률 자체를 설계한다.",
        "bijang": "운명 절단(斷). 굴림을 비틀어 최대 배수의 일격을 꽂는다.",
        "sample": "면을 다시 굴려 원하던 수를 띄운다. 천명반이 내 손 안에 있다.",
        "feel": "천명반을 갖고 노는 자",
        "difficulty": "까다로움",
    },
}


def guide(build: str) -> dict:
    return BUILD_GUIDE.get(build, BUILD_GUIDE["poison"])
