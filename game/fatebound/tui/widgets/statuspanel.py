"""상태 패널 — 플레이어/적 HP 게이지·스탯·천명괘·커서 아이템 디테일. 전투 재생 중 라이브 갱신."""
from __future__ import annotations
from textual.widget import Widget
from rich.console import Group
from rich.text import Text
from rich.rule import Rule

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f"}


def bar(cur: float, mx: float, width: int = 16, color: str = "#c2453a") -> Text:
    mx = max(1, mx)
    filled = max(0, min(width, round(width * cur / mx)))
    t = Text()
    t.append("▰" * filled, style=color)
    t.append("▱" * (width - filled), style="#3a3a42")
    t.append(f" {max(0,int(cur))}/{int(mx)}", style="grey70")
    return t


class StatusPanel(Widget):
    def __init__(self, session, **kw):
        super().__init__(**kw)
        self.session = session
        self.p_hp = self.p_max = 0
        self.e_name = "-"; self.e_hp = self.e_max = 0
        self.bijang = 0; self.bijang_max = 6
        self.detail_item = None
        self.faces: list = []

    def set_combat(self, p_hp, p_max, e_name, e_hp, e_max, bijang=0):
        self.p_hp, self.p_max = p_hp, p_max
        self.e_name, self.e_hp, self.e_max = e_name, e_hp, e_max
        self.bijang = bijang
        self.refresh()

    def render(self):
        s = self.session
        g = []
        g.append(Text(f"{s.name} · 제{s.reincarnations+1}생 · Lv{s.level}", style="#c8a24a"))
        if self.p_max:
            g.append(bar(self.p_hp, self.p_max, color="#c2453a"))
        else:
            p = s.player_preview()
            g.append(bar(p.hp, p.max_hp, color="#c2453a"))
        g.append(Text(f"깨달음 {s.insight} · 골드 {s.gold} · 파편 {s.shards}", style="grey62"))
        # 비장 게이지
        bj = "●" * self.bijang + "○" * max(0, self.bijang_max - self.bijang)
        g.append(Text(f"비장 {bj}", style="#e0b341"))
        g.append(Rule(style="#3a3a42"))
        # 적
        if self.e_max:
            g.append(Text(f"敵 {self.e_name}", style="#d4582f"))
            g.append(bar(self.e_hp, self.e_max, color="#d4582f"))
            g.append(Rule(style="#3a3a42"))
        # 천명괘
        faces = self.faces or s.loadout().faces
        g.append(Text("천명괘", style="grey62"))
        g.append(Text(" ".join(f"〔{f if len(f)<=4 else f[:3]}〕" for f in faces), style="#4a90a4"))
        g.append(Rule(style="#3a3a42"))
        # 커서 아이템 디테일
        it = self.detail_item
        if it:
            g.append(Text(it["name_ko"], style=RARITY.get(it["rarity"], "white")))
            g.append(Text(f"{it['rarity']} · 예산 {it.get('power_budget','?')} · {'/'.join(it.get('tags',[]))}", style="grey54"))
            fx = "; ".join(f"{e['condition'].replace('on_face:','▸')}:{e['effect']}" for e in it.get("effects", [])[:3])
            g.append(Text(fx, style="grey46"))
        return Group(*g)
