"""천명괘(天命卦) 3D 주사위 위젯 — 게임의 정체성·랜덤성의 축(D1).

진짜 3D 큐브를 매 프레임 소프트웨어로 래스터라이즈한다(순수 Textual, 새 의존성 0):
  · 8정점 회전 → 약투시 투영 → z버퍼 페인터
  · 면별 람베르트 음영 + Blinn-Phong 스페큘러 + 림라이트 → 하프블록(▀) 트루컬러
  · 금/은테 모서리 + 눈(pip) 디스크 + 바닥 그림자 + 텀블링 모션블러 + 착지 기 스파크
  · 6면(눈 1~6) ↔ 천명괘 6줄(1행~3열). 재질=아이템(스킨+스탯, 스탯은 engine.combat_m1.DICE_MODS).

동적 포커스: 패널 크기는 고정, 다이 스케일만 lerp(굴림 땐 확대·배치 땐 축소)해 reflow 없음.
게임 화면은 `roll(target_line)`으로 엔진의 굴림 결과(줄)에 맞춰 착지시키고, 착지 시
`Dice3D.Landed(line)` 메시지를 받아 전투 발동 juice와 동기화한다.
"""
from __future__ import annotations
import math, random
from textual.widget import Widget
from textual.message import Message
from rich.text import Text
from rich.console import Group

# 천명괘 줄 라벨(눈 1~6 ↔ 줄). engine.combat_m1.LINE_KO와 동일 순서.
LINE_KO = ["1행", "2행", "3행", "1열", "2열", "3열"]

L = (0.50, 0.62, 0.60)
_l = math.sqrt(sum(c * c for c in L)); L = tuple(c / _l for c in L)
_HV = (L[0], L[1], L[2] + 1.0)                       # half(L + 시선 +Z)
_h = math.sqrt(sum(c * c for c in _HV)); H = tuple(c / _h for c in _HV)
HL = (255, 250, 236)

V8 = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
      (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
FACES = [
    ((0, 0, 1), [4, 5, 6, 7], (1, 0, 0), (0, 1, 0), 1),
    ((0, 0, -1), [1, 0, 3, 2], (1, 0, 0), (0, 1, 0), 6),
    ((1, 0, 0), [5, 1, 2, 6], (0, 0, -1), (0, 1, 0), 3),
    ((-1, 0, 0), [0, 4, 7, 3], (0, 0, 1), (0, 1, 0), 4),
    ((0, 1, 0), [7, 6, 2, 3], (1, 0, 0), (0, 0, -1), 2),
    ((0, -1, 0), [0, 1, 5, 4], (1, 0, 0), (0, 0, 1), 5),
]
PIP_LAYOUT = {
    1: [(0, 0)], 2: [(-1, 1), (1, -1)], 3: [(-1, 1), (0, 0), (1, -1)],
    4: [(-1, -1), (-1, 1), (1, -1), (1, 1)],
    5: [(-1, -1), (-1, 1), (0, 0), (1, -1), (1, 1)],
    6: [(-1, -1), (-1, 0), (-1, 1), (1, -1), (1, 0), (1, 1)],
}
FACE_HOME = [(0, 0), (0, math.pi), (0, -math.pi / 2), (0, math.pi / 2),
             (math.pi / 2, 0), (-math.pi / 2, 0)]

# 재질(아이템) 비주얼. id는 engine.combat_m1.DICE_MODS 키와 일치(스킨↔스탯).
DICE_SKINS = {
    "baekok": dict(name="백옥", rarity="common", glyph="◇",
                   face=(232, 224, 205), pip=(20, 16, 12), edge=(224, 179, 65),
                   spec=0.30, shine=14, rim=0.0, rim_col=(0, 0, 0),
                   flavor="흠 없는 흰 옥. 천명을 읽기엔 이만한 게 없다더라."),
    "heukyo": dict(name="흑요석", rarity="rare", glyph="◆",
                   face=(40, 38, 48), pip=(224, 179, 65), edge=(196, 200, 214),
                   spec=0.85, shine=42, rim=0.10, rim_col=(120, 130, 160),
                   flavor="빛을 먹는 검은 유리. 구르는 소리마저 묵직하다."),
    "bichwi": dict(name="비취", rarity="epic", glyph="❖",
                   face=(64, 150, 108), pip=(224, 240, 226), edge=(34, 92, 70),
                   spec=0.45, shine=22, rim=0.35, rim_col=(120, 240, 180),
                   flavor="속이 비치는 푸른 옥. 모서리에 빛이 고인다."),
    "hyeolok": dict(name="혈옥", rarity="legendary", glyph="✦",
                    face=(122, 30, 36), pip=(14, 10, 10), edge=(214, 96, 60),
                    spec=0.55, shine=26, rim=0.22, rim_col=(230, 70, 60),
                    flavor="혈마의 피로 굳었다는 붉은 옥. 굴릴 때마다 운이 끈적인다."),
    "baekgol": dict(name="백골", rarity="rare", glyph="☠",
                    face=(212, 206, 190), pip=(96, 30, 28), edge=(150, 142, 126),
                    spec=0.08, shine=6, rim=0.0, rim_col=(0, 0, 0),
                    flavor="누구 뼈로 깎았는지는 묻지 않는 게 좋다."),
}
RARITY_COL = {"common": "#9a958a", "rare": "#5a9ad4", "epic": "#c8a24a", "legendary": "#d4582f"}


def face_for_line(line):
    for i, f in enumerate(FACES):
        if f[4] - 1 == line:
            return i
    return 0


def _clamp3(t):
    return (max(0, min(255, int(t[0]))), max(0, min(255, int(t[1]))), max(0, min(255, int(t[2]))))


def _rot(p, ax, ay, az):
    x, y, z = p
    c, s = math.cos(az), math.sin(az); x, y = x * c - y * s, x * s + y * c
    c, s = math.cos(ax), math.sin(ax); y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ay), math.sin(ay); x, z = x * c + z * s, -x * s + z * c
    return (x, y, z)


