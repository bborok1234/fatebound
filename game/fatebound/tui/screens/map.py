"""강호 지도(17 §13.5) — 현재 갈림길의 노드 중 하나를 고른다. 선택을 dismiss(node)로 반환."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.containers import Vertical, Center, Middle
from textual.widgets import Static
from textual.reactive import reactive
from ...engine.runmap import NODE_LABEL, NODE_GLYPH, NODE_DESC

NODE_COLOR = {"battle": "#e8e2d4", "elite": "#d4582f", "event": "#7fa8d4",
              "inn": "#5aa67c", "fortune": "#e0b341", "boss": "#d4582f"}


class MapScreen(ModalScreen):
    BINDINGS = [("up", "move(-1)"), ("down", "move(1)"),
                ("1", "pick(0)"), ("2", "pick(1)"), ("3", "pick(2)"),
                ("enter", "confirm"), ("space", "confirm"), ("escape", "cancel")]
    sel: reactive[int] = reactive(0)

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.choices = session.node_choices()

    def compose(self):
        with Middle():
            with Center():
                yield Static(id="map-progress")
            with Center():
                yield Static("[#c8a24a]갈림길 · 어느 길로 나아가는가[/]", id="map-title")
            with Center():
                with Vertical(id="map-list"):
                    for i in range(len(self.choices)):
                        yield Static(id=f"mn-{i}", classes="map-node")
            with Center():
                yield Static("[#9a958a]↑↓/①②③ 선택 · Enter 결정 · Esc 돌아가 구궁 정비[/]", id="map-foot")

    def on_mount(self):
        self._progress()
        self._paint()

    def _progress(self):
        s = self.session
        marks = []
        for i in range(len(s.map_steps)):
            if i < s.map_step:
                marks.append("[#5aa67c]●[/]")
            elif i == s.map_step:
                marks.append("[#c8a24a bold]◉[/]")
            else:
                marks.append("[#3a3a42]○[/]")
        z = {"bamboo_grove": "입문 죽림", "black_wind_forest": "흑풍림",
             "frost_spring_valley": "한천비곡"}.get(s.zone, s.zone)
        self.query_one("#map-progress", Static).update(
            f"[#e8e2d4]{z}[/]   " + "[#3a3a42]─[/]".join(marks) + f"   [#9a958a]관문 {s.map_step+1}/{len(s.map_steps)}[/]")

    def watch_sel(self):
        try:
            self._paint()
        except Exception:
            pass

    def _paint(self):
        for i, node in enumerate(self.choices):
            t = node["type"]
            col = NODE_COLOR.get(t, "#e8e2d4")
            row = self.query_one(f"#mn-{i}", Static)
            head = f"{NODE_GLYPH.get(t,'·')} {NODE_LABEL.get(t,t)}"
            if i == self.sel:
                row.update(f"[#1a1a1f on {col}] ▸ {head} [/]  [{col}]{NODE_DESC.get(t,'')}[/]")
            else:
                row.update(f"[{col}]   {head}[/]  [#6b665c]{NODE_DESC.get(t,'')}[/]")

    def action_move(self, d: int):
        self.sel = (self.sel + d) % len(self.choices)

    def action_pick(self, i: int):
        if i < len(self.choices):
            self.sel = i

    def action_confirm(self):
        self.dismiss(self.choices[self.sel])

    def action_cancel(self):
        self.dismiss(None)
