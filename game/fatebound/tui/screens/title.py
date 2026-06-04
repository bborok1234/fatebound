"""타이틀 화면 — 천명반 모티프 ASCII + 빌드 선택 → 새 회귀 시작."""
from __future__ import annotations
from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button
from ...engine.session import GameSession
from ... import persistence

ART = r"""
        ╔═══════════════════════════╗
        ║   템 빨 · 天 命 回 歸       ║
        ║      ◍  구궁의 주사위       ║
        ╚═══════════════════════════╝
   회귀한 전대 고수, 천명반으로 강호를 다시 걷다.
"""

BUILDS = [("poison", "독(毒)"), ("crit", "치명(致命)"), ("guard", "방어·반격"), ("dice", "주사위 조작")]


class TitleScreen(Screen):
    def compose(self):
        yield Static(ART, id="title-art")
        with Vertical(id="title-menu"):
            if persistence.has_save():
                yield Button("이어하기 (회귀 계속)", id="continue", variant="success")
            yield Static("무공 기틀을 고르라 — 새 회귀", classes="label")
            with Horizontal():
                for key, label in BUILDS:
                    yield Button(label, id=f"build-{key}", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        from .game import GameScreen
        if event.button.id == "continue":
            session = persistence.load()
            if session:
                self.app.push_screen(GameScreen(session))
                return
        key = event.button.id.replace("build-", "")
        session = GameSession.new_game("천기노조", key)
        persistence.save(session)
        self.app.push_screen(GameScreen(session))
