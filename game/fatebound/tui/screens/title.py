"""타이틀 — 천명반 모티프 + 메뉴(이어하기/새 회귀/도움말/종료). 키보드 우선(17 §13)."""
from __future__ import annotations
from textual.screen import Screen
from textual.containers import Vertical, Center, Middle
from textual.widgets import Static
from textual.reactive import reactive
from ... import persistence
from ...engine.session import BUILD_LABEL

ART = r"""[#c8a24a]
        ╔══════════════════════════════╗
        ║      天 命 回 歸  ·  Fatebound ║
        ║        ◍   구궁의 주사위        ║
        ╚══════════════════════════════╝[/]
   [#9a958a]회귀한 전대 고수, 천명반으로 강호를 다시 걷다.[/]"""

ZONE_KO = {"bamboo_grove": "입문 죽림", "black_wind_forest": "흑풍림",
           "frost_spring_valley": "한천비곡", "central_plains_gate": "중원 진입로"}


class TitleScreen(Screen):
    BINDINGS = [("up", "move(-1)"), ("down", "move(1)"), ("enter", "confirm"),
                ("space", "confirm"), ("question_mark", "help"), ("q", "app.quit")]
    sel: reactive[int] = reactive(0)

    def compose(self):
        self.has_save = persistence.has_save()
        self.items = []
        if self.has_save:
            self.items.append(("continue", "이어하기 · 회귀를 계속한다"))
        self.items.append(("new", "새 회귀 · 처음부터 시작"))
        self.items.append(("help", "도움말"))
        self.items.append(("quit", "종료"))
        with Middle():
            with Center():
                yield Static(ART, id="title-art")
            with Center():
                yield Static(id="title-save")
            with Center():
                with Vertical(id="title-menu"):
                    for i, (_id, _lbl) in enumerate(self.items):
                        yield Static(id=f"tm-{i}", classes="tm-row")
            with Center():
                yield Static("[#9a958a]↑↓ 선택 · Enter 결정 · ? 도움말[/]", id="title-foot")

    def on_mount(self):
        self._save_line()
        self._paint()

    def _save_line(self):
        line = ""
        if self.has_save:
            try:                                    # 손상/구버전 세이브에 타이틀이 죽지 않게(프로덕션 견고성)
                s = persistence.load()
                if s:
                    z = ZONE_KO.get(s.zone, s.zone) if isinstance(s.zone, str) else "?"
                    line = (f"[#9a958a]이어하기: 제{s.reincarnations+1}생 · {z} · "
                            f"{BUILD_LABEL.get(s.build, s.build)} 계열 · Lv{s.level}[/]")
            except Exception:
                line = ""                           # 읽기 실패 → 이어하기 줄만 생략(앱은 정상)
        self.query_one("#title-save", Static).update(line)

    def watch_sel(self):
        try:
            self._paint()
        except Exception:
            pass

    def _paint(self):
        for i, (_id, lbl) in enumerate(self.items):
            row = self.query_one(f"#tm-{i}", Static)
            if i == self.sel:
                row.update(f"[#1a1a1f on #c8a24a]  ▸ {lbl}  [/]")
            else:
                row.update(f"[#e8e2d4]    {lbl}[/]")

    def action_move(self, d: int):
        self.sel = (self.sel + d) % len(self.items)

    def action_help(self):
        from .help import HelpScreen
        self.app.push_screen(HelpScreen())

    def action_confirm(self):
        _id = self.items[self.sel][0]
        if _id == "quit":
            self.app.exit()
        elif _id == "help":
            self.action_help()
        elif _id == "continue":
            s = persistence.load()
            if s:
                from .game import GameScreen
                self.app.switch_screen(GameScreen(s))
        elif _id == "new":
            # 처음(세이브 없음)이면 콜드오픈부터, 이미 본 적 있으면 바로 기틀 선택
            if self.has_save:
                from .buildselect import BuildSelectScreen
                self.app.switch_screen(BuildSelectScreen())
            else:
                from .coldopen import ColdOpenScreen
                self.app.switch_screen(ColdOpenScreen())
