"""천명회귀 · Fatebound — Textual 앱 진입(17). 엔진=권위, UI=구독자(15)."""
from __future__ import annotations
from pathlib import Path
from textual.app import App
from .screens.title import TitleScreen


class FateboundApp(App):
    CSS_PATH = Path(__file__).parent / "app.tcss"
    TITLE = "천명회귀 · Fatebound"

    def on_mount(self):
        self.push_screen(TitleScreen())
