"""세이브 — 메타/런 직렬화·원자적 쓰기·버전드(20 §3). 로컬 store(MMO 시 store_remote로 교체)."""
from __future__ import annotations
import json
import os
from pathlib import Path
from ..engine.session import GameSession

SAVE_DIR = Path(os.environ.get("FATEBOUND_SAVE_DIR") or
                (Path.home() / ".local" / "share" / "fatebound"))


def _path(slot: str) -> Path:
    return SAVE_DIR / f"{slot}.json"


def has_save(slot: str = "default") -> bool:
    return _path(slot).exists()


def save(session: GameSession, slot: str = "default"):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    p = _path(slot)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)          # 원자적

def load(slot: str = "default") -> GameSession | None:
    p = _path(slot)
    if not p.exists():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return GameSession.from_dict(json.load(f))
    except Exception:
        return None