def _proj(p, W, H_, scale, cy, focal):
    x, y, z = p
    f = focal / (focal - z)
    return (x * f * scale + W / 2, -y * f * scale + cy, z)


def _face_color(nr, sk):
    d = max(0.0, nr[0] * L[0] + nr[1] * L[1] + nr[2] * L[2])
    base = [c * (0.24 + 0.76 * d) for c in sk["face"]]
    sp = sk["spec"] * (max(0.0, nr[0] * H[0] + nr[1] * H[1] + nr[2] * H[2]) ** sk["shine"])
    rim = sk["rim"] * (1.0 - max(0.0, nr[2])) ** 2
    return _clamp3(tuple(base[i] + sp * HL[i] + rim * sk["rim_col"][i] for i in range(3)))


def rasterize(ax, ay, az, sk, W, Hp, scale, cy, focal=6.0):
    P = [_proj(_rot(v, ax, ay, az), W, Hp, scale, cy, focal) for v in V8]
    col = [[None] * W for _ in range(Hp)]
    zb = [[-1e9] * W for _ in range(Hp)]
    vis = []
    for (n, idx, ud, vd, pips) in FACES:
        nr = _rot(n, ax, ay, az)
        if nr[2] <= 0.03:
            continue
        vis.append((n, idx, ud, vd, pips, nr))
        fc = _face_color(nr, sk)
        a, b, c, dd = (P[i] for i in idx)
        _tri(col, zb, a, b, c, fc); _tri(col, zb, a, c, dd, fc)
    for (n, idx, ud, vd, pips, nr) in vis:
        d = max(0.0, nr[0] * L[0] + nr[1] * L[1] + nr[2] * L[2])
        eg = _clamp3(tuple(c * (0.6 + 0.4 * d) for c in sk["edge"]))
        ring = idx + [idx[0]]
        for k in range(4):
            _line(col, zb, P[ring[k]], P[ring[k + 1]], eg)
        pc = _clamp3(tuple(c * (0.45 + 0.55 * d) for c in sk["pip"]))
        for (pu, pv) in PIP_LAYOUT[pips]:
            cen = tuple(n[j] * 1.02 + ud[j] * pu * 0.52 + vd[j] * pv * 0.52 for j in range(3))
            _disc(col, zb, _proj(_rot(cen, ax, ay, az), W, Hp, scale, cy, focal), scale * 0.115, pc)
    return col


def _tri(col, zb, a, b, c, color):
    Hp, W = len(col), len(col[0])
    minx = max(0, int(min(a[0], b[0], c[0]))); maxx = min(W - 1, int(max(a[0], b[0], c[0])) + 1)
    miny = max(0, int(min(a[1], b[1], c[1]))); maxy = min(Hp - 1, int(max(a[1], b[1], c[1])) + 1)
    area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(area) < 1e-6:
        return
    for py in range(miny, maxy + 1):
        for px in range(minx, maxx + 1):
            x, y = px + 0.5, py + 0.5
            w0 = ((b[0] - x) * (c[1] - y) - (b[1] - y) * (c[0] - x)) / area
            w1 = ((c[0] - x) * (a[1] - y) - (c[1] - y) * (a[0] - x)) / area
            w2 = 1 - w0 - w1
            if w0 >= -0.01 and w1 >= -0.01 and w2 >= -0.01:
                z = w0 * a[2] + w1 * b[2] + w2 * c[2]
                if z > zb[py][px]:
                    zb[py][px] = z; col[py][px] = color


