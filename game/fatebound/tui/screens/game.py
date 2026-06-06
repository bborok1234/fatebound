"""허브 게임 화면 — 구궁 정비 + 강호 지도 여정(17 §13.5) + 이벤트 스트림 전투(D2).
Space로 갈림길(지도)을 열어 전투/사건/객잔/기연/보스를 고르고, 결과를 안고 허브로 돌아온다.
"""
from __future__ import annotations
import asyncio
import os
from textual import work
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Static, RichLog
from ..widgets.gugung import GugungWidget
from ..widgets.statuspanel import StatusPanel
from ..widgets.dice3d import Dice3D
from ...engine.combat_m1 import LINES, cell_eff, OUTPUT_C
from ...engine import render_text, balance
from ... import persistence

DELAY = {"round_start": 0.18, "dice": 0.16, "damage": 0.14, "tick": 0.12, "bijang": 0.30,
         "enemy_action": 0.16, "counter": 0.10, "status": 0.08, "summon_attack": 0.10,
         "heal": 0.10, "shield": 0.10, "focus": 0.06, "info": 0.10, "end": 0.2,
         "m1_line": 0.0, "m1_fire": 0.05}      # m1_line은 주사위 굴림이 페이싱

# 디제틱 가이드(첫 회귀에만, 17 §13.2)
COACH = [
    "여기가 [#c8a24a]구궁(九宮)[/]. [#c8a24a]방향키[/]로 놓인 무공을 하나씩 살펴보라.",
    "[#5aa67c]녹색[/]으로 이어진 둘은 [#5aa67c]상생(相生)[/]한다. [#c8a24a]Enter[/]로 집어 옮겨 붙여보라.",
    "준비됐으면 [#c8a24a]Space[/]로 [#c8a24a]강호 지도[/]를 열어 첫 길을 고르라.",
    "[#e0b341]비장(秘藏)의 수[/]는 전투 중 차올라 [#e0b341]저절로[/] 터지는 필살 한 수. 익혔다. ([#9a958a]Esc로 닫기[/])",
]
ZONE_KO = {"bamboo_grove": "입문 죽림", "black_wind_forest": "흑풍림",
           "frost_spring_valley": "한천비곡", "central_plains_gate": "중원 진입로"}


