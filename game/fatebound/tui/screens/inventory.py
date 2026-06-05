"""보관함(보유·미배치 무공) — 골라서 구궁 커서 칸에 투입. dismiss(placed_bool)."""
from __future__ import annotations
from textual.screen import ModalScreen
from textual.containers import Vertical, Center, Middle
from textual.widgets import Static
from textual.reactive import reactive

RARITY = {"common": "grey70", "rare": "#4a90a4", "epic": "#c8a24a", "legendary": "#d4582f"}


class InventoryScreen(ModalScreen):
    BINDINGS = [("up", "move(-1)"), ("down", "move(1)"),
                ("enter", "confirm"), ("space", "confirm"), ("escape", "cancel"), ("i", "cancel")]
    sel: reactive[int] = reactive(0)

    def __init__(self, session, target_idx: int):
        super().__init__()
        self.session = session
        self.target_idx = target_idx
        self.items = session.reserve()

    def compose(self):
        with Middle():
            with Center():
                with Vertical(id="inv-box"):
                    yield Static(id="inv-title")
                    yield Static(id="inv-list")
                    yield Static(id="inv-foot")

    def on_mount(self):
        self.query_one("#inv-title", Static).update("[#c8a24a]보관함 · 구궁에 놓을 무공[/]")
        self._paint()

    def watch_sel(self):
        try:
            self._paint()
        except Exception:
            pass

    def _paint(self):
        if not self.items:
            self.query_one("#inv-list", Static).update("[#9a958a]보관 중인 무공이 없다. (전투·기연·객잔으로 모은다)[/]")
            self.query_one("#inv-foot", Static).update("[#9a958a]닫기: Esc[/]")
            return
        lines = []
        for i, it in enumerate(self.items):
            r = RARITY.get(it["rarity"], "white")
            tags = "·".join(it.get("tags", []))
            if i == self.sel:
                lines.append(f"[#1a1a1f on #c8a24a] ▸ {it['name_ko']} [/] [#9a958a]{it['rarity']}·{tags}[/]")
            else:
                lines.append(f"[{r}]   {it['name_ko']}[/] [#6b665c]{it['rarity']}·{tags}[/]")
        self.query_one("#inv-list", Static).update("\n".join(lines))
        self.query_one("#inv-foot", Static).update(
            f"[#9a958a]↑↓ 선택 · Enter 놓기(커서 칸 {self.target_idx//3+1}행 {self.target_idx%3+1}열) · Esc 취소[/]")

    def action_move(self, d: int):
        if self.items:
            self.sel = (self.sel + d) % len(self.items)

    def action_confirm(self):
        if not self.items:
            self.dismiss(False)
            return
        it = self.items[self.sel]
        self.session.place_from_reserve(it["item_id"], self.target_idx)
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)
