"""서재 — 사슬 편집 (5권 05 §4 · 04 §2.1.1 T1 키보드 시퀀스).
집기→이동→놓기 = 검산 즉시 갱신(rulebook 엔진 — 텔레그래프). 유파 프리셋·클러스터 ═/┄.
키: Tab 사슬↔서가 · ←→ 포커스 · Space 집기 · Enter 놓기/스왑 · P 유파 정석 · Esc 지도로."""
from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from .. import theme as T
from ..data import slice_pack as P
from ..engine.render import fg, R


def _c(rgb):
    return T.hexc(rgb)


def ansi(s: str) -> Text:
    return Text.from_ansi(s)


class StudyScreen(Screen):
    BINDINGS = [
        ("tab", "zone", "사슬↔서가"),
        ("left", "mv(-1)", "◀"), ("right", "mv(1)", "▶"),
        ("space", "grab", "집기"), ("enter", "drop", "놓기"),
        ("p", "yupa", "유파 정석"), ("escape", "back", "지도로"),
    ]

    def __init__(self):
        super().__init__()
        self.zone = "chain"          # chain|shelf
        self.cur = 0
        self.grabbed: str | None = None   # 집은 무공(서가 출신 or 사슬 칸)
        self.grab_from: tuple[str, int] | None = None
        self.base: dict | None = None     # 직전 검산(Δ 기준)

    @property
    def st(self):
        return self.app.state  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        yield Static(id="study")
        yield Static(id="voice")
        yield Static(id="hints")

    def on_mount(self) -> None:
        self.base = self.st.appraise()
        self.redraw()
        v = (fg(T.GOLD) + " 천기노조" + R + fg(T.DIM)
             + " — 사슬은 순서가 절반이야. 증폭기 옆자리부터 봐라." + R)
        self.query_one("#voice", Static).update(ansi(v))
        self.query_one("#hints", Static).update(ansi(
            fg(T.DIM) + " [Tab]사슬↔서가  [←→]포커스  [Space]집기  [Enter]놓기  [P]유파 정석  [Esc]지도" + R))

    # ── 렌더 ──
    def redraw(self, preview: dict | None = None) -> None:
        st = self.st
        out = []
        out.append(fg(T.INK) + " ◆ 서재 — 사슬" + R + fg(T.DIM)
                   + f"   심법 [{P.SIMBEOP['name']}]" + R)
        out.append("")
        # 사슬 행 + 클러스터 ═/┄
        row = " 사슬  "
        for i, key in enumerate(st.chain):
            m = P.MOVES[key]
            focus = self.zone == "chain" and self.cur == i
            grabbed_here = self.grab_from == ("chain", i)
            col = T.AMBER if focus else ((180, 150, 220) if m["role"] == "burst" else T.INK)
            mark = "▲" if grabbed_here else ""
            row += fg(col) + f"[{mark}{key}]" + R
            if i < len(st.chain) - 1:
                a, b = P.MOVES[st.chain[i]], P.MOVES[st.chain[i + 1]]
                link = "═" if a["series"] == b["series"] else "┄"
                row += fg(T.POISON if link == "═" else T.DIM) + link + R
        out.append(row)
        # 유파/하이브리드 판정 행
        is_yupa = st.chain == P.YUPA["chain"]
        out.append(fg(T.DIM) + " 현재 사슬: " + R
                   + (fg(T.GOLD) + f"유파({P.YUPA['name']})" if is_yupa
                      else fg((130, 190, 230)) + "하이브리드 발굴") + R)
        out.append("")
        # 서가
        out.append(fg(T.DIM) + " 서가" + R)
        if not st.shelf:
            out.append(fg(T.DIM) + "   (비어 있음)" + R)
        for i, key in enumerate(st.shelf):
            m = P.MOVES[key]
            focus = self.zone == "shelf" and self.cur == i
            grabbed_here = self.grab_from == ("shelf", i)
            col = T.AMBER if focus else T.INK
            out.append("  " + fg(col) + f"{'▲' if grabbed_here else '▸'} {key}" + R
                       + fg(T.DIM) + f"  {m['gist']}" + R)
        out.append("")
        # 검산 패널 (실시간 — 집은 상태면 미리보기)
        ap = preview or self.st.appraise()
        d_avg = (ap["avg"] - self.base["avg"]) if self.base else 0.0
        dcol = T.POISON if d_avg < -0.05 else (T.SEAL if d_avg > 0.05 else T.DIM)
        out.append(fg(T.DIM) + " ┌ 검산(실시간 — rulebook 엔진) ┐" + R)
        out.append(fg(T.DIM) + " │ vs 죽림 적  평균 " + R
                   + fg(T.INK) + f"{ap['avg']:.1f}합" + R
                   + fg(T.DIM) + f" · 승률 {ap['winrate']:.0%}" + R)
        out.append(fg(T.DIM) + " │ 속성 매치업  독 ↔ 양강 — 우위" + R)
        out.append(fg(T.DIM) + " │ Δ " + R + fg(dcol) + f"{d_avg:+.1f}합"
                   + (" ▲ 좋아졌다" if d_avg < -0.05 else (" ▼ 나빠졌다" if d_avg > 0.05 else " — 동일")) + R)
        out.append(fg(T.DIM) + " └──────────────────────────┘" + R)
        if self.grabbed:
            out.append("")
            out.append(fg(T.AMBER) + f" ▲ 집음: {self.grabbed}" + R + fg(T.DIM)
                       + " — 사슬 칸 위에서 [Enter]=놓기(스왑)" + R)
        self.query_one("#study", Static).update(ansi("\n".join(out)))

    # ── 입력 ──
    def action_zone(self) -> None:
        self.zone = "shelf" if self.zone == "chain" else "chain"
        self.cur = 0
        self.redraw()

    def action_mv(self, d: int) -> None:
        n = len(self.st.chain) if self.zone == "chain" else max(1, len(self.st.shelf))
        self.cur = (self.cur + d) % n
        # 집은 상태에서 사슬 위 이동 = 가상 배치 미리보기(텔레그래프)
        if self.grabbed and self.zone == "chain":
            trial = list(self.st.chain)
            trial[self.cur] = self.grabbed
            self.redraw(preview=self.st.appraise(trial))
        else:
            self.redraw()

    def action_grab(self) -> None:
        st = self.st
        if self.grabbed:
            return
        if self.zone == "shelf" and st.shelf:
            self.grabbed = st.shelf[self.cur]
            self.grab_from = ("shelf", self.cur)
            self.zone = "chain"
            self.cur = 0
        elif self.zone == "chain":
            self.grabbed = st.chain[self.cur]
            self.grab_from = ("chain", self.cur)
        self.redraw()

    def action_drop(self) -> None:
        st = self.st
        if not self.grabbed or self.zone != "chain":
            return
        src_zone, src_i = self.grab_from
        tgt = self.cur
        if src_zone == "shelf":                       # 서가 → 사슬: 교체(밀려난 건 서가로)
            out = st.chain[tgt]
            st.chain[tgt] = self.grabbed
            st.shelf.pop(src_i)
            st.shelf.append(out)
        else:                                         # 사슬 내 스왑
            st.chain[src_i], st.chain[tgt] = st.chain[tgt], st.chain[src_i]
        self.grabbed = None
        self.grab_from = None
        self.base = st.appraise()                     # 새 기준(Δ 리셋)
        self.redraw()

    def action_yupa(self) -> None:
        st = self.st
        # 정석 깔기 — 사슬 전체 교체, 밀려난 비정석 무공은 서가로
        for k in st.chain:
            if k not in P.YUPA["chain"] and k not in st.shelf:
                st.shelf.append(k)
        st.chain = list(P.YUPA["chain"])
        st.shelf = [k for k in st.shelf if k not in st.chain]
        self.grabbed = None
        self.grab_from = None
        self.base = st.appraise()
        self.redraw()

    def action_back(self) -> None:
        self.app.pop_screen()
