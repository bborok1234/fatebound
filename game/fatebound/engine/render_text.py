"""이벤트 스트림 → 무협체 텍스트 로그(02 §전투 로그 · 10 §8 보이스). TUI/CLI 공용 폴백."""
from __future__ import annotations
from .events import Event


def line(e: Event) -> str | None:
    k, d = e.kind, e.data
    if k == "battle_start":
        return f"[{d['enemy']}이(가) 길을 막아섰다.]  천명괘: {' '.join(d['faces'])}"
    if k == "round_start":
        return f"[{d['n']}합]"
    if k == "dice":
        return f"  천명괘 → {d['face']}" + ("  (재점)" if d.get("rerolled") else "")
    if k == "focus":
        return f"    허초 — 응기 {d['count']}"
    if k == "damage":
        lbl = (d.get("label") + " ") if d.get("label") else ""
        crit = "⚡치명! " if d.get("crit") else ""
        return f"    {crit}{lbl}{d['src']} → {d['tgt']} {d['amount']} 피해 (HP {d['tgt_hp']}/{d['tgt_max']})"
    if k == "status":
        names = {"poison": "독", "burn": "화상", "weak": "약화", "vulnerable": "취약", "stun": "기절"}
        s = names.get(d["status"], d["status"])
        extra = f" {d['stacks']}중첩" if "stacks" in d else ""
        return f"    {d['tgt']}에 {s}{extra}"
    if k == "tick":
        s = {"poison": "☠ 독", "burn": "🔥 화상"}.get(d["status"], d["status"])
        return f"    {s} {d['amount']} (HP {d['tgt_hp']})"
    if k == "heal":
        return f"    회복 +{d['amount']}"
    if k == "shield":
        return f"    보호막 +{d['amount']}"
    if k == "counter":
        return f"      ↳ 반격! {d['amount']} 반환 (HP {d['tgt_hp']})"
    if k == "bijang":
        return "  ✦ 비장(秘藏)의 수 발동!"
    if k == "summon_attack":
        return f"    {d['name']} 가세 — {d['amount']} 피해 (HP {d['tgt_hp']})"
    if k == "enemy_action":
        return f"  [적] {d['name']}!"
    if k == "info":
        return f"    {d['text']}"
    if k == "end":
        r = {"win": "승리", "loss": "패배", "timeout": "무승부"}[d["outcome"]]
        return f"[{r}] {d['rounds']}합 · {e.data.get('player_hp')}/{e.data.get('player_max')} HP"
    return None


def render(events) -> str:
    return "\n".join(s for s in (line(e) for e in events) if s)
