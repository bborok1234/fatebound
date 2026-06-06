"""허브 게임 화면 — 구궁 정비 + 강호 지도 여정(17 §13.5) + 이벤트 스트림 전투(D2).
Space로 갈림길(지도)을 열어 전투/사건/객잔/기연/보스를 고르고, 결과를 안고 허브로 돌아온다.
"""
from __future__ import annotations
import asyncio
import os
from textual import work, on
from textual.screen import Screen
from textual.containers import Horizontal, Container
from textual.widgets import Static, RichLog
from ..widgets.gugung import GugungWidget
from ..widgets.statuspanel import StatusPanel
from ..widgets.dice3d import Dice3D
from ..widgets.reserve import ReserveWidget
from ...engine.combat_m1 import LINES, cell_eff, OUTPUT_C, N_SPOT, DICE_MODS
from ...engine.bag import Bag, synergy_cells
from ...engine import render_text, balance
from ... import persistence

DELAY = {"round_start": 0.18, "dice": 0.16, "damage": 0.14, "tick": 0.12, "bijang": 0.30,
         "enemy_action": 0.16, "counter": 0.10, "status": 0.08, "summon_attack": 0.10,
         "heal": 0.10, "shield": 0.10, "focus": 0.06, "info": 0.10, "end": 0.2,
         "m1_line": 0.0, "m1_fire": 0.05}      # m1_line은 주사위 굴림이 페이싱

# 디제틱 가이드(첫 회귀에만, 17 §13.2) — 한 번에 한 메커니즘씩(just-in-time)
COACH = [
    "여기가 [#c8a24a]구궁(九宮)[/]. [#c8a24a]방향키[/]나 [#c8a24a]마우스 클릭[/]으로 놓인 무공을 살펴보라.",
    "[#c8a24a]Enter[/]로 무공을 집어 다른 칸에 대보라 — 오른쪽 [#c8a24a]살핌[/]에 [#5aa67c]출력 변화(▲%)[/]가 미리 뜬다. [#e0b341]중앙 칸은 ×1.5[/].",
    "[#c8a24a]Tab[/]으로 [#c8a24a]보관함[/], [#c8a24a]Ctrl+P[/]로 무공·명령 검색. 모은 무공을 구궁에 배치하라.",
    "준비됐으면 [#c8a24a]Space[/]로 [#c8a24a]강호 지도[/]를 열어 첫 길을 고르라. ([#9a958a]Esc로 닫기[/])",
]
ZONE_KO = {"bamboo_grove": "입문 죽림", "black_wind_forest": "흑풍림",
           "frost_spring_valley": "한천비곡", "central_plains_gate": "중원 진입로"}


