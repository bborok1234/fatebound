"""상태 패널(17 §13.4) — 플레이어/적 HP·천명괘·상생쌍·커서 무공 디테일. 전투 중 라이브 갱신."""
from __future__ import annotations
from textual.widget import Widget
from rich.console import Group
from rich.text import Text
from rich.rule import Rule
from ...engine.bag import synergy_cells

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f"}
EFFECT_KO = {
    "apply_poison": "독 부여", "deal_damage": "피해", "damage": "피해",
    "increase_attack": "공격↑", "increase_defense": "방어↑", "increase_crit": "치명↑",
    "increase_crit_dmg": "치명배수↑", "increase_speed": "속도↑", "counter": "반격",
    "amplify_poison_pct": "독 증폭", "heal": "회복", "shield": "보호막",
    "apply_burn": "화상", "apply_weak": "약화", "apply_vulnerable": "취약",
    "summon_ally": "소환", "reroll": "리롤", "stun": "기절",
}


STATUS_GLYPH = {"poison": "☠독", "burn": "🔥화", "weak": "▽약", "vulnerable": "◇취", "stun": "✦둔"}
STATUS_COLOR = {"poison": "#6fae5a", "burn": "#d4582f", "weak": "#b06a3a",
                "vulnerable": "#b07fd4", "stun": "#b07fd4"}


def bar(cur: float, mx: float, width: int = 16, color: str = "#c2453a") -> Text:
    mx = max(1, mx)
    ratio = cur / mx
    if ratio <= 0.3 and cur > 0:        # 저HP 위험 강조(juice, 17 §2.4)
        color = "#ff6b5e"
    filled = max(0, min(width, round(width * ratio)))
    t = Text()
    t.append("▰" * filled, style=color)
    t.append("▱" * (width - filled), style="#3a3a42")
    warn = " ⚠" if (ratio <= 0.3 and cur > 0) else ""
    t.append(f" {max(0,int(cur))}/{int(mx)}{warn}", style="grey70" if not warn else "#ff6b5e")
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
        self.cur_face = ""
        self.statuses: dict = {}
        self.output = None          # M1 빌드 출력(텔레그래프)
        self.preview_output = None  # 잡은 무공을 커서 칸에 놓을 때 예상 출력
        self.syn_formed = None      # 스왑 시 새로 생기는 상생쌍
        self.syn_broken = None      # 스왑 시 깨지는 상생쌍

    def set_combat(self, p_hp, p_max, e_name, e_hp, e_max, bijang=0, cur_face="", statuses=None):
        self.p_hp, self.p_max = p_hp, p_max
        self.e_name, self.e_hp, self.e_max = e_name, e_hp, e_max
        self.bijang = bijang
        self.cur_face = cur_face
        self.statuses = statuses or {}
        self.refresh()

    def _synergy_lines(self):
        bag = self.session.bag
        _, pairs = synergy_cells(bag)
        seen, out = set(), []
        for a, b in pairs:
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            na = bag.cells[a]["name_ko"] if bag.cells[a] else "?"
            nb = bag.cells[b]["name_ko"] if bag.cells[b] else "?"
            out.append(f"{na} ↔ {nb}")
        return out

    def render(self):
        s = self.session
        g = []
        g.append(Text(f"{s.name} · 제{s.reincarnations+1}생 · Lv{s.level}", style="#c8a24a"))
        if self.p_max:
            g.append(bar(self.p_hp, self.p_max, color="#c2453a"))
        else:
            p = s.player_preview()
            g.append(bar(p.hp, p.max_hp, color="#c2453a"))
        # 출력(出力) 텔레그래프 — 배치가 출력을 바꾼다(M1). 잡고 호버하면 commit 전 델타.
        if self.output is not None:
            if self.preview_output is not None:
                d = self.preview_output - self.output
                pct = (100 * d / self.output) if self.output else 0
                up, dn = d > 0.05, d < -0.05
                arrow = "▲" if up else ("▼" if dn else "·")
                col = "#5aa67c" if up else ("#d4582f" if dn else "#9a958a")
                t = Text("출력 ", style="#9a958a")
                t.append(f"{arrow}{pct:+.0f}%", style=f"{col} bold")               # %를 앞·굵게(스케일 무관 가독)
                t.append(f"  {self.output:.1f}→{self.preview_output:.1f}", style="#9a958a")
                g.append(t)
                for a, b in (self.syn_formed or [])[:2]:
                    g.append(Text(f"  ＋상생 {a}↔{b}", style="#5aa67c"))
                for a, b in (self.syn_broken or [])[:2]:
                    g.append(Text(f"  －상생 {a}↔{b}", style="#d4582f"))
                g.append(Text("  Enter로 확정", style="#55504a"))
            else:
                g.append(Text(f"출력(出力) {self.output:.1f} /합", style="#c8a24a bold"))
        g.append(Text(f"깨달음 {s.insight} · 골드 {s.gold} · 파편 {s.shards}", style="grey62"))
        # 비장 게이지
        bj = "●" * self.bijang + "○" * max(0, self.bijang_max - self.bijang)
        g.append(Text(f"비장 {bj}", style="#e0b341"))
        # 적(전투 중) + 상태이상 배지
        if self.e_max:
            g.append(Rule(style="#3a3a42"))
            g.append(Text(f"敵 {self.e_name}", style="#d4582f"))
            g.append(bar(self.e_hp, self.e_max, color="#d4582f"))
            if self.statuses:
                bt = Text()
                for st, n in self.statuses.items():
                    if n and n > 0:
                        bt.append(f"{STATUS_GLYPH.get(st, st)}{n} ", style=STATUS_COLOR.get(st, "grey70"))
                if len(bt):
                    g.append(bt)
        g.append(Rule(style="#3a3a42"))
        # 상생쌍(사람이 읽게 — 접근성 §8). 천명괘는 상단 DiceWidget이 전담.
        syn = self._synergy_lines()
        if syn:
            g.append(Text("상생(相生)", style="#5aa67c"))
            for line in syn[:4]:
                g.append(Text(f" ◆ {line}", style="#5aa67c"))
        # 커서 무공 디테일
        it = self.detail_item
        g.append(Rule(style="#3a3a42"))
        if it:
            g.append(Text(it["name_ko"], style=f"{RARITY.get(it['rarity'],'white')} bold"))
            # 쉬운 말 한 줄 — 가장 먼저·또렷이(라이트 무협 가독성)
            gist = it.get("gist_ko", "")
            if gist:
                g.append(Text(gist, style="#e8e2d4"))
            tags = "·".join(it.get("tags", []))
            g.append(Text(f"{it['rarity']} · {tags}", style="grey54"))
            for e in it.get("effects", [])[:3]:
                cond = e.get("condition", "").replace("on_face:", "▸").replace("passive", "상시").replace("on_crit", "치명시")
                ek = EFFECT_KO.get(e.get("effect", ""), e.get("effect", ""))
                g.append(Text(f"  {cond} → {ek}", style="grey46"))
            fl = it.get("flavor_ko", "")
            if fl:
                g.append(Text(fl, style="#6b665c italic"))   # 펀치라인 안 잘리게 전문 노출(자동 줄바꿈)
        else:
            g.append(Text("커서를 무공 위에 두면 상세가 보인다.", style="grey42"))
        return Group(*g)
