"""무공 기틀 선택 — 설명 카드 + 프리뷰(17 §13.2). 한자 버튼이 아니라 '이해되는 선택'."""
from __future__ import annotations
from textual.screen import Screen
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static
from textual.reactive import reactive
from ..buildinfo import BUILD_ORDER, guide
from ...engine.session import GameSession
from ... import persistence

DIFF_COLOR = {"쉬움": "#5aa67c", "보통": "#c8a24a", "까다로움": "#d4582f"}


class BuildSelectScreen(Screen):
    BINDINGS = [
        ("up", "move(-1)"), ("down", "move(1)"),
        ("1", "pick(0)"), ("2", "pick(1)"), ("3", "pick(2)"), ("4", "pick(3)"),
        ("enter", "confirm"), ("space", "confirm"),
        ("escape", "back"),
    ]
    sel: reactive[int] = reactive(0)

    def compose(self):
        yield Static("[#c8a24a]무공의 기틀을 정하라[/]   [#9a958a]회귀한 그대가 가장 먼저 더듬는 힘[/]", id="bs-title")
        with Horizontal(id="bs-body"):
            with Vertical(id="bs-list"):
                for i, key in enumerate(BUILD_ORDER):
                    yield Static(id=f"bs-row-{i}", classes="bs-row")
            with Container(id="bs-detail-pane"):
                yield Static(id="bs-detail")
        yield Static("[#9a958a]①②③④ / ↑↓ 선택 · [#c8a24a]Enter[/#9a958a] 이 기틀로 시작 · Esc 뒤로[/]", id="bs-foot")

    def on_mount(self):
        self._paint()

    def watch_sel(self):
        try:
            self._paint()
        except Exception:
            pass

    def _paint(self):
        for i, key in enumerate(BUILD_ORDER):
            g = guide(key)
            row = self.query_one(f"#bs-row-{i}", Static)
            if i == self.sel:
                row.update(f"[#1a1a1f on #c8a24a] {g['glyph']} {g['name']} [/]")
                row.add_class("active")
            else:
                row.update(f"[#9a958a] {g['glyph']} {g['name']} [/]")
                row.remove_class("active")
        g = guide(BUILD_ORDER[self.sel])
        dc = DIFF_COLOR.get(g["difficulty"], "#9a958a")
        detail = (
            f"[#c8a24a]{g['glyph']}  {g['name']}[/]   [{dc}]난이도 {g['difficulty']}[/]\n"
            f"[#e8e2d4 italic]\"{g['tagline']}\"[/]\n\n"
            f"[#9a958a]▸ 어떻게 싸우나[/]\n  {g['how']}\n\n"
            f"[#e0b341]▸ 비장(秘藏)의 수[/]\n  {g['bijang']}\n\n"
            f"[#7fa8d4]▸ 한 장면[/]\n  [italic]{g['sample']}[/]\n\n"
            f"[#9a958a]▸ 이런 그대에게[/]  {g['feel']}"
        )
        self.query_one("#bs-detail", Static).update(detail)

    def action_move(self, d: int):
        self.sel = (self.sel + d) % len(BUILD_ORDER)

    def action_pick(self, i: int):
        self.sel = i

    def action_confirm(self):
        from .game import GameScreen
        key = BUILD_ORDER[self.sel]
        session = GameSession.new_game("천기노조", key)
        persistence.save(session)
        self.app.switch_screen(GameScreen(session, first_run=True))

    def action_back(self):
        from .title import TitleScreen
        self.app.switch_screen(TitleScreen())
