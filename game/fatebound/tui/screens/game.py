"""메인 게임 화면 — 구궁·전투로그·상태 3분할 + 이벤트 스트림 애니메이션 재생(D2 관전 + 비장)."""
from __future__ import annotations
import asyncio
from textual import work
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Static, RichLog
from ..widgets.gugung import GugungWidget
from ..widgets.statuspanel import StatusPanel
from ...engine import render_text, balance
from ... import persistence

# 이벤트별 재생 딜레이(초) — t-beat 기반(17 §2.4). 배속은 self.speed로 나눔.
DELAY = {"round_start": 0.18, "dice": 0.16, "damage": 0.14, "tick": 0.12, "bijang": 0.30,
         "enemy_action": 0.16, "counter": 0.10, "status": 0.08, "summon_attack": 0.10,
         "heal": 0.10, "shield": 0.10, "focus": 0.06, "info": 0.10, "end": 0.2}


class GameScreen(Screen):
    BINDINGS = [
        ("up", "cur(-1,0)"), ("down", "cur(1,0)"), ("left", "cur(0,-1)"), ("right", "cur(0,1)"),
        ("enter", "grab"), ("space", "fight(False)"), ("b", "fight(True)"),
        ("f", "speed"), ("q", "app.quit"),
    ]

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.speed = 1.0
        self.busy = False

    def compose(self):
        yield Static(id="topbar")
        with Horizontal(id="main"):
            with Container(id="gugung-pane"):
                yield Static("구궁(九宮)", classes="label")
                yield GugungWidget(self.session, id="gugung")
            with Container(id="log-pane"):
                yield RichLog(id="log", wrap=True, markup=True, auto_scroll=True)
            yield StatusPanel(self.session, id="status-pane")
        yield Static(id="actionbar")

    def on_mount(self):
        self._topbar()
        self.query_one("#actionbar", Static).update(
            "[#c8a24a]방향키[/] 이동 · [#c8a24a]Enter[/] 집기/놓기 · [#c8a24a]Space[/] 전투 · [#c8a24a]B[/] 보스 · [#c8a24a]F[/] 배속 · [#c8a24a]Q[/] 종료")
        self._sync_detail()
        self.query_one("#log", RichLog).write("[#9a958a]강호에 들어선다. 구궁을 살피고, 전투를 시작하라.[/]")

    def _topbar(self):
        s = self.session
        z = {"bamboo_grove": "입문 죽림", "black_wind_forest": "흑풍림", "frost_spring_valley": "한천비곡"}.get(s.zone, s.zone)
        self.query_one("#topbar", Static).update(
            f"강호유력 · [#e8e2d4]{z}[/] · 회귀 #{s.reincarnations} · {balance.BUILD_LABEL.get(s.build, s.build)} 계열 · 배속 ×{self.speed:g}")

    def _sync_detail(self):
        g = self.query_one("#gugung", GugungWidget)
        p = self.query_one("#status-pane", StatusPanel)
        p.detail_item = g.current_item()
        p.faces = self.session.loadout().faces
        p.refresh()

    def action_cur(self, dr: int, dc: int):
        if self.busy:
            return
        self.query_one("#gugung", GugungWidget).move_cursor(dr, dc)
        self._sync_detail()

    def action_grab(self):
        if self.busy:
            return
        self.query_one("#gugung", GugungWidget).toggle_grab()
        self._sync_detail()
        persistence.save(self.session)          # 배치 변경 자동저장

    def action_speed(self):
        self.speed = {1.0: 2.0, 2.0: 4.0, 4.0: 1.0}[self.speed]
        self._topbar()

    def action_fight(self, boss: bool):
        if self.busy:
            return
        self._play(boss)

    @work(exclusive=True)
    async def _play(self, boss: bool):
        self.busy = True
        log = self.query_one("#log", RichLog)
        panel = self.query_one("#status-pane", StatusPanel)
        res, enemy = self.session.fight(boss)
        log.clear()
        p_hp = p_max = e_hp = e_max = 0
        e_name = enemy.get("name_ko", "적")
        pname = self.session.name
        bj = 0
        for e in res.events:
            d = e.data
            if e.kind == "battle_start":
                e_max = e_hp = d["enemy_hp"]
                pv = self.session.player_preview()
                p_hp, p_max = pv.max_hp, pv.max_hp
                panel.bijang_max = balance.BIJANG_CHARGE
            # HP 라이브 추적
            if "tgt_hp" in d:
                if d.get("tgt") == e_name:
                    e_hp = d["tgt_hp"]
                elif d.get("tgt") == pname:
                    p_hp = d["tgt_hp"]
            if e.kind == "heal" and d.get("tgt") == pname:
                p_hp = d.get("tgt_hp", p_hp)
            if e.kind == "bijang":
                bj = 0
            if e.kind == "dice":
                bj = min(panel.bijang_max, bj + 1)
            line = render_text.line(e)
            if line:
                styled = self._style(e, line)
                log.write(styled)
            panel.set_combat(p_hp, p_max, e_name, e_hp, e_max, bj)
            await asyncio.sleep(DELAY.get(e.kind, 0.1) / self.speed)
        # 결과 처리
        out = self.session.apply_result(res, enemy, boss)
        self._after(res, out, log)
        persistence.save(self.session)          # 자동저장(전투 결과·회귀 반영)
        self.busy = False
        self._topbar(); self._sync_detail()

    def _style(self, e, line: str) -> str:
        if e.kind == "damage" and e.data.get("crit"):
            return f"[#e0b341 bold]{line}[/]"
        if e.kind == "bijang":
            return f"[#e0b341 bold]{line}[/]"
        if e.kind == "tick":
            return f"[#6fae5a]{line}[/]"
        if e.kind == "counter":
            return f"[#7fa8d4]{line}[/]"
        if e.kind == "end":
            oc = e.data["outcome"]
            col = {"win": "#5aa67c", "loss": "#d4582f", "timeout": "#9a958a"}[oc]
            return f"[{col} bold]{line}[/]"
        if e.kind == "enemy_action":
            return f"[#d4582f]{line}[/]"
        return line

    def _after(self, res, out, log: RichLog):
        if res.outcome == "win":
            g = out.get("gains", {})
            log.write(f"[#5aa67c]전리품: 경험치 +{g.get('xp',0)} · 골드 +{g.get('gold',0)} · 파편 +{g.get('shards',0)}[/]")
            for lv in out.get("leveled", []):
                log.write(f"[#c8a24a bold]경지 상승! Lv{lv}[/]")
            if out.get("drop"):
                log.write(f"[#c8a24a]전리품 무공: {out['drop']['name_ko']} 획득![/]")
        elif out.get("reincarnated"):
            log.write(f"[#d4582f bold]━━ 전사 — 회귀(回歸) ━━[/]")
            from .reincarnate import ReincarnateScreen
            self.app.push_screen(ReincarnateScreen(self.session, out.get("gain", 0), "전사"))