class GameScreen(Screen):
    BINDINGS = [
        ("up", "cur(-1,0)"), ("down", "cur(1,0)"), ("left", "cur(0,-1)"), ("right", "cur(0,1)"),
        ("enter", "grab"), ("space", "journey"), ("m", "journey"), ("i", "inventory"),
        ("f", "speed"), ("question_mark", "help"), ("escape", "dismiss_coach"), ("q", "app.quit"),
    ]

    def __init__(self, session, first_run: bool = False):
        super().__init__()
        self.session = session
        # 축소 모션(접근성, 17 §8): 환경변수 설정 시 전투 즉시 재생
        self.reduced_motion = bool(os.environ.get("FATEBOUND_REDUCED_MOTION"))
        self.speed = 64.0 if self.reduced_motion else 1.0
        self.busy = False
        self.coach = 0 if (first_run and session.reincarnations == 0 and not session.tutorial_done) else None

    def compose(self):
        yield Static(id="topbar")
        yield Static(id="coach", classes="hidden")
        with Horizontal(id="main"):
            with Container(id="dice-pane"):       # 좌: 天命卦 3D 주사위(핵심·랜덤성의 축)
                yield Static("[#c8a24a]天命卦 · 천명괘[/]", classes="label")
                yield Dice3D(skin=getattr(self.session, "die_skin", "baekok"), id="dice")
            with Container(id="gugung-pane"):      # 중앙: 구궁(배치=결정 공간)
                yield Static("[#9a958a]구궁(九宮) · 무공 배치[/]", classes="label")
                yield GugungWidget(self.session, id="gugung")
            yield StatusPanel(self.session, id="status-pane")   # 우: 敵/보스 + 내 상태
        with Container(id="log-pane"):             # 하단 전폭: 천명록
            yield Static("[#9a958a]천명록(天命錄)[/]", classes="label")
            yield RichLog(id="log", wrap=True, markup=True, auto_scroll=True)
        yield Static(id="actionbar")

    def on_mount(self):
        self.session.ensure_map()
        self._topbar()
        self._actionbar()
        self._sync_detail()
        self._coach_refresh()
        log = self.query_one("#log", RichLog)
        log.can_focus = False
        self.set_focus(None)
        z = ZONE_KO.get(self.session.zone, self.session.zone)
        log.write(f"[#9a958a]── {z} ──[/]")
        log.write("[#9a958a]구궁을 정비하고, [/][#c8a24a]Space[/][#9a958a]로 강호에 나서라.  ([/][#c8a24a]?[/][#9a958a] 도움말)[/]")

    # ── HUD ──
    def _topbar(self):
        s = self.session
        z = ZONE_KO.get(s.zone, s.zone)
        gate = f"관문 {min(s.map_step+1, len(s.map_steps))}/{len(s.map_steps)}" if s.map_steps else ""
        sp = "즉시" if self.speed >= 64 else f"×{self.speed:g}"
        self.query_one("#topbar", Static).update(
            f"강호유력 · [#e8e2d4]{z}[/] · {gate} · 회귀 #{s.reincarnations} · "
            f"{balance.BUILD_LABEL.get(s.build, s.build)} 계열 · 배속 {sp}")

    def _actionbar(self, combat: bool = False):
        if combat:
            txt = "[#c8a24a]F[/] 배속  ·  전투가 끝나면 다시 조작할 수 있다"
        else:
            txt = ("[#c8a24a]방향키[/] 이동 · [#c8a24a]Enter[/] 집기/놓기 · [#c8a24a]Space[/] 강호로(갈림길) · "
                   "[#c8a24a]I[/] 보관함 · [#c8a24a]F[/] 배속 · [#c8a24a]?[/] 도움말 · [#c8a24a]Q[/] 종료")
        self.query_one("#actionbar", Static).update(txt)

    def _sync_detail(self):
        g = self.query_one("#gugung", GugungWidget)
        p = self.query_one("#status-pane", StatusPanel)
        p.detail_item = g.current_item()
        p.faces = self.session.loadout().faces
        # M1 출력 텔레그래프 — 배치가 출력을 바꾼다. 잡고 다른 칸에 커서 두면 commit 전 예상치.
        if self.session.use_m1():
            cells = self.session.bag.cells
            scale = self.session.player_preview().atk * OUTPUT_C
            p.output = sum(cell_eff(cells, i, scale) for i in range(9))
            if g.grabbed is not None and g.grabbed != g.cursor:
                clone = list(cells)
                clone[g.grabbed], clone[g.cursor] = clone[g.cursor], clone[g.grabbed]
                p.preview_output = sum(cell_eff(clone, i, scale) for i in range(9))
            else:
                p.preview_output = None
        else:
            p.output = p.preview_output = None
        p.refresh()

    def _refresh_hub(self):
        self.query_one("#gugung", GugungWidget).refresh()
        self._sync_detail()
        self._topbar()

    # ── 코치 ──
    def _coach_refresh(self):
        banner = self.query_one("#coach", Static)
        if self.coach is None or self.coach >= len(COACH):
            banner.add_class("hidden"); banner.update("")
        else:
            banner.remove_class("hidden")
            banner.update(f"[#c8a24a]☞[/] {COACH[self.coach]}")

    def _coach_advance(self, frm: int):
        if self.coach == frm:
            self.coach = frm + 1
            if self.coach >= len(COACH):
                self.coach = None
            self._coach_refresh()

    def action_dismiss_coach(self):
        if self.coach is not None:
            self.coach = None
            self._finish_tutorial()
            self._coach_refresh()

    def _finish_tutorial(self):
        if not self.session.tutorial_done:
            self.session.tutorial_done = True
            persistence.save(self.session)

    def action_help(self):
        from .help import HelpScreen
        self.app.push_screen(HelpScreen())

    # ── 구궁 조작 ──
    def action_cur(self, dr: int, dc: int):
        if self.busy:
            return
        self.query_one("#gugung", GugungWidget).move_cursor(dr, dc)
        self._sync_detail()
        self._coach_advance(0)

    def action_grab(self):
        if self.busy:
            return
        g = self.query_one("#gugung", GugungWidget)
        was = g.grabbed is not None
        g.toggle_grab()
        self._sync_detail()
        persistence.save(self.session)
        if was and g.grabbed is None:
            self._coach_advance(1)

    def action_inventory(self):
        if self.busy:
            return
        from .inventory import InventoryScreen
        idx = self.query_one("#gugung", GugungWidget).cursor
        self.app.push_screen(InventoryScreen(self.session, idx), self._after_inventory)

    def _after_inventory(self, placed):
        if placed:
            persistence.save(self.session)
        self._refresh_hub()

    def action_speed(self):
        self.speed = {1.0: 2.0, 2.0: 4.0, 4.0: 1.0}.get(self.speed, 1.0)  # 즉시(64)에서 누르면 ×1로
        self._topbar()

    # ── 여정(강호 지도) ──
    def action_journey(self):
        if self.busy:
            return
        from .map import MapScreen
        self.app.push_screen(MapScreen(self.session), self._on_node)

    def _on_node(self, node):
        if not node:
            return
        t = node["type"]
        log = self.query_one("#log", RichLog)
        if t in ("battle", "elite", "boss"):
            if self.coach == 2:
                self.coach = 3
            self._play(boss=(t == "boss"), elite=(t == "elite"))
        elif t == "event":
            ev = self.session.pick_event()
            if ev:
                from .event import EventScreen
                self.app.push_screen(EventScreen(self.session, ev), self._after_noncombat)
            else:
                self._after_noncombat(True)
        elif t == "inn":
            from .inn import InnScreen
            self.app.push_screen(InnScreen(self.session), self._after_noncombat)
        elif t == "fortune":
            it = self.session.fortune_grant()
            if it:
                log.write(f"[#e0b341]기연(緣). 무공 '{it['name_ko']}'을(를) 얻었다![/]")
            else:
                log.write("[#e0b341]기연(緣). 더 얻을 무공이 없어 정수(精) +5.[/]")
            self._after_noncombat(True)

    def _after_noncombat(self, _=None):
        self.session.advance_node()
        persistence.save(self.session)
        self._refresh_hub()
        self.query_one("#log", RichLog).write("[#9a958a]다음 갈림길로 가려면 Space[/]")

    # ── 전투 ──
    @work(exclusive=True)
    async def _play(self, boss: bool, elite: bool = False):
        self.busy = True
        self._actionbar(combat=True)
        log = self.query_one("#log", RichLog)
        panel = self.query_one("#status-pane", StatusPanel)
        dice = self.query_one("#dice", Dice3D)
        gug = self.query_one("#gugung", GugungWidget)
        m1 = self.session.use_m1()
        res, enemy = (self.session.fight_m1 if m1 else self.session.fight)(boss, elite)
        log.clear()
        if elite:
            log.write("[#d4582f]── 정예와의 일전 ──[/]")
        # 적 size-up — 천기노조의 한 줄(gist=정체, flavor=품평)
        if enemy.get("gist_ko"):
            log.write(f"[#d4582f]{enemy.get('name_ko','적')}[/] · [#9a958a]{enemy['gist_ko']}[/]")
        if enemy.get("flavor_ko"):
            log.write(f"[#6b665c italic]\"{enemy['flavor_ko']}\"[/]")
        p_hp = p_max = e_hp = e_max = 0
        e_name = enemy.get("name_ko", "적")
        pname = self.session.name
        bj = 0
        cur_face = ""
        estatus: dict = {}
        rollc = 0
        for e in res.events:
            d = e.data
            if e.kind == "battle_start":
                e_max = e_hp = d["enemy_hp"]
                pv = self.session.player_preview()
                p_hp, p_max = pv.max_hp, pv.max_hp
                panel.bijang_max = balance.BIJANG_CHARGE
            if "tgt_hp" in d:
                if d.get("tgt") == e_name:
                    e_hp = d["tgt_hp"]
                elif d.get("tgt") == pname:
                    p_hp = d["tgt_hp"]
            if e.kind == "heal" and d.get("tgt") == pname:
                p_hp = d.get("tgt_hp", p_hp)
            if e.kind == "bijang":
                bj = 0
            if e.kind == "round_start":
                gug.douse()                               # 지난 합 점화 해제
            if e.kind == "dice":                          # M0: 천명괘(코스메틱 굴림)
                bj = min(panel.bijang_max, bj + 1)
                cur_face = d.get("face", cur_face)
                await self._do_roll(dice, rollc % 6); rollc += 1
            if e.kind == "m1_line":                       # M1: 줄 강조 → 굴림 + 구궁 점화
                await self._do_roll(dice, d["line"])
                gug.ignite(LINES[d["line"]])
            if e.kind == "status" and d.get("tgt") == e_name:
                estatus[d["status"]] = d.get("stacks", estatus.get(d["status"], 0) + 1)
            ln = render_text.line(e)
            if ln and e.kind != "battle_start":          # 적 소개는 위에서 이미 출력함
                if e.kind == "round_start" and d.get("n", 1) > 1:
                    log.write("")                          # 합 사이 한 줄 띄워 가독성
                log.write(self._style(e, ln))
            panel.set_combat(p_hp, p_max, e_name, e_hp, e_max, bj, cur_face=cur_face, statuses=dict(estatus))
            # hitstop — 치명·비장은 한 박자 더 머문다(임팩트, 17 §2.4)
            hit = 0.12 if ((e.kind == "damage" and d.get("crit")) or e.kind == "bijang") else 0.0
            if e.kind not in ("dice", "m1_line"):         # 주사위 굴림이 자체 페이싱
                await asyncio.sleep((DELAY.get(e.kind, 0.1) + hit) / self.speed)
        gug.douse()
        out = self.session.apply_result(res, enemy, boss, elite)
        self._after(res, out, log)
        persistence.save(self.session)
        # 노드 진행: 회귀/보스돌파는 지도가 이미 리셋·재생성됨 → 일반/정예 승리만 한 칸 전진
        if not out.get("reincarnated") and not out.get("boss_cleared"):
            self.session.advance_node()
            persistence.save(self.session)
        self.busy = False
        self._refresh_hub(); self._actionbar()
        if self.coach == 3:
            self._coach_refresh(); self._finish_tutorial()

    async def _do_roll(self, dice, line: int):
        """천명괘 3D 주사위를 결과 줄(0~5)로 굴린다. 고배속/축소모션은 즉시 착지."""
        instant = self.speed >= 2.0
        dice.roll(line, instant=instant)
        if not instant:
            await asyncio.sleep(Dice3D.ROLL_SECONDS)       # 위젯이 자체 타이머로 굴러 착지

    def _style(self, e, line: str) -> str:
        k, d = e.kind, e.data
        if k == "round_start":
            return f"[#55504a]{line}[/]"                  # 합 구분선 — 흐리게
        if k == "dice":
            return f"[#7fa8d4]{line}[/]"
        if k == "damage":
            if d.get("crit"):
                return f"[#e0b341 bold]{line}[/]"         # 치명 — 사이다 금빛
            return f"[#e8e2d4]{line}[/]" if d.get("by_player") else f"[#c08a7a]{line}[/]"  # 내 공격 밝게 / 적 공격 흐린 적
        if k == "bijang":
            return f"[#e0b341 bold]{line}[/]"
        if k == "tick":
            return f"[#6fae5a]{line}[/]"
        if k == "counter":
            return f"[#7fa8d4]{line}[/]"
        if k == "status":
            return f"[#9a958a]{line}[/]"
        if k == "info":
            return f"[#c8a24a]{line}[/]"
        if k == "enemy_action":
            return f"[#d4582f]{line}[/]"
        if k == "end":
            col = {"win": "#5aa67c", "loss": "#d4582f", "timeout": "#9a958a"}[d["outcome"]]
            return f"[{col} bold]{line}[/]"
        return line

    def _after(self, res, out, log: RichLog):
        if res.outcome == "win":
            g = out.get("gains", {})
            log.write(f"[#5aa67c]전리품: 경험치 +{g.get('xp',0)} · 골드 +{g.get('gold',0)} · 파편 +{g.get('shards',0)}[/]")
            for lv in out.get("leveled", []):
                log.write(f"[#c8a24a bold]경지 상승! Lv{lv}[/]")
            if out.get("drop"):
                log.write(f"[#c8a24a]전리품 무공: {out['drop']['name_ko']} 획득![/]")
            if out.get("boss_cleared"):
                za = out.get("zone_advanced")
                if za:
                    log.write(f"[#c8a24a bold]━━ 관문 돌파! 새 강호 '{ZONE_KO.get(za, za)}'(이)가 열렸다 ━━[/]")
                else:
                    log.write("[#c8a24a bold]━━ 이 강호를 평정했다. 더 깊은 곳으로… ━━[/]")
        elif out.get("reincarnated"):
            log.write("[#d4582f bold]━━ 전사, 그리고 회귀(回歸) ━━[/]")
            from .reincarnate import ReincarnateScreen
            self.app.push_screen(ReincarnateScreen(self.session, out.get("gain", 0), "전사"))