class GameScreen(Screen):
    # 좁은 터미널: 주사위 패널을 접어 살핌(인스펙터)을 살린다(게임성 우선). 넓으면 전부 표시.
    HORIZONTAL_BREAKPOINTS = [(0, "narrow"), (118, "wide")]
    BINDINGS = [
        ("up", "cur(-1,0)"), ("down", "cur(1,0)"), ("left", "cur(0,-1)"), ("right", "cur(0,1)"),
        ("enter", "grab"), ("tab", "toggle_pane"), ("i", "focus_reserve"),
        ("space", "journey"), ("m", "journey"),
        ("f", "speed"), ("question_mark", "help"), ("escape", "dismiss_coach"), ("q", "app.quit"),
    ]

    def __init__(self, session, first_run: bool = False):
        super().__init__()
        self.session = session
        self.pane = "gugung"            # 활성 패널: gugung | reserve(보관함)
        # 축소 모션(접근성, 17 §8): 환경변수 설정 시 전투 즉시 재생
        self.reduced_motion = bool(os.environ.get("FATEBOUND_REDUCED_MOTION"))
        self.speed = 64.0 if self.reduced_motion else 1.0
        self.busy = False
        self.coach = 0 if (first_run and session.reincarnations == 0 and not session.tutorial_done) else None

    def compose(self):
        yield Static(id="topbar")
        yield Static(id="coach", classes="hidden")
        with Horizontal(id="main"):
            with Container(id="reserve-pane"):    # 좌: 보관함(인라인, 모달 대체)
                yield ReserveWidget(self.session, id="reserve")
            with Container(id="dice-pane"):       # 天命卦 3D 주사위(핵심·랜덤성의 축)
                yield Static("[#c8a24a]天命卦 · 천명괘[/]", classes="label")
                yield Dice3D(skin=getattr(self.session, "die_skin", "baekok"), id="dice")
            with Container(id="gugung-pane"):      # 중앙: 구궁(배치=결정 공간)
                yield Static("[#9a958a]구궁(九宮) · 무공 배치[/]", classes="label")
                yield GugungWidget(self.session, id="gugung")
            yield StatusPanel(self.session, id="status-pane")   # 우: 敵/보스 + 내 상태
        with Container(id="log-pane"):             # 하단 전폭: 천명록
            yield Static("[#9a958a]천명록(天命錄)[/]", classes="label")
            yield RichLog(id="log", wrap=True, markup=True, auto_scroll=True, max_lines=500)
        yield Static(id="actionbar")

    def on_mount(self):
        self.session.ensure_map()
        self._topbar()
        self._actionbar()
        self._sync_detail()
        self._coach_refresh()
        log = self.query_one("#log", RichLog)
        log.can_focus = False
        self.set_focus(self.query_one("#gugung", GugungWidget))   # 구궁이 활성(:focus-within 금테)
        z = ZONE_KO.get(self.session.zone, self.session.zone)
        log.write(f"[#9a958a]── {z} ──[/]")
        log.write("[#9a958a]구궁을 정비하고, [/][#c8a24a]Space[/][#9a958a]로 강호에 나서라.  ([/][#c8a24a]?[/][#9a958a] 도움말)[/]")
        # 복귀 유저(온보딩 지난)에게 새 조작 1회만 안내(persisted seen_events 재사용)
        if (self.coach is None and not self.reduced_motion
                and "p3_controls" not in self.session.seen_events):
            self.session.seen_events.append("p3_controls")
            persistence.save(self.session)
            self.call_after_refresh(lambda: self.app.notify(
                "새 조작 · Ctrl+P 검색 · 마우스로 칸 클릭 · Tab 보관함 · 잡으면 출력 변화 미리보기", timeout=6))

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
            txt = ("[#c8a24a]방향키/클릭[/] 이동 · [#c8a24a]Enter[/] 집기/놓기 · [#c8a24a]Tab[/] 보관함 · "
                   "[#c8a24a]Ctrl+P[/] 명령·검색 · [#c8a24a]Space[/] 강호로 · [#c8a24a]F[/] 배속 · [#c8a24a]?[/] 도움말")
        self.query_one("#actionbar", Static).update(txt)

    def _scale_spot(self):
        """출력 스케일·스폿 배수 — 주사위 재질 반영. player_preview는 sync당 1회만(핫패스)."""
        mods = DICE_MODS.get(getattr(self.session, "die_skin", "baekok"), {})
        scale = max(1.0, self.session.player_preview().atk * OUTPUT_C) * mods.get("dmg_mult", 1.0)
        return scale, N_SPOT * mods.get("spot_mult", 1.0)

    @staticmethod
    def _build_output(cells, scale, spot):
        """M1 빌드의 합당(合當) 기대 출력 — BattleM1 첫 합과 일치(취약 보너스·천명괘 스폿라이트 평균, 적 방어 제외)."""
        has_vuln = any((c.get("m1") or {}).get("fx") == "vulnerable_if_poisoned" for c in cells if c)
        base = sum(cell_eff(cells, i, scale, has_vuln) for i in range(9))
        return base * (1 + (spot - 1) / 3)        # 매 합 6줄 중 1줄 강조 → 기대 +1/3·(spot-1)

    def _sync_detail(self):
        g = self.query_one("#gugung", GugungWidget)
        p = self.query_one("#status-pane", StatusPanel)
        rw = self.query_one("#reserve", ReserveWidget)
        p.detail_item = rw.current() if self.pane == "reserve" else g.current_item()
        p.faces = self.session.loadout().faces
        cells = self.session.bag.cells
        # 미리보기 대상: 잡기 스왑(구궁) 또는 보관함 무공→커서 칸
        clone = ghost = None
        if self.pane == "gugung" and g.grabbed is not None and g.grabbed != g.cursor:
            clone = list(cells)
            clone[g.grabbed], clone[g.cursor] = clone[g.cursor], clone[g.grabbed]
            ghost = cells[g.grabbed]
        elif self.pane == "reserve":
            it = rw.current()
            if it is not None:
                clone = list(cells); clone[g.cursor] = it
                ghost = it
        g.ghost_item = ghost
        # 출력 텔레그래프(배치가 출력을 바꾼다). 위치쌍(idx) 기준 상생 비교 → 동명 무공도 안전.
        if self.session.use_m1():
            scale, spot = self._scale_spot()
            p.output = self._build_output(cells, scale, spot)
            if clone is not None:
                p.preview_output = self._build_output(clone, scale, spot)
                cur, nxt = self._syn_pairs(cells), self._syn_pairs(clone)
                p.syn_formed = self._name_pairs(nxt - cur, clone)
                p.syn_broken = self._name_pairs(cur - nxt, cells)
                dd = p.preview_output - p.output
                pc = (100 * dd / p.output) if p.output else 0
                ar = "▲" if dd > 0.05 else ("▼" if dd < -0.05 else "·")
                g.ghost_delta = f"{ar}{pc:+.0f}%"          # 고스트 칸에 델타 동거(원인+결과)
            else:
                p.preview_output = p.syn_formed = p.syn_broken = None
                g.ghost_delta = None
        else:
            p.output = p.preview_output = p.syn_formed = p.syn_broken = None
            g.ghost_delta = None
        g.refresh()
        p.refresh()

    @staticmethod
    def _syn_pairs(cells):
        """배치의 상생쌍을 {frozenset(위치,위치)}로 — 동명 무공 충돌 없이 스왑 전후 비교."""
        _, pairs = synergy_cells(Bag(cells=list(cells)))
        return {frozenset((a, b)) for a, b in pairs}

    @staticmethod
    def _name_pairs(pos_pairs, src):
        """위치쌍 집합 → 표시용 (이름, 이름) 리스트(해당 배치 src에서 룩업)."""
        out = []
        for pr in pos_pairs:
            a, b = tuple(pr)
            na = src[a]["name_ko"] if src[a] else "?"
            nb = src[b]["name_ko"] if src[b] else "?"
            out.append((na, nb))
        return out

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
            self.coach = None                    # 이번 세션만 숨김 — 영구 완료 아님(#16). 첫 전투 완주 시 done 처리.
            self._coach_refresh()

    def _finish_tutorial(self):
        if not self.session.tutorial_done:
            self.session.tutorial_done = True
            persistence.save(self.session)

    def action_help(self):
        from .help import HelpScreen
        self.app.push_screen(HelpScreen())

    # ── 구궁/보관함 조작 (활성 패널로 라우팅) ──
    def _focus_pane(self, name: str):
        self.pane = name
        try:
            w = self.query_one("#reserve" if name == "reserve" else "#gugung")
            if name == "reserve":
                w.clamp()
            self.set_focus(w)
        except Exception:
            pass
        if name == "reserve":
            self._coach_advance(2)        # 보관함 열기 = 온보딩 3단계로
        self._sync_detail()

    def action_toggle_pane(self):
        if not self.busy:
            self._focus_pane("gugung" if self.pane == "reserve" else "reserve")

    def action_focus_reserve(self):
        if not self.busy:
            self._focus_pane("reserve")

    def goto_cell(self, idx: int):
        """팔레트/외부에서 특정 구궁 칸으로 커서 점프."""
        if self.busy:
            return
        self._focus_pane("gugung")
        self.query_one("#gugung", GugungWidget).cursor = max(0, min(8, idx))
        self._sync_detail()

    def select_reserve(self, item_id: str):
        """팔레트에서 특정 보관함 무공을 골라 선택 상태로."""
        if self.busy:
            return
        self._focus_pane("reserve")
        rw = self.query_one("#reserve", ReserveWidget)
        for i, it in enumerate(rw.items()):
            if it["item_id"] == item_id:
                rw.sel = i
                break
        self._sync_detail()

    # ── 마우스(키보드와 동등) ──
    @on(GugungWidget.CellClicked)
    def _on_cell_click(self, msg: GugungWidget.CellClicked):
        if self.busy:
            return
        self._focus_pane("gugung")
        self.query_one("#gugung", GugungWidget).cursor = msg.idx
        self._coach_advance(0)                   # 클릭 경로도 코치 0단계(살펴봄) 진행 — 클릭-only 유저 정체 방지(#16)
        self.action_grab()                       # 클릭=집기/놓기(빈손이면 집고, 들었으면 놓는다)

    @on(ReserveWidget.Clicked)
    def _on_reserve_click(self, msg: ReserveWidget.Clicked):
        if self.busy:
            return
        self.pane = "reserve"
        rw = self.query_one("#reserve", ReserveWidget)
        rw.sel = msg.row
        self.set_focus(rw)
        self._sync_detail()

    def action_cur(self, dr: int, dc: int):
        if self.busy:
            return
        if self.pane == "reserve":
            if dc > 0:                                       # → 구궁으로 건너가기
                self._focus_pane("gugung")
            else:
                self.query_one("#reserve", ReserveWidget).move(dr)
                self._sync_detail()
            return
        g = self.query_one("#gugung", GugungWidget)
        if dc < 0 and g.cursor % 3 == 0 and self.session.reserve():   # 좌 끝에서 ← → 보관함
            self._focus_pane("reserve")
            return
        g.move_cursor(dr, dc)
        self._sync_detail()
        self._coach_advance(0)

    def action_grab(self):
        if self.busy:
            return
        if self.pane == "reserve":
            self._place_from_reserve()
            return
        g = self.query_one("#gugung", GugungWidget)
        was = g.grabbed is not None
        g.toggle_grab()
        self._sync_detail()
        persistence.save(self.session)
        if was and g.grabbed is None:
            self._coach_advance(1)

    def _place_from_reserve(self):
        rw = self.query_one("#reserve", ReserveWidget)
        it = rw.current()
        if not it:
            return
        g = self.query_one("#gugung", GugungWidget)
        self.session.place_from_reserve(it["item_id"], g.cursor)
        rw.clamp()
        if not self.session.reserve():                       # 보관함이 비면 구궁으로
            self._focus_pane("gugung")
        self._refresh_hub()
        persistence.save(self.session)
        self.app.notify(f"⇲ {it['name_ko']} 배치", timeout=2)

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
                if not self.reduced_motion:
                    lit = list(LINES[d["line"]])
                    for x in d.get("extra", []):           # dice 천명 조작: 추가 강조줄도 점화(넓은 스폿라이트)
                        lit += LINES[x]
                    gug.ignite(lit)
                if "m1_line_taught" not in self.session.seen_events:   # 천명괘 just-in-time 교육(평생 1회)
                    self.session.seen_events.append("m1_line_taught")
                    self.app.notify("매 합 6줄 중 한 줄(금빛)이 강조돼 그 줄 무공이 더 세게 친다. "
                                    "강한 무공을 한 줄로 모아 두면 천명이 깃들 때 크게 터진다.",
                                    title="天命卦 천명괘", severity="information", timeout=7)
            if e.kind == "m1_fire" and not self.reduced_motion:   # 발동 캐스케이드: 무공이 차례로 번쩍(기여 수치 표시)
                ci = self._cell_index(d.get("name"))
                if ci is not None:
                    gug.pulse(ci, round(d.get("amount", 0)))
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
        # 첫 전투 완주 = 튜토리얼 소임 완료(코치 단계·Esc 숨김 무관). 이후 재등장 안 함(#16).
        self.coach = None
        self._coach_refresh(); self._finish_tutorial()

    async def _do_roll(self, dice, line: int):
        """천명괘 3D 주사위를 결과 줄(0~5)로 굴린다. 고배속/축소모션은 즉시 착지."""
        instant = self.speed >= 2.0
        dice.roll(line, instant=instant)
        if not instant:
            await asyncio.sleep(Dice3D.ROLL_SECONDS)       # 위젯이 자체 타이머로 굴러 착지

    def _cell_index(self, name):
        """무공 이름 → 구궁 칸 index(발동 캐스케이드용). 동명은 첫 칸."""
        for i, c in enumerate(self.session.bag.cells):
            if c and c["name_ko"] == name:
                return i
        return None

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

    def _toast(self, msg, severity="information"):
        # 보상/사건을 토스트로도(라이트 유저가 로그를 놓쳐도 보이게). 축소모션은 생략.
        if not self.reduced_motion:
            self.app.notify(msg, severity=severity, timeout=4)

    def _after(self, res, out, log: RichLog):
        if res.outcome == "win":
            g = out.get("gains", {})
            log.write(f"[#5aa67c]전리품: 경험치 +{g.get('xp',0)} · 골드 +{g.get('gold',0)} · 파편 +{g.get('shards',0)}[/]")
            for lv in out.get("leveled", []):
                log.write(f"[#c8a24a bold]경지 상승! Lv{lv}[/]")
            if out.get("leveled"):                          # 다중 레벨업은 1토스트로 합산
                lvs = out["leveled"]
                self._toast(f"경지 상승 · Lv{lvs[-1]}" + (f" (+{len(lvs)})" if len(lvs) > 1 else ""), "warning")
            if out.get("drop"):
                log.write(f"[#c8a24a]전리품 무공: {out['drop']['name_ko']} 획득![/]")
                self._toast(f"무공 획득 · {out['drop']['name_ko']}", "warning")
            if out.get("boss_cleared"):
                za = out.get("zone_advanced")
                if za:
                    log.write(f"[#c8a24a bold]━━ 관문 돌파! 새 강호 '{ZONE_KO.get(za, za)}'(이)가 열렸다 ━━[/]")
                    self._toast(f"관문 돌파! 새 강호 · {ZONE_KO.get(za, za)}", "warning")
                else:
                    log.write("[#c8a24a bold]━━ 이 강호를 평정했다. 더 깊은 곳으로… ━━[/]")
                    self._toast("강호를 평정했다", "warning")
        elif out.get("reincarnated"):
            log.write("[#d4582f bold]━━ 전사, 그리고 회귀(回歸) ━━[/]")
            self._toast("전사 — 회귀(回歸)", "error")
            from .reincarnate import ReincarnateScreen
            self.app.push_screen(ReincarnateScreen(self.session, out.get("gain", 0), "전사"))
