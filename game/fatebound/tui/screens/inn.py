"""객잔(店) — 정비·상점(17 §13.5). 미보유 무공 1자루 구매 또는 쉬어가기. dismiss(True)."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.containers import Vertical, Center, Middle
from textual.widgets import Static
from textual.reactive import reactive

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f"}


class InnScreen(ModalScreen):
    BINDINGS = [("up", "move(-1)"), ("down", "move(1)"),
                ("1", "pick(0)"), ("2", "pick(1)"),
                ("enter", "confirm"), ("space", "confirm"), ("escape", "leave")]
    sel: reactive[int] = reactive(0)

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.item, self.price = session.inn_offer()
        self.done = False

    def compose(self):
        with Middle():
            with Center():
                with Vertical(id="inn-box"):
                    yield Static(id="inn-title")
                    yield Static(id="inn-body")
                    yield Static(id="inn-opts")
                    yield Static(id="inn-foot")

    def on_mount(self):
        self.query_one("#inn-title", Static).update("[#5aa67c]⌂ 객잔(客棧)[/]")
        self.query_one("#inn-body", Static).update(
            "[#cfc8b8 italic]희미한 등불 아래 노파가 차를 내온다. \"무인이라면… 쓸 만한 물건도 있지.\"[/]")
        self._paint()

    @property
    def _options(self):
        opts = []
        if self.item:
            opts.append(("buy", f"무공 구매: {self.item['name_ko']} ({self.price}골드)"))
        opts.append(("leave", "쉬어가기 (다음 길로)"))
        return opts

    def watch_sel(self):
        try:
            if not self.done:
                self._paint()
        except Exception:
            pass

    def _paint(self):
        s = self.session
        lines = [f"[#9a958a]보유 골드: {s.gold}[/]", ""]
        for i, (kind, label) in enumerate(self._options):
            afford = not (kind == "buy" and s.gold < self.price)
            if not afford:
                lines.append(f"[#55504a]   {label}  (골드 부족)[/]")
            elif i == self.sel:
                lines.append(f"[#1a1a1f on #c8a24a] ▸ {label} [/]")
            else:
                lines.append(f"[#e8e2d4]   {label}[/]")
        if self.item:
            it = self.item
            lines += ["", f"[{RARITY.get(it['rarity'],'white')}]{it['name_ko']}[/] [#6b665c]· {it['rarity']} · {'·'.join(it.get('tags',[]))}[/]"]
        self.query_one("#inn-opts", Static).update("\n".join(lines))
        self.query_one("#inn-foot", Static).update("[#9a958a]↑↓ 선택 · Enter 결정 · Esc 나가기[/]")

    def action_move(self, d: int):
        self.sel = (self.sel + d) % len(self._options)

    def action_pick(self, i: int):
        if i < len(self._options):
            self.sel = i

    def action_confirm(self):
        kind = self._options[self.sel][0]
        if kind == "buy":
            if self.session.buy(self.item, self.price):
                self.done = True
                self.query_one("#inn-opts", Static).update(
                    f"[#c8a24a]{self.item['name_ko']} 을(를) 손에 넣었다. 구궁에 빈 칸이 있으면 자동 배치된다.[/]")
                self.query_one("#inn-foot", Static).update("[#9a958a]계속하려면 [Enter][/]")
                return
        self.dismiss(True)

    def action_leave(self):
        self.dismiss(True)
