"""스테이지 — 전투 관전 (5권 05 §1.5 확정: 고정 HUD + 스크롤 로그 + 인라인 컷인 + 요약 카드 박제).
R8 반영: 플레이어 자원열(중독 N/6 → 만독발현)·速 선공 표식·적 속성 태그.
템포 정본(01 §1): 합당 0.22s · 타자 효과 금지 · 정적 0.3s."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import RichLog, Static

from .. import theme as T
from ..data import slice_pack as P
from ..engine import combat, render


def _c(rgb):
    return T.hexc(rgb)


def ansi(s: str) -> Text:
    return Text.from_ansi(s)


class StageScreen(Screen):
    BINDINGS = [("space", "speed", "배속"), ("s", "settle", "즉시 정산"), ("enter", "done", "계속")]

    def __init__(self, enemy_key: str, seed: int = 7):
        super().__init__()
        self.enemy_key = enemy_key
        self.enemy = P.ENEMIES[enemy_key]
        self.gen = combat.run_battle(enemy_key, seed)
        self.speed = 1
        self.finished = False
        self.state = dict(enemy_hp=self.enemy["hp"], poison=0.0, charge=0,
                          player_hp=P.PLAYER["hp"])

    # ── 레이아웃: 고정 HUD(Static) + 로그(RichLog) + 화자/힌트 ──
    def compose(self) -> ComposeResult:
        yield Static(id="hud")
        yield RichLog(id="log", wrap=False, markup=False)
        yield Static(id="voice")
        yield Static(id="hints")

    def on_mount(self) -> None:
        self.query_one("#log", RichLog).styles.height = "1fr"
        self.draw_hud()
        v = Text()
        v.append("  천기노조", style=f"bold {_c(T.GOLD)}")
        v.append(f" — {self.enemy['intro']}", style=_c(T.DIM))
        self.query_one("#voice", Static).update(v)
        h = Text("  [Space]배속 ×1·×2·×4   [S]즉시 정산   (관전 — 다음에 시작하는 판부터)", style=_c(T.DIM))
        self.query_one("#hints", Static).update(h)
        self.timer = self.set_interval(0.22, self.tick)

    # ── 고정 HUD (05 §1.5 와이어 그대로) ──
    def draw_hud(self) -> None:
        st = self.state
        spr = render.sprite(self.enemy_key, poison=int(st["poison"]))
        lines = []
        head = (render.fg(T.INK) + f" ◆ {P.HUNT_TITLE}" + render.R
                + render.fg(T.DIM) + "   (관전 중 — 천명반이 읽는 흐름)" + render.R)
        lines.append(head)
        info_x = 22
        e = self.enemy
        first = "무명" if P.PLAYER["spd"] >= e["spd"] else self.enemy_key
        rows = [
            "",
            render.tinted_name(self.enemy_key, st["poison"]) + render.fg(T.DIM)
            + f"  · {e['kind']} · {e['attr']}  速{e['spd']}" + render.R,
            render.fg(T.DIM) + "체력 " + render.R + render.hp_bar(st["enemy_hp"], e["hp"])
            + f" {st['enemy_hp']:>3}",
            render.fg(T.DIM) + "중독 " + render.dots(st["poison"]) + render.R,
            "",
        ]
        for i in range(8):
            left = spr[i] if i < len(spr) else ""
            pad = " " * max(0, info_x - 18)
            right = rows[i] if i < len(rows) else ""
            lines.append("  " + left + pad + right)
        # 주인공 행 + ★자원열(R8) + 절기 게이지
        poi = int(st["poison"])
        nxt = " → 만독발현 다음 합" if poi >= 6 else ""
        res_col = T.AMBER if poi >= 5 else T.DIM
        lines.append(
            render.fg(T.GOLD) + " 무명" + render.R + render.fg(T.DIM)
            + f" (독계·삼류)  速{P.PLAYER['spd']}"
            + (" 선공" if first == "무명" else "") + "  체력 " + render.R
            + render.hp_bar(st["player_hp"], P.PLAYER["hp"], 12, (90, 140, 90))
            + f" {st['player_hp']:>3}")
        lines.append(
            render.fg(res_col) + " 중독 " + render.R + render.dots(st["poison"])
            + render.fg(res_col) + f" {poi}/6{nxt}" + render.R
            + render.fg(T.DIM) + "   절기 " + render.R
            + render.fg(T.AMBER if st["charge"] >= 5 else T.DIM)
            + render.gauge(st["charge"]) + render.R
            + (render.fg(T.AMBER) + " 充" + render.R if st["charge"] >= 6 else ""))
        lines.append(
            render.fg(T.DIM) + " 사슬 " + render.R + render.fg(T.INK)
            + "[독침]═[독무]═[독증폭]═" + render.fg((180, 150, 220)) + "[만독발현]"
            + render.R + render.fg(T.DIM) + f"   심법 [{P.SIMBEOP['name']}]" + render.R)
        lines.append(render.fg(T.DIM) + " " + "─" * 64 + render.R)
        self.query_one("#hud", Static).update(ansi("\n".join(lines)))

    # ── 재생 ──
    def tick(self) -> None:
        if self.finished:
            return
        for _ in range(self.speed):
            try:
                ev = next(self.gen)
            except StopIteration:
                return
            self.play(ev)
            if ev.result:
                self.finish(ev)
                return

    def play(self, ev: combat.RoundEvent) -> None:
        log = self.query_one("#log", RichLog)
        d = render.fg(T.DIM)
        for a in ev.actions:
            if a.kind == "smyeong":
                self.cutin(log, ev)
            elif a.kind == "burst":
                log.write(ansi(f"{d}  [{ev.round}합]{render.R} "
                               + render.fg((150, 230, 150)) + f"✦ {a.move} · {a.chosik}"
                               + render.R + "  " + render.fg((255, 235, 190)) + a.effect + render.R))
            elif a.kind == "enemy":
                log.write(ansi(f"{d}  [{ev.round}합]{render.R} {d}{a.move} 반격 {a.effect}{render.R}"))
            elif a.kind in ("gen",):
                log.write(ansi(f"{d}  [{ev.round}합]{render.R} "
                               + render.fg(T.INK) + f"{a.move} · {a.chosik}" + render.R
                               + "  " + render.fg(T.POISON) + a.effect + render.R))
        self.state.update(enemy_hp=ev.enemy_hp, poison=ev.poison,
                          charge=ev.charge, player_hp=ev.player_hp)
        self.draw_hud()

    def cutin(self, log: RichLog, ev: combat.RoundEvent) -> None:
        """인라인 컷인 약식(M0) — 대형 박스+계열색. 래스터 밴드는 M1에서 스파이크 이식."""
        c = render.fg(T.AMBER)
        name = " ".join(P.SMYEONG["name"])
        bar = "─" * (len(name) + 10)
        log.write(ansi(""))
        log.write(ansi(f"  {c}┌{bar}┐{render.R}"))
        log.write(ansi(f"  {c}│  ✦ {name} ✦  │{render.R}"))
        log.write(ansi(f"  {c}└{bar}┘{render.R}"))
        log.write(ansi("  " + render.fg((255, 240, 200)) + f"☠ {ev.smyeong_dmg:.0f}" + render.R
                       + render.fg(T.DIM) + " — 사혈을 짚고, 쌓인 독을 한 번에." + render.R))

    def finish(self, ev: combat.RoundEvent) -> None:
        self.finished = True
        self.timer.stop()
        log = self.query_one("#log", RichLog)
        d = render.fg(T.DIM)
        bd = getattr(ev, "breakdown", {"slots": {}, "smyeong": 0, "dot": 0, "taken": 0})
        total = sum(bd["slots"].values()) + bd["smyeong"] + bd["dot"]
        log.write(ansi(f"{d}  {self.enemy_key} — {self.enemy['death']}{render.R}"))
        log.write(ansi(""))
        # 종료 요약 카드 (박제 — fight 분해 1:1 매핑)
        slot_s = " · ".join(f"{k} {v:.0f}" for k, v in bd["slots"].items())
        card = [
            f"{d} ┌─ 전투 결과 ─ {self.enemy_key} ─────────────────────────┐{render.R}",
            f"{d} │ {render.fg(T.INK)}승리 · {ev.round}합{render.R}{d}"
            f"  피해 {total:.0f} ({slot_s} · 절기 {bd['smyeong']:.0f} · 틱 {bd['dot']:.0f}){d} │{render.R}",
            f"{d} │ {render.fg(T.GOLD)}천기노조{render.R}{d} — {P.VOICE['victory']} │{render.R}",
            f"{d} └──────────────────────────────────────────────────┘{render.R}",
        ]
        for ln in card:
            log.write(ansi(ln))
        self.app.summary = dict(enemy=self.enemy_key, rounds=ev.round, total=total)  # type: ignore[attr-defined]
        h = Text("  [Enter] 전선 지도로 — 강호가 열린다", style=_c(T.AMBER))
        self.query_one("#hints", Static).update(h)

    def action_speed(self) -> None:
        self.speed = {1: 2, 2: 4, 4: 1}[self.speed]
        h = Text(f"  배속 ×{self.speed}   [S]즉시 정산", style=_c(T.DIM))
        if not self.finished:
            self.query_one("#hints", Static).update(h)

    def action_settle(self) -> None:
        """즉시 정산 — 남은 합을 한 번에(관전 다이얼, 02 §2)."""
        if self.finished:
            return
        for ev in self.gen:
            self.play(ev)
            if ev.result:
                self.finish(ev)
                return

    def action_done(self) -> None:
        if self.finished:
            from .map import MapScreen
            self.app.switch_screen(MapScreen())
