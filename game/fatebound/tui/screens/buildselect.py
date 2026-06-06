"""무공 기틀 + 천명괘 재질 선택(2단계) — 17 §13.2. 계열×재질이 빌드 정체성(#6 키스톤)."""
from __future__ import annotations
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static
from textual.reactive import reactive
from ..buildinfo import BUILD_ORDER, guide
from ...engine.session import GameSession
from ... import persistence

DIFF_COLOR = {"쉬움": "#5aa67c", "보통": "#c8a24a", "까다로움": "#d4582f"}

# 천명괘 재질 = 변수↔일관 메타축(키스톤). 계열과 짝지어 빌드 성격을 정한다.
DIE_ORDER = ["baekok", "bichwi", "heukyo", "hyeolok", "baekgol"]
DIE_INFO = {
    "baekok":  {"glyph": "○", "name": "백옥(白玉)",   "color": "#e8e2d4", "axis": "기준",
                "tag": "치우침 없는 기준점. 변수도 일관도 중간 — 뭘 골라야 할지 모르겠다면 이걸로."},
    "bichwi":  {"glyph": "◇", "name": "비취(翡翠)",   "color": "#5aa67c", "axis": "일관",
                "tag": "약하게 나온 줄을 한 번 다시 굴려 들쭉날쭉을 줄인다. 꾸준히 쌓는 독·버티는 방어와 잘 맞는다."},
    "heukyo":  {"glyph": "◆", "name": "흑요석(黑曜石)", "color": "#7fa8d4", "axis": "조준",
                "tag": "천명이 깃든 줄에 힘이 더 쏠린다. 강한 무공을 한 줄로 몰아 두는 빌드가 크게 본다."},
    "hyeolok": {"glyph": "◈", "name": "혈옥(血玉)",   "color": "#d4582f", "axis": "고점",
                "tag": "한 합이 크게 터지거나, 빗나가거나. 분산이 큰 'd20' — 한 방을 노리는 치명과 만나면 천장이 치솟는다."},
    "baekgol": {"glyph": "◐", "name": "백골(白骨)",   "color": "#c8a24a", "axis": "올라운드",
                "tag": "출력도 분산도 조금씩. 무난하되 백옥보다 살짝 공격적이고 살짝 들쭉날쭉."},
}


class BuildSelectScreen(Screen):
    BINDINGS = [
        ("up", "move(-1)"), ("down", "move(1)"),
        ("1", "pick(0)"), ("2", "pick(1)"), ("3", "pick(2)"), ("4", "pick(3)"), ("5", "pick(4)"),
        ("enter", "confirm"), ("space", "confirm"),
        ("escape", "back"),
    ]
    sel: reactive[int] = reactive(0)
    phase: reactive[str] = reactive("build")     # build → die

    def __init__(self):
        super().__init__()
        self.picked_build: str | None = None

    def _items(self) -> list:
        return BUILD_ORDER if self.phase == "build" else DIE_ORDER

    def compose(self):
        yield Static(id="bs-title")
        with Horizontal(id="bs-body"):
            with Vertical(id="bs-list"):
                for i in range(max(len(BUILD_ORDER), len(DIE_ORDER))):
                    yield Static(id=f"bs-row-{i}", classes="bs-row")
            with Container(id="bs-detail-pane"):
                yield Static(id="bs-detail")
        yield Static(id="bs-foot")

    def on_mount(self):
        self._paint()

    def watch_sel(self):
        try:
            self._paint()
        except Exception:
            pass

    def watch_phase(self):
        try:
            self._paint()
        except Exception:
            pass

    def _paint(self):
        items = self._items()
        n_rows = max(len(BUILD_ORDER), len(DIE_ORDER))
        if self.phase == "build":
            self.query_one("#bs-title", Static).update(
                "[#c8a24a]무공의 기틀을 정하라[/]   [#9a958a]회귀한 그대가 가장 먼저 더듬는 힘[/]")
            self.query_one("#bs-foot", Static).update(
                "[#9a958a]①②③④ / ↑↓ 선택 · [#c8a24a]Enter[/#9a958a] 다음(천명괘) · Esc 뒤로[/]")
        else:
            self.query_one("#bs-title", Static).update(
                f"[#c8a24a]천명괘를 고르라[/]   [#9a958a]{guide(self.picked_build)['name']}와 함께 굴릴 주사위 — 변수↔일관[/]")
            self.query_one("#bs-foot", Static).update(
                "[#9a958a]①~⑤ / ↑↓ 선택 · [#c8a24a]Enter[/#9a958a] 이 기틀로 시작 · Esc 계열 다시[/]")
        for i in range(n_rows):
            row = self.query_one(f"#bs-row-{i}", Static)
            if i >= len(items):
                row.update(""); row.remove_class("active"); continue
            key = items[i]
            if self.phase == "build":
                g = guide(key); label = f"{g['glyph']} {g['name']}"
            else:
                d = DIE_INFO[key]; label = f"{d['glyph']} {d['name']}"
            if i == self.sel:
                row.update(f"[#1a1a1f on #c8a24a] {label} [/]"); row.add_class("active")
            else:
                row.update(f"[#9a958a] {label} [/]"); row.remove_class("active")
        self.query_one("#bs-detail", Static).update(self._detail())

    def _detail(self) -> str:
        if self.phase == "build":
            g = guide(self._items()[self.sel])
            dc = DIFF_COLOR.get(g["difficulty"], "#9a958a")
            return (
                f"[#c8a24a]{g['glyph']}  {g['name']}[/]   [{dc}]난이도 {g['difficulty']}[/]\n"
                f"[#e8e2d4 italic]\"{g['tagline']}\"[/]\n\n"
                f"[#9a958a]▸ 어떻게 싸우나[/]\n  {g['how']}\n\n"
                f"[#e0b341]▸ 비장(秘藏)의 수[/]\n  {g['bijang']}\n\n"
                f"[#7fa8d4]▸ 한 장면[/]\n  [italic]{g['sample']}[/]\n\n"
                f"[#9a958a]▸ 이런 그대에게[/]  {g['feel']}"
            )
        d = DIE_INFO[self._items()[self.sel]]
        return (
            f"[{d['color']}]{d['glyph']}  {d['name']}[/]   [#9a958a]{d['axis']}[/]\n\n"
            f"[#e8e2d4]{d['tag']}[/]\n\n"
            f"[#9a958a]천명괘는 매 합 6줄 중 한 줄을 강조한다. 재질이 그 굴림의 성격을 바꾼다 —\n"
            f"일관(비취)은 들쭉날쭉을 누르고, 고점(혈옥)은 천장과 바닥을 함께 키운다.[/]"
        )

    def action_move(self, d: int):
        self.sel = (self.sel + d) % len(self._items())

    def action_pick(self, i: int):
        if i < len(self._items()):
            self.sel = i

    def action_confirm(self):
        if self.phase == "build":
            self.picked_build = BUILD_ORDER[self.sel]
            self.phase = "die"
            self.sel = 0
            return
        from .game import GameScreen
        die = DIE_ORDER[self.sel]
        session = GameSession.new_game("천기노조", self.picked_build, die_skin=die)
        persistence.save(session)
        self.app.switch_screen(GameScreen(session, first_run=True))

    def action_back(self):
        if self.phase == "die":
            self.phase = "build"
            self.sel = BUILD_ORDER.index(self.picked_build) if self.picked_build in BUILD_ORDER else 0
            return
        from .title import TitleScreen
        self.app.switch_screen(TitleScreen())