def _disc(col, zb, cen, r, color):
    Hp, W = len(col), len(col[0])
    cx, cy, cz = cen; r2 = r * r
    for py in range(max(0, int(cy - r)), min(Hp, int(cy + r) + 1)):
        for px in range(max(0, int(cx - r)), min(W, int(cx + r) + 1)):
            if (px + 0.5 - cx) ** 2 + (py + 0.5 - cy) ** 2 <= r2 and cz + 0.03 >= zb[py][px] and zb[py][px] > -1e8:
                col[py][px] = color


def _line(col, zb, a, b, color):
    Hp, W = len(col), len(col[0])
    x0, y0 = int(a[0]), int(a[1]); x1, y1 = int(b[0]), int(b[1])
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        if 0 <= x0 < W and 0 <= y0 < Hp and zb[y0][x0] > -1e8:
            col[y0][x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy


def _hex(c):
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def to_lines(col):
    rows = []
    Hp = len(col)
    for cy in range(0, Hp - 1, 2):
        t = Text()
        for cx in range(len(col[0])):
            top, bot = col[cy][cx], col[cy + 1][cx]
            if top is None and bot is None:
                t.append(" ")
            elif bot is None:
                t.append("▀", style=_hex(top))
            elif top is None:
                t.append("▄", style=_hex(bot))
            else:
                t.append("▀", style=f"{_hex(top)} on {_hex(bot)}")
        rows.append(t)
    return rows


def _dim(c, f):
    return (int(c[0] * f), int(c[1] * f), int(c[2] * f))


class Dice3D(Widget):
    """천명괘 3D 주사위. roll(line)으로 엔진 결과에 맞춰 착지, 착지 시 Landed 메시지."""

    PX = 34                              # 고정 버퍼(패널 크기 불변 → reflow 없음). 짝수 필수.
    FOCAL = 6.0
    TUMBLE_FRAMES = 26                   # 굴림(구르기) 프레임
    SETTLE_FRAMES = 12                   # 착지(안착) 프레임
    ROLL_SECONDS = (26 + 12) / 30        # 화면이 await할 굴림 총길이(≈1.27s)

    class Landed(Message):
        def __init__(self, line: int):
            self.line = line
            super().__init__()

    def __init__(self, skin: str = "baekok", **kw):
        super().__init__(**kw)
        self.skin = skin if skin in DICE_SKINS else "baekok"
        self.ax, self.ay, self.az = 0.5, 0.7, 0.0
        self.vx = self.vy = self.vz = 0.0
        self.phase = "idle"              # idle | tumble | settle
        self.target = 0                  # 착지 목표 면
        self.result_line = 0
        self.flash = 0
        self.scale_mul = 0.72            # 동적 포커스(0.72 배치 / 1.0 굴림)
        self.want_big = False
        self.hist = []
        self.sparks = []
        self.border_title = "天命卦 · 천명괘"

    def on_mount(self):
        self.set_interval(1 / 30, self._tick)

    # ── 게임 화면 API ──
    def set_skin(self, skin: str):
        if skin in DICE_SKINS:
            self.skin = skin
            self.refresh()

    def roll(self, target_line: int, instant: bool = False):
        """엔진이 굴린 줄(0~5)에 맞춰 그 면으로 착지. instant=즉시(축소모션/고배속)."""
        self.result_line = target_line % 6
        self.target = face_for_line(self.result_line)
        self.want_big = True
        if instant:
            self.ax, self.ay = FACE_HOME[self.target]; self.az = 0.0
            self.phase = "idle"; self._t = 1; self.flash = 4; self._burst()
            self.refresh()
            return
        self.phase = "tumble"; self._frames = 0
        self.vx = random.uniform(0.30, 0.55) * random.choice((-1, 1))
        self.vy = random.uniform(0.42, 0.62) * random.choice((-1, 1))
        self.vz = random.uniform(0.10, 0.20) * random.choice((-1, 1))

    def focus(self, big: bool):
        self.want_big = big

    # ── 프레임 ──
    def _tick(self):
        tgt = 1.0 if (self.want_big or self.phase != "idle") else 0.72
        self.scale_mul += (tgt - self.scale_mul) * 0.25
        if self.phase == "idle":
            self.ay += 0.012; self.ax += 0.005
        elif self.phase == "tumble":
            self.ax += self.vx; self.ay += self.vy; self.az += self.vz
            self.vx *= 0.96; self.vy *= 0.96; self.vz *= 0.96
            self._frames = getattr(self, "_frames", 0) + 1
            if self._frames >= self.TUMBLE_FRAMES:
                self.phase = "settle"; self._t = 0
        elif self.phase == "settle":
            hx, hy = FACE_HOME[self.target]
            self.ax += (hx - self.ax) * 0.32
            self.ay = self._toward(self.ay, hy, 0.32)
            self.az += (0.0 - self.az) * 0.32
            self._t = getattr(self, "_t", 0) + 1
            if self._t == 1:
                self.flash = 5; self._burst()
            if self._t >= self.SETTLE_FRAMES:
                self.ax, self.ay = FACE_HOME[self.target]; self.az = 0.0
                self.phase = "idle"; self.want_big = False
                self.post_message(self.Landed(self.result_line))
        self.flash = max(0, self.flash - 1)
        if self.sparks:
            for s in self.sparks:
                s["x"] += s["vx"]; s["y"] += s["vy"]; s["vy"] += 0.18; s["vx"] *= 0.99; s["age"] += 1
            self.sparks = [s for s in self.sparks if s["age"] < s["life"]]
        self.refresh()

    def _burst(self):
        acc = DICE_SKINS[self.skin]["edge"]
        cx = self.PX / 2; cy = self.PX * 0.43
        for _ in range(34):
            a = random.random() * math.tau
            sp = 0.8 + random.random() * 2.2
            self.sparks.append({"x": cx, "y": cy, "vx": math.cos(a) * sp,
                                "vy": math.sin(a) * sp - 0.6, "age": 0,
                                "life": 11 + random.randint(0, 12), "c": acc})

    @staticmethod
    def _toward(a, target, k):
        d = (target - a) % (2 * math.pi)
        if d > math.pi:
            d -= 2 * math.pi
        return a + d * k

    # ── 렌더 ──
    def render(self):
        sk = DICE_SKINS[self.skin]
        W = Hp = self.PX
        scale = W * 0.30 * self.scale_mul
        cy = Hp * 0.43
        col = rasterize(self.ax, self.ay, self.az, sk, W, Hp, scale, cy, self.FOCAL)
        clean = [r[:] for r in col]
        if self.phase == "tumble" and self.hist:
            for gi, alpha in ((len(self.hist) - 1, 0.5), (0, 0.24)):
                if 0 <= gi < len(self.hist):
                    g = self.hist[gi]
                    for y in range(Hp):
                        for x in range(W):
                            if col[y][x] is None and g[y][x] is not None:
                                col[y][x] = _dim(g[y][x], alpha)
        self.hist.append(clean); self.hist = self.hist[-2:]
        self._shadow(col, W, Hp)
        for s in self.sparks:
            px, py = int(s["x"]), int(s["y"])
            if 0 <= px < W and 0 <= py < Hp:
                f = 1 - s["age"] / s["life"]
                col[py][px] = _clamp3(_dim(s["c"], 0.5 + 0.5 * f))
        if self.flash > 0 and self.flash % 2 == 1:
            for r in col:
                for x in range(W):
                    if r[x] is not None:
                        r[x] = (255, 250, 240)
        rows = to_lines(col)
        rc = RARITY_COL[sk["rarity"]]
        cap = Text(f"{sk['glyph']} {sk['name']}", style=f"{rc} bold", justify="center")
        if self.phase in ("settle",) or (self.phase == "idle" and self.flash == 0 and getattr(self, "_t", 0)):
            cap.append(f"  ▶ {LINE_KO[self.result_line]}", style="#5aa67c bold")
        elif self.phase == "tumble":
            cap = Text("천명이 구른다…", style="#e0b341", justify="center")
        return Group(*rows, cap)

    @staticmethod
    def _shadow(col, W, Hp):
        cx, cy, rx, ry = W / 2, Hp * 0.93, W * 0.34, 2.6
        for py in range(int(cy - ry), min(Hp, int(cy + ry) + 1)):
            for px in range(max(0, int(cx - rx)), min(W, int(cx + rx) + 1)):
                if col[py][px] is not None:
                    continue
                e = ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2
                if e <= 1.0:
                    v = int(24 * (1 - e))
                    col[py][px] = (v, v, v + 3)


def _selftest():
    for sid, sk in DICE_SKINS.items():
        col = rasterize(0.5, 0.62, 0.08, sk, Dice3D.PX, Dice3D.PX, Dice3D.PX * 0.30, Dice3D.PX * 0.43)
        lit = sum(1 for r in col for c in r if c is not None)
        assert 0 < lit < Dice3D.PX * Dice3D.PX, f"{sk['name']} {lit}"
        print(f"{sk['name']:4}({sk['rarity']:9}) 픽셀 {lit:4d} · 하프블록 {len(to_lines(col))}행")
    for ln in range(6):
        f = face_for_line(ln)
        assert FACES[f][4] - 1 == ln
    print(f"줄→면 매핑 OK · 스킨 {len(DICE_SKINS)}종 · Dice3D 위젯(버퍼 {Dice3D.PX}px) 정상.")


if __name__ == "__main__":
    _selftest()
